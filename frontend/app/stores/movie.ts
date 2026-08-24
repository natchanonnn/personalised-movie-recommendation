import { defineStore } from 'pinia'

interface Genre {
  id: number
  name: string
}

interface CastCredit {
  name: string
  character_name: string
  billing_order: number | null
}

interface CrewCredit {
  name: string
  department: string
  job: string
}

interface Movie {
  id: number
  tmdb_id: number
  title: string
  release_date: string | null
  duration_minutes?: number | null
  genres: Genre[]
  tmdb_vote_average: number | null
  backdrop_path: string
  synopsis?: string
  cast?: CastCredit[]
  crew?: CrewCredit[]
}

interface RecommendedMovie extends Movie {
  score: number
  explanation: string | null
}

interface SearchResponse {
  query: string
  count: number
  results: Movie[]
}

interface RecommendationsResponse {
  detail?: string
  variant: string | null
  results: RecommendedMovie[]
}

interface Person {
  id: number
  name: string
}

interface PersonSearchResponse {
  query: string
  results: Person[]
}

export const useMovieStore = defineStore('movie', () => {
  const movies = ref<Movie[]>([])
  const totalCount = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const movie = ref<Movie | null>(null)

  const recommendations = ref<RecommendedMovie[]>([])
  const recommendationVariant = ref<string | null>(null)
  const recommendationMessage = ref<string | null>(null)

  const people = ref<Person[]>([])
  const peopleLoading = ref(false)

  async function fetchMovies(
    query = '',
    limit = 20,
    personId?: number | string,
    page = 1,
    year?: number | string
  ) {
    const config = useRuntimeConfig()

    loading.value = true
    error.value = null

    try {
      const response = await $fetch<SearchResponse>('/movies/search/', {
        baseURL: config.public.apiBase,
        query: { q: query, limit, person: personId, page, year }
      })
      movies.value = response.results
      totalCount.value = response.count
      return movies.value
    } catch (err) {
      error.value = 'Could not load movies.'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchPeople(query: string, limit = 10) {
    const config = useRuntimeConfig()

    peopleLoading.value = true

    try {
      const response = await $fetch<PersonSearchResponse>('/movies/people/search/', {
        baseURL: config.public.apiBase,
        query: { q: query, limit }
      })
      people.value = response.results
      return people.value
    } catch (err) {
      people.value = []
      throw err
    } finally {
      peopleLoading.value = false
    }
  }

  async function fetchMovieById(movieId: number | string) {
    const config = useRuntimeConfig()

    loading.value = true
    error.value = null

    try {
      const response = await $fetch<Movie>(`/movies/${movieId}/`, {
        baseURL: config.public.apiBase
      })
      movie.value = response
      return movie.value
    } catch (err) {
      error.value = 'Could not load movie.'
      movie.value = null
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchRecommendations(k = 10) {
    const authStore = useAuthStore()

    loading.value = true
    error.value = null

    try {
      const response = await authStore.authFetch<RecommendationsResponse>('/recommendations/', {
        query: { k }
      })
      recommendations.value = response.results
      recommendationVariant.value = response.variant
      recommendationMessage.value = response.results.length === 0 ? (response.detail ?? null) : null
      return recommendations.value
    } catch (err) {
      const data = (err as { data?: { detail?: string } })?.data
      error.value = data?.detail ?? 'Could not load recommendations.'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    movies,
    totalCount,
    movie,
    loading,
    error,
    recommendations,
    recommendationVariant,
    recommendationMessage,
    people,
    peopleLoading,
    fetchMovies,
    fetchMovieById,
    fetchRecommendations,
    fetchPeople
  }
})
