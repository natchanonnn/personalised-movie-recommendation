<template>
  <div class="container flex flex-col gap-4">
    <div class="flex gap-4">
      <UInput
        label="Search"
        placeholder="Search Movies"
        icon="i-lucide-search"
        class="grow"
      />
      <div class="flex gap-2">
        <UButton color="neutral" variant="subtle">Search</UButton>
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
            </div>
          </template>
          <template #footer>
            <div class="flex justify-end gap-2">
              <UButton color="neutral" variant="ghost">Cancel</UButton>
              <UButton color="primary" variant="solid" @click="applyFilters"
                >Apply</UButton
              >
            </div>
          </template>
        </UDrawer>
      </div>

      <!-- TODO: Add filter dropdown -->
    </div>
    <div class="flex gap-4 flex-wrap">
      <MovieCard />
      <MovieCard />
      <MovieCard />
      <MovieCard />
      <MovieCard />
      <MovieCard />
      <MovieCard />
    </div>
    <div>
      <!-- TODO: Pagination -->
    </div>
  </div>
</template>

<script setup lang="ts">
const isFilterDrawerOpen = ref(false);
const applyFilters = () => {
  isFilterDrawerOpen.value = false;
};
</script>