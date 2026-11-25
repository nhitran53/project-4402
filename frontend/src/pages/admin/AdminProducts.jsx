import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api'
import { categoryInfo } from '../../categories'
import { useApi } from '../../useApi'
import { ConfirmDialog, Loading, Notice, Pagination, SortHeader, TableMessage } from '../../components/ui'

export default function AdminProducts() {
  const lookups = useApi('/admin/lookups')
  const [query, setQuery] = useState({ q: '', category: '', page: 1, sort: 'id', dir: 'desc' })
  const products = useApi('/admin/products', query)
  const [search, setSearch] = useState('')
  const [form, setForm] = useState(null)
  const [toDelete, setToDelete] = useState(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState(null)

  const update = (changes) => setQuery((q) => ({ ...q, page: 1, ...changes }))

  async function remove() {
    setBusy(true)
    try {
      await api(`/admin/products/${toDelete.product_id}`, { method: 'DELETE' })
      setMessage({ type: 'success', text: `Deleted product “${toDelete.name}”.` })
      products.reload()
    } catch (e) {
      setMessage({ type: 'error', text: e.message })
    } finally {
      setBusy(false)
      setToDelete(null)
    }
  }

  if (lookups.error) return <Notice type="error" onRetry={lookups.reload}>Could not load form options. {lookups.error.message}</Notice>
  if (!lookups.data) return <Loading />

  return (
    <div>
      {message && (
        <Notice type={message.type} onDismiss={() => setMessage(null)} className="mb-3">
          {message.text}
          {message.productId && (
            <>
              {' '}
              <Link to={`/admin/listings?product_id=${message.productId}`} className="link">Add listing</Link> ·{' '}
              <Link to={`/product/${message.productId}`} className="link">View product</Link>
            </>
          )}
        </Notice>
      )}

      {form ? (
        <ProductForm
          key={form.productId ?? 'new'}
          productId={form.productId}
          lookups={lookups.data}
          onCancel={() => setForm(null)}
          onSaved={(result, isNew) => {
            setForm(null)
            setMessage({ type: 'success', text: isNew ? `Added product “${result.name}”.` : `Product “${result.name}” updated.`, productId: result.product_id })
            products.reload()
          }}
        />
      ) : (
        <div className="mb-3 flex flex-wrap items-end gap-3">
          <form
            className="flex flex-1 flex-wrap items-end gap-2"
            onSubmit={(e) => {
              e.preventDefault()
              update({ q: search.trim() })
            }}
          >
            <div className="min-w-36 flex-1">
              <label htmlFor="admin-product-search" className="label">Search products</label>
              <input id="admin-product-search" type="search" className="input" placeholder="Name, brand or model" value={search} onChange={(e) => setSearch(e.target.value)} />
            </div>
            <div>
              <label htmlFor="admin-product-category" className="label">Category</label>
              <select id="admin-product-category" className="input" value={query.category} onChange={(e) => update({ category: e.target.value })}>
                <option value="">All categories</option>
                {lookups.data.categories.map((c) => <option key={c.category_id} value={c.name}>{categoryInfo(c.name).label}</option>)}
              </select>
            </div>
            <button type="submit" className="btn-secondary">Search</button>
          </form>
          <button type="button" className="btn-primary" onClick={() => setForm({ productId: null })}>Add product</button>
        </div>
      )}

      {products.error && <Notice type="error" onRetry={products.reload} className="mb-3">Could not load products. {products.error.message}</Notice>}

      <div className="panel overflow-x-auto">
        <table className="data-table min-w-[760px]">
          <thead>
            <tr>
              <SortHeader field="id" sort={{ field: query.sort, dir: query.dir }} onSort={(sort, dir) => update({ sort, dir })}>ID</SortHeader>
              <SortHeader field="name" sort={{ field: query.sort, dir: query.dir }} onSort={(sort, dir) => update({ sort, dir })}>Name</SortHeader>
              <SortHeader field="category" sort={{ field: query.sort, dir: query.dir }} onSort={(sort, dir) => update({ sort, dir })}>Category</SortHeader>
              <th>Brand</th>
              <th>Model</th>
              <SortHeader field="listings" sort={{ field: query.sort, dir: query.dir }} onSort={(sort, dir) => update({ sort, dir })} align="right" className="text-right">Listings</SortHeader>
              <th className="text-right">In builds</th>
              <th><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {products.loading && !products.data && <TableMessage colSpan={8}><Loading /></TableMessage>}
            {products.data?.items.length === 0 && <TableMessage colSpan={8}>No products match.</TableMessage>}
            {products.data?.items.map((p) => (
              <tr key={p.product_id}>
                <td className="text-muted">{p.product_id}</td>
                <td><Link to={`/product/${p.product_id}`} className="link font-semibold">{p.name}</Link></td>
                <td>{categoryInfo(p.category).label}</td>
                <td>{p.brand}</td>
                <td>{p.model}</td>
                <td className="text-right">{p.listing_count}</td>
                <td className="text-right">{p.build_count}</td>
                <td>
                  <div className="flex justify-end gap-1.5">
                    <button type="button" className="btn-secondary btn-sm" onClick={() => { setForm({ productId: p.product_id }); window.scrollTo(0, 0) }}>Edit</button>
                    <button type="button" className="btn-secondary btn-sm" onClick={() => setToDelete(p)}>Delete</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {products.data && <Pagination {...products.data} pageSize={products.data.page_size} noun="products" onPage={(page) => setQuery((q) => ({ ...q, page }))} />}

      <ConfirmDialog open={Boolean(toDelete)} title="Delete this product?" busy={busy} onCancel={() => setToDelete(null)} onConfirm={remove}>
        <p>“{toDelete?.name}” will be permanently deleted along with its specifications.</p>
        {(toDelete?.listing_count > 0 || toDelete?.build_count > 0) && (
          <p className="mt-2 text-warn">
            Remove the listings and references in saved builds before deleting this product.
          </p>
        )}
      </ConfirmDialog>
    </div>
  )
}

function ProductForm({ productId, lookups, onCancel, onSaved }) {
  const existing = useApi(productId ? `/admin/products/${productId}` : null)
  const [values, setValues] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  let form = values
  if (!form && !productId) form = { category: lookups.categories[0]?.name || '', brand: '', model: '', specification: '', spec: {}, links: [] }
  if (!form && existing.data) {
    const { product, spec, links } = existing.data
    form = { category: product.category, brand: product.brand, model: product.model, specification: product.specification || '', spec, links }
  }

  if (existing.error) return (
    <div className="mb-4 space-y-2">
      <Notice type="error" onRetry={existing.reload}>{existing.error.message}</Notice>
      <button type="button" className="btn-secondary" onClick={onCancel} disabled={busy}>Cancel</button>
    </div>
  )
  if (!form) return <Loading />

  const set = (changes) => setValues({ ...form, ...changes })
  const setSpec = (column, value) => set({ spec: { ...form.spec, [column]: value } })
  const fields = lookups.spec_fields[form.category] || []
  const linkOptions = form.category === 'Case' ? lookups.form_factors : form.category === 'Cooler' ? lookups.sockets : null

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const result = productId
        ? await api(`/admin/products/${productId}`, { method: 'PUT', body: form })
        : await api('/admin/products', { method: 'POST', body: form })
      onSaved(result, !productId)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="panel mb-4 p-4" onSubmit={submit}>
      <h2 className="mb-3 text-lg font-semibold">{productId ? `Edit product #${productId}` : 'Add product'}</h2>
      {error && <Notice type="error" className="mb-3">{error}</Notice>}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <label htmlFor="pf-category" className="label">Category</label>
          <select
            id="pf-category"
            className="input"
            value={form.category}
            disabled={Boolean(productId)}
            onChange={(e) => set({ category: e.target.value, spec: {}, links: [] })}
          >
            {lookups.categories.map((c) => <option key={c.category_id} value={c.name}>{categoryInfo(c.name).label}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="pf-brand" className="label">Brand</label>
          <input id="pf-brand" className="input" maxLength={100} value={form.brand} onChange={(e) => set({ brand: e.target.value })} required />
        </div>
        <div className="lg:col-span-2">
          <label htmlFor="pf-model" className="label">Model</label>
          <input id="pf-model" className="input" maxLength={100} value={form.model} onChange={(e) => set({ model: e.target.value })} required />
        </div>
        <div className="sm:col-span-2 lg:col-span-4">
          <label htmlFor="pf-spec-text" className="label">Specification summary (optional)</label>
          <input id="pf-spec-text" className="input" maxLength={1000} value={form.specification} onChange={(e) => set({ specification: e.target.value })} />
        </div>
      </div>

      {fields.length > 0 && (
        <fieldset className="mt-4">
          <legend className="mb-2 text-sm font-semibold">{categoryInfo(form.category).label} specifications</legend>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {fields.map((f) => (
              <SpecInput key={f.column} field={f} value={form.spec[f.column] ?? ''} lookups={lookups} onChange={(v) => setSpec(f.column, v)} />
            ))}
          </div>
        </fieldset>
      )}

      {linkOptions && (
        <fieldset className="mt-4">
          <legend className="mb-2 text-sm font-semibold">{form.category === 'Case' ? 'Supported motherboard sizes' : 'Supported CPU sockets'}</legend>
          <div className="flex flex-wrap gap-x-5 gap-y-1">
            {linkOptions.map((o) => (
              <label key={o.id} className="flex items-center gap-1.5 text-sm">
                <input
                  type="checkbox"
                  checked={form.links.includes(o.id)}
                  onChange={(e) => set({ links: e.target.checked ? [...form.links, o.id] : form.links.filter((id) => id !== o.id) })}
                />
                {o.name}
              </label>
            ))}
          </div>
        </fieldset>
      )}

      <div className="mt-4 flex gap-2">
        <button type="submit" className="btn-primary" disabled={busy}>{busy ? 'Saving…' : productId ? 'Save changes' : 'Add product'}</button>
        <button type="button" className="btn-secondary" onClick={onCancel} disabled={busy}>Cancel</button>
      </div>
    </form>
  )
}

function SpecInput({ field, value, lookups, onChange }) {
  const id = `spec-${field.column}`
  const label = field.label.charAt(0).toUpperCase() + field.label.slice(1)
  let input
  if (field.kind === 'choice' || field.kind === 'lookup') {
    const options = field.kind === 'choice'
      ? field.options.map((o) => ({ id: o, name: o }))
      : (field.lookup === 'socket' ? lookups.sockets : lookups.form_factors)
    input = (
      <select id={id} className="input" value={value} onChange={(e) => onChange(field.kind === 'lookup' ? Number(e.target.value) || '' : e.target.value)} required>
        <option value="">Choose…</option>
        {options.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
      </select>
    )
  } else {
    const numeric = field.kind === 'int' || field.kind === 'float'
    input = (
      <input
        id={id}
        className="input"
        type={numeric ? 'number' : 'text'}
        min={numeric ? 0 : undefined}
        step={field.kind === 'float' ? 'any' : field.kind === 'int' ? '1' : undefined}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
      />
    )
  }
  return (
    <div>
      <label htmlFor={id} className="label">{label}</label>
      {input}
    </div>
  )
}
