import { useEffect, useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../AuthContext'
import Crest from './Crest'

const links = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export default function NavBar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <header className={`site-header${scrolled ? ' scrolled' : ''}`}>
      <div className="announcement">
        <span>Officially licensed Yale apparel</span>
        <span className="dot">✦</span>
        <span>57 Broadway, New Haven</span>
        <span className="dot">✦</span>
        <span>Ask our chat about any size, any time</span>
      </div>
      <nav className="navbar">
        <Link to="/" className="brand">
          <Crest size={34} />
          <span className="brand-text">
            Campus Customs
            <small>Yale Bulldog Blue</small>
          </span>
        </Link>
        <ul className="nav-links">
          {links.map((l) => (
            <li key={l.to}>
              <NavLink to={l.to} end={l.end}>{l.label}</NavLink>
            </li>
          ))}
        </ul>
        <div className="nav-account">
          {user ? (
            <>
              <span className="greeting"><span className="avatar-initial">{user.first_name[0]}</span>Hi, {user.first_name}</span>
              <button type="button" className="btn btn-small" onClick={async () => { await logout(); navigate('/') }}>Log out</button>
            </>
          ) : (
            <>
              <NavLink to="/login">Login</NavLink>
              <NavLink to="/create-account" className="btn btn-small">Create Account</NavLink>
            </>
          )}
        </div>
      </nav>
    </header>
  )
}
