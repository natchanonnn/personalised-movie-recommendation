FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Point these at your downloaded Encoding-3.ipynb output + the 3 checkpoints.
ENV REPLAY_ENCODER_PATH=/artifacts/encoded/encoder \
    REPLAY_ITEM_FEATURES_PATH=/artifacts/encoded/item_features_encoded.parquet \
    REPLAY_CKPT_COLLABORATIVE=/artifacts/checkpoints/collaborative.ckpt \
    REPLAY_CKPT_HYBRID_CONTENT=/artifacts/checkpoints/hybrid_content.ckpt \
    REPLAY_CKPT_PURE_CONTENT=/artifacts/checkpoints/pure_content.ckpt

EXPOSE 8000
# --workers 1: each worker would load its own full set of 3 models into
# memory and run its own micro-batchers -- scale via replicas, not workers.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]