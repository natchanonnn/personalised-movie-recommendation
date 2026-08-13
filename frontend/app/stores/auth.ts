import { defineStore } from 'pinia'

interface User {
  id: number
  username: string
  email: string
  [key: string]: unknown
}

interface TokenPair {
  access: string
  refresh: string
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

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as User | null,
    accessToken: null as string | null,
    refreshToken: null as string | null,
    // avoids firing multiple refresh calls in parallel
    refreshPromise: null as Promise<string> | null
  }),

  getters: {
    isAuthenticated: state => !!state.accessToken
  },

  actions: {
    // Call this once (e.g. in an app plugin) to hydrate tokens from cookies
    // on both server and client.
    initFromCookies() {
      const access = useCookie<string | null>('access_token')
      const refresh = useCookie<string | null>('refresh_token')
      this.accessToken = access.value ?? null
      this.refreshToken = refresh.value ?? null
    },

    persistTokens(tokens: TokenPair) {
      this.accessToken = tokens.access
      this.refreshToken = tokens.refresh

      const access = useCookie('access_token', {
        maxAge: 60 * 5, // match your ACCESS token lifetime, e.g. 5 min
        sameSite: 'lax',
        secure: true,
        httpOnly: false // set true only if you handle cookies purely server-side
      })
      const refresh = useCookie('refresh_token', {
        maxAge: 60 * 60 * 24 * 7, // match your REFRESH token lifetime
        sameSite: 'lax',
        secure: true,
        httpOnly: false
      })
      access.value = tokens.access
      refresh.value = tokens.refresh
    },

    clearTokens() {
      this.accessToken = null
      this.refreshToken = null
      this.user = null

      const access = useCookie('access_token')
      const refresh = useCookie('refresh_token')
      access.value = null
      refresh.value = null
    },

    async login(payload: LoginPayload) {
      const config = useRuntimeConfig()

      const tokens = await $fetch<TokenPair>('/accounts/login/', {
        baseURL: config.public.apiBase,
        method: 'POST',
        body: payload
      })

      this.persistTokens(tokens)
      await this.fetchUser()
      return tokens
    },

    async register(payload: RegisterPayload) {
      const config = useRuntimeConfig()

      return $fetch<{ message: string, user: User }>('/accounts/register/', {
        baseURL: config.public.apiBase,
        method: 'POST',
        body: payload
      })
    },

    async refreshAccessToken(): Promise<string> {
      // If a refresh is already in flight, reuse it instead of firing another
      if (this.refreshPromise) return this.refreshPromise

      if (!this.refreshToken) {
        this.clearTokens()
        throw new Error('No refresh token available')
      }

      const config = useRuntimeConfig()

      this.refreshPromise = $fetch<{ access: string }>('/accounts/token/refresh/', {
        baseURL: config.public.apiBase,
        method: 'POST',
        body: { refresh: this.refreshToken }
      })
        .then((res) => {
          this.accessToken = res.access
          const access = useCookie('access_token', { sameSite: 'lax', secure: true })
          access.value = res.access
          return res.access
        })
        .catch((err) => {
          this.clearTokens()
          throw err
        })
        .finally(() => {
          this.refreshPromise = null
        })

      return this.refreshPromise
    },

    async fetchUser() {
      if (!this.accessToken) return null
      const config = useRuntimeConfig()

      this.user = await $fetch<User>('/accounts/me/', {
        baseURL: config.public.apiBase,
        headers: { Authorization: `Bearer ${this.accessToken}` }
      })
      return this.user
    },

    async logout() {
      const config = useRuntimeConfig()

      if (this.refreshToken) {
        try {
          await $fetch('/accounts/logout/', {
            baseURL: config.public.apiBase,
            method: 'POST',
            body: { refresh: this.refreshToken },
            headers: { Authorization: `Bearer ${this.accessToken}` }
          })
        } catch {
          // token already invalid/expired server-side — fine to proceed
        }
      }

      this.clearTokens()
      await navigateTo('/account/login')
    },

    // Wraps $fetch with automatic access-token attach + one retry on 401
    // via token refresh. Use this for all authenticated API calls.
    async authFetch<T>(url: string, opts: Record<string, unknown> = {}): Promise<T> {
      const config = useRuntimeConfig()

      const doFetch = (token: string | null) =>
        $fetch<T>(url, {
          baseURL: config.public.apiBase,
          ...opts,
          headers: {
            ...(opts.headers as Record<string, string> | undefined),
            ...(token ? { Authorization: `Bearer ${token}` } : {})
          }
        })

      try {
        return await doFetch(this.accessToken)
      } catch (err: any) {
        if (err?.response?.status === 401 && this.refreshToken) {
          const newToken = await this.refreshAccessToken()
          return await doFetch(newToken)
        }
        throw err
      }
    }
  }
})
