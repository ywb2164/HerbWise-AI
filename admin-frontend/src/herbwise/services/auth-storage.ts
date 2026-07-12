import type { UserSummary } from '../types/api'

const ACCESS_TOKEN_KEY = 'herbwise.access_token'
const REFRESH_TOKEN_KEY = 'herbwise.refresh_token'
const USER_KEY = 'herbwise.user'
const LEARNER_KEY = 'herbwise.learner_id'

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function setTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
}

export function getStoredUser(): UserSummary | null {
  const value = localStorage.getItem(USER_KEY)
  if (!value) return null
  try {
    return JSON.parse(value) as UserSummary
  } catch {
    localStorage.removeItem(USER_KEY)
    return null
  }
}

export function setStoredUser(user: UserSummary): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
  if (user.learner_id) localStorage.setItem(LEARNER_KEY, user.learner_id)
}

export function getStoredLearnerId(): string {
  return localStorage.getItem(LEARNER_KEY) || 'stu_001'
}

export function setStoredLearnerId(learnerId: string): void {
  localStorage.setItem(LEARNER_KEY, learnerId)
}

export function clearAuthStorage(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}
