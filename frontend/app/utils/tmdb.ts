const TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p/w500'

export function buildTmdbImageUrl(path?: string | null): string | null {
  if (!path) return null
  return path.startsWith('http') ? path : `${TMDB_IMAGE_BASE}${path}`
}
