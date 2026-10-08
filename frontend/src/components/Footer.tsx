import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="site-footer">
      <div>
        <strong>Campus Customs</strong>
        <p>57 Broadway, New Haven, CT 06511</p>
      </div>
      <div className="footer-links">
        <Link to="/products">Shop</Link>
        <Link to="/about">About Us</Link>
        <Link to="/create-account">Create Account</Link>
      </div>
      <p className="fine-print">Class project demo store · Built with React, FastAPI, and Pydantic AI</p>
    </footer>
  )
}
