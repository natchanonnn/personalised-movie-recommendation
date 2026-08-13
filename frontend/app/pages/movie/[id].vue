<template>
  <div class="container flex flex-col gap-4">
    <MovieHero />
    <div class="flex flex-col gap-2">
      <span class="text-2xl font-bold">Your rating</span>
      <!-- <URating :value="4" /> -->
      <div>TODO: Implement rating component here</div>
      <div class="flex gap-2">
        <UButton color="neutral" variant="subtle">Watch Trailer</UButton>
        <UButton color="primary" variant="solid">Add to Watchlist</UButton>
      </div>
    </div>
    <div class="flex flex-col gap-2">
      <span class="text-2xl font-bold">Description</span>
      <p class="text-gray-600">
        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam auctor,
        nisl eget ultricies tincidunt, nunc nisl aliquam nisl, eget ultricies
        nisl nunc eget nisl.
      </p>
    </div>
    <div class="flex flex-col gap-2">
      <span class="text-2xl font-bold">Cast</span>
      <p class="text-gray-600">
        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam auctor,
        nisl eget ultricies tincidunt, nunc nisl aliquam nisl, eget ultricies
        nisl nunc eget nisl.
      </p>
    </div>
    <div class="flex flex-col gap-2">
      <span class="text-2xl font-bold">Crew</span>
      <p class="text-gray-600">
        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam auctor,
        nisl eget ultricies tincidunt, nunc nisl aliquam nisl, eget ultricies
        nisl nunc eget nisl.
      </p>
    </div>
    <div class="flex flex-col gap-2">
      <span class="text-2xl font-bold">Reviews</span>
      <p class="text-gray-600">
        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam auctor,
        nisl eget ultricies tincidunt, nunc nisl aliquam nisl, eget ultricies
        nisl nunc eget nisl.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style>
</style>