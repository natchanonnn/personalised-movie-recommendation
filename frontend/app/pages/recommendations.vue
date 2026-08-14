<template>
  <div class="page-container flex flex-col gap-4">
    <span class="text-2xl font-bold">Your Personalized Recommendation</span>

    <p
      v-if="movieStore.loading"
      class="text-dimmed"
    >
      Loading recommendations…
    </p>
    <p
      v-else-if="movieStore.error"
      class="text-error"
    >
      {{ movieStore.error }}
    </p>
    <p
      v-else-if="movieStore.recommendationMessage"
      class="text-dimmed"
    >
      {{ movieStore.recommendationMessage }}
    </p>
    <div
      v-else
      class="flex flex-col gap-4"
    >
      <MovieRecommendationCard
        v-for="rec in recommendations"
        :key="rec.id"
        :name="rec.name"
        :backdrop-path="rec.backdropPath"
        :release-year="rec.releaseYear"
        :genre="rec.genre"
        :variant-label="rec.variantLabel"
        :explanation="rec.explanation"
        class="cursor-pointer"
        @click="() => $router.push(`/movie/${rec.id}`)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
const VARIANT_LABELS: Record<string, string> = {
  collaborative: 'Recommender: Collaborative',
  hybrid_content: 'Recommender: Hybrid Content-Based',
  pure_content: 'Recommender: Content-Based'
}

const authStore = useAuthStore()
const movieStore = useMovieStore()

if (!authStore.isAuthenticated) {
  await navigateTo('/')
}

const recommendations = computed(() =>
  movieStore.recommendations.map(rec => ({
    id: rec.id,
    name: rec.title,
    backdropPath: rec.backdrop_path || null,
    releaseYear: rec.release_date ? new Date(rec.release_date).getFullYear() : null,
    genre: rec.genres.map(genre => genre.name).join(', '),
    variantLabel:
      (movieStore.recommendationVariant && VARIANT_LABELS[movieStore.recommendationVariant])
      || movieStore.recommendationVariant,
    explanation: rec.explanation
  }))
)

if (authStore.isAuthenticated) {
  try {
    await movieStore.fetchRecommendations()
  } catch {
    // movieStore.error already holds the message; the template renders it
  }
}
</script>

<style>
</style>
