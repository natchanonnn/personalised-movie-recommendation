<template>
  <div
    class="w-[217px] overflow-hidden rounded-2xl border border-default bg-default"
  >
    <div class="relative h-[139px] w-full bg-elevated">
      <img
        v-if="backdropUrl"
        :src="backdropUrl"
        :alt="name"
        class="absolute inset-0 size-full object-cover"
      />
      <div v-else class="absolute inset-0 flex items-center justify-center">
        <UIcon name="i-lucide-videotape" class="size-6 text-dimmed" />
      </div>
    </div>

    <div class="flex flex-col gap-2 p-2.5">
      <p class="truncate text-xl font-medium text-highlighted">
        {{ name }}
      </p>

      <div class="flex items-center gap-2 py-1">
        <div class="flex items-center gap-1">
          <span class="text-[12px] text-amber-600">TMDB</span>
          <UIcon
            name="i-lucide-star"
            class="size-3.5 fill-amber-400 text-amber-400"
          />
          <span class="text-xs text-dimmed">{{ displayRating }}</span>
        </div>
        <span v-if="genre" class="text-xs text-dimmed">{{ genre }}</span>
      </div>
      <div class="flex gap-2" v-if="props.showUserRating">
        <span> Your Rating: </span>
        <div
          class="flex items-center gap-2.5"
          role="radiogroup"
          aria-label="Rate this movie"
        >
          <button
            v-for="star in 5"
            :key="star"
            type="button"
            class="flex size-4 items-center justify-center"
            role="radio"
            :aria-checked="star <= userRating"
            :aria-label="`Rate ${star} star${star > 1 ? 's' : ''}`"
            @mouseenter="hoverRating = star"
            @mouseleave="hoverRating = 0"
            @click.stop="onRate(star)"
          >
            <UIcon
              name="i-lucide-star"
              class="size-4"
              :class="
                star <= (hoverRating || userRating)
                  ? 'fill-amber-400 text-amber-400'
                  : 'text-dimmed'
              "
            />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    backdropPath?: string | null;
    name: string;
    rating?: number;
    genre?: string;
    showUserRating?: boolean;
  }>(),
  {
    backdropPath: null,
    rating: 0,
    genre: "",
    showUserRating: false,
  }
);

const userRating = defineModel<number>("userRating", { default: 0 });

const emit = defineEmits<{ rate: [value: number] }>();

const backdropUrl = computed(() => buildTmdbImageUrl(props.backdropPath));

const displayRating = computed(() => (props.rating / 2).toFixed(1));

const hoverRating = ref(0);

const onRate = (value: number) => {
  userRating.value = value;
  emit("rate", value);
};
</script>
