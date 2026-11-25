import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../../api'
import { categoryInfo } from '../../categories'
import { AVAILABILITY_LABELS, formatDate, formatPrice } from '../../format'
import { useApi } from '../../useApi'
import { AvailabilityBadge, ConfirmDialog, Loading, Notice, Pagination, SortHeader, TableMessage } from '../../components/ui'

const EMPTY_FORM = { product_id: '', store_id: '', price: '', availability: 'in_stock', product_url: '' }

export default function AdminListings() {
  const [params] = useSearchParams()
  const initialProduct = params.get('product_id') || ''
  const lookups = useApi('/admin/lookups')
  const [query, setQuery] = useState({ product_id: initialProduct, store_id: '', availability: '', stale_days: '', page: 1, sort: 'product', dir: 'asc' })
  const listings = useApi('/admin/listings', query)
  const [form, setForm] = useState(initialProduct ? { listing: null, productId: initialProduct } : null)
  const [toDelete, setToDelete] = useState(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState(null)

  const update = (changes) => setQuery((q) => ({ ...q, page: 1, ...changes }))
  const sort = { field: query.sort, dir: query.dir }
  const onSort = (field, dir) => update({ sort: field, dir })

  async function remove() {
    setBusy(true)
    try {
      await api(`/admin/listings/${toDelete.listing_id}`, { method: 'DELETE' })
      setMessage({ type: 'success', text: `Deleted the ${toDelete.store} listing for ${toDelete.product}.` })
      listings.reload()
    } catch (e) {
      setMessage({ type: 'error', text: e.message })
    } finally {
      setBusy(false)
      setToDelete(null)
    }
  }

  if (lookups.error) return <Notice type="error" onRetry={lookups.reload}>Could not load form options. {lookups.error.message}</Notice>
  if (!lookups.data) return <Loading />
  const { products, stores } = lookups.data

  return (
    <div>
      {message && <Notice type={message.type} onDismiss={() => setMessage(null)} className="mb-3">{message.text}</Notice>}

      {form ? (
        <ListingForm
          key={form.listing?.listing_id ?? 'new'}
          listing={form.listing}
          productId={form.productId}
          products={products}
          stores={stores}
          onCancel={() => setForm(null)}
          onSaved={(text) => {
            setForm(null)
            setMessage({ type: 'success', text })
            listings.reload()
          }}
        />
      ) : (
        <div className="mb-3 flex justify-end">
          <button type="button" className="btn-primary" onClick={() => setForm({ listing: null, productId: query.product_id })}>Add listing</button>
        </div>
      )}

      <div className="panel mb-3 grid gap-3 p-3 sm:grid-cols-2 lg:grid-cols-[2fr_1fr_1fr_1fr_auto] lg:items-end">
        <div>
          <label htmlFor="lf-product" className="label">Product</label>
          <ProductSelect id="lf-product" products={products} value={query.product_id} onChange={(v) => update({ product_id: v })} emptyLabel="All products" />
        </div>
        <div>
          <label htmlFor="lf-store" className="label">Store</label>
          <select id="lf-store" className="input" value={query.store_id} onChange={(e) => update({ store_id: e.target.value })}>
            <option value="">All stores</option>
            {stores.map((s) => <option key={s.store_id} value={s.store_id}>{s.name}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="lf-availability" className="label">Availability</label>
          <select id="lf-availability" className="input" value={query.availability} onChange={(e) => update({ availability: e.target.value })}>
            <option value="">Any</option>
            {Object.entries(AVAILABILITY_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="lf-stale" className="label">Not updated for (days)</label>
          <input id="lf-stale" type="number" min="0" className="input" placeholder="Any" value={query.stale_days} onChange={(e) => update({ stale_days: e.target.value })} />
        </div>
        <button type="button" className="btn-secondary" onClick={() => update({ product_id: '', store_id: '', availability: '', stale_days: '' })}>Clear</button>
      </div>

      {listings.error && <Notice type="error" onRetry={listings.reload} className="mb-3">Could not load listings. {listings.error.message}</Notice>}

      <div className="panel overflow-x-auto">
        <table className="data-table min-w-[900px]">
          <thead>
            <tr>
              <SortHeader field="id" sort={sort} onSort={onSort}>ID</SortHeader>
              <SortHeader field="product" sort={sort} onSort={onSort}>Product</SortHeader>
              <SortHeader field="store" sort={sort} onSort={onSort}>Store</SortHeader>
              <SortHeader field="price" sort={sort} onSort={onSort} align="right" className="text-right">Price</SortHeader>
              <SortHeader field="availability" sort={sort} onSort={onSort}>Availability</SortHeader>
              <SortHeader field="updated" sort={sort} onSort={onSort}>Updated</SortHeader>
              <th>Created by</th>
              <th><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {listings.loading && !listings.data && <TableMessage colSpan={8}><Loading /></TableMessage>}
            {listings.data?.items.length === 0 && <TableMessage colSpan={8}>No listings match these filters.</TableMessage>}
            {listings.data?.items.map((l) => (
              <tr key={l.listing_id}>
                <td className="text-muted">{l.listing_id}</td>
                <td><Link to={`/product/${l.product_id}`} className="link font-semibold">{l.product}</Link></td>
                <td>{l.store}</td>
                <td className="text-right font-semibold">{formatPrice(l.price)}</td>
                <td><AvailabilityBadge value={l.availability} /></td>
                <td className="whitespace-nowrap text-muted">{formatDate(l.last_updated)}</td>
                <td className="text-muted">{l.created_by}</td>
                <td>
                  <div className="flex justify-end gap-1.5">
                    <button type="button" className="btn-secondary btn-sm" onClick={() => { setForm({ listing: l }); window.scrollTo(0, 0) }}>Edit</button>
                    <button type="button" className="btn-secondary btn-sm" onClick={() => setToDelete(l)}>Delete</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {listings.data && <Pagination {...listings.data} pageSize={listings.data.page_size} noun="listings" onPage={(page) => setQuery((q) => ({ ...q, page }))} />}

      <ConfirmDialog open={Boolean(toDelete)} title="Delete this listing?" busy={busy} onCancel={() => setToDelete(null)} onConfirm={remove}>
        The {toDelete?.store} price of {formatPrice(toDelete?.price)} for {toDelete?.product} will be removed from the database.
      </ConfirmDialog>
    </div>
  )
}

function ProductSelect({ id, products, value, onChange, emptyLabel, required }) {
  const groups = Object.create(null)
  for (const product of products) {
    (groups[product.category] ??= []).push(product)
  }
  return (
    <select id={id} className="input" value={value} onChange={(e) => onChange(e.target.value)} required={required}>
      <option value="">{emptyLabel}</option>
      {Object.entries(groups).map(([category, items]) => (
        <optgroup key={category} label={categoryInfo(category).plural}>
          {items.map((p) => <option key={p.product_id} value={p.product_id}>{p.name}</option>)}
        </optgroup>
      ))}
    </select>
  )
}

function ListingForm({ listing, productId, products, stores, onCancel, onSaved }) {
  const [values, setValues] = useState(
    listing
      ? { product_id: listing.product_id, store_id: listing.store_id, price: String(listing.price), availability: listing.availability, product_url: listing.product_url || '' }
      : { ...EMPTY_FORM, product_id: productId || '' },
  )
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const set = (changes) => setValues((v) => ({ ...v, ...changes }))

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    const body = { ...values, product_id: Number(values.product_id), store_id: Number(values.store_id), price: Number(values.price) }
    try {
      if (listing) {
        await api(`/admin/listings/${listing.listing_id}`, { method: 'PUT', body })
        onSaved('Listing updated.')
      } else {
        await api('/admin/listings', { method: 'POST', body })
        onSaved('Listing added.')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="panel mb-4 p-4" onSubmit={submit}>
      <h2 className="mb-3 text-lg font-semibold">{listing ? `Edit listing #${listing.listing_id}` : 'Add listing'}</h2>
      {error && <Notice type="error" className="mb-3">{error}</Notice>}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[2fr_1fr_1fr_1fr]">
        <div>
          <label htmlFor={listing ? undefined : 'lform-product'} className="label">Product</label>
          {listing ? (
            <p id="lform-product" className="py-1.5">{listing.product}</p>
          ) : (
            <ProductSelect id="lform-product" products={products} value={values.product_id} onChange={(v) => set({ product_id: v })} emptyLabel="Choose a product…" required />
          )}
        </div>
        <div>
          <label htmlFor={listing ? undefined : 'lform-store'} className="label">Store</label>
          {listing ? (
            <p id="lform-store" className="py-1.5">{listing.store}</p>
          ) : (
            <select id="lform-store" className="input" value={values.store_id} onChange={(e) => set({ store_id: e.target.value })} required>
              <option value="">Choose a store…</option>
              {stores.map((s) => <option key={s.store_id} value={s.store_id}>{s.name}</option>)}
            </select>
          )}
        </div>
        <div>
          <label htmlFor="lform-price" className="label">Price (USD)</label>
          <input id="lform-price" type="number" min="0" step="any" className="input" value={values.price} onChange={(e) => set({ price: e.target.value })} required />
        </div>
        <div>
          <label htmlFor="lform-availability" className="label">Availability</label>
          <select id="lform-availability" className="input" value={values.availability} onChange={(e) => set({ availability: e.target.value })}>
            {Object.entries(AVAILABILITY_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
        <div className="sm:col-span-2 lg:col-span-4">
          <label htmlFor="lform-url" className="label">Product URL (optional)</label>
          <input id="lform-url" type="url" className="input" placeholder="https://" maxLength={500} value={values.product_url} onChange={(e) => set({ product_url: e.target.value })} />
        </div>
      </div>
      <div className="mt-3 flex gap-2">
        <button type="submit" className="btn-primary" disabled={busy}>{busy ? 'Saving…' : listing ? 'Save changes' : 'Add listing'}</button>
        <button type="button" className="btn-secondary" onClick={onCancel} disabled={busy}>Cancel</button>
      </div>
    </form>
  )
}
