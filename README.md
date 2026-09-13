## Building and Evaluating a Personalized Movie Recommendation System

In this project, you will design, implement, and evaluate your own personal movie discovery platform using a TMDB dataset. Your system will allow a user to search for movies, rate them, and receive personalized recommendations that evolve based on their preferences—similar to the core ideas behind platforms like Netflix.

Rather than simply building an app, you will explore how intelligent systems make decisions. You will experiment with different search and recommendation methods, compare their performance, and investigate how design choices influence the quality of results.

The system must provide a clear, human-readable explanation for why each movie is recommended.

By the end of the project, you will have created a working system that not only functions correctly, but also demonstrates your ability to analyse, evaluate, and justify how and why it works.

## Project structure

```
.
├── frontend/        # Nuxt 4 + Nuxt UI SPA
├── backend/         # Django REST API
├── recommendation/  # FastAPI service serving the models live
├── notebooks/       # Data collection, parsing, encoding, model training, evaluation
├── data/            # Processed datasets
└── docker-compose.yml
```

Each service has its own README with more detail: [frontend](frontend/README.md), [backend](backend/README.md), [recommendation](recommendation/README.md).

## Running with Docker Compose

```bash
cp .env.example .env   # optional — defaults work for local use
docker compose up --build
```

This starts four services:

| Service | URL | Notes |
|---|---|---|
| `db` | internal only (`db:5432`) | Postgres, not published to the host by default |
| `recommendation` | internal only (`recommendation:8000`) | Loads all 3 model checkpoints on startup — mount `./recommendation/replay_artifacts` with the trained artifacts first (see [recommendation/README.md](recommendation/README.md)) |
| `backend` | http://localhost:8000 | Django API, runs migrations on startup |
| `frontend` | http://localhost | Nuxt app, talks to the backend via `NUXT_PUBLIC_API_BASE` |

To bring everything down:

```bash
docker compose down          # add -v to also drop the postgres_data volume
```