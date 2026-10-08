import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { formatPrice, type Product } from '../api'

// Small stock badge: helps shoppers skip items that are gone in their size.
function stockBadge(product: Product, size?: string): { text: string; tone: 'low' | 'out' } | null {
  if (size) {
    const qty = product.inventory.find((s) => s.size === size)?.quantity ?? 0
    if (qty === 0) return { text: `Sold out in ${size}`, tone: 'out' }
    if (qty <= 5) return { text: `Only ${qty} left in ${size}`, tone: 'low' }
    return null
  }
  if (product.total_stock === 0) return { text: 'Sold out', tone: 'out' }
  if (product.inventory.every((s) => s.quantity <= 5)) return { text: 'Only a few left', tone: 'low' }
  return null
}

function shortType(garmentType: string) {
  return garmentType.replace(/^(men's|short-sleeve|long-sleeve|heavyweight)\s+/i, '').replace(/\bt-shirt\b/i, 'tee')
}

export default function ProductCard({ product, highlightSize, index = 0 }: { product: Product; highlightSize?: string; index?: number }) {
  const badge = stockBadge(product, highlightSize)
  return (
    <Link
      to={`/products/${product.product_id}`}
      className="product-card"
      style={{ '--i': Math.min(index, 11) } as CSSProperties}
    >
      <div className="product-card-image">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        {badge && <span className={`stock-badge ${badge.tone}`}>{badge.text}</span>}
        <span className="type-tag">{shortType(product.garment_type)}</span>
        {/* Size strip: filled = in stock, struck = sold out (shows on hover/focus) */}
        <span className="size-strip" aria-label={`In stock: ${product.inventory.filter((s) => s.quantity > 0).map((s) => s.size).join(', ')}`}>
          {product.inventory.map((s) => (
            <span key={s.size} className={s.quantity === 0 ? 'out' : s.quantity <= 5 ? 'low' : ''}>{s.size}</span>
          ))}
        </span>
      </div>
      <div className="product-card-body">
        <h3>{product.name}</h3>
        <p className="short-desc">{product.description}</p>
        <div className="card-foot">
          <span className="price">{formatPrice(product.price)}</span>
          <span className="card-cta">View →</span>
        </div>
      </div>
    </Link>
  )
}
