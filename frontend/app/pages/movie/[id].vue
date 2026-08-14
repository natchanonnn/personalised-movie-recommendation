<template>
  <div class="page-container flex flex-col gap-4">
    <p
      v-if="movieStore.loading"
      class="text-dimmed"
    >
      Loading movie…
    </p>
    <p
      v-else-if="movieStore.error"
      class="text-error"
    >
      {{ movieStore.error }}
    </p>
    <template v-else-if="movie">
      <MovieHero
        :name="movie.name"
        :backdrop-path="movie.backdropPath"
        :release-year="movie.releaseYear"
        :director="movie.director"
        :duration-minutes="movie.durationMinutes"
        :rating="movie.rating"
        :genre="movie.genre"
        :ratings-count="movie.ratingsCount"
      />
      <div
        v-if="authStore.isAuthenticated"
        class="flex"
      >
        <UButton
          :icon="inWatchlist ? 'i-lucide-bookmark-check' : 'i-lucide-bookmark-plus'"
          :color="inWatchlist ? 'primary' : 'neutral'"
          variant="subtle"
          @click="onToggleWatchlist"
        >
          {{ inWatchlist ? 'In Watchlist' : 'Add to Watchlist' }}
        </UButton>
      </div>

      <div
        v-if="authStore.isAuthenticated"
        class="flex flex-col gap-2"
      >
        <span class="text-2xl font-bold">Your rating</span>
        <div
          class="flex items-center gap-2.5"
          role="radiogroup"
          aria-label="Rate this movie"
        >
          <button
            v-for="star in 5"
            :key="star"
            type="button"
            class="flex size-8 items-center justify-center"
            role="radio"
            :aria-checked="star <= userRating"
            :aria-label="`Rate ${star} star${star > 1 ? 's' : ''}`"
            @mouseenter="hoverRating = star"
            @mouseleave="hoverRating = 0"
            @click="onRateMovie(star)"
          >
            <UIcon
              name="i-lucide-star"
              class="size-8"
              :class="
                star <= (hoverRating || userRating)
                  ? 'fill-amber-400 text-amber-400'
                  : 'text-dimmed'
              "
            />
          </button>
        </div>
        <p
          v-if="interactionsStore.error"
          class="text-sm text-error"
        >
          {{ interactionsStore.error }}
        </p>
      </div>

      <div class="flex flex-col gap-2">
        <span class="text-2xl font-bold">Description</span>
        <p class="text-gray-600">
          {{ movie.synopsis || "No description available." }}
        </p>
      </div>

      <div
        v-if="topCast.length"
        class="flex flex-col gap-2"
      >
        <span class="text-2xl font-bold">Cast</span>
        <div class="flex flex-wrap gap-2">
          <div
            v-for="member in topCast"
            :key="member.name + member.character_name"
            class="rounded-lg border border-default bg-elevated px-3 py-2"
          >
            <p class="text-sm font-medium text-highlighted">
              {{ member.name }}
            </p>
            <p
              v-if="member.character_name"
              class="text-xs text-dimmed"
            >
              as {{ member.character_name }}
            </p>
          </div>
        </div>
      </div>

      <div
        v-if="keyCrew.length"
        class="flex flex-col gap-2"
      >
        <span class="text-2xl font-bold">Crew</span>
        <div class="flex flex-wrap gap-4">
          <div
            v-for="member in keyCrew"
            :key="member.name + member.job"
          >
            <p class="text-sm font-medium text-highlighted">
              {{ member.name }}
            </p>
            <p class="text-xs text-dimmed">
              {{ member.job }}
            </p>
          </div>
        </div>
      </div>

      <div class="flex flex-col gap-2">
        <span class="text-2xl font-bold">Ratings</span>
        <p
          v-if="!ratingTotal"
          class="text-dimmed"
        >
          Not rated yet.
        </p>
        <div
          v-else
          class="flex flex-col gap-1"
        >
          <div
            v-for="star in [5, 4, 3, 2, 1]"
            :key="star"
            class="flex items-center gap-2"
          >
            <span class="w-8 shrink-0 text-xs text-dimmed">{{ star }} star</span>
            <div class="h-2 flex-1 overflow-hidden rounded-full bg-elevated">
              <div
                class="h-full rounded-full bg-amber-400"
                :style="{ width: ratingBarWidth(star) + '%' }"
              />
            </div>
            <span class="w-4 shrink-0 text-right text-xs text-dimmed">{{ ratingCounts[star] }}</span>
          </div>
          <p class="text-xs text-dimmed">
            {{ ratingTotal }} total
          </p>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
// Not every crew credit is worth surfacing (dozens of minor roles on a
// typical scraped credits list) -- only show the ones a viewer cares about.
const KEY_CREW_JOBS = ['Director', 'Writer', 'Screenplay', 'Story', 'Producer']
const MAX_CAST_SHOWN = 6

definePageMeta({
  key: route => `movie-${route.params.id}`
})

const route = useRoute()
const movieStore = useMovieStore()
const authStore = useAuthStore()
const interactionsStore = useInteractionsStore()

const topCast = computed(() => {
  const cast = movieStore.movie?.cast ?? []
  return [...cast]
    .sort(
      (a, b) => (a.billing_order ?? Infinity) - (b.billing_order ?? Infinity)
    )
    .slice(0, MAX_CAST_SHOWN)
})

const keyCrew = computed(() => {
  const crew = movieStore.movie?.crew ?? []
  return crew.filter(member => KEY_CREW_JOBS.includes(member.job))
})

const director = computed(
  () =>
    movieStore.movie?.crew?.find(member => member.job === 'Director')?.name
    ?? null
)

const movie = computed(() => {
  const m = movieStore.movie
  if (!m) return null
  return {
    name: m.title,
    backdropPath: m.backdrop_path || null,
    releaseYear: m.release_date ? new Date(m.release_date).getFullYear() : null,
    director: director.value,
    durationMinutes: m.duration_minutes ?? null,
    rating: m.tmdb_vote_average ?? 0,
    genre: m.genres.map(genre => genre.name).join(', '),
    ratingsCount: interactionsStore.ratingSummary?.total ?? 0,
    synopsis: m.synopsis ?? ''
  }
})

const ratingCounts = computed(() => interactionsStore.ratingSummary?.counts ?? {})
const ratingTotal = computed(() => interactionsStore.ratingSummary?.total ?? 0)
const ratingBarWidth = (star: number) => {
  if (!ratingTotal.value) return 0
  return ((ratingCounts.value[star] ?? 0) / ratingTotal.value) * 100
}

try {
  await movieStore.fetchMovieById(route.params.id as string)
  if (movieStore.movie) {
    await interactionsStore.fetchRatingSummary(movieStore.movie.tmdb_id)
    if (authStore.isAuthenticated) {
      await interactionsStore.fetchMyRating(movieStore.movie.tmdb_id)
      await interactionsStore.fetchWatchlistStatus(movieStore.movie.tmdb_id)
    }
  }
} catch {
  // movieStore.error already holds the message; the template renders it
}

const userRating = ref(interactionsStore.myRating?.score ?? 0)
const hoverRating = ref(0)

const onRateMovie = async (value: number) => {
  if (!movieStore.movie) return
  const previous = userRating.value
  userRating.value = value
  try {
    await interactionsStore.postRating(movieStore.movie.tmdb_id, value)
  } catch {
    userRating.value = previous
  }
}

const inWatchlist = computed(
  () => !!movieStore.movie && interactionsStore.isInWatchlist(movieStore.movie.tmdb_id)
)

const onToggleWatchlist = async () => {
  if (!movieStore.movie) return
  try {
    if (inWatchlist.value) {
      await interactionsStore.removeFromWatchlist(movieStore.movie.tmdb_id)
    } else {
      await interactionsStore.addToWatchlist(movieStore.movie.tmdb_id)
    }
  } catch {
    // interactionsStore.error already holds the message
  }
}
</script>

<style>
</style>
