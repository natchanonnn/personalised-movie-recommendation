import { defineStore } from 'pinia'

interface MovieDetail {
  id: number
  tmdb_id: number
  title: string
  release_date: string | null
  genres: { id: number, name: string }[]
  tmdb_vote_average: number | null
  backdrop_path: string
}

interface Review {
  id: number
  movie: number
  movie_detail: MovieDetail
  movie_title: string
  username: string
  score: number
  review_text: string
  contains_spoilers: boolean
  created_at: string
  updated_at: string
}

interface RatingSummary {
  movie: number
  total: number
  counts: Record<string, number>
}

interface WatchlistEntry {
  id: number
  movie: number
  movie_detail: MovieDetail
  movie_title: string
  added_at: string
}

export const useInteractionsStore = defineStore('interactions', () => {
  const reviews = ref<Review[]>([])
  const ratingSummary = ref<RatingSummary | null>(null)
  const myRating = ref<Review | null>(null)
  // Keyed by movie tmdb_id -- lets list views (e.g. the search page) show a
  // logged-in user's own star rating on every card without a per-movie
  // request.
  const myRatings = ref<Record<number, number>>({})
  // Full rows (with movie_detail) behind the map above -- the "My Ratings"
  // page renders straight from this instead of re-fetching.
  const myRatingsList = ref<Review[]>([])
  const watchlist = ref<WatchlistEntry[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchReviews(movieTmdbId: number | string) {
    const config = useRuntimeConfig()

    loading.value = true
    error.value = null

    try {
      const response = await $fetch<Review[]>('/interactions/ratings/', {
        baseURL: config.public.apiBase,
        query: { movie: movieTmdbId }
      })
      reviews.value = response
      return reviews.value
    } catch (err) {
      error.value = 'Could not load reviews.'
      throw err
    } finally {
      loading.value = false
    }
  }

  // Counts per star bucket, not the raw rows -- for rendering a
  // distribution instead of a per-user list.
  async function fetchRatingSummary(movieTmdbId: number | string) {
    const config = useRuntimeConfig()

    try {
      const response = await $fetch<RatingSummary>('/interactions/ratings/summary/', {
        baseURL: config.public.apiBase,
        query: { movie: movieTmdbId }
      })
      ratingSummary.value = response
      return response
    } catch (err) {
      ratingSummary.value = null
      throw err
    }
  }

  // Just the current user's own rating for a movie (0 or 1 rows), to
  // pre-fill a "your rating" widget without fetching everyone else's.
  async function fetchMyRating(movieTmdbId: number | string) {
    const authStore = useAuthStore()

    try {
      const response = await authStore.authFetch<Review[]>('/interactions/ratings/', {
        query: { movie: movieTmdbId, mine: 1 }
      })
      myRating.value = response[0] ?? null
      return myRating.value
    } catch (err) {
      myRating.value = null
      throw err
    }
  }

  // All of the current user's ratings across every movie, for pre-filling
  // the star widget on list views (search results, recommendations) instead
  // of just a single movie's detail page.
  async function fetchMyRatings() {
    const authStore = useAuthStore()

    try {
      const response = await authStore.authFetch<Review[]>('/interactions/ratings/', {
        query: { mine: 1 }
      })
      myRatingsList.value = response
      myRatings.value = Object.fromEntries(response.map(review => [review.movie, review.score]))
      return myRatings.value
    } catch (err) {
      myRatingsList.value = []
      myRatings.value = {}
      throw err
    }
  }

  // Current user's watchlist, movie_detail included so the watchlist page
  // can render MovieCard directly from this response.
  async function fetchWatchlist() {
    const authStore = useAuthStore()

    try {
      const response = await authStore.authFetch<WatchlistEntry[]>('/interactions/watchlist/')
      watchlist.value = response
      return watchlist.value
    } catch (err) {
      watchlist.value = []
      throw err
    }
  }

  // Just this movie's entry (0 or 1 rows), to prime watchlist state for a
  // single-movie view (the detail page) without loading the whole list.
  // Merges into `watchlist` rather than replacing it, so it composes with
  // fetchWatchlist.
  async function fetchWatchlistStatus(movieTmdbId: number | string) {
    const authStore = useAuthStore()

    const response = await authStore.authFetch<WatchlistEntry[]>('/interactions/watchlist/', {
      query: { movie: movieTmdbId }
    })
    const entry = response[0] ?? null
    if (entry) {
      const index = watchlist.value.findIndex(e => e.id === entry.id)
      if (index >= 0) watchlist.value[index] = entry
      else watchlist.value = [entry, ...watchlist.value]
    }
    return entry
  }

  function isInWatchlist(movieTmdbId: number) {
    return watchlist.value.some(entry => entry.movie === movieTmdbId)
  }

  async function addToWatchlist(movieTmdbId: number | string) {
    const authStore = useAuthStore()

    error.value = null
    try {
      const entry = await authStore.authFetch<WatchlistEntry>('/interactions/watchlist/', {
        method: 'POST',
        body: { movie: movieTmdbId }
      })
      const index = watchlist.value.findIndex(e => e.id === entry.id)
      if (index >= 0) watchlist.value[index] = entry
      else watchlist.value = [entry, ...watchlist.value]
      return entry
    } catch (err) {
      error.value = 'Could not update your watchlist.'
      throw err
    }
  }

  // Looks the entry up by movie id in the already-loaded `watchlist` --
  // callers that haven't loaded it yet should fetchWatchlistStatus first.
  async function removeFromWatchlist(movieTmdbId: number) {
    const authStore = useAuthStore()

    const entry = watchlist.value.find(e => e.movie === movieTmdbId)
    if (!entry) return

    error.value = null
    try {
      await authStore.authFetch(`/interactions/watchlist/${entry.id}/`, { method: 'DELETE' })
      watchlist.value = watchlist.value.filter(e => e.id !== entry.id)
    } catch (err) {
      error.value = 'Could not update your watchlist.'
      throw err
    }
  }

  // Upserts, matching the backend's one-row-per-(user,movie) Rating design
  // -- rating the same movie again edits the existing review instead of
  // creating a new one.
  async function postRating(
    movieTmdbId: number | string,
    score: number,
    reviewText = '',
    containsSpoilers = false
  ) {
    const authStore = useAuthStore()

    loading.value = true
    error.value = null

    try {
      const response = await authStore.authFetch<Review>('/interactions/ratings/', {
        method: 'POST',
        body: {
          movie: movieTmdbId,
          score,
          review_text: reviewText,
          contains_spoilers: containsSpoilers
        }
      })

      const index = reviews.value.findIndex(review => review.id === response.id)
      if (index >= 0) reviews.value[index] = response
      else reviews.value = [response, ...reviews.value]

      myRating.value = response
      myRatings.value[response.movie] = response.score
      const myIndex = myRatingsList.value.findIndex(review => review.id === response.id)
      if (myIndex >= 0) myRatingsList.value[myIndex] = response
      else myRatingsList.value = [response, ...myRatingsList.value]
      fetchRatingSummary(movieTmdbId).catch(() => {})

      return response
    } catch (err) {
      error.value = 'Could not save your rating.'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    reviews,
    ratingSummary,
    myRating,
    myRatings,
    myRatingsList,
    watchlist,
    loading,
    error,
    fetchReviews,
    fetchRatingSummary,
    fetchMyRating,
    fetchMyRatings,
    postRating,
    fetchWatchlist,
    fetchWatchlistStatus,
    isInWatchlist,
    addToWatchlist,
    removeFromWatchlist
  }
})
