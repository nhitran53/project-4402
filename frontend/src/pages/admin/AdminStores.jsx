import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api'
import { useApi } from '../../useApi'
import { ConfirmDialog, Loading, Notice, TableMessage } from '../../components/ui'

export default function AdminStores() {
  const stores = useApi('/stores')
  const [form, setForm] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [toDelete, setToDelete] = useState(null)
  const [message, setMessage] = useState(null)

  async function submit(e) {
    e.preventDefault()
    if (!form.name.trim()) return setError('Store name is required.')
    setBusy(true)
    setError(null)
    try {
      const body = { name: form.name, website: form.website }
      if (form.store_id) await api(`/admin/stores/${form.store_id}`, { method: 'PUT', body })
      else await api('/admin/stores', { method: 'POST', body })
      setMessage({ type: 'success', text: form.store_id ? `Store “${form.name}” updated.` : `Store “${form.name}” added.` })
      setForm(null)
      stores.reload()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function remove() {
    setBusy(true)
    try {
      await api(`/admin/stores/${toDelete.store_id}`, { method: 'DELETE' })
      setMessage({ type: 'success', text: `Store “${toDelete.name}” deleted.` })
      stores.reload()
    } catch (err) {
      setMessage({ type: 'error', text: err.message })
    } finally {
      setBusy(false)
      setToDelete(null)
    }
  }

  return (
    <div>
      {message && <Notice type={message.type} onDismiss={() => setMessage(null)} className="mb-3">{message.text}</Notice>}

      {form ? (
        <form className="panel mb-4 p-4" onSubmit={submit}>
          <h2 className="mb-3 text-lg font-semibold">{form.store_id ? `Edit store #${form.store_id}` : 'Add store'}</h2>
          {error && <Notice type="error" className="mb-3">{error}</Notice>}
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="sf-name" className="label">Store name</label>
              <input id="sf-name" className="input" maxLength={100} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </div>
            <div>
              <label htmlFor="sf-website" className="label">Website (optional)</label>
              <input id="sf-website" type="url" className="input" placeholder="https://" value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} />
            </div>
          </div>
          <div className="mt-3 flex gap-2">
            <button type="submit" className="btn-primary" disabled={busy}>{busy ? 'Saving…' : form.store_id ? 'Save changes' : 'Add store'}</button>
            <button type="button" className="btn-secondary" onClick={() => { setForm(null); setError(null) }} disabled={busy}>Cancel</button>
          </div>
        </form>
      ) : (
        <div className="mb-3 flex justify-end">
          <button type="button" className="btn-primary" onClick={() => setForm({ name: '', website: '' })}>Add store</button>
        </div>
      )}

      {stores.error && <Notice type="error" onRetry={stores.reload} className="mb-3">Could not load stores. {stores.error.message}</Notice>}
      <div className="panel overflow-x-auto">
        <table className="data-table min-w-[640px]">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Website</th>
              <th className="text-right">Listings</th>
              <th><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {stores.loading && !stores.data && <TableMessage colSpan={5}><Loading /></TableMessage>}
            {stores.data?.length === 0 && <TableMessage colSpan={5}>No stores yet.</TableMessage>}
            {stores.data?.map((s) => (
              <tr key={s.store_id}>
                <td className="text-muted">{s.store_id}</td>
                <td><Link to={`/stores/${s.store_id}`} className="link font-semibold">{s.name}</Link></td>
                <td className="text-muted">{s.website || '—'}</td>
                <td className="text-right">{s.listing_count}</td>
                <td>
                  <div className="flex justify-end gap-1.5">
                    <button type="button" className="btn-secondary btn-sm" onClick={() => { setError(null); setForm({ store_id: s.store_id, name: s.name, website: s.website || '' }) }}>Edit</button>
                    <button type="button" className="btn-secondary btn-sm" onClick={() => setToDelete(s)}>Delete</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ConfirmDialog open={Boolean(toDelete)} title="Delete this store?" busy={busy} onCancel={() => setToDelete(null)} onConfirm={remove}>
        <p>“{toDelete?.name}” will be permanently deleted.</p>
        {toDelete?.listing_count > 0 && (
          <p className="mt-2 text-warn">
            Remove this store’s listings before deleting it.
          </p>
        )}
      </ConfirmDialog>
    </div>
  )
}
