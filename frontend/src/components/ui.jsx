import { useEffect, useRef } from 'react'
import { AVAILABILITY_LABELS } from '../format'

const NOTICE_STYLES = {
  success: 'border-ok/30 bg-green-50 text-ok',
  error: 'border-bad/30 bg-red-50 text-bad',
  warning: 'border-warn/30 bg-amber-50 text-warn',
  info: 'border-line bg-white text-muted',
}

export function Notice({ type = 'info', children, onRetry, onDismiss, className = '' }) {
  return (
    <div role={type === 'error' ? 'alert' : 'status'} className={`flex items-start gap-2 rounded-sm border px-3 py-2.5 ${NOTICE_STYLES[type]} ${className}`}>
      <div className="flex-1 text-ink">{children}</div>
      {onRetry && (
        <button type="button" className="btn-secondary btn-sm" onClick={onRetry}>
          Retry
        </button>
      )}
      {onDismiss && (
        <button type="button" className="text-xs underline" onClick={onDismiss} aria-label="Dismiss message">
          Dismiss
        </button>
      )}
    </div>
  )
}

export function Loading({ text = 'Loading…' }) {
  return <span role="status" className="text-muted">{text}</span>
}

export function TableMessage({ colSpan, children }) {
  return (
    <tr>
      <td colSpan={colSpan} className="px-3 py-8 text-center text-muted">
        {children}
      </td>
    </tr>
  )
}

export function PageTitle({ children, sub }) {
  return (
    <div className="mb-4">
      <h1 className="text-2xl leading-tight font-semibold text-ink sm:text-3xl">{children}</h1>
      {sub && <p className="mt-1.5 text-sm text-muted">{sub}</p>}
    </div>
  )
}

export function AvailabilityBadge({ value }) {
  const color = { in_stock: 'text-ok', out_of_stock: 'text-bad', preorder: 'text-warn' }[value] || 'text-muted'
  return <span className={`text-sm font-semibold ${color}`}>{AVAILABILITY_LABELS[value] || 'Unknown'}</span>
}

export function SortHeader({ field, sort, onSort, children, align = 'left', className = '' }) {
  const active = sort.field === field
  return (
    <th className={className} aria-sort={active ? (sort.dir === 'desc' ? 'descending' : 'ascending') : undefined}>
      <button
        type="button"
        onClick={() => onSort(field, active && sort.dir === 'asc' ? 'desc' : 'asc')}
        className={`inline-flex items-center gap-1 font-semibold hover:text-ink ${active ? 'text-ink' : ''} ${align === 'right' ? 'flex-row-reverse' : ''}`}
      >
        {children}
        {active && <span aria-hidden="true">{sort.dir === 'desc' ? '↓' : '↑'}</span>}
      </button>
    </th>
  )
}

export function Pagination({ page, pages, total, pageSize, onPage, noun = 'results' }) {
  if (!total) return null
  const first = (page - 1) * pageSize + 1
  const last = Math.min(page * pageSize, total)
  return (
    <nav className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm text-muted" aria-label="Pagination">
      <span>
        Showing {first}–{last} of {total} {noun}
      </span>
      {pages > 1 && (
        <div className="flex items-center gap-2">
          <button type="button" className="btn-secondary btn-sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>
            Previous
          </button>
          <span>
            Page {page} of {pages}
          </span>
          <button type="button" className="btn-secondary btn-sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>
            Next
          </button>
        </div>
      )}
    </nav>
  )
}

export function ConfirmDialog({ open, title, children, confirmLabel = 'Delete', danger = true, busy, onConfirm, onCancel }) {
  const ref = useRef(null)
  useEffect(() => {
    const dialog = ref.current
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])
  return (
    <dialog
      ref={ref}
      onCancel={(e) => {
        e.preventDefault()
        if (!busy) onCancel()
      }}
      className="m-auto w-[min(440px,calc(100vw-32px))] rounded-sm border border-line p-0 text-ink backdrop:bg-black/40"
      aria-labelledby="confirm-title"
    >
      <div className="border-b border-line px-4 py-3">
        <h2 id="confirm-title" className="text-lg font-semibold">
          {title}
        </h2>
      </div>
      <div className="px-4 py-3 text-sm">{children}</div>
      <div className="flex justify-end gap-2 border-t border-line bg-page px-4 py-3">
        <button type="button" className="btn-secondary" onClick={onCancel} disabled={busy} autoFocus>
          Cancel
        </button>
        <button type="button" className={danger ? 'btn-danger' : 'btn-primary'} onClick={onConfirm} disabled={busy}>
          {busy ? 'Working…' : confirmLabel}
        </button>
      </div>
    </dialog>
  )
}
