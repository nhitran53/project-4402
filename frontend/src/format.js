const usd = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })

export function formatPrice(value) {
  return value === null || value === undefined ? '—' : usd.format(value)
}

export const AVAILABILITY_LABELS = {
  in_stock: 'In stock',
  out_of_stock: 'Out of stock',
  preorder: 'Preorder',
}

export function formatSpec(value, unit) {
  if (value === null || value === undefined || value === '') return '—'
  if (unit === 'GB' && value >= 1000 && value % 1000 === 0) return `${value / 1000} TB`
  return unit ? `${value} ${unit}` : String(value)
}

export function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value.replace(' ', 'T') + 'Z')
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}
