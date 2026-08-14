from functools import lru_cache

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExperimentVariant(BaseModel):
    name: str
    weight: float


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REPLAY_", env_file=".env", extra="ignore")

    # --- Artifacts from Encoding-3.ipynb -------------------------------------------
    encoder_path: str
    item_features_path: str  # item_id, title, genres, genre_names, item_numerics, embeddings, keyword_embedding

    # --- Checkpoints from CF.ipynb / HBF.ipynb / CBF.ipynb --------------------------
    ckpt_collaborative: str
    ckpt_hybrid_content: str
    ckpt_pure_content: str

    # --- A/B experiment ---------------------------------------------------------------
    experiment_salt: str = "sasrec-ab-v1"
    default_k: int = 10
    max_k: int = 100

    # --- Micro-batching (see services/micro_batcher.py) --------------------------------
    # Requests wait up to max_wait_ms (or until max_batch_size accumulates,
    # whichever comes first) so concurrent requests can share one
    # Trainer.predict() call instead of paying its overhead individually.
    max_wait_ms: int = 75
    max_batch_size: int = 64
    scratch_dir: str = "/tmp/replay_live_scratch"

    @property
    def variants(self) -> list[ExperimentVariant]:
        return [
            ExperimentVariant(name="collaborative", weight=0.34),
            ExperimentVariant(name="hybrid_content", weight=0.33),
            ExperimentVariant(name="pure_content", weight=0.33),
        ]

    @property
    def checkpoint_paths(self) -> dict[str, str]:
        return {
            "collaborative": self.ckpt_collaborative,
            "hybrid_content": self.ckpt_hybrid_content,
            "pure_content": self.ckpt_pure_content,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
