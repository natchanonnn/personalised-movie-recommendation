<template>
  <div class="page-container">
    <span class="text-2xl font-medium">Login</span>
    <UForm
      ref="loginForm"
      :model="form"
      label-position="top"
      class="flex flex-col gap-4"
      @submit="onSubmit"
    >
      <div class="lex flex-col gap-4 max-w-100 w-full-md">
        <div class="flex flex-col gap-4">
          <span class="text-lg font-medium">Username</span>
          <UInput v-model="form.username" name="username" />
        </div>
        <div class="flex flex-col gap-4">
          <span class="text-lg font-medium">Password</span>
          <UInput v-model="form.password" type="password" name="password" />
        </div>
      </div>
      <span v-if="error" class="text-error">{{ error }}</span>
      <div class="flex flex-col gap-4">
        <UButton
          class="max-w-100 w-full-md"
          type="submit"
          color="neutral"
          variant="solid"
          :loading="loading"
        >
          Login
        </UButton>
        <span class="text-sm text-dimmed">
          Don't have an account?
          <RouterLink to="/account/create" class="text-neutral font-medium">
            Register here
          </RouterLink>
        </span>
      </div>
    </UForm>
  </div>
</template>

<script setup lang="ts">
const auth = useAuthStore();

const form = ref({
  username: "",
  password: "",
});
const error = ref("");
const loading = ref(false);

const onSubmit = async () => {
  error.value = "";
  loading.value = true;
  try {
    await auth.login(form.value);
    await navigateTo("/");
  } catch (err) {
    const data = (err as { data?: { detail?: string } })?.data;
    error.value = data?.detail ?? "Invalid username or password.";
  } finally {
    loading.value = false;
  }
};
</script>

<style>
</style>
