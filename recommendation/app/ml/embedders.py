"""Transcribed from Content_Based2-4.ipynb / Content_Based3.ipynb (now
HBF.ipynb / CBF.ipynb). Unchanged from the batch-scoring version of this
file — the model architecture doesn't care whether it's being called from
an offline job or a live request.
"""

import torch

from replay.nn.embedding import SequenceEmbedding
from replay.nn.sequential.twotower import FeaturesReader


class _BaseContentAwareEmbedder(torch.nn.Module):
    def __init__(self, train_schema, full_schema, content_feature_configs, embedding_dim):
        super().__init__()
        self.base_embedder = SequenceEmbedding(schema=train_schema)

        self.content_tables = torch.nn.ModuleDict()
        self.projections = torch.nn.ModuleDict()
        self.norms = torch.nn.ModuleDict()

        for cfg in content_feature_configs:
            name = cfg["name"]
            reader = FeaturesReader(schema=full_schema, metadata={name: {}}, path=cfg["path"])
            # Cast explicitly rather than trust the source parquet's dtype --
            # confirmed in practice that keyword_embedding comes out float64
            # (Encoding-3.ipynb used .tolist(), which silently drops a numpy
            # float32 cast down to Python's native double) while embeddings/
            # item_numerics come out float32 correctly (built via list() on
            # the array instead). The model's Linear layers are float32 as
            # trained; defend against any content feature being wrong here
            # rather than depending on every upstream artifact being right.
            table = reader[name].float()
            self.register_buffer(f"content_table_{name}", table)
            self.projections[name] = torch.nn.Linear(table.size(-1), embedding_dim)
            self.norms[name] = torch.nn.LayerNorm(embedding_dim)

        self._feature_names = [cfg["name"] for cfg in content_feature_configs]

    def reset_parameters(self):
        self.base_embedder.reset_parameters()
        for name in self._feature_names:
            torch.nn.init.xavier_uniform_(self.projections[name].weight)


class HybridContentAwareEmbedder(_BaseContentAwareEmbedder):
    """HBF.ipynb: item-id embedding + content features, summed in."""

    def forward(self, feature_tensors, feature_names=None):
        embeddings = self.base_embedder(feature_tensors, feature_names)
        item_ids = feature_tensors["item_id"]

        for name in self._feature_names:
            table = getattr(self, f"content_table_{name}")
            vecs = table[item_ids]
            embeddings[name] = self.norms[name](self.projections[name](vecs))

        return embeddings

    def get_item_weights(self, indices=None):
        return self.base_embedder.get_item_weights(indices)


class PureContentAwareEmbedder(_BaseContentAwareEmbedder):
    """CBF.ipynb: item-id embedding zeroed out, content features only."""

    def forward(self, feature_tensors, feature_names=None):
        embeddings = self.base_embedder(feature_tensors, feature_names)
        item_ids = feature_tensors["item_id"]

        embeddings["item_id"] = torch.zeros_like(embeddings["item_id"])

        for name in self._feature_names:
            table = getattr(self, f"content_table_{name}")
            vecs = table[item_ids]
            embeddings[name] = self.norms[name](self.projections[name](vecs))

        return embeddings

    def get_item_weights(self, indices=None):
        if indices is None:
            first_table = getattr(self, f"content_table_{self._feature_names[0]}")
            indices = torch.arange(first_table.size(0), device=first_table.device)

        total = None
        for name in self._feature_names:
            table = getattr(self, f"content_table_{name}")
            vecs = self.norms[name](self.projections[name](table[indices]))
            total = vecs if total is None else total + vecs
        return total