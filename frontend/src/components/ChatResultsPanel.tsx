import { useEffect, useRef } from 'react'
import { useChatResults } from '../ChatResultsContext'
import ProductCard from './ProductCard'

// Renders the chat's product matches on the page as regular product cards.
export default function ChatResultsPanel({ compact = false }: { compact?: boolean }) {
  const { results, fresh, clearResults } = useChatResults()
  const ref = useRef<HTMLElement>(null)

  // Bring fresh results into view when the chat sends new ones.
  useEffect(() => {
    if (results && fresh && !compact) ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [results, fresh, compact])

  if (!results) return null
  const { title, query, total_matches, products } = results
  const countText = total_matches > products.length ? `Showing ${products.length} of ${total_matches} matches` : `${products.length} ${products.length === 1 ? 'match' : 'matches'}`

  return (
    <div className="page chat-results-slot">
    <section ref={ref} className={`chat-results${compact ? ' compact' : ''}`} aria-live="polite" aria-label="Chat search results">
      <div className="chat-results-header">
        <div>
          <p className="eyebrow">💬 From your chat · “{query}”</p>
          <h2>{title}</h2>
          <p className="muted">{countText}</p>
        </div>
        <button type="button" className="btn btn-small btn-ghost" onClick={clearResults} aria-label="Clear chat results">Clear</button>
      </div>
      <div className="product-grid">
        {products.map((p, i) => <ProductCard key={p.product_id} product={p} index={i} />)}
      </div>
    </section>
    </div>
  )
}
