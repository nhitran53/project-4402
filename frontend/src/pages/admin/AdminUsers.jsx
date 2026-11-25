import { useState } from 'react'
import { api } from '../../api'
import { useAuth } from '../../auth'
import { useApi } from '../../useApi'
import { ConfirmDialog, Loading, Notice, Pagination, TableMessage } from '../../components/ui'

const EMPTY_USER = { username: '', email: '', role: 'customer' }

export default function AdminUsers() {
  const { user: me } = useAuth()
  const [query, setQuery] = useState({ q: '', page: 1 })
  const users = useApi('/admin/users', query)
  const [search, setSearch] = useState('')
  const [form, setForm] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [toDelete, setToDelete] = useState(null)
  const [message, setMessage] = useState(null)

  async function run(action, success) {
    try {
      await action()
      setMessage({ type: 'success', text: success })
      users.reload()
    } catch (err) {
      setMessage({ type: 'error', text: err.message })
    }
  }

  async function addUser(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api('/admin/users', { method: 'POST', body: form })
      setMessage({ type: 'success', text: `User “${form.username}” added.` })
      setForm(null)
      users.reload()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      {message && <Notice type={message.type} onDismiss={() => setMessage(null)} className="mb-3">{message.text}</Notice>}

      {form ? (
        <form className="panel mb-4 p-4" onSubmit={addUser}>
          <h2 className="mb-3 text-lg font-semibold">Add user</h2>
          {error && <Notice type="error" className="mb-3">{error}</Notice>}
          <div className="grid gap-3 sm:grid-cols-3">
            <div>
              <label htmlFor="uf-username" className="label">Username</label>
              <input id="uf-username" className="input" maxLength={50} value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required />
            </div>
            <div>
              <label htmlFor="uf-email" className="label">Email</label>
              <input id="uf-email" type="email" className="input" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
            </div>
            <div>
              <label htmlFor="uf-role" className="label">Role</label>
              <select id="uf-role" className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                <option value="customer">Customer</option>
                <option value="admin">Administrator</option>
              </select>
            </div>
          </div>
          <div className="mt-3 flex gap-2">
            <button type="submit" className="btn-primary" disabled={busy}>{busy ? 'Saving…' : 'Add user'}</button>
            <button type="button" className="btn-secondary" onClick={() => { setForm(null); setError(null) }} disabled={busy}>Cancel</button>
          </div>
        </form>
      ) : (
        <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
          <form className="flex flex-1 items-end gap-2" onSubmit={(e) => { e.preventDefault(); setQuery({ q: search.trim(), page: 1 }) }}>
            <div className="max-w-sm flex-1">
              <label htmlFor="user-search" className="label">Search users</label>
              <input id="user-search" type="search" className="input" placeholder="Username or email" value={search} onChange={(e) => setSearch(e.target.value)} />
            </div>
            <button type="submit" className="btn-secondary">Search</button>
          </form>
          <button type="button" className="btn-primary" onClick={() => setForm(EMPTY_USER)}>Add user</button>
        </div>
      )}

      {users.error && <Notice type="error" onRetry={users.reload} className="mb-3">Could not load users. {users.error.message}</Notice>}
      <div className="panel overflow-x-auto">
        <table className="data-table min-w-[720px]">
          <thead>
            <tr>
              <th>ID</th>
              <th>Username</th>
              <th>Email</th>
              <th>Role</th>
              <th className="text-right">Builds</th>
              <th className="text-right">Listings created</th>
              <th><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {users.loading && !users.data && <TableMessage colSpan={7}><Loading /></TableMessage>}
            {users.data?.items.length === 0 && <TableMessage colSpan={7}>No users match.</TableMessage>}
            {users.data?.items.map((u) => {
              const self = u.user_id === me.user_id
              return (
                <tr key={u.user_id}>
                  <td className="text-muted">{u.user_id}</td>
                  <td className="font-semibold">{u.username}{self && <span className="font-normal text-muted"> (you)</span>}</td>
                  <td>{u.email}</td>
                  <td>
                    <label htmlFor={`role-${u.user_id}`} className="sr-only">Role for {u.username}</label>
                    <select
                      id={`role-${u.user_id}`}
                      className="input disabled:bg-page"
                      value={u.role}
                      disabled={self}
                      onChange={(e) => run(() => api(`/admin/users/${u.user_id}`, { method: 'PUT', body: { role: e.target.value } }), `${u.username} is now ${e.target.value === 'admin' ? 'an administrator' : 'a customer'}.`)}
                    >
                      <option value="customer">Customer</option>
                      <option value="admin">Administrator</option>
                    </select>
                  </td>
                  <td className="text-right">{u.build_count}</td>
                  <td className="text-right">{u.listing_count}</td>
                  <td className="text-right">
                    <button type="button" className="btn-secondary btn-sm" disabled={self} onClick={() => setToDelete(u)}>Delete</button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      {users.data && <Pagination {...users.data} pageSize={users.data.page_size} noun="users" onPage={(page) => setQuery((q) => ({ ...q, page }))} />}

      <ConfirmDialog
        open={Boolean(toDelete)}
        title="Delete this user?"
        busy={busy}
        onCancel={() => setToDelete(null)}
        onConfirm={async () => {
          setBusy(true)
          await run(() => api(`/admin/users/${toDelete.user_id}`, { method: 'DELETE' }), `User “${toDelete.username}” deleted.`)
          setBusy(false)
          setToDelete(null)
        }}
      >
        <p>“{toDelete?.username}” and their {toDelete?.build_count} saved builds will be deleted.</p>
        {toDelete?.listing_count > 0 && (
          <p className="mt-2 text-warn">Remove the listings created by this user before deleting the account.</p>
        )}
      </ConfirmDialog>
    </div>
  )
}
