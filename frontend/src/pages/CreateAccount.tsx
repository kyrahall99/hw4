import { useState, type ChangeEvent, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../AuthContext'

export default function CreateAccount() {
  const { signup } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ first_name: '', last_name: '', email: '', password: '', confirm_password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const update = (key: keyof typeof form) => (e: ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }))

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (form.password !== form.confirm_password) {
      setError('Passwords do not match.')
      return
    }
    setBusy(true)
    try {
      await signup(form)
      navigate('/products')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="page auth-page">
      <form className="auth-form" onSubmit={onSubmit}>
        <h1>Create an account</h1>
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="name-row">
          <label>First name<input value={form.first_name} onChange={update('first_name')} required maxLength={50} autoComplete="given-name" /></label>
          <label>Last name<input value={form.last_name} onChange={update('last_name')} required maxLength={50} autoComplete="family-name" /></label>
        </div>
        <label>Email<input type="email" value={form.email} onChange={update('email')} required autoComplete="email" /></label>
        <label>
          Password <span className="hint">(at least 8 characters)</span>
          <input type="password" value={form.password} onChange={update('password')} required minLength={8} maxLength={128} autoComplete="new-password" />
        </label>
        <label>Confirm password<input type="password" value={form.confirm_password} onChange={update('confirm_password')} required minLength={8} maxLength={128} autoComplete="new-password" /></label>
        <button type="submit" className="btn" disabled={busy}>{busy ? 'Creating account…' : 'Create account'}</button>
        <p>Already have an account? <Link to="/login">Log in</Link></p>
      </form>
    </section>
  )
}
