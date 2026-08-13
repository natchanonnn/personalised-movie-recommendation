<template>
  <div class="movie-card grow">
    <div class="movie-card__poster">
      <span class="movie-card__poster-backdrop"></span>
      <span class="movie-card__poster-overlay"></span>
    </div>
    <div class="movie-card__details">
      <span class="movie-card__title">Movie Title</span>
      <span class="movie-card__meta">Genre • Year</span>
    </div>
  </div>
</template>

<style scoped>
.movie-card {
  height: 239px;
  border-radius: 16px;
  background: #f8fafc;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.movie-card__poster {
  flex: 1;
  position: relative;
  background: #e2e8f0;
}

.movie-card__poster-backdrop,
.movie-card__poster-overlay {
  position: absolute;
  inset: 0;
}

.movie-card__poster-backdrop {
  background: linear-gradient(180deg, #eef2ff 0%, #e2e8f0 100%);
}

.movie-card__poster-overlay {
  background: radial-gradient(
      circle at 30% 30%,
      rgba(255, 255, 255, 0.75),
      transparent 35%
    ),
    radial-gradient(circle at 70% 40%, rgba(252, 200, 0, 0.25), transparent 30%);
}

.movie-card__details {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: white;
}

.movie-card__title {
  display: block;
  font-size: 14px;
  font-weight: 700;
  color: #0f172b;
}

.movie-card__meta {
  display: block;
  font-size: 12px;
  color: #64748b;
}
</style>