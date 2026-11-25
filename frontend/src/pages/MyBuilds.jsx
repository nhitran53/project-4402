import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { useBuild } from '../build'
import { formatDate, formatPrice } from '../format'
import { useApi } from '../useApi'
import { ConfirmDialog, Loading, Notice, PageTitle, TableMessage } from '../components/ui'

export default function MyBuilds() {
  const { user, checking } = useAuth()
  const build = useBuild()
  const navigate = useNavigate()
  const builds = useApi(user ? '/builds' : null)
  const [message, setMessage] = useState(null)
  const [toDelete, setToDelete] = useState(null)
  const [busy, setBusy] = useState(false)

  if (checking) return <Loading />
  if (!user) {
    return (
      <div>
        <PageTitle>My builds</PageTitle>
        <p>
          <Link to="/login" state={{ from: '/builds' }} className="link">Log in</Link> to see your saved builds.
        </p>
      </div>
    )
  }

  async function open(id) {
    try {
      const { build: saved, items } = await api(`/builds/${id}`)
      build.loadSaved({ id: saved.build_id, name: saved.name, userId: user.user_id }, items)
      navigate('/', { state: { message: `Opened saved build “${saved.name}”.` } })
    } catch (e) {
      setMessage({ type: 'error', text: `Unable to open the build: ${e.message}` })
    }
  }

  async function remove() {
    setBusy(true)
    try {
      await api(`/builds/${toDelete.build_id}`, { method: 'DELETE' })
      build.detachSaved(toDelete.build_id, user.user_id)
      setMessage({ type: 'success', text: `Deleted build “${toDelete.name}”.` })
      builds.reload()
    } catch (e) {
      setMessage({ type: 'error', text: `Unable to delete the build: ${e.message}` })
    } finally {
      setBusy(false)
      setToDelete(null)
    }
  }

  return (
    <div>
      <PageTitle sub="Totals use the lowest in-stock price for each part.">
        My builds
      </PageTitle>
      {message && <Notice type={message.type} onDismiss={() => setMessage(null)} className="mb-3">{message.text}</Notice>}
      {builds.error && <Notice type="error" onRetry={builds.reload} className="mb-3">Unable to load your builds: {builds.error.message}</Notice>}

      <div className="panel overflow-x-auto">
        <table className="data-table" aria-label="Saved builds">
          <thead>
            <tr>
              <th>Name</th>
              <th className="hidden sm:table-cell">Created</th>
              <th className="hidden text-right md:table-cell">Parts</th>
              <th className="text-right">Total</th>
              <th className="hidden lg:table-cell">Compatibility</th>
              <th><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {builds.loading && !builds.data && <TableMessage colSpan={6}><Loading text="Loading builds…" /></TableMessage>}
            {builds.data?.length === 0 && (
              <TableMessage colSpan={6}>
                No saved builds yet. <Link to="/" className="link">Start a build</Link>.
              </TableMessage>
            )}
            {builds.data?.map((b) => (
              <tr key={b.build_id}>
                <td className="font-semibold">
                  {b.name}
                </td>
                <td className="hidden whitespace-nowrap text-muted sm:table-cell">{formatDate(b.created_at)}</td>
                <td className="hidden text-right md:table-cell">{b.part_count}</td>
                <td className="text-right font-semibold whitespace-nowrap tabular-nums">
                  {formatPrice(b.total_price)}
                  {b.parts_without_price > 0 && <div className="text-xs font-normal text-warn">{b.parts_without_price} unpriced</div>}
                </td>
                <td className="hidden lg:table-cell">
                  {b.errors > 0 ? (
                    <span className="font-semibold text-bad">{b.errors} {b.errors === 1 ? 'problem' : 'problems'}</span>
                  ) : (
                    <span className="font-semibold text-ok">No problems</span>
                  )}
                  {b.missing > 0 && <span className="text-xs text-muted"> · {b.missing} missing</span>}
                </td>
                <td>
                  <div className="flex flex-wrap justify-end gap-1.5">
                    <button type="button" className="btn-primary btn-sm" onClick={() => open(b.build_id)}>Open</button>
                    <button type="button" className="btn-secondary btn-sm" onClick={() => setToDelete(b)}>Delete</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ConfirmDialog open={Boolean(toDelete)} title="Delete this build?" busy={busy} onCancel={() => setToDelete(null)} onConfirm={remove}>
        Delete “{toDelete?.name}” from your saved builds?
      </ConfirmDialog>
    </div>
  )
}
