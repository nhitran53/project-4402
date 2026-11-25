import { createContext, useContext, useEffect, useState } from 'react'

const STORAGE_KEY = 'pcparts.build'
const EMPTY = { items: [], saved: null }

function loadStored() {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY))
    return stored && Array.isArray(stored.items) ? stored : EMPTY
  } catch {
    return EMPTY
  }
}

// Saved builds store parts and quantities only, so that is what we compare for unsaved changes.
export function partsSnapshot(items) {
  return JSON.stringify(
    items.map((i) => [i.productId, i.quantity]).sort((a, b) => a[0] - b[0]),
  )
}

const BuildContext = createContext(null)

export function BuildProvider({ children }) {
  const [build, setBuild] = useState(loadStored)

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(build))
    } catch {
      // Keep the draft in memory if storage is unavailable.
    }
  }, [build])

  const updateItems = (fn) => setBuild((b) => ({ ...b, items: fn(b.items) }))

  const actions = {
    addProduct({ productId, category, multi, listingId = null, replaceId = null }) {
      updateItems((items) => {
        const existing = items.find((i) => i.productId === productId)
        if (multi && existing && !replaceId) {
          return items.map((i) => (i === existing ? { ...i, quantity: i.quantity + 1, listingId: listingId ?? i.listingId } : i))
        }
        const replaced = items.find((item) => item.productId === replaceId && item.category === category)
        const quantity = multi && replaced
          ? replaced.quantity + (existing && existing !== replaced ? existing.quantity : 0)
          : 1
        const next = { productId, category, quantity, listingId }
        const kept = items.filter((item) =>
          multi ? item !== replaced && item !== existing : item.category !== category,
        )
        return [...kept, next]
      })
    },
    removeItem(productId) {
      updateItems((items) => items.filter((i) => i.productId !== productId))
    },
    setQuantity(productId, quantity) {
      updateItems((items) => items.map((i) => (i.productId === productId ? { ...i, quantity } : i)))
    },
    setOffer(productId, listingId) {
      updateItems((items) => items.map((i) => (i.productId === productId ? { ...i, listingId } : i)))
    },
    clear() {
      setBuild(EMPTY)
    },
    markSaved(saved) {
      setBuild((b) => ({ ...b, saved }))
    },
    detachSaved(id, userId) {
      setBuild((b) => b.saved?.id === id && b.saved.userId === userId ? { ...b, saved: null } : b)
    },
    loadSaved({ id, name, userId }, savedItems) {
      const items = savedItems.map((i) => ({
        productId: i.product_id,
        category: i.category,
        quantity: i.quantity,
        listingId: null,
      }))
      setBuild({ items, saved: { id, name, userId, snapshot: partsSnapshot(items) } })
    },
  }

  return <BuildContext.Provider value={{ ...build, ...actions }}>{children}</BuildContext.Provider>
}

export function useBuild() {
  return useContext(BuildContext)
}
