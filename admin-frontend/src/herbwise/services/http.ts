import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { getServiceBaseURL } from '@/utils/service'
import type { ApiEnvelope, TokenPair } from '../types/api'
import {
  clearAuthStorage,
  getAccessToken,
  getRefreshToken,
  setStoredUser,
  setTokens,
} from './auth-storage'

interface RetryConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
}

const isHttpProxy = import.meta.env.DEV && import.meta.env.VITE_HTTP_PROXY === 'Y'
const { baseURL } = getServiceBaseURL(import.meta.env, isHttpProxy)

const http = axios.create({
  baseURL,
  timeout: 30_000,
})

const refreshClient = axios.create({
  baseURL,
  timeout: 15_000,
})

let refreshPromise: Promise<string> | null = null

function extractTokenPair(payload: ApiEnvelope<TokenPair> | TokenPair): TokenPair {
  if ('code' in payload) {
    if (payload.code !== 0) throw new Error(payload.message || '会话刷新失败')
    return payload.data
  }
  return payload
}

async function refreshAccessToken(): Promise<string> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) throw new Error('缺少刷新凭证')
  const response = await refreshClient.post<ApiEnvelope<TokenPair> | TokenPair>('/auth/refresh', {
    refresh_token: refreshToken,
  })
  const pair = extractTokenPair(response.data)
  setTokens(pair.access_token, pair.refresh_token)
  if (pair.user) setStoredUser(pair.user)
  return pair.access_token
}

http.interceptors.request.use((config) => {
  const accessToken = getAccessToken()
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`
  return config
})

http.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as RetryConfig | undefined
    const isAuthRoute = original?.url?.includes('/auth/login') || original?.url?.includes('/auth/refresh')

    if (error.response?.status !== 401 || !original || original._retry || isAuthRoute) {
      return Promise.reject(error)
    }

    original._retry = true
    try {
      refreshPromise ??= refreshAccessToken().finally(() => {
        refreshPromise = null
      })
      const token = await refreshPromise
      original.headers.Authorization = `Bearer ${token}`
      return http(original)
    } catch (refreshError) {
      clearAuthStorage()
      if (window.location.pathname !== '/login') window.location.assign('/login')
      return Promise.reject(refreshError)
    }
  },
)

export default http
