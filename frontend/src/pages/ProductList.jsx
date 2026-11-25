import { useState } from 'react'
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useBuild } from '../build'
import { categoryFromSlug, categoryInfo, sortCategories } from '../categories'
import { formatPrice, formatSpec } from '../format'
import { useApi, useCategories } from '../useApi'
import { Loading, Notice, PageTitle, Pagination, SortHeader, TableMessage } from '../components/ui'

const MODE_PARAMS = ['mode', 'replace']

export default function ProductList() {
  const { slug } = useParams()
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const location = useLocation()
  const build = useBuild()
  const { categories, loading: categoriesLoading, error: categoriesError, reload: reloadCategories } = useCategories()
  const [showFilters, setShowFilters] = useState(false)

  const category = slug ? categoryFromSlug(slug, categories) : null
  const info = category ? categoryInfo(category) : null
  const selectMode = params.get('mode') === 'select' && Boolean(category)
  const replaceId = selectMode ? Number(params.get('replace')) || null : null
  const selection = { back: location.pathname + location.search, replaceId }
  const ready = !slug || Boolean(category)

  const query = { category }
  for (const [key, value] of params) if (!MODE_PARAMS.includes(key)) query[key] = value
  const products = useApi(ready ? '/products' : null, query)
  const filterOptions = useApi(ready ? '/products/filters' : null, { category })
  const sort = { field: params.get('sort') || 'price', dir: params.get('dir') || 'asc' }

  function update(changes, resetPage = true) {
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(changes)) {
      const empty = value === null || value === undefined || value === '' || (Array.isArray(value) && !value.length)
      if (empty) next.delete(key)
      else next.set(key, Array.isArray(value) ? value.join(',') : value)
    }
    if (resetPage) next.delete('page')
    setParams(next)
  }

  function clearFilters() {
    const next = new URLSearchParams()
    for (const key of MODE_PARAMS) if (params.get(key)) next.set(key, params.get(key))
    setParams(next)
  }

  function addToBuild(product) {
    const multi = Boolean(product.multi_allowed)
    build.addProduct({ productId: product.product_id, category: product.category, multi, replaceId })
    navigate('/', { state: { message: replaceId ? `Switched to ${product.name}.` : `Added ${product.name}.` } })
  }

  if (slug && !categoriesLoading && !category) {
    return (
      <div>
        <PageTitle>{categoriesError ? 'Browse parts' : 'Category not found'}</PageTitle>
        {categoriesError ? (
          <Notice type="error" onRetry={reloadCategories}>Could not load categories. {categoriesError.message}</Notice>
        ) : (
          <p>
            There is no product category called “{slug}”. <Link to="/products" className="link">Browse all products</Link>.
          </p>
        )}
      </div>
    )
  }

  const title = selectMode ? `${replaceId ? 'Replace' : 'Choose'} ${info.label === 'CPU' ? 'CPU' : info.label.toLowerCase()}` : info?.plural || 'Browse parts'
  const hasFilters = [...params.keys()].some((k) => !MODE_PARAMS.includes(k) && !['sort', 'dir', 'page'].includes(k))

  return (
    <div>
      {selectMode && (
        <p className="mb-1 text-sm">
          <Link to="/" className="link">
            ← Back to build
          </Link>
        </p>
      )}
      <PageTitle>{title}</PageTitle>

      <button type="button" className="btn-secondary mb-3 lg:hidden" onClick={() => setShowFilters((s) => !s)} aria-expanded={showFilters}>
        {showFilters ? 'Hide filters' : 'Show filters'}
      </button>

      <div className="flex flex-col gap-5 lg:flex-row lg:items-start">
        <aside className={`${showFilters ? 'block' : 'hidden'} w-full shrink-0 lg:block lg:w-[245px]`} aria-label="Filters">
          <FilterSidebar
            key={`${category}:${params.get('min_price')}:${params.get('max_price')}`}
            categories={selectMode ? [] : sortCategories(categories)}
            activeCategory={category}
            onCategory={() => setShowFilters(false)}
            options={filterOptions}
            params={params}
            update={update}
            hasFilters={hasFilters}
            clearFilters={clearFilters}
          />
        </aside>

        <section className="min-w-0 flex-1">
          <SearchBar initial={params.get('q') || ''} onSearch={(q) => update({ q })} key={params.get('q') || ''} />

          {products.data?.fuzzy && products.data.items.length > 0 && (
            <Notice type="warning" className="mb-2">
              No exact match for “{params.get('q')}”. Showing similar results.
            </Notice>
          )}
          {products.error && (
            <Notice type="error" onRetry={products.reload} className="mb-2">
              Could not load products. {products.error.message}
            </Notice>
          )}

          <div className="panel overflow-x-auto">
            <ProductTable
              data={products.data}
              loading={products.loading || Boolean(slug && categoriesLoading)}
              error={products.error}
              selection={selection}
              category={category}
              sort={sort}
              onSort={(field, dir) => update({ sort: field, dir })}
              onAdd={addToBuild}
              addLabel={replaceId ? 'Replace' : 'Add'}
              hasFilters={hasFilters}
              clearFilters={clearFilters}
            />
          </div>
          {products.data && (
            <Pagination
              page={products.data.page}
              pages={products.data.pages}
              total={products.data.total}
              pageSize={products.data.page_size}
              noun="products"
              onPage={(page) => {
                update({ page }, false)
                window.scrollTo(0, 0)
              }}
            />
          )}
        </section>
      </div>
    </div>
  )
}

function SearchBar({ initial, onSearch }) {
  const [text, setText] = useState(initial)
  return (
    <form
      role="search"
      className="mb-3 flex gap-2"
      onSubmit={(e) => {
        e.preventDefault()
        onSearch(text.trim())
      }}
    >
      <label htmlFor="product-search" className="sr-only">
        Search products
      </label>
      <div className="min-w-0 flex-1">
        <input
          id="product-search"
          type="search"
          className="input"
          placeholder="Search by name, brand, or model"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
      </div>
      <button type="submit" className="btn-primary">
        Search
      </button>
      {initial && (
        <button
          type="button"
          className="btn-secondary"
          onClick={() => {
            setText('')
            onSearch('')
          }}
        >
          Clear
        </button>
      )}
    </form>
  )
}

function ProductTable({ data, loading, error, selection, category, sort, onSort, onAdd, addLabel, hasFilters, clearFilters }) {
  const specColumns = category ? data?.columns || [] : []
  const colSpan = 4 + (category ? specColumns.length : 2)
  const sortProps = { sort, onSort }

  return (
    <table className="data-table" aria-label="Products">
      <thead>
        <tr>
          <SortHeader field="name" {...sortProps}>
            Name
          </SortHeader>
          {category ? (
            specColumns.map((c) => (
              <SortHeader key={c.key} field={c.key} className="hidden xl:table-cell" {...sortProps}>
                {c.label}
              </SortHeader>
            ))
          ) : (
            <>
              <SortHeader field="category" className="hidden sm:table-cell" {...sortProps}>
                Category
              </SortHeader>
              <th className="hidden xl:table-cell">Specifications</th>
            </>
          )}
          <SortHeader field="price" align="right" className="text-right" {...sortProps}>
            Price
          </SortHeader>
          <th className="hidden md:table-cell">Availability</th>
          <th>
            <span className="sr-only">Add to build</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {loading && !data && (
          <TableMessage colSpan={colSpan}>
            <Loading text="Loading products…" />
          </TableMessage>
        )}
        {error && <TableMessage colSpan={colSpan}>Products are unavailable.</TableMessage>}
        {data && !data.items.length && (
          <TableMessage colSpan={colSpan}>
            No matching products.{' '}
            {hasFilters && (
              <button type="button" className="link" onClick={clearFilters}>
                Reset search and filters
              </button>
            )}
          </TableMessage>
        )}
        {data?.items.map((p) => (
          <tr key={p.product_id} className={loading ? 'opacity-60' : ''}>
            <td className="w-full min-w-28">
              <Link to={`/product/${p.product_id}`} state={selection} className="link font-semibold">
                {p.name}
              </Link>
              {!category && <div className="mt-0.5 text-xs text-muted sm:hidden">{categoryInfo(p.category).label}</div>}
            </td>
            {category ? (
              specColumns.map((c) => (
                <td key={c.key} className="hidden whitespace-nowrap xl:table-cell">
                  {formatSpec(p[c.key], c.unit)}
                </td>
              ))
            ) : (
              <>
                <td className="hidden whitespace-nowrap sm:table-cell">{categoryInfo(p.category).label}</td>
                <td className="hidden min-w-32 text-xs text-muted xl:table-cell">{p.specification || '—'}</td>
              </>
            )}
            <td className="text-right whitespace-nowrap tabular-nums">
              {p.best_price !== null ? (
                <>
                  <div className="font-semibold">{formatPrice(p.best_price)}</div>
                  <div className="text-xs text-muted">{p.best_store}</div>
                </>
              ) : (
                <span className="text-muted">—</span>
              )}
            </td>
            <td className="hidden text-xs whitespace-nowrap md:table-cell">
              {p.in_stock_count > 0 ? (
                <span className="text-ok">
                  {p.in_stock_count} of {p.listing_count} in stock
                </span>
              ) : p.listing_count > 0 ? (
                <span className="text-muted">No in-stock offers</span>
              ) : (
                <span className="text-muted">No listings</span>
              )}
            </td>
            <td className="text-right">
              <button type="button" className="btn-primary btn-sm" aria-label={`${addLabel} ${p.name}`} onClick={() => onAdd(p)}>
                {addLabel}
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function FilterSection({ title, children, expanded = false }) {
  return (
    <details open={expanded} className="border-b border-line last:border-0">
      <summary className="cursor-pointer px-3 py-2 text-sm font-semibold select-none">{title}</summary>
      <div className="px-3 pb-3">{children}</div>
    </details>
  )
}

function CheckboxList({ name, values, selected, onToggle, format = (v) => v.value }) {
  return (
    <ul className="max-h-56 space-y-1 overflow-y-auto">
      {values.map((v) => {
        const id = `${name}-${v.value}`
        return (
          <li key={v.value} className="flex items-center gap-2 text-sm">
            <input id={id} type="checkbox" checked={selected.includes(String(v.value))} onChange={() => onToggle(String(v.value))} />
            <label htmlFor={id} className="flex-1 cursor-pointer">
              {format(v)}
            </label>
            <span className="text-xs text-muted">{v.count}</span>
          </li>
        )
      })}
    </ul>
  )
}

function FilterSidebar({ categories, activeCategory, onCategory, options, params, update, hasFilters, clearFilters }) {
  const listParam = (key) => (params.get(key) || '').split(',').filter(Boolean)
  const toggle = (key) => (value) => {
    const current = listParam(key)
    update({ [key]: current.includes(value) ? current.filter((v) => v !== value) : [...current, value] })
  }
  const [minPrice, setMinPrice] = useState(params.get('min_price') || '')
  const [maxPrice, setMaxPrice] = useState(params.get('max_price') || '')

  const data = options.data
  const searchQuery = new URLSearchParams()
  if (params.get('q')) searchQuery.set('q', params.get('q'))
  const search = searchQuery.toString()
  return (
    <div className="panel">
      <div className="flex items-center justify-between border-b border-line px-3 py-2">
        <h2 className="text-base font-semibold">Filters</h2>
        <button type="button" className="link text-xs disabled:text-muted disabled:no-underline" onClick={clearFilters} disabled={!hasFilters}>
          Reset all
        </button>
      </div>

      {categories.length > 0 && (
        <FilterSection title="Category" expanded>
          <ul className="space-y-1 text-sm">
            <li>
              <Link to={{ pathname: '/products', search }} onClick={onCategory} className={activeCategory ? 'link' : 'font-semibold'}>
                All parts
              </Link>
            </li>
            {categories.map((c) => (
              <li key={c.category_id} className="flex justify-between">
                <Link to={{ pathname: `/products/${categoryInfo(c.name).slug}`, search }} onClick={onCategory} className={activeCategory === c.name ? 'font-semibold' : 'link'}>
                  {categoryInfo(c.name).plural}
                </Link>
                <span className="text-xs text-muted">{c.product_count}</span>
              </li>
            ))}
          </ul>
        </FilterSection>
      )}

      {options.loading && !data && (
        <div className="p-3">
          <Loading text="Loading filters…" />
        </div>
      )}
      {options.error && (
        <div className="p-3">
          <Notice type="error" onRetry={options.reload}>
            Unable to load filters.
          </Notice>
        </div>
      )}

      {data && (
        <>
          <FilterSection title="Price" expanded>
            <form
              className="space-y-2"
              onSubmit={(e) => {
                e.preventDefault()
                const maxInput = e.currentTarget.elements.namedItem('max-price')
                if (minPrice && maxPrice && Number(maxPrice) < Number(minPrice)) {
                  maxInput.setCustomValidity('Enter a maximum price at least as high as the minimum.')
                  maxInput.reportValidity()
                  return
                }
                update({ min_price: minPrice, max_price: maxPrice })
              }}
            >
              <div className="flex items-center gap-2">
                <label htmlFor="min-price" className="sr-only">
                  Minimum price
                </label>
                <input id="min-price" type="number" min="0" step="any" className="input py-1" placeholder={`$${Math.floor(data.price.min ?? 0)}`} value={minPrice} onChange={(e) => {
                  e.currentTarget.form.elements.namedItem('max-price').setCustomValidity('')
                  setMinPrice(e.target.value)
                }} />
                <span className="text-muted">to</span>
                <label htmlFor="max-price" className="sr-only">
                  Maximum price
                </label>
                <input id="max-price" name="max-price" type="number" min="0" step="any" className="input py-1" placeholder={`$${Math.ceil(data.price.max ?? 0)}`} value={maxPrice} onChange={(e) => {
                  e.currentTarget.setCustomValidity('')
                  setMaxPrice(e.target.value)
                }} />
              </div>
              <button type="submit" className="btn-secondary btn-sm w-full">
                Apply range
              </button>
            </form>
            <p className="mt-1 text-xs text-muted">Uses the lowest in-stock price across stores.</p>
          </FilterSection>

          <FilterSection title="Availability" expanded>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={params.get('in_stock') === '1'} onChange={(e) => update({ in_stock: e.target.checked ? '1' : null })} />
              In stock at one or more stores
            </label>
          </FilterSection>

          <FilterSection title="Brand" expanded={Boolean(params.get('brand'))}>
            <CheckboxList name="brand" values={data.brands} selected={listParam('brand')} onToggle={toggle('brand')} />
          </FilterSection>

          {data.specs.map((spec) => (
            <FilterSection key={spec.key} title={spec.label} expanded={Boolean(params.get(spec.key))}>
              <CheckboxList name={spec.key} values={spec.values} selected={listParam(spec.key)} onToggle={toggle(spec.key)} format={(v) => formatSpec(v.value, spec.unit)} />
            </FilterSection>
          ))}

          <FilterSection title="Listed at" expanded={Boolean(params.get('store'))}>
            <CheckboxList name="store" values={data.stores} selected={listParam('store')} onToggle={toggle('store')} format={(v) => v.label} />
          </FilterSection>
        </>
      )}
    </div>
  )
}
