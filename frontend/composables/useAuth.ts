import { computed } from 'vue'

interface AuthUser {
  id: string
  username: string
  role?: string
}

interface AuthResponse {
  success: boolean
  message?: string
  token?: string
  user?: AuthUser
}

const restorePromise: { value?: Promise<void> } = {}

export function useAuth() {
  const user = useState<AuthUser | null>('auth-user', () => null)
  const loading = useState<boolean>('auth-loading', () => false)
  const error = useState<string>('auth-error', () => '')
  const tokenCookie = useCookie<string | null>('auth_token', { sameSite: 'lax' })
  const userCookie = useCookie<AuthUser | null>('auth_user', { sameSite: 'lax' })
  const isAuthenticated = computed(() => Boolean(tokenCookie.value && user.value))

  const setSession = (payload: { token: string; user: AuthUser }) => {
    tokenCookie.value = payload.token
    userCookie.value = payload.user
    user.value = payload.user
  }

  const clearSession = () => {
    tokenCookie.value = null
    userCookie.value = null
    user.value = null
  }

  const restoreSession = async () => {
    if (restorePromise.value) return restorePromise.value
    restorePromise.value = (async () => {
      if (userCookie.value && !user.value) {
        user.value = userCookie.value
      }
      if (tokenCookie.value && !user.value) {
        try {
          const profile = await $fetch<AuthResponse>('/api/auth/profile', {
            headers: { Authorization: `Bearer ${tokenCookie.value}` }
          })
          if (profile?.success && profile.user) {
            setSession({ token: tokenCookie.value as string, user: profile.user })
          } else {
            clearSession()
          }
        } catch (err) {
          console.warn('restoreSession failed', err)
          clearSession()
        }
      }
    })()
    return restorePromise.value
  }

  const login = async (payload: { username: string; password: string }) => {
    loading.value = true
    error.value = ''
    try {
      const res = await $fetch<AuthResponse>('/api/auth/login', { method: 'POST', body: payload })
      if (res?.success && res.token && res.user) {
        setSession({ token: res.token, user: res.user })
        return { success: true }
      }
      const msg = res?.message || '登录失败'
      error.value = msg
      return { success: false, message: msg }
    } catch (err: any) {
      const msg = err?.data?.message || err?.message || '登录异常'
      error.value = msg
      return { success: false, message: msg }
    } finally {
      loading.value = false
    }
  }

  const register = async (payload: { username: string; password: string; confirm?: string }) => {
    loading.value = true
    error.value = ''
    try {
      const res = await $fetch<AuthResponse>('/api/auth/register', { method: 'POST', body: payload })
      if (res?.success && res.token && res.user) {
        setSession({ token: res.token, user: res.user })
        return { success: true }
      }
      const msg = res?.message || '注册失败'
      error.value = msg
      return { success: false, message: msg }
    } catch (err: any) {
      const msg = err?.data?.message || err?.message || '注册异常'
      error.value = msg
      return { success: false, message: msg }
    } finally {
      loading.value = false
    }
  }

  const logout = () => {
    clearSession()
  }

  if (process.client) restoreSession()

  return {
    user,
    loading,
    error,
    isAuthenticated,
    login,
    register,
    logout,
    restoreSession
  }
}
