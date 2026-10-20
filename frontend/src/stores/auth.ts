import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '../api/client'
import type { TokenResponse, User } from '../types'

const TOKEN_KEY = 'docflow_token'
const USER_KEY = 'docflow_user'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) || '')
  const user = ref<User | null>(JSON.parse(localStorage.getItem(USER_KEY) || 'null'))
  const loading = ref(false)
  const isAuthenticated = computed(() => Boolean(token.value))

  function applySession(payload: TokenResponse) {
    token.value = payload.access_token
    user.value = payload.user
    localStorage.setItem(TOKEN_KEY, payload.access_token)
    localStorage.setItem(USER_KEY, JSON.stringify(payload.user))
  }

  async function login(form: {
    username: string
    password: string
    captcha_id: string
    captcha_code: string
  }) {
    loading.value = true
    try {
      const { data } = await api.post<TokenResponse>('/auth/login', form)
      applySession(data)
    } finally {
      loading.value = false
    }
  }

  async function register(form: {
    username: string
    password: string
    confirm_password: string
    captcha_id: string
    captcha_code: string
  }) {
    loading.value = true
    try {
      const { data } = await api.post<TokenResponse>('/auth/register', form)
      applySession(data)
    } finally {
      loading.value = false
    }
  }

  async function fetchMe() {
    if (!token.value) return
    const { data } = await api.get<User>('/auth/me')
    user.value = data
    localStorage.setItem(USER_KEY, JSON.stringify(data))
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  return { token, user, loading, isAuthenticated, login, register, fetchMe, logout }
})
