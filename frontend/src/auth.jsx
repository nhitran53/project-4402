import { createContext, useContext, useEffect, useState } from 'react'
import { api, getToken, setToken } from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [checking, setChecking] = useState(Boolean(getToken()))

  useEffect(() => {
    if (!getToken()) return
    api('/me')
      .then(({ user }) => {
        if (!user) setToken(null)
        setUser(user)
      })
      .catch(() => setUser(null))
      .finally(() => setChecking(false))
  }, [])

  async function startSession(path, body) {
    const { token, user } = await api(path, { method: 'POST', body })
    setToken(token)
    setUser(user)
    return user
  }

  async function logout() {
    try {
      await api('/logout', { method: 'POST' })
    } catch {
      // Clear the local session even if the server is offline.
    } finally {
      setToken(null)
      setUser(null)
    }
  }

  const value = {
    user,
    checking,
    isAdmin: user?.role === 'admin',
    login: (username) => startSession('/login', { username }),
    register: (username, email) => startSession('/register', { username, email }),
    logout,
  }
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
