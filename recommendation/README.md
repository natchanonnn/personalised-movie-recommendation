# Live serving: CF / HBF / CBF (from the latest notebooks)

## What changed from the batch-scoring version

Same three models, same encoder/artifact layout from Encoding-3.ipynb, same
explanation logic transcribed from each notebook — but this now serves
requests live instead of precomputing everyone's recommendations nightly
into SQLite. There's no `recommendations.db` and no scheduled job anymore;
one long-running process holds all three models warm and answers requests
as they arrive.

## The core tension, and how this resolves it

The only proven inference path in these notebooks is `ParquetModule` ->
`Trainer.predict()`. That's inherently batch-shaped machinery — building a
`Trainer`, a `ParquetModule`, and a dataloader has real overhead that's fine
to pay once for a million users overnight, and expensive to pay per HTTP
request.

This design keeps the models permanently loaded (`app/services/model_registry.py`
loads all 3 checkpoints once at startup and never reloads them), and
resolves the batch-shaped-pipeline problem with **micro-batching**
(`app/services/micro_batcher.py`): each variant has its own queue. A
request calls `submit()` and waits; a background worker drains the queue
either after `max_wait_ms` (default 75ms) or once `max_batch_size` (default
64) requests have piled up, whichever comes first, then scores everyone
currently waiting in a single `Trainer.predict()` call and hands each
requester their own slice of the result.

**This is a real latency trade-off, not a free lunch.** A lone request with
no concurrent traffic waits close to the full `max_wait_ms` before being
served (a synthetic test of the isolated batching logic confirmed ~51ms
wait against a configured 50ms window). Under concurrent load, requests
share that wait and the cost amortizes — that's the whole point. Tune
`max_wait_ms` down for lower latency at lower throughput-per-call, or up for
the reverse. If you need genuine sub-10ms single-request latency, that
requires bypassing `ParquetModule`/`Trainer` entirely and calling each
body's `forward()` directly — I did not build that path, because the exact
tensor contract each custom body's `forward()` expects (beyond what
`ParquetModule`'s transforms construct for it) isn't something I've
confirmed from the notebooks, and I'd rather leave that seam explicit than
guess at a raw tensor interface for three different architectures.

## Request shape

There's no stored interaction history to look up anymore — the caller
supplies it directly:

```bash
curl -X POST localhost:8000/v1/recommendations \
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

`rating` is optional per history item — only the collaborative variant uses
it (CF.ipynb's schema includes `rating`; CBF/HBF's doesn't). Send it when
you have it; harmless to omit if the request happens to route to a content
variant.

```bash
curl localhost:8000/health   # reports which of the 3 variants are loaded
```

## One thing I flagged rather than guessed at

`micro_batcher.py`'s `_score_batch_sync` calls
`encoder.rules[1].transform(raw_df)` (the item_id `LabelEncodingRule`) on
raw ids at request time. Every place this rule got used in the notebooks,
it was transforming data the rule had already been fit on
(`interactions_df`, `movie_df`) — never genuinely new values arriving after
the fact. I'm assuming unknown ids come back as droppable (`NaN`, handled
via `dropna`), which is the standard sklearn-style-encoder convention, but
I haven't seen this specific code path exercised in your notebooks against
truly out-of-vocabulary ids. Worth a quick manual check against your
installed RePlay version — if it raises instead of returning `NaN`, that
`dropna` needs to become a `try/except` around the whole transform instead.

## What's still on you

- **`app/core/config.py`** env vars — same artifact paths as before
  (`REPLAY_ENCODER_PATH`, `REPLAY_ITEM_FEATURES_PATH`,
  `REPLAY_CKPT_COLLABORATIVE`/`_HYBRID_CONTENT`/`_PURE_CONTENT`), now read by
  the live process instead of a scoring job.
- **Startup time**: loading 3 checkpoints (the two content variants also
  read their content-feature parquet at construction time, per
  `ContentAwareEmbedder.__init__`) takes real wall-clock time before the
  process is ready. Point your readiness probe at `/health`, not just "port
  is open."
- **Scaling**: each process replica loads all 3 models fully into memory —
  scale by adding replicas behind a load balancer, not by adding uvicorn
  workers within one container (each worker would duplicate all 3 models).
- **`max_wait_ms`/`max_batch_size` tuning**: the defaults (75ms / 64) are a
  starting point, not a measured optimum — you'll want to tune these
  against your actual traffic shape and latency budget.
