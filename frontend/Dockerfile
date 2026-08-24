FROM node:22-slim AS base
WORKDIR /app
RUN corepack enable

FROM base AS deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

FROM base AS build
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# NUXT_PUBLIC_API_BASE is also read at runtime (see docker-compose.yml) --
# this build-time value is only a fallback for `nuxt build`'s prerendered "/".
ENV NUXT_PUBLIC_API_BASE=http://localhost:8000/v1
# Bundling the Nitro server OOMs at Node's default heap cap (~2GB) inside
# typical Docker build memory limits -- raise it.
ENV NODE_OPTIONS=--max-old-space-size=3072
RUN pnpm build

FROM base AS runner
ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=3000
COPY --from=build /app/.output ./.output

EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
