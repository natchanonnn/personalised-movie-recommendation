# Frontend

Nuxt 4 + Nuxt UI single-page app for the movie recommendation platform: search, movie details, ratings/watchlist, and personalized recommendations.

## Path

```
frontend/
├── app/
│   ├── pages/          # File-based routes (index, movie/[id], my-ratings, watchlist, recommendations, account/*)
│   ├── components/     # MovieCard, MovieHero, MovieRecommendationCard
│   ├── stores/         # Pinia stores: auth.ts, movie.ts, interactions.ts
│   ├── utils/           # tmdb.ts (TMDB image URL helpers)
│   ├── assets/css/      # Global styles
│   └── app.config.ts, app.vue
├── public/              # Static files
├── nuxt.config.ts       # runtimeConfig.public.apiBase points at the backend API
├── Dockerfile
└── package.json
```


## Develop

Requires Node 22+ and pnpm.

### Install dependencies
```bash
pnpm install
```

### Run in development mode
```bash
pnpm dev
```

Other useful commands during development:

```bash
pnpm lint        # eslint
pnpm typecheck   # nuxt typecheck
pnpm build && pnpm preview   # build for production and preview it locally
```

## Deploy

Built and run as a Docker image (see [Dockerfile](Dockerfile)), orchestrated by the root [docker-compose.yml](../docker-compose.yml):

```bash
docker compose up frontend
```
