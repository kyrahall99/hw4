import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProducts, type Product } from '../api'
import ProductCard from '../components/ProductCard'
import { openChat } from '../chatEvents'

const FEATURED = [
  'basic-hoodie-big-yale',
  'champion-reverse-weave-crewneck',
  '2025-yale-vs-harvard-t-shirt',
  'benjamin-franklin-1-4-zip',
]

// Collection "pennants" link straight into a filtered Products view.
const collections = [
  { title: 'Hoodies', text: 'Heavyweight layers for late nights at Sterling.', to: '/products?cat=hoodie', tone: 'navy' },
  { title: 'Crewnecks', text: 'The classic. Rep your college or your sport.', to: '/products?cat=crewneck', tone: 'gold' },
  { title: 'Quarter-zips', text: 'Office hours to alumni weekend.', to: '/products?cat=quarter-zip', tone: 'cream' },
  { title: 'Game Day Tees', text: 'Built for The Game and every match after.', to: '/products?cat=t-shirt', tone: 'navy' },
]

const TICKER = [
  '12 residential colleges', 'Varsity team gear', 'Mom · Dad · Grandpa', 'Harvard–Yale ready',
  'Sizes XS–XXL', 'Live stock in every size', 'Fleece for New Haven winters', 'Bulldogs, bark loud',
]

export default function Home() {
  const [featured, setFeatured] = useState<Product[]>([])

  useEffect(() => {
    fetchProducts()
      .then((all) => setFeatured(FEATURED.map((id) => all.find((p) => p.product_id === id)).filter((p): p is Product => !!p)))
      .catch(() => setFeatured([]))
  }, [])

  return (
    <>
      <section className="hero">
        <div className="hero-inner">
          <div className="hero-copy">
            <p className="eyebrow">New Haven · 57 Broadway</p>
            <h1>
              Wear your <em>Bulldog</em> Blue.
            </h1>
            <p>
              Comfortable, officially licensed Yale gear for students, alumni, and every fan in between.
              Find your fit, pick your college, and show up in true Yale navy.
            </p>
            <div className="hero-actions">
              <Link to="/products" className="btn btn-gold">Shop all merch</Link>
              <button type="button" className="btn btn-outline" onClick={() => openChat('Help me find a gift for a Yale student')}>
                Ask a Bulldog 💬
              </button>
            </div>
          </div>
          <div className="hero-art" aria-hidden="true">
            <div className="pennant pennant-big"><span>YALE</span></div>
            <div className="felt-letter">Y</div>
            <div className="hero-stamp">EST.<br />NEW HAVEN</div>
          </div>
        </div>
      </section>

      <div className="ticker" aria-hidden="true">
        <div className="ticker-track">
          {[...TICKER, ...TICKER].map((t, i) => <span key={i}>{t}<b>✦</b></span>)}
        </div>
      </div>

      <section className="page">
        <div className="section-head">
          <p className="eyebrow">Find your section</p>
          <h2 className="section-title">Shop by collection</h2>
        </div>
        <div className="pennant-row">
          {collections.map((c, i) => (
            <Link to={c.to} key={c.title} className={`pennant-card tone-${c.tone}`} style={{ '--i': i } as React.CSSProperties}>
              <h3>{c.title}</h3>
              <p>{c.text}</p>
              <span className="pennant-cta">Shop →</span>
            </Link>
          ))}
        </div>

        <div className="section-head">
          <p className="eyebrow">Most loved on campus</p>
          <h2 className="section-title">Campus favorites</h2>
        </div>
        <div className="product-grid">
          {featured.map((p, i) => <ProductCard key={p.product_id} product={p} index={i} />)}
        </div>

        <div className="callout chat-callout">
          <div className="callout-bubble">💬</div>
          <div>
            <h2>Not sure what fits?</h2>
            <p>Our assistant checks live stock in every size. Ask "Is the navy hoodie in stock in M?" and get a real answer.</p>
          </div>
          <button type="button" className="btn" onClick={() => openChat('Is the Basic Hoodie Big Yale in stock in M?')}>Try it</button>
        </div>
      </section>
    </>
  )
}
