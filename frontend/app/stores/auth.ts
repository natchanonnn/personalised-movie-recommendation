import { defineStore } from 'pinia'

interface User {
  id: number
  username: string
  email: string
  [key: string]: unknown
}

interface LoginPayload {
  username: string
  password: string
}

interface RegisterPayload {
  username: string
  email: string
  password: string
  password_confirm: string
}

// JWTs in httpOnly cookies set by Django. credentials: 'include' attaches
// them to cross-origin requests. For SSR, manually forward Cookie header.
function authFetchOptions(headers?: Record<string, string>) {
  return {
    credentials: 'include' as const,
    headers: import.meta.server
      ? { ...useRequestHeaders(['cookie']), ...headers }
      : headers
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as User | null,
    authenticated: false,
    // avoids firing multiple refresh calls in parallel
    refreshPromise: null as Promise<void> | null
  }),

  getters: {
    isAuthenticated: state => state.authenticated
  },

  actions: {
    // Pick up existing session from non-sensitive 'logged_in' marker cookie
    initFromCookies() {
      // useCookie decodes '1' as number 1, so compare truthily
      const marker = useCookie<string | number | null>('logged_in')
      this.authenticated = !!marker.value
    },

    async login(payload: LoginPayload) {
      const config = useRuntimeConfig()

      const result = await $fetch<{ user: User }>('/accounts/login/', {
        baseURL: config.public.apiBase,
        method: 'POST',
        body: payload,
        ...authFetchOptions()
      })

      this.user = result.user
      this.authenticated = true
      return result
    },

    async register(payload: RegisterPayload) {
      const config = useRuntimeConfig()

      return $fetch<{ message: string, user: User }>('/accounts/register/', {
        baseURL: config.public.apiBase,
        method: 'POST',
        body: payload
      })
    },

    async refreshAccessToken(): Promise<void> {
      if (this.refreshPromise) return this.refreshPromise

      const config = useRuntimeConfig()

      this.refreshPromise = $fetch('/accounts/token/refresh/', {
        baseURL: config.public.apiBase,
        method: 'POST',
        ...authFetchOptions()
      })
        .then(() => undefined)
        .catch((err) => {
          this.user = null
          this.authenticated = false
          throw err
        })
        .finally(() => {
          this.refreshPromise = null
        })

      return this.refreshPromise
    },

    async fetchUser() {
      const config = useRuntimeConfig()
      // Call useCookie before await for Nuxt context
      const marker = useCookie('logged_in')
      try {
        this.user = await $fetch<User>('/accounts/me/', {
          baseURL: config.public.apiBase,
          ...authFetchOptions()
        })
        this.authenticated = true
      } catch (err) {
        // Clear 'logged_in' marker to prevent SSR mismatch crash when
        // httpOnly JWT cookies expire. They can't be cleared from JS anyway.
        marker.value = null
        this.user = null
        this.authenticated = false
      }
      return this.user
    },

    async logout() {
      const config = useRuntimeConfig()

      try {
        await $fetch('/accounts/logout/', {
          baseURL: config.public.apiBase,
          method: 'POST',
          ...authFetchOptions()
        })
      } catch {
        // Token already invalid server-side, local state clears below
      }

      this.user = null
      this.authenticated = false
      await navigateTo('/account/login')
    },

    // Wraps $fetch with auth cookies + one retry on 401 via token refresh
    async authFetch<T>(url: string, opts: Record<string, unknown> = {}): Promise<T> {
      const config = useRuntimeConfig()

      const doFetch = () =>
        $fetch<T>(url, {
          baseURL: config.public.apiBase,
          ...opts,
          ...authFetchOptions(opts.headers as Record<string, string> | undefined)
        })

      try {
        return await doFetch()
      } catch (err: any) {
        if (err?.response?.status === 401 && this.authenticated) {
          await this.refreshAccessToken()
          return await doFetch()
        }
        throw err
      }
    }
  }
})
