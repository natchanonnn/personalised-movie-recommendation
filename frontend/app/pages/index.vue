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
        <UButton color="neutral" variant="subtle" @click="onSearch">
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
                  v-model="selectedGenre"
                  :items="['Action', 'Comedy', 'Drama', 'Horror', 'Romance']"
                  placeholder="Select Genre"
                />
              </div>
              <div class="flex flex-col gap-2">
                <span class="text-sm font-medium">Year</span>
                <UInput
                  v-model="selectedYear"
                  type="number"
                  placeholder="Search Year"
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
            <div class="flex justify-between gap-2">
              <UButton color="neutral" variant="ghost" @click="clearFilters">
                Clear
              </UButton>
              <div class="flex gap-2">
                <UButton
                  color="neutral"
                  variant="ghost"
                  @click="isFilterDrawerOpen = false"
                >
                  Cancel
                </UButton>
                <UButton color="primary" variant="solid" @click="applyFilters">
                  Apply
                </UButton>
              </div>
            </div>
          </template>
        </UDrawer>
      </div>

      <!-- TODO: Add filter dropdown -->
    </div>
    <p v-if="interactionsStore.error" class="text-error">
      {{ interactionsStore.error }}
    </p>
    <p v-if="movieStore.loading" class="text-dimmed">Loading movies…</p>
    <p v-else-if="movieStore.error" class="text-error">
      {{ movieStore.error }}
    </p>
    <div
      v-else
      class="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5"
    >
      <div v-for="movie in movies" :key="movie.id" class="flex">
        <MovieCard
          :key="movie.id"
          class="grow cursor-pointer"
          :name="movie.name"
          :backdrop-path="movie.backdropPath"
          :rating="movie.rating"
          :genre="movie.genre"
          :show-user-rating="authStore.isAuthenticated"
          :user-rating="interactionsStore.myRatings[movie.tmdbId] ?? 0"
          @rate="(value) => onRate(movie.tmdbId, value)"
          @click="
            () => {
              $router.push(`/movie/${movie.id}`);
            }
          "
        />
      </div>
    </div>
    <div v-if="movieStore.totalCount > PAGE_SIZE" class="flex justify-end">
      <UPagination
        :page="page"
        :items-per-page="PAGE_SIZE"
        :total="movieStore.totalCount"
        @update:page="onPageChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
const movieStore = useMovieStore();
const authStore = useAuthStore();
const interactionsStore = useInteractionsStore();

const PAGE_SIZE = 20;

const isFilterDrawerOpen = ref(false);
const page = ref(1);

const searchQuery = ref("");
const selectedGenre = ref<string | null>(null);
// UInput's type="number" coerces this to a number once a valid digit is
// typed, but leaves it as an empty string while the field is being cleared
// -- both are handled fine by runSearch's `?? undefined` and the backend's
// falsy check.
const selectedYear = ref<number | string | null>(null);
const selectedPersonId = ref<number | null>(null);
const personSearchTerm = ref("");

const personItems = computed(() =>
  movieStore.people.map((person) => ({ label: person.name, id: person.id }))
);

let personSearchTimer: ReturnType<typeof setTimeout> | undefined;
const onPersonSearchInput = (term: string) => {
  if (personSearchTimer) clearTimeout(personSearchTimer);
  personSearchTimer = setTimeout(() => {
    movieStore.fetchPeople(term).catch(() => {
      // movieStore.people is already cleared on failure; menu just shows no results
    });
  }, 300);
};

const runSearch = async () => {
  try {
    await movieStore.fetchMovies(
      searchQuery.value,
      PAGE_SIZE,
      selectedPersonId.value ?? undefined,
      page.value,
      selectedYear.value ?? undefined
    );
  } catch {
    // movieStore.error already holds the message; the template renders it
  }
};

// A new search/filter invalidates the current page position, so it resets
// to 1. Bound to UPagination imperatively (not v-model) so a page change
// only ever triggers one fetch, never two.
const onPageChange = (newPage: number) => {
  page.value = newPage;
  runSearch();
};

const onSearch = () => {
  page.value = 1;
  runSearch();
};

const applyFilters = () => {
  isFilterDrawerOpen.value = false;
  page.value = 1;
  runSearch();
};

// Resets every filter field back to empty and re-runs the search so the
// results reflect the clear immediately, without requiring a separate Apply.
const clearFilters = () => {
  selectedGenre.value = null;
  selectedYear.value = null;
  selectedPersonId.value = null;
  personSearchTerm.value = "";
  page.value = 1;
  runSearch();
};

const movies = computed(() =>
  movieStore.movies.map((movie) => ({
    id: movie.id,
    tmdbId: movie.tmdb_id,
    name: movie.title,
    backdropPath: movie.backdrop_path || null,
    rating: movie.tmdb_vote_average ?? 0,
    genre: movie.genres.map((genre) => genre.name).join(", "),
  }))
);

const onRate = async (tmdbId: number, value: number) => {
  // MovieCard only renders the rating widget when :show-user-rating is
  // true (i.e. authStore.isAuthenticated), so this is never reachable
  // while logged out.
  try {
    await interactionsStore.postRating(tmdbId, value);
  } catch {
    // interactionsStore.error already holds the message
  }
};

try {
  await movieStore.fetchMovies("", PAGE_SIZE, undefined, page.value);
} catch {
  // movieStore.error already holds the message; the template renders it
}

if (authStore.isAuthenticated) {
  interactionsStore.fetchMyRatings().catch(() => {
    // interactionsStore.myRatings stays empty; cards just show unrated stars
  });
}
</script>
