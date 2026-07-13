import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '../services/api'
import {
  clearAuthStorage,
  getAccessToken,
  getRefreshToken,
  getStoredLearnerId,
  getStoredUser,
  setStoredLearnerId,
  setStoredUser,
  setTokens,
} from '../services/auth-storage'
import type { UserSummary } from '../types/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserSummary | null>(getStoredUser())
  const learnerId = ref(getStoredLearnerId())
  const restoring = ref(false)
  const isAuthenticated = computed(() => Boolean(getAccessToken()))
  const isAdmin = computed(() => Boolean(user.value?.roles.includes('admin')))

  async function login(username: string, password: string): Promise<void> {
    const pair = await api.login(username, password)
    setTokens(pair.access_token, pair.refresh_token)
    setStoredUser(pair.user)
    user.value = pair.user
    learnerId.value = pair.user.learner_id || learnerId.value || 'stu_001'
    setStoredLearnerId(learnerId.value)
  }

  async function restore(): Promise<void> {
    if (!getAccessToken() || restoring.value) return
    restoring.value = true
    try {
      const currentUser = await api.me()
      user.value = currentUser
      setStoredUser(currentUser)
      if (currentUser.learner_id) setLearnerId(currentUser.learner_id)
    } catch {
      clearAuthStorage()
      user.value = null
    } finally {
      restoring.value = false
    }
  }

  function setLearnerId(value: string): void {
    learnerId.value = value.trim() || 'stu_001'
    setStoredLearnerId(learnerId.value)
  }

  async function logout(): Promise<void> {
    const refreshToken = getRefreshToken()
    if (refreshToken) {
      try {
        await api.logout(refreshToken)
      } catch {
        // Local logout still proceeds when the backend session is unavailable.
      }
    }
    clearAuthStorage()
    user.value = null
  }

  return {
    user,
    learnerId,
    restoring,
    isAuthenticated,
    isAdmin,
    login,
    restore,
    setLearnerId,
    logout,
  }
})
