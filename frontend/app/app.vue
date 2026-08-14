<script setup>
useHead({
  meta: [{ name: "viewport", content: "width=device-width, initial-scale=1" }],
  link: [{ rel: "icon", href: "/favicon.ico" }],
  htmlAttrs: {
    lang: "en",
  },
});

const auth = useAuthStore();

// Runs on both server and client render — hydrates tokens from cookies
// before the rest of the app mounts.
auth.initFromCookies();

// Optional: if you want the user profile available immediately too,
// fetch it here (only if we actually have a token).
if (auth.isAuthenticated && !auth.user) {
  await auth.fetchUser();
}

const title = "Movie Recommendation System";
const description =
  "A production-ready starter template powered by Nuxt UI. Build beautiful, accessible, and performant applications in minutes, not hours.";

useSeoMeta({
  title,
  description,
  ogTitle: title,
  ogDescription: description,
  ogImage: "https://ui.nuxt.com/assets/templates/nuxt/starter-light.png",
  twitterCard: "summary_large_image",
});
</script>

<template>
  <UApp>
    <UHeader>
      <template #left>
        <NuxtLink to="/"> Search Movies </NuxtLink>
      </template>
      <div v-if="auth.isAuthenticated" class="flex gap-4">
        <NuxtLink to="/recommendations"> Recommendations </NuxtLink>
        <NuxtLink to="/watchlist"> Watchlist </NuxtLink>
        <NuxtLink to="/my-ratings"> My Ratings </NuxtLink>
      </div>
      <template #body>
        <div v-if="auth.isAuthenticated" class="flex flex-col gap-4">
          <NuxtLink to="/recommendations"> Recommendations </NuxtLink>
          <NuxtLink to="/watchlist"> Watchlist </NuxtLink>
          <NuxtLink to="/my-ratings"> My Ratings </NuxtLink>
        </div>
      </template>

      <template #right>
        <UColorModeButton />
        <UButton
          v-if="!auth.isAuthenticated"
          to="/account/login"
          variant="ghost"
          icon="i-lucide-log-in"
          color="neutral"
          aria-label="Login"
        >
          Login
        </UButton>
        <UButton
          v-else
          @click="auth.logout()"
          variant="ghost"
          color="neutral"
          icon="i-lucide-log-out"
          aria-label="Logout"
        >
          Logout
        </UButton>
      </template>
    </UHeader>

    <UMain>
      <NuxtPage />
    </UMain>
  </UApp>
</template>

<style>
.page-container {
  width: 100vw;
  padding: 20px;
}
</style>