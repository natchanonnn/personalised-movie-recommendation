<template>
  <div class="page-container flex flex-col gap-4">
    <div class="flex gap-4">
      <UInput
        v-model="searchQuery"
        label="Search"
        placeholder="Search Movies"
        icon="i-lucide-search"
        class="grow"
        @keyup.enter="onSearch"
      />
      <div class="flex gap-2">
        <UButton
          color="neutral"
          variant="subtle"
          @click="onSearch"
        >
          Search
        </UButton>
        <UDrawer
          v-model="isFilterDrawerOpen"
          placement="right"
          :width="300"
          :close-on-esc="true"
        >
          <UButton
            label="Filter"
            color="neutral"
            variant="subtle"
            icon="i-lucide-filter"
          />
          <template #header>
            <span class="text-lg font-medium">Filters</span>
          </template>
          <template #body>
            <div class="flex flex-col gap-4">
              <div class="flex flex-col gap-2">
                <span class="text-sm font-medium">Genre</span>
                <USelect
                  :options="['Action', 'Comedy', 'Drama', 'Horror', 'Romance']"
                  placeholder="Select Genre"
                />
              </div>
              <div class="flex flex-col gap-2">
                <span class="text-sm font-medium">Year</span>
                <USelect
                  :options="['2020', '2021', '2022', '2023  ']"
                  placeholder="Select Year"
                />
              </div>
              <div class="flex flex-col gap-2">
                <span class="text-sm font-medium">Cast / Crew</span>
                <UInputMenu
                  v-model="selectedPersonId"
                  v-model:search-term="personSearchTerm"
                  :items="personItems"
                  :loading="movieStore.peopleLoading"
                  value-key="id"
                  ignore-filter
                  clear
                  icon="i-lucide-user-search"
                  placeholder="Search actor or director"
                  @update:search-term="onPersonSearchInput"
                  @update:model-value="onPersonSelect"
                />
              </div>
            </div>
          </template>
          <template #footer>
            <div class="flex justify-end gap-2">
              <UButton
                color="neutral"
                variant="ghost"
                @click="isFilterDrawerOpen = false"
              >
                Cancel
              </UButton>
              <UButton
                color="primary"
                variant="solid"
                @click="applyFilters"
              >
                Apply
              </UButton>
            </div>
          </template>
        </UDrawer>
      </div>

      <!-- TODO: Add filter dropdown -->
    </div>
    <p
      v-if="interactionsStore.error"
      class="text-error"
    >
      {{ interactionsStore.error }}
    </p>
    <p
      v-if="movieStore.loading"
      class="text-dimmed"
    >
      Loading movies…
    </p>
    <p
      v-else-if="movieStore.error"
      class="text-error"
    >
      {{ movieStore.error }}
    </p>
    <div
      v-else
      class="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5"
    >
      <div
        v-for="movie in movies"
        :key="movie.id"
        class="flex"
      >
        <MovieCard
          :key="movie.id"
          class="grow cursor-pointer"
          :name="movie.name"
          :backdrop-path="movie.backdropPath"
          :rating="movie.rating"
          :genre="movie.genre"
          :show-user-rating="authStore.isAuthenticated"
          @rate="(value) => onRate(movie.tmdbId, value)"
          @click="
            () => {
              $router.push(`/movie/${movie.id}`);
            }
          "
        />
      </div>
    </div>
    <div class="flex justify-end">
      <UPagination
        v-model:page="page"
        :items-per-page="10"
        :total="totalPages * 10"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
const movieStore = useMovieStore()
const authStore = useAuthStore()
const interactionsStore = useInteractionsStore()

const isFilterDrawerOpen = ref(false)
const page = ref(1)
const totalPages = ref(10)

const searchQuery = ref('')
const selectedPersonId = ref<number | null>(null)
const personSearchTerm = ref('')

const personItems = computed(() =>
  movieStore.people.map(person => ({ label: person.name, id: person.id }))
)

let personSearchTimer: ReturnType<typeof setTimeout> | undefined
const onPersonSearchInput = (term: string) => {
  if (personSearchTimer) clearTimeout(personSearchTimer)
  personSearchTimer = setTimeout(() => {
    movieStore.fetchPeople(term).catch(() => {
      // movieStore.people is already cleared on failure; menu just shows no results
    })
  }, 300)
}

const runSearch = async () => {
  try {
    await movieStore.fetchMovies(
      searchQuery.value,
      undefined,
      selectedPersonId.value ?? undefined
    )
  } catch {
    // movieStore.error already holds the message; the template renders it
  }
}

const onSearch = () => {
  runSearch()
}

const applyFilters = () => {
  isFilterDrawerOpen.value = false
  runSearch()
}

const movies = computed(() =>
  movieStore.movies.map(movie => ({
    id: movie.id,
    tmdbId: movie.tmdb_id,
    name: movie.title,
    backdropPath: movie.backdrop_path || null,
    rating: movie.tmdb_vote_average ?? 0,
    genre: movie.genres.map(genre => genre.name).join(', ')
  }))
)

const onRate = async (tmdbId: number, value: number) => {
  // MovieCard only renders the rating widget when :show-user-rating is
  // true (i.e. authStore.isAuthenticated), so this is never reachable
  // while logged out.
  try {
    await interactionsStore.postRating(tmdbId, value)
  } catch {
    // interactionsStore.error already holds the message
  }
}

try {
  await movieStore.fetchMovies()
} catch {
  // movieStore.error already holds the message; the template renders it
}
</script>
