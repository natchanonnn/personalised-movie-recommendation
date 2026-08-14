<template>
  <div class="overflow-hidden rounded-2xl border border-default">
    <div class="relative h-[180px] w-full bg-elevated">
      <img
        v-if="backdropUrl"
        :src="backdropUrl"
        :alt="name"
        class="absolute inset-0 size-full object-cover"
      />
      <div v-else class="absolute inset-0 flex items-center justify-center">
        <UIcon name="i-lucide-videotape" class="size-6 text-dimmed" />
      </div>

      <div
        v-if="backdropUrl"
        class="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-black/70 to-transparent"
      />

      <div
        class="absolute inset-x-0 bottom-0 flex flex-col gap-2.5 p-2.5"
        :class="backdropUrl ? 'text-white' : 'text-highlighted'"
      >
        <p class="min-w-full text-3xl leading-9 font-medium">
          {{ name }}
        </p>
        <p v-if="subtitle" class="text-xs whitespace-nowrap">
          {{ subtitle }}
        </p>
      </div>
    </div>

    <div class="flex h-10 w-full items-center gap-2 bg-default p-2.5">
      <div class="flex shrink-0 items-center gap-1">
        <UBadge color="neutral" variant="solid" icon="i-lucide-star" size="md">
          <span class="text-[10px]">TMDB</span>
          {{ displayRating }}
        </UBadge>
      </div>
      <p v-if="genre" class="min-w-px flex-1 truncate text-xs text-dimmed">
        {{ genre }}
      </p>
      <p v-if="ratingsCount != null" class="shrink-0 text-xs text-highlighted">
        {{ ratingsCount.toLocaleString() }} Ratings
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    backdropPath?: string | null;
    name: string;
    releaseYear?: number | string | null;
    director?: string | null;
    durationMinutes?: number | null;
    rating?: number;
    genre?: string;
    ratingsCount?: number | null;
  }>(),
  {
    backdropPath: null,
    releaseYear: null,
    director: null,
    durationMinutes: null,
    rating: 0,
    genre: "",
    ratingsCount: null,
  }
);

const backdropUrl = computed(() => buildTmdbImageUrl(props.backdropPath));

const displayRating = computed(() => (props.rating / 2).toFixed(1));

const subtitle = computed(() =>
  [
    props.releaseYear,
    props.director,
    props.durationMinutes ? `${props.durationMinutes} min` : null,
  ]
    .filter(Boolean)
    .join(" | ")
);
</script>
