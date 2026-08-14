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

// The JWTs live in httpOnly cookies Django sets directly -- this store
// never holds or reads a token value. `credentials: 'include'` is what
// makes the browser attach those cookies to a cross-origin request to the
// API. During SSR there's no browser doing that on our behalf, so the
// incoming request's Cookie header has to be forwarded by hand.
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
    // Call this once (e.g. in app.vue) to pick up whether a session already
    // exists, from the non-sensitive `logged_in` marker cookie Django sets
    // alongside the real (httpOnly) token cookies -- it carries no token
    // material, just a "you're logged in" flag readable on first paint.
    initFromCookies() {
      // useCookie decodes with destr, so the literal value "1" comes back
      // as the *number* 1, not the string '1' -- compare loosely/truthily
      // rather than against a specific string.
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

      this.user = await $fetch<User>('/accounts/me/', {
        baseURL: config.public.apiBase,
        ...authFetchOptions()
      })
      this.authenticated = true
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
        // token already invalid/expired server-side -- fine to proceed,
        // local state gets cleared either way below.
      }

      this.user = null
      this.authenticated = false
      await navigateTo('/account/login')
    },

    // Wraps $fetch with the auth cookies attached + one retry on 401 via
    // token refresh. Use this for all authenticated API calls.
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
