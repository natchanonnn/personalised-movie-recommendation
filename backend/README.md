# Backend

Django REST Framework API: accounts (auth), movies (catalogue/search), interactions (ratings/watchlist), and recommendations (proxies the [recommendation service](../recommendation)).

## Path

```
backend/
├── website/             # Project settings, root urls.py, middleware, asgi/wsgi
├── accounts/            # JWT auth: register, login, logout, token refresh, me
├── movies/              # Movie/Person/Genre models, search, detail, import_movies command
│   └── management/commands/import_movies.py
├── interactions/        # Ratings + watchlist (DRF viewsets)
├── recommendations/     # Calls out to the recommendation service
├── manage.py
├── Dockerfile
├── requirements.txt / pyproject.toml / uv.lock
└── .env.example
```

API is mounted under `/v1/`: `/v1/accounts/`, `/v1/movies/`, `/v1/interactions/`, `/v1/recommendations/`. Interactive docs at `/swagger/` (and `/redoc/`), raw schema at `/swagger.json`.

## Develop

Requires Python 3.11 and a Postgres instance.

```bash
uv sync                      # or: pip install -r requirements.txt
cp .env.example .env         # adjust DB_* / SECRET_KEY as needed
python manage.py migrate
python manage.py runserver
```

Serves on `http://localhost:8000`. 

By default it expects Postgres on `localhost:5432` (see `DB_HOST`/`DB_PORT` in `.env`) and the recommendation service at `RECOMMENDATION_SERVICE_URL` (defaults to `http://localhost:8080`, the host-mapped Docker port).

## Deploy

Built and run as a Docker image (see [Dockerfile](Dockerfile)), orchestrated by the root [docker-compose.yml](../docker-compose.yml):

```bash
docker compose up backend
```

## Test

```bash
python manage.py test
```


## Data import

Movies are loaded from a consolidated TMDB CSV export (one row per movie, with cast/crew flattened into `credits.cast` / `credits.crew` JSON columns) via the `import_movies` management command:

```bash
python manage.py import_movies /path/to/movies.csv
```

Options:

- `--limit N` — only process the first N rows
- `--skip N` — skip the first N rows

The command upserts `Movie` rows by `tmdb_id`, and creates/links `Genre`, `Person`, `CastCredit`, and `CrewCredit` rows.
Safe to re-run on the same file.

To snapshot the currently loaded movie catalogue as a fixture (e.g. for handing off a working dataset without the raw CSV), use Django's `dumpdata`:

```bash
python manage.py dumpdata movies --indent 2 > movies_fixture.json
```

and load it with:

```bash
python manage.py loaddata movies_fixture.json
```
