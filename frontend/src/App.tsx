import { useEffect } from 'react'
import { Route, Routes, useLocation } from 'react-router-dom'
import NavBar from './components/NavBar'
import Footer from './components/Footer'
import ChatWidget from './components/ChatWidget'
import ChatResultsPanel from './components/ChatResultsPanel'
import Home from './pages/Home'
import Products from './pages/Products'
import ProductDetail from './pages/ProductDetail'
import About from './pages/About'
import Login from './pages/Login'
import CreateAccount from './pages/CreateAccount'

export default function App() {
  const { pathname } = useLocation()
  // On a single-item page the chat results sit below the item; everywhere else they lead the page.
  const onDetailPage = /^\/products\/[^/]+$/.test(pathname)
  // The Home hero stays first; chat results go below it.
  const resultsBelow = onDetailPage || pathname === '/'
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])

  return (
    <>
      <NavBar />
      <main>
        {!resultsBelow && <ChatResultsPanel />}
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/:productId" element={<ProductDetail />} />
          <Route path="/about" element={<About />} />
          <Route path="/login" element={<Login />} />
          <Route path="/create-account" element={<CreateAccount />} />
          <Route path="*" element={<section className="page"><h1>Page not found</h1></section>} />
        </Routes>
        {resultsBelow && <ChatResultsPanel compact={onDetailPage} />}
      </main>
      <Footer />
      <ChatWidget />
    </>
  )
}
