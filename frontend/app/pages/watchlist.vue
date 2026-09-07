<template>
  <div class="page-container flex flex-col gap-4">
    <span class="text-2xl font-bold">My Watchlist</span>

    <p
      v-if="loading"
      class="text-dimmed"
    >
      Loading watchlist…
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
      Your watchlist is empty. Add movies from their detail page.
    </p>
    <div
      v-else
      class="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5"
    >
      <div
        v-for="movie in movies"
        :key="movie.entryId"
        class="flex"
      >
        <MovieCard
          class="grow cursor-pointer"
          :name="movie.name"
          :backdrop-path="movie.backdropPath"
          :rating="movie.rating"
          :genre="movie.genre"
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
  await navigateTo('/')
}

const loading = ref(false)
const error = ref<string | null>(null)

const movies = computed(() =>
  interactionsStore.watchlist.map(entry => ({
    entryId: entry.id,
    movieId: entry.movie_detail.id,
    name: entry.movie_detail.title,
    backdropPath: entry.movie_detail.backdrop_path || null,
    rating: entry.movie_detail.tmdb_vote_average ?? 0,
    genre: entry.movie_detail.genres.map(genre => genre.name).join(', ')
  }))
)

loading.value = true
try {
  await interactionsStore.fetchWatchlist()
} catch {
  error.value = 'Could not load your watchlist.'
} finally {
  loading.value = false
}
</script>
