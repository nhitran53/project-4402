import { Link, useParams, useSearchParams } from 'react-router-dom'
import { categoryInfo, sortCategories } from '../categories'
import { AVAILABILITY_LABELS, formatDate, formatPrice } from '../format'
import { useApi, useCategories } from '../useApi'
import { AvailabilityBadge, Loading, Notice, PageTitle, Pagination, SortHeader, TableMessage } from '../components/ui'

export default function StoreDetail() {
  const { id } = useParams()
  const [params, setParams] = useSearchParams()
  const { categories } = useCategories()
  const store = useApi(`/stores/${id}`)
  const listings = useApi(`/stores/${id}/listings`, Object.fromEntries(params))
  const sort = { field: params.get('sort') || 'category', dir: params.get('dir') || 'asc' }

  function update(changes, resetPage = true) {
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(changes)) value ? next.set(key, value) : next.delete(key)
    if (resetPage) next.delete('page')
    setParams(next)
  }

  if (store.error?.status === 404) {
    return (
      <div>
        <PageTitle>Store not found</PageTitle>
        <Link to="/stores" className="link">Back to stores</Link>
      </div>
    )
  }
  if (store.error) return <Notice type="error" onRetry={store.reload}>Could not load store. {store.error.message}</Notice>
  if (!store.data) return <Loading text="Loading store…" />

  const s = store.data
  return (
    <div>
      <nav aria-label="Breadcrumb" className="mb-2 text-sm text-muted">
        <Link to="/stores" className="link">Stores</Link> › {s.name}
      </nav>
      <PageTitle sub={s.website}>
        {s.name}
      </PageTitle>

      <form className="panel mb-3 flex flex-wrap items-end gap-3 px-3 py-3" onSubmit={(event) => {
        event.preventDefault()
        update({ q: event.currentTarget.elements.namedItem('q').value.trim() })
      }}>
        <div>
          <label htmlFor="store-category" className="label">Category</label>
          <select id="store-category" className="input" value={params.get('category') || ''} onChange={(e) => update({ category: e.target.value })}>
            <option value="">All categories</option>
            {sortCategories(categories).map((c) => (
              <option key={c.category_id} value={c.name}>{categoryInfo(c.name).plural}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="store-availability" className="label">Availability</label>
          <select id="store-availability" className="input" value={params.get('availability') || ''} onChange={(e) => update({ availability: e.target.value })}>
            <option value="">Any</option>
            {Object.entries(AVAILABILITY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
        <div className="min-w-36 flex-1">
          <label htmlFor="store-search" className="label">Product name</label>
          <input
            id="store-search"
            type="search"
            className="input"
            name="q"
            placeholder="Name or brand"
            key={params.get('q') || ''}
            defaultValue={params.get('q') || ''}
          />
        </div>
        <button type="submit" className="btn-primary">Search</button>
        {[...params.keys()].some((k) => ['category', 'availability', 'q'].includes(k)) && (
          <button type="button" className="btn-secondary" onClick={() => setParams({})}>Reset filters</button>
        )}
      </form>

      {listings.error && <Notice type="error" onRetry={listings.reload} className="mb-3">Could not load listings. {listings.error.message}</Notice>}

      <div className="panel overflow-x-auto">
        <table className="data-table" aria-label="Store listings">
          <thead>
            <tr>
              <SortHeader field="product" sort={sort} onSort={(f, d) => update({ sort: f, dir: d })}>Product</SortHeader>
              <SortHeader className="hidden md:table-cell" field="category" sort={sort} onSort={(f, d) => update({ sort: f, dir: d })}>Category</SortHeader>
              <SortHeader className="hidden sm:table-cell" field="availability" sort={sort} onSort={(f, d) => update({ sort: f, dir: d })}>Availability</SortHeader>
              <SortHeader field="price" sort={sort} onSort={(f, d) => update({ sort: f, dir: d })} align="right" className="text-right">Price</SortHeader>
              <SortHeader className="hidden lg:table-cell" field="updated" sort={sort} onSort={(f, d) => update({ sort: f, dir: d })}>Updated</SortHeader>
            </tr>
          </thead>
          <tbody>
            {listings.loading && !listings.data && <TableMessage colSpan={5}><Loading text="Loading listings…" /></TableMessage>}
            {listings.data?.items.length === 0 && <TableMessage colSpan={5}>No listings match these filters.</TableMessage>}
            {listings.data?.items.map((l) => (
              <tr key={l.listing_id}>
                <td>
                  <Link to={`/product/${l.product_id}`} className="link font-semibold">{l.product}</Link>
                  {l.is_best ? <div className="text-xs text-ok">Lowest price</div> : null}
                  <div className="mt-1 sm:hidden"><AvailabilityBadge value={l.availability} /></div>
                </td>
                <td className="hidden md:table-cell">{categoryInfo(l.category).label}</td>
                <td className="hidden sm:table-cell"><AvailabilityBadge value={l.availability} /></td>
                <td className="text-right font-semibold whitespace-nowrap tabular-nums">{formatPrice(l.price)}</td>
                <td className="hidden text-muted lg:table-cell">{formatDate(l.last_updated)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {listings.data && (
        <Pagination {...listings.data} pageSize={listings.data.page_size} noun="listings" onPage={(page) => update({ page }, false)} />
      )}
    </div>
  )
}
