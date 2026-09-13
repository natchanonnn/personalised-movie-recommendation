# Recommendation service

FastAPI service that serves live recommendations from the CF / HBF / CBF models (see `../notebooks`), keeping all three checkpoints warm in memory and micro-batching concurrent requests.

## API

- `POST /v1/recommendations` — get recommendations for a user.

  ```bash
  curl -X POST localhost:8080/v1/recommendations \
    -H "Content-Type: application/json" \
    -d '{
      "user_id": "u_123",
      "history": [
        {"item_id": "27205", "rating": 4.5},
        {"item_id": "155", "rating": 5.0}
      ],
      "k": 10
    }'
  ```

  `rating` is optional per history item (only the collaborative variant uses it).

- `GET /health` — reports which of the 3 model variants are loaded.

## Develop

Requires the artifacts produced by `Encoding-3.ipynb` / `CF.ipynb` / `HBF.ipynb` / `CBF.ipynb`: an encoder, an item-features parquet, and 3 checkpoints.

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Set the artifact paths (see `app/core/config.py`), then run:

```bash
REPLAY_ENCODER_PATH=/path/to/encoder \
REPLAY_ITEM_FEATURES_PATH=/path/to/item_features_encoded.parquet \
REPLAY_CKPT_COLLABORATIVE=/path/to/collaborative.ckpt \
REPLAY_CKPT_HYBRID_CONTENT=/path/to/hybrid_content.ckpt \
REPLAY_CKPT_PURE_CONTENT=/path/to/pure_content.ckpt \
uvicorn app.main:app --reload --port 8000
```

Loading all 3 checkpoints takes real wall-clock time before `/health` reports ready.

## Run

Built and run as a Docker image (see [Dockerfile](Dockerfile)), orchestrated by the root [docker-compose.yml](../docker-compose.yml):

```bash
docker compose up recommendation
```

Model artifacts aren't baked into the image — the compose file mounts `./recommendation/replay_artifacts` into the container at `/artifacts`. Place the encoder/checkpoints there before starting.

### Download Artifacts

The trained artifacts can be download from:
https://drive.google.com/drive/folders/1gqrEq-OyGKkFCJb0R-GFoliONDO8YsNV?usp=sharing

Place them in the `recommendation/replay_artifacts` folder.
