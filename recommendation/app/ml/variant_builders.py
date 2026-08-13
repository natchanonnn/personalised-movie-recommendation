"""Reconstructs each notebook's SasRec body from a fitted encoder + known
hyperparameters. Loading a checkpoint only restores weights, so this has to
match each notebook's construction exactly (embedding_dim, num_heads,
num_blocks, dropout, max_seq_len) or `load_state_dict` fails on a shape
mismatch. Unchanged from the batch-scoring module.
"""

from dataclasses import dataclass

import torch
from replay.data import FeatureHint, FeatureSource, FeatureType
from replay.data.nn import TensorFeatureInfo, TensorFeatureSource, TensorSchema
from replay.nn.agg import SumAggregator
from replay.nn.lightning import LightningModule
from replay.nn.loss import CE
from replay.nn.mask import DefaultAttentionMask
from replay.nn.sequential import PositionAwareAggregator, SasRec, SasRecBody, SasRecTransformerLayer

from app.ml.embedders import HybridContentAwareEmbedder, PureContentAwareEmbedder


@dataclass
class VariantSpec:
    name: str
    kind: str  # "collaborative" or "content" — selects which explanation function applies
    lightning_module_ctor: object  # callable() -> LightningModule wrapping a fresh, untrained body
    tensor_schema: TensorSchema
    max_seq_len: int
    required_columns: list[str]


def build_collaborative_spec(num_unique_items: int) -> VariantSpec:
    """Matches CF.ipynb: SasRec.from_params, item_id + rating."""
    from replay.nn.sequential import SasRec as SasRecFromParams

    EMBEDDING_DIM = 64
    MAX_SEQ_LEN = 50
    NUM_HEADS = 2
    NUM_BLOCKS = 2
    DROPOUT = 0.3

    tensor_schema = TensorSchema(
        [
            TensorFeatureInfo(
                name="item_id",
                is_seq=True,
                padding_value=num_unique_items,
                cardinality=num_unique_items,
                embedding_dim=EMBEDDING_DIM,
                feature_type=FeatureType.CATEGORICAL,
                feature_hint=FeatureHint.ITEM_ID,
            ),
            TensorFeatureInfo(
                name="rating",
                is_seq=True,
                feature_type=FeatureType.NUMERICAL,
                tensor_dim=1,
                embedding_dim=EMBEDDING_DIM,
                feature_sources=[TensorFeatureSource(FeatureSource.INTERACTIONS, "rating")],
            ),
        ]
    )

    def ctor() -> LightningModule:
        sasrec = SasRecFromParams.from_params(
            schema=tensor_schema,
            embedding_dim=EMBEDDING_DIM,
            max_sequence_length=MAX_SEQ_LEN,
            num_heads=NUM_HEADS,
            num_blocks=NUM_BLOCKS,
            dropout=DROPOUT,
        )
        return LightningModule(sasrec)

    return VariantSpec(
        name="collaborative",
        kind="collaborative",
        lightning_module_ctor=ctor,
        tensor_schema=tensor_schema,
        max_seq_len=MAX_SEQ_LEN,
        required_columns=["user_id", "item_id", "rating"],
    )


def _build_content_schemas(
    num_unique_items: int, num_genres: int, embedding_dim: int, include_rating: bool
) -> tuple[TensorSchema, TensorSchema]:
    full_schema = TensorSchema(
        [
            TensorFeatureInfo(
                name="item_id",
                is_seq=True,
                feature_type=FeatureType.CATEGORICAL,
                cardinality=num_unique_items,
                padding_value=num_unique_items,
                embedding_dim=embedding_dim,
                feature_hint=FeatureHint.ITEM_ID,
                feature_sources=[TensorFeatureSource(FeatureSource.INTERACTIONS, "item_id")],
            ),
            TensorFeatureInfo(
                name="embeddings",
                is_seq=False,
                feature_type=FeatureType.NUMERICAL_LIST,
                tensor_dim=1024,
                embedding_dim=embedding_dim,
                feature_sources=[TensorFeatureSource(FeatureSource.ITEM_FEATURES, "embeddings")],
            ),
            TensorFeatureInfo(
                name="keyword_embedding",
                is_seq=True,
                feature_type=FeatureType.NUMERICAL_LIST,
                tensor_dim=128,
                embedding_dim=embedding_dim,
                feature_sources=[TensorFeatureSource(FeatureSource.ITEM_FEATURES, "keyword_embedding")],
            ),
        ]
    )

    train_features = [full_schema["item_id"]]
    if include_rating:
        # HBF.ipynb only -- confirmed directly from its train_schema definition.
        # CBF.ipynb's train_schema has no rating feature; verified separately.
        train_features.append(
            TensorFeatureInfo(
                name="rating",
                is_seq=True,
                feature_type=FeatureType.NUMERICAL,
                tensor_dim=1,
                embedding_dim=embedding_dim,  # must match item_id's -- SumAggregator requires it
                feature_sources=[TensorFeatureSource(FeatureSource.INTERACTIONS, "rating")],
            )
        )
    train_features.append(
        TensorFeatureInfo(
            name="genres",
            is_seq=True,
            feature_type=FeatureType.CATEGORICAL_LIST,
            cardinality=num_genres,
            padding_value=num_genres,
            embedding_dim=embedding_dim,
            feature_sources=[TensorFeatureSource(FeatureSource.ITEM_FEATURES, "genres")],
        )
    )
    train_features.append(
        TensorFeatureInfo(
            name="item_numerics",
            is_seq=True,
            feature_type=FeatureType.NUMERICAL_LIST,
            tensor_dim=4,
            embedding_dim=embedding_dim,
            feature_sources=[TensorFeatureSource(FeatureSource.ITEM_FEATURES, "item_numerics")],
        )
    )
    train_schema = TensorSchema(train_features)
    return full_schema, train_schema


def _build_content_body(
    embedder_cls, num_unique_items: int, num_genres: int, content_feature_configs: list[dict], include_rating: bool
) -> tuple[object, TensorSchema, int]:
    EMBEDDING_DIM = 128
    MAX_SEQ_LEN = 60
    NUM_HEADS = 4
    NUM_BLOCKS = 2
    DROPOUT = 0.2

    full_schema, train_schema = _build_content_schemas(num_unique_items, num_genres, EMBEDDING_DIM, include_rating)

    def ctor() -> LightningModule:
        body = SasRecBody(
            embedder=embedder_cls(
                train_schema=train_schema,
                full_schema=full_schema,
                content_feature_configs=content_feature_configs,
                embedding_dim=EMBEDDING_DIM,
            ),
            embedding_aggregator=PositionAwareAggregator(
                embedding_aggregator=SumAggregator(embedding_dim=EMBEDDING_DIM),
                max_sequence_length=MAX_SEQ_LEN,
                dropout=DROPOUT,
            ),
            attn_mask_builder=DefaultAttentionMask(
                reference_feature_name=train_schema.item_id_feature_name,
                num_heads=NUM_HEADS,
            ),
            encoder=SasRecTransformerLayer(
                embedding_dim=EMBEDDING_DIM,
                num_heads=NUM_HEADS,
                num_blocks=NUM_BLOCKS,
                dropout=DROPOUT,
                activation="relu",
                hidden_dim=EMBEDDING_DIM * 4,
            ),
            output_normalization=torch.nn.LayerNorm(EMBEDDING_DIM),
        )
        sasrec = SasRec(body=body, loss=CE(ignore_index=train_schema["item_id"].padding_value))
        return LightningModule(sasrec)

    return ctor, train_schema, MAX_SEQ_LEN


def build_hybrid_content_spec(num_unique_items: int, num_genres: int, content_feature_configs: list[dict]) -> VariantSpec:
    """Matches HBF.ipynb: item-id embedding + content features + rating."""
    ctor, train_schema, max_seq_len = _build_content_body(
        HybridContentAwareEmbedder, num_unique_items, num_genres, content_feature_configs, include_rating=True
    )
    return VariantSpec(
        name="hybrid_content",
        kind="content",
        lightning_module_ctor=ctor,
        tensor_schema=train_schema,
        max_seq_len=max_seq_len,
        required_columns=["user_id", "item_id", "rating", "genres", "item_numerics"],
    )


def build_pure_content_spec(num_unique_items: int, num_genres: int, content_feature_configs: list[dict]) -> VariantSpec:
    """Matches CBF.ipynb: item-id embedding zeroed, content features only, no rating."""
    ctor, train_schema, max_seq_len = _build_content_body(
        PureContentAwareEmbedder, num_unique_items, num_genres, content_feature_configs, include_rating=False
    )
    return VariantSpec(
        name="pure_content",
        kind="content",
        lightning_module_ctor=ctor,
        tensor_schema=train_schema,
        max_seq_len=max_seq_len,
        required_columns=["user_id", "item_id", "genres", "item_numerics"],
    )