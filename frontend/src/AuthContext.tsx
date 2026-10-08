import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import * as api from './api'

interface AuthState {
  user: api.User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (data: api.SignupData) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<api.User | null>(null)
  const [loading, setLoading] = useState(true)

  // The session lives in an HttpOnly cookie; ask the backend who we are on load.
  useEffect(() => {
    api.fetchMe().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false))
  }, [])

  const value: AuthState = {
    user,
    loading,
    login: async (email, password) => setUser(await api.login(email, password)),
    signup: async (data) => setUser(await api.signup(data)),
    logout: async () => {
      await api.logout()
      setUser(null)
    },
  }
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
