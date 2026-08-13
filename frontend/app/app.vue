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

const title = "Nuxt Starter Template";
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
        <NuxtLink to="/"> Recommended System </NuxtLink>
        <TemplateMenu />
      </template>

      <div>
        TODO: Navigation menu goes here. For example, you could add a link to
        the login page:
      </div>

      <template #right>
        <UColorModeButton />

        <!-- <UButton TODO: Change to user profile menu when logged in
          to="https://github.com/nuxt-ui-templates/starter"
          target="_blank"
          icon="i-simple-icons-github"
          aria-label="GitHub"
          color="neutral"
          variant="ghost"
        /> -->
      </template>
    </UHeader>

    <UMain>
      <NuxtPage />
    </UMain>

    <USeparator icon="i-simple-icons-nuxtdotjs" />

    <UFooter>
      <template #left>
        <p class="text-sm text-muted">
          Built with Nuxt UI • © {{ new Date().getFullYear() }}
        </p>
      </template>

      <template #right>
        <UButton
          to="https://github.com/nuxt-ui-templates/starter"
          target="_blank"
          icon="i-simple-icons-github"
          aria-label="GitHub"
          color="neutral"
          variant="ghost"
        />
      </template>
    </UFooter>
  </UApp>
</template>

<style>
.container {
  margin: 32px;
  padding: 20px;
}
</style>