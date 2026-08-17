import logging
from dataclasses import dataclass

import pandas as pd
from replay.nn.lightning import LightningModule
from replay.preprocessing import LabelEncoder

from app.core.config import Settings
from app.ml.variant_builders import (
    VariantSpec,
    build_collaborative_spec,
    build_hybrid_content_spec,
    build_pure_content_spec,
)

logger = logging.getLogger(__name__)


@dataclass
class LoadedVariant:
    spec: VariantSpec
    lightning_module: object  # loaded weights, .eval(), resident in memory for the life of the process


class ModelRegistry:
    """Loaded once at process startup (see app/main.py's lifespan). Nothing
    in here gets reloaded per request — that's the whole point of keeping
    this warm instead of the old batch job's "load checkpoint, score
    everyone, exit" pattern.
    """

    def __init__(self) -> None:
        self.encoder = None
        self.item_id_to_encoded: dict = {}  # raw item_id -> internal id, from encoder.mapping (name-keyed, order-independent)
        self.encoded_to_item_id: dict = {}  # internal id -> raw item_id, from encoder.inverse_mapping
        self.item_features: pd.DataFrame | None = None
        self.item_metadata: pd.DataFrame | None = None  # item_features indexed by encoded item_id
        self.item_titles: dict[int, str] = {}
        self.num_unique_items = 0
        self.max_genres_per_item: int | None = None
        self.variants: dict[str, LoadedVariant] = {}

    def load(self, settings: Settings) -> None:
        logger.info("Loading shared encoder from %s", settings.encoder_path)
        self.encoder = LabelEncoder.load(settings.encoder_path)
        # NOTE: don't use encoder.rules[N] by position anywhere -- LabelEncoder.load()
        # reconstructs .rules via os.walk() over saved rule directories, which is NOT
        # guaranteed to preserve original construction order. encoder.mapping /
        # encoder.inverse_mapping are keyed by column NAME and are safe regardless.
        self.item_id_to_encoded = self.encoder.mapping["item_id"]
        self.encoded_to_item_id = self.encoder.inverse_mapping["item_id"]
        self.num_unique_items = len(self.item_id_to_encoded)

        logger.info("Loading item features from %s", settings.item_features_path)
        self.item_features = pd.read_parquet(settings.item_features_path)
        self.item_metadata = self.item_features.set_index("item_id", drop=False)
        self.item_titles = self.item_metadata["title"].to_dict()
        self.max_genres_per_item = int(self.item_features["genres"].apply(len).max())
        num_genres = int(self.item_features["genres"].explode().dropna().astype(int).max()) + 1

        # embeddings/keyword_embedding both live in item_features_path — confirmed
        # against CBF.ipynb/HBF.ipynb's PATH_ENCODED_FEATURES = ITEM_FEATURES_PATH.
        content_feature_configs = [
            {"name": "embeddings", "path": settings.item_features_path},
            {"name": "keyword_embedding", "path": settings.item_features_path},
        ]

        specs = {
            "collaborative": build_collaborative_spec(self.num_unique_items),
            "hybrid_content": build_hybrid_content_spec(self.num_unique_items, num_genres, content_feature_configs),
            "pure_content": build_pure_content_spec(self.num_unique_items, num_genres, content_feature_configs),
        }

        for name, spec in specs.items():
            logger.info("Loading checkpoint for '%s' from %s", name, settings.checkpoint_paths[name])
            untrained = spec.lightning_module_ctor()
            lightning_module = LightningModule.load_from_checkpoint(
                settings.checkpoint_paths[name], model=untrained.model
            )
            lightning_module.eval()
            self.variants[name] = LoadedVariant(spec=spec, lightning_module=lightning_module)

        logger.info("All 3 variants loaded and warm: %s", sorted(self.variants.keys()))

    @property
    def is_loaded(self) -> bool:
        return len(self.variants) == 3

registry = ModelRegistry()