<template>
  <div class="page-container flex flex-col gap-4">
    <span class="text-2xl font-bold">My Ratings</span>

    <p
      v-if="loading"
      class="text-dimmed"
    >
      Loading your ratings…
    </p>
    <p
      v-else-if="error"
      class="text-error"
    >
      {{ error }}
    </p>
    <p
      v-else-if="!movies.length"
      class="text-dimmed"
    >
      You haven't rated any movies yet.
    </p>
    <div
      v-else
      class="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5"
    >
      <div
        v-for="movie in movies"
        :key="movie.ratingId"
        class="flex"
      >
        <MovieCard
          class="grow cursor-pointer"
          :name="movie.name"
          :backdrop-path="movie.backdropPath"
          :rating="movie.rating"
          :genre="movie.genre"
          show-user-rating
          :user-rating="movie.userRating"
          @click="() => $router.push(`/movie/${movie.movieId}`)"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const authStore = useAuthStore()
const interactionsStore = useInteractionsStore()

if (!authStore.isAuthenticated) {
  await navigateTo('/account/login')
}

const loading = ref(false)
const error = ref<string | null>(null)

const movies = computed(() =>
  interactionsStore.myRatingsList.map(review => ({
    ratingId: review.id,
    movieId: review.movie_detail.id,
    name: review.movie_detail.title,
    backdropPath: review.movie_detail.backdrop_path || null,
    rating: review.movie_detail.tmdb_vote_average ?? 0,
    genre: review.movie_detail.genres.map(genre => genre.name).join(', '),
    userRating: review.score
  }))
)

loading.value = true
try {
  await interactionsStore.fetchMyRatings()
} catch {
  error.value = 'Could not load your ratings.'
} finally {
  loading.value = false
}
</script>
