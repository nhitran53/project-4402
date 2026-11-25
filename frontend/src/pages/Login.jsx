import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { Notice, PageTitle } from '../components/ui'

export default function Login() {
  const { user, login, register, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const returnTo = location.state?.from && location.state.from !== '/login' ? location.state.from : '/'

  const [username, setUsername] = useState('')
  const [newUser, setNewUser] = useState({ username: '', email: '' })
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function submit(action) {
    setBusy(true)
    setError(null)
    try {
      await action()
      navigate(returnTo, { replace: true })
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  if (user) {
    return (
      <div>
        <PageTitle>Account</PageTitle>
        <p className="mb-3">
          You are logged in as <strong>{user.username}</strong> ({user.email}, {user.role}).
        </p>
        <button type="button" className="btn-secondary" onClick={logout}>Log out</button>
      </div>
    )
  }

  return (
    <div>
      <PageTitle sub="Use a username or email to sign in to the demo.">
        Log in
      </PageTitle>
      {error && <Notice type="error" className="mb-3">{error}</Notice>}

      <div className="grid max-w-[860px] gap-4 md:grid-cols-2">
        <form
          className="panel p-4"
          onSubmit={(e) => {
            e.preventDefault()
            submit(() => login(username.trim()))
          }}
        >
          <h2 className="mb-3 text-lg font-semibold">Existing account</h2>
          <label htmlFor="login-username" className="label">Username or email</label>
          <input id="login-username" className="input mb-3" value={username} onChange={(e) => setUsername(e.target.value)} required autoComplete="username" />
          <button type="submit" className="btn-primary" disabled={busy}>Log in</button>
          <p className="mt-3 text-xs text-muted">
            Sample accounts: <code>dwhitfield</code> (administrator), <code>linda.johnson95</code> (customer).
          </p>
        </form>

        <form
          className="panel p-4"
          onSubmit={(e) => {
            e.preventDefault()
            submit(() => register(newUser.username.trim(), newUser.email.trim()))
          }}
        >
          <h2 className="mb-3 text-lg font-semibold">New account</h2>
          <label htmlFor="register-username" className="label">Username</label>
          <input id="register-username" className="input mb-3" maxLength={50} autoComplete="username" value={newUser.username} onChange={(e) => setNewUser({ ...newUser, username: e.target.value })} required />
          <label htmlFor="register-email" className="label">Email</label>
          <input id="register-email" type="email" autoComplete="email" className="input mb-3" value={newUser.email} onChange={(e) => setNewUser({ ...newUser, email: e.target.value })} required />
          <button type="submit" className="btn-secondary" disabled={busy}>Create account</button>
        </form>
      </div>
    </div>
  )
}
