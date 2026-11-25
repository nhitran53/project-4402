const categories = {
  CPU: { slug: 'cpu', label: 'CPU', plural: 'CPUs' },
  Cooler: { slug: 'cpu-cooler', label: 'CPU cooler', plural: 'CPU coolers' },
  Motherboard: { slug: 'motherboard', label: 'Motherboard', plural: 'Motherboards' },
  RAM: { slug: 'memory', label: 'Memory', plural: 'Memory' },
  Storage: { slug: 'storage', label: 'Storage', plural: 'Storage' },
  GPU: { slug: 'video-card', label: 'Graphics card', plural: 'Graphics cards' },
  Case: { slug: 'case', label: 'Case', plural: 'Cases' },
  PSU: { slug: 'power-supply', label: 'Power supply', plural: 'Power supplies' },
}
const order = Object.keys(categories)

export function categoryInfo(name) {
  return categories[name] || { slug: name.toLowerCase(), label: name, plural: name }
}

export function categoryFromSlug(slug, entries) {
  return entries.find(({ name }) => categoryInfo(name).slug === slug)?.name
}

export function sortCategories(entries) {
  const rank = (name) => order.includes(name) ? order.indexOf(name) : order.length
  return [...entries].sort((a, b) => rank(a.name) - rank(b.name))
}
