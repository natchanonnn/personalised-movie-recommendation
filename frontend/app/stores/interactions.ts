import { defineStore } from 'pinia'

interface Review {
  id: number
  movie: number
  movie_title: string
  username: string
  score: number
  review_text: string
  contains_spoilers: boolean
  created_at: string
  updated_at: string
}

export const useInteractionsStore = defineStore('interactions', () => {
  const reviews = ref<Review[]>([])
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
    loading,
    error,
    fetchReviews,
    postRating
  }
})
