"""Each variant gets its own queue + background worker. A request calls
submit() and awaits its Future; the worker drains the queue every
max_wait_ms (or once max_batch_size requests have piled up, whichever
happens first), scores everyone currently waiting in ONE
ParquetModule + Trainer.predict() call, and resolves each request's Future
with its own slice of the result.

This is the whole answer to "live inference through a pipeline whose only
proven entry point is a batch-oriented Trainer.predict() call": pay that
overhead once per window instead of once per request. max_wait_ms is a
direct latency/throughput knob -- 75ms default adds at most 75ms to a
request under load, in exchange for not spinning up a fresh
ParquetModule/Trainer/dataloader for every single call.

The underlying LightningModule is NOT reconstructed here -- it's already
loaded and warm in ModelRegistry. Only the Trainer + ParquetModule +
scratch parquet get rebuilt per batch round, which is far cheaper than
loading a checkpoint.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import lightning as L
import numpy as np
import pandas as pd
from replay.data.nn import ParquetModule
from replay.data.nn.utils import groupby_sequences
from replay.nn.lightning.callback import PandasTopItemsCallback
from replay.nn.lightning.postprocessor import SeenItemsFilter
from replay.nn.transform import CopyTransform, GroupTransform, RenameTransform
from replay.nn.transform.template import make_default_sasrec_transforms

from app.ml.explanations import explain_collaborative, explain_content, explain_hybrid
from app.ml.variant_builders import VariantSpec
from app.services.model_registry import ModelRegistry

logger = logging.getLogger(__name__)


@dataclass
class PendingRequest:
    user_id: str
    history: list  # list[tuple[str, float | None]] -- raw (item_id, rating) pairs, oldest first
    k: int
    future: object = field(default=None)


def _inference_metadata_for(spec: VariantSpec, max_genres_per_item) -> dict:
    metadata = {"predict": {"user_id": {}}}
    for feature_name in spec.tensor_schema.names:
        feature = spec.tensor_schema[feature_name]
        if feature_name == "item_id":
            metadata["predict"]["item_id"] = {"shape": spec.max_seq_len, "padding": feature.padding_value}
        elif feature_name == "rating":
            metadata["predict"]["rating"] = {"shape": spec.max_seq_len, "padding": 0.0}
        elif feature_name == "genres":
            metadata["predict"]["genres"] = {
                "shape": [spec.max_seq_len, max_genres_per_item],
                "padding": feature.padding_value,
            }
        elif feature_name == "item_numerics":
            metadata["predict"]["item_numerics"] = {"shape": [spec.max_seq_len, feature.tensor_dim], "padding": 0.0}
    return metadata


def _histories_from_encoded(encoded_df: pd.DataFrame) -> tuple:
    ordered = encoded_df.sort_values("timestamp")
    content_histories = ordered.groupby("user_id")["item_id"].apply(list).to_dict()
    collab_histories = {
        uid: {"item_id": group["item_id"].tolist(), "rating": group["rating"].tolist()}
        for uid, group in ordered.groupby("user_id")[["item_id", "rating"]]
    }
    return collab_histories, content_histories


class VariantMicroBatcher:
    def __init__(
        self, spec: VariantSpec, registry: ModelRegistry, max_wait_ms: int, max_batch_size: int, scratch_dir: Path
    ) -> None:
        self.spec = spec
        self.registry = registry
        self.max_wait_ms = max_wait_ms
        self.max_batch_size = max_batch_size
        self.scratch_dir = scratch_dir
        self._queue: asyncio.Queue = asyncio.Queue()
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()

    async def submit(self, user_id: str, history: list, k: int) -> list:
        req = PendingRequest(user_id=user_id, history=history, k=k, future=asyncio.get_running_loop().create_future())
        await self._queue.put(req)
        return await req.future

    async def _run(self) -> None:
        while True:
            batch = [await self._queue.get()]
            deadline = asyncio.get_event_loop().time() + self.max_wait_ms / 1000
            while len(batch) < self.max_batch_size:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    break
                try:
                    batch.append(await asyncio.wait_for(self._queue.get(), timeout=remaining))
                except asyncio.TimeoutError:
                    break

            try:
                loop = asyncio.get_event_loop()
                results = await loop.run_in_executor(None, self._score_batch_sync, batch)
                for req, items in zip(batch, results):
                    if not req.future.done():
                        req.future.set_result(items)
            except Exception as exc:  # noqa: BLE001 -- surface to every waiter in this round
                logger.exception("Micro-batch scoring failed for variant '%s'", self.spec.name)
                for req in batch:
                    if not req.future.done():
                        req.future.set_exception(exc)

    def _score_batch_sync(self, batch: list) -> list:
        item_id_to_encoded = self.registry.item_id_to_encoded

        rows = []
        for i, req in enumerate(batch):
            for pos, (raw_item_id, rating) in enumerate(req.history):
                # Mapping keys come from the original encoded interactions'
                # item_id dtype (int64, per Encoding-3.ipynb's astype("int64"))
                # -- cast the incoming string id to match, skip unparseable ids.
                try:
                    lookup_id = int(raw_item_id)
                except (TypeError, ValueError):
                    continue
                encoded_id = item_id_to_encoded.get(lookup_id)
                if encoded_id is None:
                    continue  # item unknown to the trained catalog -- skip, don't error
                rows.append(
                    {"user_id": i, "item_id": encoded_id, "rating": rating if rating is not None else 0.0, "timestamp": pos}
                )
        if not rows:
            return [[] for _ in batch]

        encoded_df = pd.DataFrame(rows)
        # rating is built fresh from the JSON request body, so pandas infers
        # float64 ("Double") by default. genres/item_numerics/embeddings all
        # come from item_features_encoded.parquet, which Encoding-3.ipynb
        # explicitly wrote as float32 -- rating never went through that cast
        # here, and the model's nn.Linear layers are float32 (as trained).
        # Match it explicitly rather than relying on pandas' default inference.
        encoded_df["rating"] = encoded_df["rating"].astype("float32")

        if self.spec.kind == "content":
            # item_metadata is indexed by item_id AND keeps item_id as a column
            # (drop=False, for .loc[] lookups elsewhere) -- merging with on="item_id"
            # against that is ambiguous to pandas (is it the index or the column?).
            # Join against the index explicitly instead.
            encoded_df = encoded_df.merge(
                self.registry.item_metadata[["genres", "item_numerics"]],
                left_on="item_id", right_index=True, how="inner",
            )
            if encoded_df.empty:
                return [[] for _ in batch]

        collab_histories, content_histories = _histories_from_encoded(encoded_df)

        sequences = groupby_sequences(events=encoded_df, groupby_col="user_id", sort_col="timestamp")
        if "rating" in sequences.columns:
            # groupby_sequences itself re-introduces the float64 problem: it
            # extracts each user's per-position rating as a native Python
            # float when building the per-user list, discarding the float32
            # cast above -- confirmed directly (PyArrow schema showed
            # list<double> even though the column going in was float32).
            # item_numerics doesn't need this: it's already array-valued
            # going in, so groupby_sequences just collects the numpy objects
            # without touching their dtype -- only scalar columns get
            # flattened to native Python types this way.
            sequences["rating"] = sequences["rating"].apply(lambda lst: np.asarray(lst, dtype=np.float32))
        predict_path = self.scratch_dir / f"{self.spec.name}_live_{uuid.uuid4().hex}.parquet"
        sequences.to_parquet(predict_path)

        try:
            max_k = max(req.k for req in batch)
            transforms = make_default_sasrec_transforms(self.spec.tensor_schema)

            # All three variants filter seen items at prediction time -- this used
            # to be collaborative-only (CF.ipynb), on the reasoning that HBF.ipynb/
            # CBF.ipynb's own PandasTopItemsCallback calls had no postprocessors and
            # building SeenItemsFilter for content variants was an unvalidated
            # transform pipeline. Both notebooks have since been updated to prove out
            # exactly this override (RenameTransform + CopyTransform + GroupTransform
            # keyed off each variant's own tensor_schema, whether or not it also
            # carries rating/genres/item_numerics) and apply SeenItemsFilter the same
            # way CF.ipynb always did -- so it's applied unconditionally here too.
            item_id_name = self.spec.tensor_schema.item_id_feature_name
            transforms["predict"] = [
                RenameTransform({f"{item_id_name}_mask": "padding_mask"}),
                CopyTransform({item_id_name: "seen_ids"}),
                GroupTransform({"feature_tensors": self.spec.tensor_schema.names}),
            ]
            postprocessors = [
                SeenItemsFilter(item_count=self.registry.num_unique_items, seen_items_column="seen_ids")
            ]

            parquet_module = ParquetModule(
                predict_path=predict_path,
                batch_size=len(batch),
                metadata=_inference_metadata_for(self.spec, self.registry.max_genres_per_item),
                transforms=transforms,
            )
            callback = PandasTopItemsCallback(
                top_k=max_k, query_column="user_id", item_column="item_id", rating_column="score",
                postprocessors=postprocessors,
            )
            trainer = L.Trainer(callbacks=[callback], logger=False, enable_progress_bar=False, inference_mode=True)

            lightning_module = self.registry.variants[self.spec.name].lightning_module
            trainer.predict(lightning_module, datamodule=parquet_module, return_predictions=False)
            result = callback.get_result()
        finally:
            predict_path.unlink(missing_ok=True)

        if result.empty:
            return [[] for _ in batch]

        explanations = []
        if self.spec.kind == "collaborative":
            item_embeddings = lightning_module.model.body.embedder.get_item_weights()
            for row in result.itertuples(index=False):
                history = collab_histories.get(int(row.user_id))
                if not history or not history["item_id"]:
                    explanations.append(None)
                    continue
                rec_item_id = int(row.item_id)
                rec_title = self.registry.item_titles.get(rec_item_id, "Unknown title")
                explanations.append(
                    explain_collaborative(
                        history["item_id"], history["rating"], rec_item_id,
                        item_embeddings, self.registry.item_titles, rec_title,
                    )
                )
        elif self.spec.name == "hybrid_content":
            # hybrid_content is the only content variant whose embedder keeps a real
            # item-id embedding (pure_content zeroes it out in forward()), so it's
            # also the only one that can honestly cite a collaborative-filtering
            # reason alongside the content-based ones. See explain_hybrid's docstring.
            item_collab_embeddings = (
                lightning_module.model.body.embedder.get_item_weights().detach().cpu().numpy()
            )
            for row in result.itertuples(index=False):
                history = content_histories.get(int(row.user_id), [])
                if not history:
                    explanations.append(None)
                    continue
                rec_item_id = int(row.item_id)
                rec_title = self.registry.item_metadata.loc[rec_item_id, "title"]
                explanations.append(
                    explain_hybrid(
                        history, rec_item_id, self.registry.item_metadata,
                        item_collab_embeddings, rec_title,
                    )
                )
        else:
            for row in result.itertuples(index=False):
                history = content_histories.get(int(row.user_id), [])
                if not history:
                    explanations.append(None)
                    continue
                rec_item_id = int(row.item_id)
                rec_title = self.registry.item_metadata.loc[rec_item_id, "title"]
                explanations.append(explain_content(history, rec_item_id, self.registry.item_metadata, rec_title))
        result["explanation"] = explanations

        # Preserve our synthetic per-batch index, and decode item_id directly
        # via the mapping dict -- NOT encoder.inverse_transform(result), which
        # would also try to inverse-transform the "user_id" column (using the
        # real fitted user_id rule) even though it holds our synthetic index,
        # not a real encoded user id. SasRec never consumes user_id as a model
        # input; it's purely our own grouping key here, so it never needs to
        # touch RePlay's encoder machinery at all.
        result["_batch_idx"] = result["user_id"].astype(int)
        result["item_id"] = result["item_id"].astype(int).map(self.registry.encoded_to_item_id)

        per_batch = []
        for i, req in enumerate(batch):
            rows_i = (
                result[result["_batch_idx"] == i]
                .sort_values("score", ascending=False)
                .head(req.k)
            )
            per_batch.append(
                [
                    {"item_id": str(r.item_id), "score": float(r.score), "explanation": r.explanation}
                    for r in rows_i.itertuples(index=False)
                ]
            )
        return per_batch


class MicroBatcherPool:
    def __init__(self, registry: ModelRegistry, max_wait_ms: int, max_batch_size: int, scratch_dir: str) -> None:
        self._batchers: dict[str, VariantMicroBatcher] = {}
        self._registry = registry
        self._max_wait_ms = max_wait_ms
        self._max_batch_size = max_batch_size
        self._scratch_dir = Path(scratch_dir)

    def start(self) -> None:
        self._scratch_dir.mkdir(parents=True, exist_ok=True)
        for name, loaded in self._registry.variants.items():
            batcher = VariantMicroBatcher(
                spec=loaded.spec, registry=self._registry,
                max_wait_ms=self._max_wait_ms, max_batch_size=self._max_batch_size,
                scratch_dir=self._scratch_dir,
            )
            batcher.start()
            self._batchers[name] = batcher

    def stop(self) -> None:
        for batcher in self._batchers.values():
            batcher.stop()

    async def submit(self, variant: str, user_id: str, history: list, k: int) -> list:
        return await self._batchers[variant].submit(user_id, history, k)


pool: MicroBatcherPool | None = None