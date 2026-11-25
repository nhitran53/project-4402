import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { partsSnapshot, useBuild } from '../build'
import { categoryInfo, sortCategories } from '../categories'
import { formatPrice } from '../format'
import { useApi, useCategories } from '../useApi'
import { AvailabilityBadge, ConfirmDialog, Loading, Notice, PageTitle } from '../components/ui'

function rowPrice(detail) {
  if (!detail || detail.missing) return null
  if (detail.selected_offer) {
    const o = detail.selected_offer
    return { unit: o.price, store: o.store, availability: o.availability, source: 'Selected offer' }
  }
  if (detail.best_price !== null) {
    return { unit: detail.best_price, store: detail.best_store, availability: 'in_stock', source: 'Lowest price' }
  }
  return null
}

export default function SystemBuilder() {
  const build = useBuild()
  const { categories, error: categoryError, loading: categoriesLoading, reload: reloadCategories } = useCategories()
  const check = useApi(build.items.length ? '/builds/check' : null, null, {
    items: build.items.map((item) => ({
      product_id: item.productId, quantity: item.quantity, listing_id: item.listingId,
    })),
  })
  const location = useLocation()
  const navigate = useNavigate()
  const [message, setMessage] = useState(null)
  const [confirmNew, setConfirmNew] = useState(false)

  useEffect(() => {
    if (location.state?.message) {
      setMessage({ type: 'success', text: location.state.message })
      navigate('.', { replace: true, state: null })
    }
  }, [location.state, navigate])

  const details = new Map((check.data?.items || []).map((d) => [d.product_id, d]))
  const rows = build.items.map((item) => ({ item, detail: details.get(item.productId), pending: check.loading }))
  const priced = rows.map((r) => ({ ...r, price: rowPrice(r.detail) }))
  const total = priced.reduce((sum, r) => sum + (r.price ? r.price.unit * r.item.quantity : 0), 0)
  const unpriced = priced.filter((r) => r.detail && !r.price).length
  const totalLabel = check.loading ? '…' : check.error ? '—' : formatPrice(total)

  return (
    <div>
      <PageTitle>System builder</PageTitle>

      {message && (
        <Notice type={message.type} onDismiss={() => setMessage(null)} className="mb-3">
          {message.text}
        </Notice>
      )}

      <BuildControls onStartNew={() => setConfirmNew(true)} onMessage={setMessage} />

      <CompatibilityBar check={check} partCount={build.items.length} />

      {check.error && (
        <Notice type="error" onRetry={check.reload} className="mb-3">
          Could not check prices and compatibility. {check.error.message}
        </Notice>
      )}

      <div className="panel overflow-x-auto">
        <table className="data-table" aria-label="Build parts">
          <thead>
            <tr>
              <th className="hidden w-36 sm:table-cell">Component</th>
              <th><span className="sm:hidden">Component</span><span className="hidden sm:inline">Selection</span></th>
              <th className="hidden lg:table-cell">Availability</th>
              <th className="text-right">Price</th>
              <th className="hidden lg:table-cell">Store</th>
              <th className="hidden lg:table-cell">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {categoriesLoading && (
              <tr>
                <td colSpan={6} className="py-6 text-center">
                  <Loading text="Loading components…" />
                </td>
              </tr>
            )}
            {categoryError && (
              <tr>
                <td colSpan={6}>
                  <Notice type="error" onRetry={reloadCategories}>Could not load components. {categoryError.message}</Notice>
                </td>
              </tr>
            )}
            {sortCategories(categories).map((category) => (
              <CategoryRows key={category.category_id} category={category} rows={priced.filter((r) => r.item.category === category.name)} />
            ))}
          </tbody>
        </table>
        <div className="flex flex-wrap items-baseline justify-end gap-x-3 gap-y-1 border-t border-line px-3 py-3">
          {unpriced > 0 && (
            <span className="text-xs text-warn sm:mr-auto">
              {unpriced} {unpriced === 1 ? 'part has' : 'parts have'} no price and {unpriced === 1 ? 'is' : 'are'} excluded.
            </span>
          )}
          <span className="font-semibold text-muted">Total</span>
          <strong className="text-xl tabular-nums">{totalLabel}</strong>
        </div>
      </div>

      <CompatibilityNotes issues={check.data?.issues || []} />

      <ConfirmDialog
        open={confirmNew}
        title="Start a new build?"
        confirmLabel="Start new"
        onCancel={() => setConfirmNew(false)}
        onConfirm={() => {
          build.clear()
          setConfirmNew(false)
          setMessage({ type: 'info', text: 'Build cleared.' })
        }}
      >
        Clear the parts in your current draft?
      </ConfirmDialog>
    </div>
  )
}

function CategoryRows({ category, rows }) {
  const info = categoryInfo(category.name)
  const chooseUrl = `/products/${info.slug}?mode=select`
  const multi = Boolean(category.multi_allowed)
  const label = (
    <div className="font-semibold">
      <Link to={`/products/${info.slug}`} className="link">
        {info.label}
      </Link>
      {category.required ? null : <div className="text-xs font-normal text-muted">Optional</div>}
    </div>
  )

  if (!rows.length) {
    return (
      <tr>
        <td className="hidden sm:table-cell">{label}</td>
        <td colSpan={5}>
          <div className="flex items-center justify-between gap-3 sm:justify-start">
            <div className="sm:hidden">{label}</div>
            <Link to={chooseUrl} className="btn-primary">
              Choose <span className="sr-only">{info.label}</span>
            </Link>
          </div>
        </td>
      </tr>
    )
  }

  return (
    <>
      {rows.map((row) => (
        <SelectedRow key={row.item.productId} row={row} label={label} chooseUrl={chooseUrl} multi={multi} />
      ))}
      {multi && (
        <tr>
          <td className="hidden sm:table-cell" />
          <td colSpan={5}>
            <Link to={chooseUrl} className="btn-secondary btn-sm">
              Add more {info.label.toLowerCase()}
            </Link>
          </td>
        </tr>
      )}
    </>
  )
}

function SelectedRow({ row, label, chooseUrl, multi }) {
  const { removeItem, setQuantity } = useBuild()
  const { item, detail, price } = row

  function updateQuantity(event) {
    const input = event.currentTarget
    if (input.value && input.validity.valid && Number.isSafeInteger(input.valueAsNumber)) {
      setQuantity(item.productId, input.valueAsNumber)
    } else {
      input.value = item.quantity
    }
  }

  const missing = detail?.missing
  const productUrl = `/product/${item.productId}`
  const changeUrl = `${chooseUrl}&replace=${item.productId}`
  const actions = (
    <div className="flex flex-wrap gap-1.5">
      <Link to={changeUrl} className="btn-secondary btn-sm">Change</Link>
      <button type="button" className="btn-secondary btn-sm" onClick={() => removeItem(item.productId)}
        aria-label={detail?.name ? `Remove ${detail.name}` : 'Remove part'}>Remove</button>
    </div>
  )

  return (
    <tr>
      <td className="hidden sm:table-cell">{label}</td>
      <td className="min-w-28">
        <div className="mb-1 text-xs sm:hidden">{label}</div>
        {missing ? <p className="text-bad">Product unavailable</p> : detail ? (
          <>
            <Link to={productUrl} className="link font-semibold">{detail.name}</Link>
            {multi && (
              <label className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted">
                Quantity
                <input key={item.quantity} type="number" className="input w-20 px-1.5 py-1 text-xs"
                  aria-label={`Quantity for ${detail.name}`} min="1" step="1" defaultValue={item.quantity}
                  onBlur={updateQuantity} onKeyDown={(event) => event.key === 'Enter' && event.currentTarget.blur()} />
              </label>
            )}
            {price && (
              <div className="mt-1 flex flex-wrap items-center gap-x-2 text-xs text-muted lg:hidden">
                {price.store} <AvailabilityBadge value={price.availability} />
              </div>
            )}
            <Link to={productUrl} className="link mt-1 inline-block text-xs lg:hidden">
              {detail.listing_count ? 'Compare prices' : 'Product details'}
            </Link>
          </>
        ) : <span className="text-muted">{row.pending ? 'Loading part…' : 'Part details unavailable'}</span>}
        <div className="mt-2 lg:hidden">{actions}</div>
      </td>
      <td className="hidden lg:table-cell">
        {price ? <AvailabilityBadge value={price.availability} /> : '—'}
      </td>
      <td className="text-right whitespace-nowrap tabular-nums">
        {price ? (
          <>
            <div className="font-semibold">{formatPrice(price.unit * item.quantity)}</div>
            <div className="text-xs text-muted">
              {item.quantity > 1 ? `${item.quantity} × ${formatPrice(price.unit)}` : price.source}
            </div>
          </>
        ) : <span className="text-muted">—</span>}
      </td>
      <td className="hidden lg:table-cell">
        {price && <div>{price.store}</div>}
        {detail && !missing && (
          <Link to={productUrl} className="link text-xs">
            {detail.listing_count ? 'Compare prices' : 'Product details'}
          </Link>
        )}
      </td>
      <td className="hidden lg:table-cell">{actions}</td>
    </tr>
  )
}

function CompatibilityBar({ check, partCount }) {
  const issues = check.data?.issues || []
  const errors = issues.filter((issue) => issue.severity === 'ERROR').length
  const missing = issues.length - errors

  let tone = 'border-line bg-white'
  let text = 'Add parts to check compatibility.'
  if (check.loading) text = 'Checking compatibility…'
  else if (check.error) text = 'Compatibility check unavailable.'
  else if (errors) {
    tone = 'border-bad/30 bg-red-50 text-bad'
    text = errors === 1 ? '1 compatibility issue' : `${errors} compatibility issues`
  } else if (check.data?.items.some((item) => item.missing)) {
    tone = 'border-warn/30 bg-amber-50 text-warn'
    text = 'Remove or replace unavailable parts.'
  } else if (partCount) {
    tone = missing ? 'border-warn/30 bg-amber-50 text-warn' : 'border-ok/30 bg-green-50 text-ok'
    text = missing ? `${missing} required ${missing === 1 ? 'part' : 'parts'} missing` : 'No compatibility issues found'
  }

  return (
    <div role="status" className={`mb-3 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 rounded-sm border px-3 py-2.5 ${tone}`}>
      <span className="font-semibold">{text}</span>
      {check.data?.estimated_wattage != null && (
        <span className="text-muted">Estimated power <strong className="text-ink">{check.data.estimated_wattage} W</strong></span>
      )}
    </div>
  )
}

function CompatibilityNotes({ issues }) {
  if (!issues.length) return null
  return (
    <section className="mt-5">
      <h2 className="mb-2 text-lg font-semibold">Compatibility details</h2>
      <ul className="panel divide-y divide-line">
        {issues.map((issue, i) => (
          <li key={i} className="flex gap-3 px-3 py-2 text-sm">
            <span className={`w-16 shrink-0 font-semibold ${issue.severity === 'ERROR' ? 'text-bad' : 'text-warn'}`}>
              {issue.severity === 'ERROR' ? 'Problem' : 'Missing'}
            </span>
            <span>{issue.message}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

function BuildControls({ onStartNew, onMessage }) {
  const build = useBuild()
  const { user } = useAuth()
  const [name, setName] = useState(null)
  const [busy, setBusy] = useState(false)

  const saved = build.saved && user && build.saved.userId === user.user_id ? build.saved : null
  const changed = saved && saved.snapshot !== partsSnapshot(build.items)
  const body = (buildName) => ({
    name: buildName,
    items: build.items.map((i) => ({ product_id: i.productId, quantity: i.quantity })),
  })

  async function save(asNew, buildName) {
    setBusy(true)
    try {
      const result = asNew
        ? await api('/builds', { method: 'POST', body: body(buildName) })
        : await api(`/builds/${saved.id}`, { method: 'PUT', body: body(saved.name) })
      build.markSaved({ id: result.build_id, name: result.name, userId: user.user_id, snapshot: partsSnapshot(build.items) })
      setName(null)
      onMessage({ type: 'success', text: asNew ? `Saved “${result.name}”.` : 'Changes saved.' })
    } catch (error) {
      onMessage({ type: 'error', text: `Could not save the build. ${error.message}` })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="panel mb-3 flex flex-wrap items-center justify-between gap-2 px-3 py-2">
      <div className="text-sm">
        {saved ? (
          <>
            <strong>{saved.name}</strong>
            {changed && <span className="ml-2 font-semibold text-warn">Unsaved changes</span>}
          </>
        ) : (
          <span className="text-muted">Draft saved in this browser</span>
        )}
      </div>

      {name !== null ? (
        <form
          className="flex flex-wrap items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            if (name.trim()) save(true, name.trim())
          }}
        >
          <label htmlFor="build-name" className="text-xs font-semibold">
            Build name
          </label>
          <input id="build-name" className="input w-56 py-1" value={name} maxLength={100} onChange={(e) => setName(e.target.value)} autoFocus required />
          <button type="submit" className="btn-primary btn-sm" disabled={busy || !name.trim()}>
            {busy ? 'Saving…' : 'Save'}
          </button>
          <button type="button" className="btn-secondary btn-sm" onClick={() => setName(null)} disabled={busy}>
            Cancel
          </button>
        </form>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" className="btn-secondary btn-sm" onClick={onStartNew} disabled={busy || (!build.items.length && !build.saved)}>
            Start new
          </button>
          {user ? (
            <>
              {saved && (
                <button type="button" className="btn-primary btn-sm" onClick={() => save(false)} disabled={busy || !changed}>
                  Save changes
                </button>
              )}
              <button type="button" className={saved ? 'btn-secondary btn-sm' : 'btn-primary btn-sm'} onClick={() => setName('')} disabled={!build.items.length}>
                {saved ? 'Save as new' : 'Save build'}
              </button>
            </>
          ) : (
            <Link to="/login" state={{ from: '/' }} className="link text-sm">
              Log in to save
            </Link>
          )}
        </div>
      )}
    </div>
  )
}
