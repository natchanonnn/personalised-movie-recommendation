<template>
  <div class="container">
    <span class="text-2xl font-medium">Create Account</span>
    <UForm
      ref="createAccountForm"
      :model="form"
      label-position="top"
      class="flex flex-col gap-4"
      @submit="onSubmit"
    >
      <div class="lex flex-col gap-4 max-w-100 w-full-md">
        <div class="flex flex-col gap-4">
          <span class="text-lg font-medium">Username</span>
          <UInput
            v-model="form.username"
            name="username"
          />
        </div>
        <div class="flex flex-col gap-4">
          <span class="text-lg font-medium">Email</span>
          <UInput
            v-model="form.email"
            type="email"
            name="email"
          />
        </div>
        <div class="flex flex-col gap-4">
          <span class="text-lg font-medium">Password</span>
          <UInput
            v-model="form.password"
            type="password"
            name="password"
          />
        </div>
        <div class="flex flex-col gap-4">
          <span class="text-lg font-medium">Confirm Password</span>
          <UInput
            v-model="form.confirmPassword"
            type="password"
            name="confirmPassword"
          />
        </div>
      </div>
      <span
        v-if="error"
        class="text-error"
      >{{ error }}</span>
      <div class="flex flex-col gap-4">
        <UButton
          class="max-w-100 w-full-md"
          type="submit"
          color="neutral"
          variant="solid"
          :loading="loading"
        >
          Create Account
        </UButton>
      </div>
    </UForm>
  </div>
</template>

<script setup lang="ts">
const auth = useAuthStore()

const form = ref({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})
const error = ref('')
const loading = ref(false)

const onSubmit = async () => {
  error.value = ''
  loading.value = true
  try {
    await auth.register({
      username: form.value.username,
      email: form.value.email,
      password: form.value.password,
      password_confirm: form.value.confirmPassword
    })
    await auth.login({
      username: form.value.username,
      password: form.value.password
    })
    await navigateTo('/')
  } catch (err) {
    const data = (err as { data?: Record<string, string[]> })?.data
    error.value
      = data?.email?.[0]
        ?? data?.password?.[0]
        ?? data?.username?.[0]
        ?? 'Could not create account.'
  } finally {
    loading.value = false
  }
}
</script>

<style>
</style>
