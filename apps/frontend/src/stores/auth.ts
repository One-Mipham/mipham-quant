import { defineStore } from 'pinia'

interface User {
  id: number
  username: string
  nickname: string
  avatar: string
  role: string
}

// Desktop: instant local user, no login flow
const DEFAULT_USER: User = {
  id: 1,
  username: 'trader',
  nickname: 'Trader',
  avatar: '/avatar2.jpg',
  role: 'admin',
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: { ...DEFAULT_USER } as User | null,
    token: 'desktop-local',
  }),
  getters: {
    isLoggedIn: () => true, // Desktop: always logged in
  },
  actions: {
    async login(_username: string, _password: string) {
      // Desktop: no-op, already logged in
    },
    async fetchUser() {
      // Try to fetch from local backend for consistency
      try {
        const api = (await import('@/api/client')).default
        const { data } = await api.get('/auth/info')
        if (data?.code === 1) {
          this.user = data.data
        }
      } catch {
        // Offline: use default user
      }
    },
    logout() {
      // Desktop: never truly log out
    },
  },
})
