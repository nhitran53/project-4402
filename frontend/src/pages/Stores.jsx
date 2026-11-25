import { Link } from 'react-router-dom'
import { useApi } from '../useApi'
import { Loading, Notice, PageTitle, TableMessage } from '../components/ui'

export default function Stores() {
  const { data, error, loading, reload } = useApi('/stores')

  return (
    <div>
      <PageTitle>Stores</PageTitle>
      {error && (
        <Notice type="error" onRetry={reload} className="mb-3">
          Could not load stores. {error.message}
        </Notice>
      )}
      <div className="panel overflow-x-auto">
        <table className="data-table" aria-label="Stores">
          <thead>
            <tr>
              <th>Store</th>
              <th className="hidden sm:table-cell">Website</th>
              <th className="text-right">Listings</th>
              <th className="text-right">In stock</th>
              <th className="text-right">Lowest offers</th>
            </tr>
          </thead>
          <tbody>
            {loading && !data && (
              <TableMessage colSpan={5}>
                <Loading text="Loading stores…" />
              </TableMessage>
            )}
            {data?.length === 0 && <TableMessage colSpan={5}>No stores yet.</TableMessage>}
            {data?.map((s) => (
              <tr key={s.store_id}>
                <td className="font-semibold">
                  <Link to={`/stores/${s.store_id}`} className="link">
                    {s.name}
                  </Link>
                </td>
                <td className="hidden text-muted sm:table-cell">{s.website || '—'}</td>
                <td className="text-right">{s.listing_count}</td>
                <td className="text-right">{s.in_stock_count}</td>
                <td className="text-right">
                  {s.lowest_price_count} {s.lowest_price_count === 1 ? 'product' : 'products'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-muted">Lowest offers counts the products for which a store has the lowest in-stock price.</p>
    </div>
  )
}
