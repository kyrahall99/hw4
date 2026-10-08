import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchProducts, type Product } from '../api'
import ProductCard from '../components/ProductCard'

const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']

// Same grouping as category_of() in backend/tools.py: 22 raw garment types -> shopper categories.
const CATEGORIES = [
  { key: 't-shirt', label: 'T-shirts' },
  { key: 'crewneck', label: 'Crewnecks' },
  { key: 'hoodie', label: 'Hoodies' },
  { key: 'quarter-zip', label: 'Quarter-zips' },
  { key: 'jacket', label: 'Jackets' },
  { key: 'long-sleeve shirt', label: 'Long sleeve' },
]

function categoryOf(garmentType: string): string {
  const g = garmentType.toLowerCase()
  if (g.includes('quarter-zip')) return 'quarter-zip'
  if (g.includes('full-zip hood')) return 'hoodie'
  if (g.includes('jacket')) return 'jacket'
  if (g.includes('hood')) return 'hoodie'
  if (g.includes('long-sleeve')) return 'long-sleeve shirt'
  if (g.includes('t-shirt')) return 't-shirt'
  return 'crewneck'
}

const SORTS = {
  featured: { label: 'Featured', fn: () => 0 },
  'price-asc': { label: 'Price: low to high', fn: (a: Product, b: Product) => a.price - b.price },
  'price-desc': { label: 'Price: high to low', fn: (a: Product, b: Product) => b.price - a.price },
  name: { label: 'Name: A to Z', fn: (a: Product, b: Product) => a.name.localeCompare(b.name) },
} as const
type SortKey = keyof typeof SORTS

export default function Products() {
  const [products, setProducts] = useState<Product[] | null>(null)
  const [error, setError] = useState('')
  // Filters live in the URL so Back works and filtered views can be shared.
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const cat = params.get('cat') ?? ''
  const size = params.get('size') ?? ''
  const sort = (params.get('sort') ?? 'featured') as SortKey

  useEffect(() => {
    fetchProducts().then(setProducts).catch(() => setError('Could not load products. Is the backend running?'))
  }, [])

  function setParam(key: string, value: string) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: key === 'q' })
  }

  const filtered = useMemo(() => {
    if (!products) return []
    const terms = q.toLowerCase().split(/\s+/).filter(Boolean)
    const list = products.filter((p) => {
      if (cat && categoryOf(p.garment_type) !== cat) return false
      if (size && !p.inventory.some((s) => s.size === size && s.quantity > 0)) return false
      if (terms.length) {
        const hay = [p.name, p.description, p.garment_type, ...p.search_tags, ...p.colors].join(' ').toLowerCase()
        if (!terms.every((t) => hay.includes(t))) return false
      }
      return true
    })
    return sort === 'featured' ? list : [...list].sort(SORTS[sort]?.fn ?? SORTS.featured.fn)
  }, [products, q, cat, size, sort])

  const hasFilters = !!(q || cat || size || sort !== 'featured')

  return (
    <section className="page">
      <h1>Shop Campus Customs</h1>
      {error && <p className="error">{error}</p>}
      {!products && !error && <p>Loading products…</p>}
      {products && (
        <>
          <div className="shop-toolbar" role="search">
            <input
              type="search"
              className="shop-search"
              placeholder="Search: bulldog, Berkeley, hockey, navy…"
              value={q}
              onChange={(e) => setParam('q', e.target.value)}
              aria-label="Search products"
            />
            <label className="toolbar-select">
              In stock in size
              <select value={size} onChange={(e) => setParam('size', e.target.value)}>
                <option value="">Any size</option>
                {SIZES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </label>
            <label className="toolbar-select">
              Sort
              <select value={sort} onChange={(e) => setParam('sort', e.target.value === 'featured' ? '' : e.target.value)}>
                {Object.entries(SORTS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
              </select>
            </label>
          </div>
          <div className="category-chips" role="group" aria-label="Filter by category">
            <button type="button" className={!cat ? 'chip active' : 'chip'} onClick={() => setParam('cat', '')}>All</button>
            {CATEGORIES.map((c) => (
              <button key={c.key} type="button" className={cat === c.key ? 'chip active' : 'chip'} onClick={() => setParam('cat', cat === c.key ? '' : c.key)}>
                {c.label}
              </button>
            ))}
          </div>
          <p className="muted results-count">
            Showing {filtered.length} of {products.length} items
            {size && <> · in stock in <strong>{size}</strong></>}
            {hasFilters && <button type="button" className="link-button" onClick={() => setParams(new URLSearchParams())}>Clear filters</button>}
          </p>
          {filtered.length === 0 ? (
            <div className="callout">
              <h2>No matches</h2>
              <p>Try a different search or size, or ask the chat assistant in the corner. It can suggest similar items.</p>
            </div>
          ) : (
            <div className="product-grid">
              {filtered.map((p, i) => <ProductCard key={p.product_id} product={p} highlightSize={size || undefined} index={i} />)}
            </div>
          )}
        </>
      )}
    </section>
  )
}
