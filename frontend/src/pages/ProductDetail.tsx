import { useEffect, useState, type MouseEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchProduct, formatPrice, type Product } from '../api'
import { openChat } from '../chatEvents'

function stockLabel(qty: number) {
  if (qty === 0) return 'Sold out'
  if (qty <= 5) return `Only ${qty} left`
  return 'In stock'
}

export default function ProductDetail() {
  const { productId = '' } = useParams()
  const [product, setProduct] = useState<Product | null>(null)
  const [error, setError] = useState('')
  const [size, setSize] = useState<string | null>(null)
  const [zoom, setZoom] = useState<{ x: number; y: number } | null>(null)

  useEffect(() => {
    setProduct(null)
    setError('')
    setSize(null)
    fetchProduct(productId).then(setProduct).catch(() => setError('Product not found.'))
  }, [productId])

  if (error) return <section className="page"><p className="error">{error}</p><Link to="/products">← Back to products</Link></section>
  if (!product) return <section className="page"><div className="detail-skeleton" aria-label="Loading" /></section>

  const selected = size ? product.inventory.find((s) => s.size === size) : null

  // Magnifier: zoom the photo toward the cursor so shoppers can inspect prints and stitching.
  function onMove(e: MouseEvent<HTMLDivElement>) {
    const r = e.currentTarget.getBoundingClientRect()
    setZoom({ x: ((e.clientX - r.left) / r.width) * 100, y: ((e.clientY - r.top) / r.height) * 100 })
  }

  return (
    <section className="page">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/">Home</Link><span>/</span><Link to="/products">Products</Link><span>/</span><span>{product.name}</span>
      </nav>
      <div className="product-detail">
        <div
          className={`product-detail-image${zoom ? ' zooming' : ''}`}
          onMouseMove={onMove}
          onMouseLeave={() => setZoom(null)}
        >
          <img
            src={product.image_url}
            alt={product.name}
            style={zoom ? { transformOrigin: `${zoom.x}% ${zoom.y}%` } : undefined}
          />
          <span className="zoom-hint">Hover to zoom</span>
        </div>
        <div className="product-detail-info">
          <p className="eyebrow">{product.garment_type}</p>
          <h1>{product.name}</h1>
          <p className="price large">{formatPrice(product.price)}</p>
          <p className="detail-desc">{product.description}</p>
          {product.colors.length > 0 && (
            <div className="swatches" aria-label="Colors">
              {product.colors.map((c) => (
                <span key={c} className="swatch"><i style={{ background: colorCss(c) }} />{c}</span>
              ))}
            </div>
          )}
          <p className={product.total_stock > 0 ? 'in-stock' : 'error'}>
            {product.total_stock > 0 ? `● In stock · ${product.total_stock} available` : 'Sold out in all sizes'}
          </p>
          <h2 className="sizes-title">Choose a size</h2>
          <div className="size-list" role="radiogroup" aria-label="Sizes">
            {product.inventory.map((s) => (
              <button
                type="button"
                role="radio"
                aria-checked={size === s.size}
                key={s.size}
                className={`size-btn ${s.quantity === 0 ? 'sold-out' : s.quantity <= 5 ? 'low' : ''}${size === s.size ? ' selected' : ''}`}
                onClick={() => setSize(s.size)}
              >
                <span className="size">{s.size}</span>
                <span className="qty">{stockLabel(s.quantity)}</span>
              </button>
            ))}
          </div>
          <p className="size-note" aria-live="polite">
            {selected
              ? selected.quantity === 0
                ? `Size ${selected.size} is sold out. Ask the chat for a similar item in ${selected.size}.`
                : `Size ${selected.size}: ${selected.quantity} in stock${selected.quantity <= 5 ? ', so grab it soon' : ''}.`
              : 'Tap a size to see exactly how many are left.'}
          </p>
          <div className="detail-actions">
            <button
              type="button"
              className="btn"
              onClick={() => openChat(size ? `Is this in stock in ${size}?` : 'Does this come in other colors?')}
            >
              💬 Ask about this item
            </button>
            <Link to="/products" className="btn btn-ghost">Keep browsing</Link>
          </div>
          <ul className="perks">
            <li>✦ Officially licensed Yale apparel</li>
            <li>✦ Stock shown is live from our shop inventory</li>
            <li>✦ Pick it up at 57 Broadway, New Haven</li>
          </ul>
        </div>
      </div>
    </section>
  )
}

// Best-effort CSS color for catalog color names ("heather gray", "navy blue", ...).
function colorCss(name: string): string {
  const n = name.toLowerCase()
  const map: [string, string][] = [
    ['navy', '#14284b'], ['royal', '#2b59c3'], ['light blue', '#9cc3e6'], ['blue', '#2f6db5'], ['charcoal', '#3d4148'],
    ['dark heather', '#5a5f66'], ['heather', '#b9bcc1'], ['gray', '#a3a7ad'], ['grey', '#a3a7ad'], ['white', '#ffffff'],
    ['cream', '#f3ead7'], ['ivory', '#f6f1e3'], ['black', '#111'], ['red', '#b3262e'], ['yellow', '#f2c94c'],
    ['gold', '#c99a2e'], ['green', '#2f7d4f'], ['pink', '#f2a7c3'], ['coral', '#ef8a74'], ['orange', '#e67e22'],
    ['purple', '#6b4ea0'], ['maroon', '#6d1f2b'], ['brown', '#7a5230'], ['tan', '#c9a97a'],
  ]
  if (n.includes('multi')) return 'conic-gradient(#b3262e, #f2c94c, #2f6db5, #2f7d4f, #b3262e)'
  return map.find(([k]) => n.includes(k))?.[1] ?? '#cfd4da'
}
