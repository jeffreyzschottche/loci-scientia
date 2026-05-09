import { defineStore } from 'pinia'

interface AuthState {
  deviceNumber: string | null
  bearerToken: string | null
  tokenExpiresAt: string | null
  username: string | null
}

// The SPA is hosted by the FastAPI backend itself, so we always call the API
// on the same origin and never need to ask the user for a device number.
const sameOriginBase = (): string | null => {
  if (typeof window === 'undefined') return null
  const { protocol, origin } = window.location
  if (protocol !== 'http:' && protocol !== 'https:') return null
  return origin.replace(/\/$/, '')
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    deviceNumber: null,
    bearerToken: null,
    tokenExpiresAt: null,
    username: null,
  }),

  getters: {
    isDeviceConfigured: (state) => {
      if (state.deviceNumber) return true
      return sameOriginBase() !== null
    },
    isAuthenticated: (state) => {
      if (!state.bearerToken || !state.tokenExpiresAt) return false

      const expiryDate = new Date(state.tokenExpiresAt)
      const now = new Date()

      return expiryDate > now
    },
    baseUrl: (state) => {
      if (state.deviceNumber) {
        if (state.deviceNumber.startsWith('http://') || state.deviceNumber.startsWith('https://')) {
          return state.deviceNumber.replace(/\/$/, '')
        }
        if (/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/.test(state.deviceNumber)) {
          return `http://${state.deviceNumber}:8000`
        }
        return `http://aitje-${state.deviceNumber}.local:8000`
      }
      return sameOriginBase()
    },
  },

  actions: {
    setDeviceNumber(deviceNumber: string) {
      this.deviceNumber = deviceNumber
      this.saveToLocalStorage()
    },

    setAuthData(token: string, expiresAt: string, username: string) {
      this.bearerToken = token
      this.tokenExpiresAt = expiresAt
      this.username = username
      this.saveToLocalStorage()
    },

    clearAuth() {
      this.bearerToken = null
      this.tokenExpiresAt = null
      this.username = null
      this.saveToLocalStorage()
    },

    clearAll() {
      this.deviceNumber = null
      this.bearerToken = null
      this.tokenExpiresAt = null
      this.username = null
      this.clearLocalStorage()
    },

    loadFromLocalStorage() {
      if (typeof window === 'undefined') return

      const stored = localStorage.getItem('aitje_auth')
      if (stored) {
        try {
          const data = JSON.parse(stored)
          this.deviceNumber = data.deviceNumber || null
          this.bearerToken = data.bearerToken || null
          this.tokenExpiresAt = data.tokenExpiresAt || null
          this.username = data.username || null
        } catch (e) {
          console.error('Failed to parse stored auth data:', e)
        }
      }
    },

    saveToLocalStorage() {
      if (typeof window === 'undefined') return

      const data = {
        deviceNumber: this.deviceNumber,
        bearerToken: this.bearerToken,
        tokenExpiresAt: this.tokenExpiresAt,
        username: this.username,
      }
      localStorage.setItem('aitje_auth', JSON.stringify(data))
    },

    clearLocalStorage() {
      if (typeof window === 'undefined') return
      localStorage.removeItem('aitje_auth')
    },
  },
})
