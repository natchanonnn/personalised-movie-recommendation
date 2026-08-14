<template>
  <div class="flex w-full items-start gap-2 overflow-hidden rounded-2xl border border-default">
    <div class="relative h-[139px] w-[217px] shrink-0 bg-elevated">
      <img
        v-if="backdropUrl"
        :src="backdropUrl"
        :alt="name"
        class="absolute inset-0 size-full object-cover"
      >
      <div
        v-else
        class="absolute inset-0 flex items-center justify-center"
      >
        <UIcon
          name="i-lucide-videotape"
          class="size-6 text-dimmed"
        />
      </div>
    </div>

    <div class="flex min-w-px flex-1 flex-col gap-2 self-stretch bg-default p-2.5">
      <p class="truncate text-xl font-medium text-highlighted">
        {{ name }}
      </p>

      <div class="flex flex-wrap items-center gap-1">
        <p class="shrink-0 text-xs text-dimmed">
          {{ subtitle }}
        </p>
        <UBadge
          v-if="variantLabel"
          color="neutral"
          variant="solid"
          size="sm"
        >
          {{ variantLabel }}
        </UBadge>
      </div>

      <div
        v-if="explanation"
        class="flex min-h-px flex-1 items-stretch gap-2.5 overflow-hidden bg-error/10"
      >
        <div class="w-2 shrink-0 bg-error" />
        <p class="flex-1 py-4 text-xs text-default">
          {{ explanation }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  backdropPath?: string | null
  name: string
  releaseYear?: number | string | null
  genre?: string
  variantLabel?: string | null
  explanation?: string | null
}>(), {
  backdropPath: null,
  releaseYear: null,
  genre: '',
  variantLabel: null,
  explanation: null
})

const backdropUrl = computed(() => buildTmdbImageUrl(props.backdropPath))

const subtitle = computed(() => [props.releaseYear, props.genre].filter(Boolean).join(' | '))
</script>
