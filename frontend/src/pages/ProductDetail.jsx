import { useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { useBuild } from '../build'
import { categoryInfo } from '../categories'
import { formatDate, formatPrice, formatSpec } from '../format'
import { useApi } from '../useApi'
import { AvailabilityBadge, Loading, Notice, PageTitle } from '../components/ui'

export default function ProductDetail() {
  const { id } = useParams()
  const { data, error, loading, reload } = useApi(`/products/${id}`)
  const build = useBuild()
  const location = useLocation()
  const navigate = useNavigate()
  const [message, setMessage] = useState(null)

  if (loading) return <Loading text="Loading product…" />
  if (error?.status === 404) {
    return (
      <>
        <PageTitle>Product not found</PageTitle>
        <Link to="/products" className="link">Browse parts</Link>
      </>
    )
  }
  if (error) return <Notice type="error" onRetry={reload}>{error.message}</Notice>

  const { product, specs, listings } = data
  const info = categoryInfo(product.category)
  const inBuild = build.items.find((item) => item.productId === product.product_id)
  const multi = Boolean(product.multi_allowed)
  const selection = location.state
  const replacing = build.items.some((item) => item.category === product.category && item.productId === selection?.replaceId)
  const defaultOffer = listings.find((listing) => listing.is_best)
  const addLabel = replacing ? 'Replace part' : inBuild && multi ? 'Add another' : 'Add to build'

  function addToBuild(listingId = null) {
    build.addProduct({
      productId: product.product_id,
      category: product.category,
      multi,
      listingId,
      replaceId: replacing ? selection.replaceId : null,
    })
    navigate('/', { state: { message: replacing ? `Switched to ${product.name}.` : `Added ${product.name}.` } })
  }

  function chooseOffer(listingId) {
    build.setOffer(product.product_id, listingId)
    setMessage({ id, text: listingId ? 'Store updated.' : 'Using the lowest in-stock price.' })
  }

  return (
    <>
      <nav aria-label="Breadcrumb" className="mb-2 text-sm">
        <Link to={selection?.back || `/products/${info.slug}`} className="link">
          {selection?.back ? '← Back to results' : `← ${info.plural}`}
        </Link>
      </nav>
      <PageTitle sub={[product.brand, info.label].filter(Boolean).join(' · ')}>{product.name}</PageTitle>

      {message?.id === id && (
        <Notice type="success" onDismiss={() => setMessage(null)} className="mb-4">
          {message.text} <Link to="/" className="link">View build</Link>
        </Notice>
      )}

      <div className="panel mb-6 flex flex-wrap items-center justify-between gap-3 p-4">
        <div>
          <p className="text-xs font-semibold text-muted">Lowest in-stock price</p>
          <div className="mt-1 flex flex-wrap items-baseline gap-x-2">
            <strong className="text-xl tabular-nums">{defaultOffer ? formatPrice(defaultOffer.price) : '—'}</strong>
            <span className="text-sm text-muted">{defaultOffer?.store || 'No in-stock offers'}</span>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {inBuild && <Link to="/" className="link">In your build{inBuild.quantity > 1 ? ` × ${inBuild.quantity}` : ''}</Link>}
          {(!inBuild || multi || replacing) && (
            <button type="button" className="btn-primary" onClick={() => addToBuild()}>{addLabel}</button>
          )}
        </div>
      </div>

      <section className="mb-6">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold">Store prices</h2>
          {inBuild?.listingId && (
            <button type="button" className="btn-secondary btn-sm" onClick={() => chooseOffer(null)}>Use lowest price</button>
          )}
        </div>
        {!listings.length ? <Notice>No store listings yet.</Notice> : (
          <div className="panel overflow-x-auto">
            <table className="data-table" aria-label="Store prices">
              <thead>
                <tr>
                  <th>Store</th>
                  <th className="hidden sm:table-cell">Availability</th>
                  <th className="text-right">Price</th>
                  <th className="hidden md:table-cell">Updated</th>
                  <th><span className="sr-only">Build actions</span></th>
                </tr>
              </thead>
              <tbody>
                {listings.map((listing) => {
                  const selected = inBuild && (inBuild.listingId ? inBuild.listingId === listing.listing_id : listing.is_best)
                  return (
                    <tr key={listing.listing_id}>
                      <td>
                        <Link to={`/stores/${listing.store_id}`} className="link font-semibold">{listing.store}</Link>
                        {listing.is_best ? <div className="text-xs text-ok">Lowest price</div> : null}
                        <div className="mt-1 sm:hidden"><AvailabilityBadge value={listing.availability} /></div>
                      </td>
                      <td className="hidden sm:table-cell"><AvailabilityBadge value={listing.availability} /></td>
                      <td className="text-right font-semibold whitespace-nowrap tabular-nums">{formatPrice(listing.price)}</td>
                      <td className="hidden whitespace-nowrap text-muted md:table-cell">{formatDate(listing.last_updated)}</td>
                      <td className="text-right">
                        {selected && !replacing ? <span className="text-xs font-semibold text-ok">Selected</span>
                          : listing.availability !== 'out_of_stock' && (
                            <button type="button" className="btn-secondary btn-sm"
                              aria-label={`${inBuild && !replacing ? 'Use offer from' : 'Add from'} ${listing.store}`}
                              onClick={() => inBuild && !replacing ? chooseOffer(listing.listing_id) : addToBuild(listing.listing_id)}>
                              {inBuild && !replacing ? 'Use offer' : 'Add'}
                            </button>
                          )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold">Specifications</h2>
        <dl className="panel grid divide-y divide-line">
          {[{ key: 'model', label: 'Model', value: product.model }, ...specs].map((spec) => (
            <div key={spec.key} className="grid grid-cols-[minmax(7rem,1fr)_2fr] gap-3 px-3 py-2.5">
              <dt className="font-medium text-muted">{spec.label}</dt>
              <dd>{formatSpec(spec.value, spec.unit)}</dd>
            </div>
          ))}
          {!!product.specification && (
            <div className="grid grid-cols-[minmax(7rem,1fr)_2fr] gap-3 px-3 py-2.5">
              <dt className="font-medium text-muted">Summary</dt>
              <dd>{product.specification}</dd>
            </div>
          )}
        </dl>
      </section>
    </>
  )
}
