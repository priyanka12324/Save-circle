import { FormEvent, useEffect, useState } from 'react'
import {
  AlertCircle, AlertTriangle, ArrowLeft, ArrowRight, CheckCircle2, Eye, EyeOff,
  FileCheck2, Landmark, LoaderCircle, ReceiptText, ShieldCheck, UserPlus, Users,
} from 'lucide-react'
import './App.css'
import Workspace from './Workspace'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const TOKEN_KEY = 'savecircle_access_token'
const USER_KEY = 'savecircle_user'

type User = {
  id: number
  full_name: string
  email: string
  phone?: string | null
  role: 'ADMIN' | 'MEMBER' | string
  is_active: boolean
}

type AuthResponse = {
  access_token: string
  token_type: string
  user: User
}

type AuthMode = 'login' | 'register'

const metrics = [
  { label: 'Active members', value: '22', icon: Users },
  { label: 'Savings groups', value: '3', icon: Landmark },
  { label: 'Verified records', value: '40+', icon: FileCheck2 },
  { label: 'Risk alerts', value: '3', icon: AlertTriangle },
]

const features = [
  { icon: Users, title: 'Community management', text: 'Create groups, manage members and track every savings cycle from one place.' },
  { icon: ReceiptText, title: 'Transparent records', text: 'Verify contributions and issue digital receipts backed by a traceable ledger.' },
  { icon: ShieldCheck, title: 'Responsible risk review', text: 'Explainable alerts help admins review unusual activity without automatic accusations.' },
]

function readSavedUser(): User | null {
  try {
    const saved = localStorage.getItem(USER_KEY)
    return saved ? JSON.parse(saved) : null
  } catch {
    return null
  }
}

function App() {
  const [apiOnline, setApiOnline] = useState<boolean | null>(null)
  const [authMode, setAuthMode] = useState<AuthMode | null>(null)
  const [user, setUser] = useState<User | null>(readSavedUser)
  const [checkingSession, setCheckingSession] = useState(Boolean(localStorage.getItem(TOKEN_KEY)))

  useEffect(() => {
    const controller = new AbortController()
    fetch(`${API_URL}/health`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error('API unavailable')
        setApiOnline(true)
      })
      .catch(() => setApiOnline(false))
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      setCheckingSession(false)
      return
    }
    fetch(`${API_URL}/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(async (response) => {
        if (!response.ok) throw new Error('Session expired')
        return response.json() as Promise<User>
      })
      .then((currentUser) => {
        localStorage.setItem(USER_KEY, JSON.stringify(currentUser))
        setUser(currentUser)
      })
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(USER_KEY)
        setUser(null)
      })
      .finally(() => setCheckingSession(false))
  }, [])

  const handleAuthenticated = (data: AuthResponse) => {
    localStorage.setItem(TOKEN_KEY, data.access_token)
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
    setUser(data.user)
    setAuthMode(null)
  }

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setUser(null)
  }

  if (checkingSession) {
    return <div className="screen-loader"><LoaderCircle className="spin" size={34} /><p>Restoring your secure session…</p></div>
  }

  if (user) {
    return <Workspace user={user} apiOnline={apiOnline} onLogout={logout} />
  }

  return (
    <main>
      <nav>
        <a className="brand" href="#top" aria-label="SaveCircle home">
          <span className="brand-mark">S</span><span>SaveCircle</span>
        </a>
        <div className="nav-links">
          <a href="#features">Features</a>
          <a href={`${API_URL}/docs`} target="_blank" rel="noreferrer">API Docs</a>
          <button className="text-button" onClick={() => setAuthMode('login')}>Log in</button>
          <button className="nav-button" onClick={() => setAuthMode('register')}>Create account</button>
        </div>
      </nav>

      <section className="hero" id="top">
        <div className="hero-copy">
          <div className="eyebrow"><ShieldCheck size={16} /> Built for transparent community savings</div>
          <h1>Trust every contribution. Track every rupee.</h1>
          <p className="hero-text">SaveCircle replaces paper records with secure member management, verified contributions, digital receipts and explainable risk alerts.</p>
          <div className="hero-actions">
            <button className="primary" onClick={() => setAuthMode('login')}>Open dashboard <ArrowRight size={18} /></button>
            <button className="secondary" onClick={() => setAuthMode('register')}><UserPlus size={18} /> Join SaveCircle</button>
          </div>
          <div className="trust-row">
            <span><CheckCircle2 size={17} /> Human-reviewed alerts</span>
            <span><CheckCircle2 size={17} /> Synthetic demo data</span>
          </div>
        </div>

        <div className="dashboard-card" id="demo">
          <div className="card-top">
            <div><span className="muted">Admin overview</span><h2>Dehradun Community Savings</h2></div>
            <span className={`status ${apiOnline ? 'online' : ''}`}><i /> {apiOnline === null ? 'Checking API' : apiOnline ? 'API online' : 'Demo mode'}</span>
          </div>
          <div className="balance"><span>Total verified savings</span><strong>₹2,48,000</strong><small>Cycle 4 of 12 · Updated from shared records</small></div>
          <div className="progress"><span /></div>
          <div className="activity">
            <div><span className="activity-icon good"><ReceiptText size={19} /></span><p><b>Contribution verified</b><small>Priya Patel · ₹2,000</small></p><time>Today</time></div>
            <div><span className="activity-icon warn"><AlertTriangle size={19} /></span><p><b>Review requested</b><small>Unusual amount · explanation ready</small></p><time>2h</time></div>
          </div>
        </div>
      </section>

      <section className="metrics" aria-label="Demo statistics">
        {metrics.map(({ label, value, icon: Icon }) => <article key={label}><Icon size={21} /><div><strong>{value}</strong><span>{label}</span></div></article>)}
      </section>

      <section className="features" id="features">
        <div className="section-heading"><span>One shared source of truth</span><h2>Designed to reduce disputes, not just digitize paperwork.</h2></div>
        <div className="feature-grid">
          {features.map(({ icon: Icon, title, text }) => <article key={title}><span className="feature-icon"><Icon size={23} /></span><h3>{title}</h3><p>{text}</p></article>)}
        </div>
      </section>

      <footer>
        <div className="brand"><span className="brand-mark">S</span><span>SaveCircle</span></div>
        <p>Omnikon 2026 · Omni_FinTech_9 · Demonstration only—no real money is processed.</p>
      </footer>

      {authMode && <AuthDialog mode={authMode} apiOnline={apiOnline} onModeChange={setAuthMode} onClose={() => setAuthMode(null)} onAuthenticated={handleAuthenticated} />}
    </main>
  )
}

function AuthDialog({ mode, apiOnline, onModeChange, onClose, onAuthenticated }: {
  mode: AuthMode
  apiOnline: boolean | null
  onModeChange: (mode: AuthMode) => void
  onClose: () => void
  onAuthenticated: (data: AuthResponse) => void
}) {
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ full_name: '', email: mode === 'login' ? 'admin@savecircle.demo' : '', phone: '', password: mode === 'login' ? 'Admin@123' : '', confirm_password: '' })

  const switchMode = (next: AuthMode) => {
    setError('')
    onModeChange(next)
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    if (apiOnline === false) {
      setError('Backend is offline. Start FastAPI on port 8000 and try again.')
      return
    }
    if (mode === 'register' && form.password !== form.confirm_password) {
      setError('Passwords do not match.')
      return
    }
    setSubmitting(true)
    const endpoint = mode === 'login' ? '/api/auth/login' : '/api/auth/register'
    const payload = mode === 'login'
      ? { email: form.email.trim(), password: form.password }
      : { full_name: form.full_name.trim(), email: form.email.trim(), phone: form.phone.trim() || null, password: form.password, confirm_password: form.confirm_password, role: 'MEMBER' }

    try {
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Unable to authenticate.')
      onAuthenticated(data as AuthResponse)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Something went wrong.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-overlay" role="dialog" aria-modal="true" aria-label={mode === 'login' ? 'Log in' : 'Create account'}>
      <button className="overlay-close" onClick={onClose} aria-label="Close authentication"><ArrowLeft size={19} /> Back</button>
      <div className="auth-shell">
        <div className="auth-story">
          <span className="brand-mark large">S</span>
          <p className="auth-kicker">Secure community finance</p>
          <h2>{mode === 'login' ? 'Welcome back to your savings circle.' : 'Build trust with every contribution.'}</h2>
          <p>Role-based access, digital receipts and a complete audit trail keep the whole community informed.</p>
          <div className="demo-note"><ShieldCheck size={20} /><span><b>Demo administrator</b><small>admin@savecircle.demo · Admin@123</small></span></div>
        </div>
        <form className="auth-form" onSubmit={submit}>
          <div>
            <span className="auth-kicker">{mode === 'login' ? 'Secure login' : 'Member registration'}</span>
            <h2>{mode === 'login' ? 'Log in to SaveCircle' : 'Create your account'}</h2>
            <p>{mode === 'login' ? 'Use your member or administrator credentials.' : 'New public accounts are safely created as members.'}</p>
          </div>

          {mode === 'register' && <label>Full name<input required minLength={2} value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} placeholder="Priyanka Rawat" /></label>}
          <label>Email address<input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="you@example.com" /></label>
          {mode === 'register' && <label>Phone <span>(optional)</span><input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="+91 98765 43210" /></label>}
          <label>Password
            <span className="password-field"><input required minLength={6} type={showPassword ? 'text' : 'password'} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /><button type="button" onClick={() => setShowPassword(!showPassword)} aria-label="Toggle password">{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></span>
          </label>
          {mode === 'register' && <label>Confirm password<input required minLength={6} type="password" value={form.confirm_password} onChange={(e) => setForm({ ...form, confirm_password: e.target.value })} /></label>}

          {error && <div className="auth-error"><AlertCircle size={18} />{error}</div>}
          <button className="submit-button" disabled={submitting}>{submitting ? <><LoaderCircle className="spin" size={18} /> Please wait…</> : mode === 'login' ? 'Log in securely' : 'Create member account'}</button>
          <p className="auth-switch">{mode === 'login' ? "Don't have an account?" : 'Already registered?'} <button type="button" onClick={() => switchMode(mode === 'login' ? 'register' : 'login')}>{mode === 'login' ? 'Create one' : 'Log in'}</button></p>
        </form>
      </div>
    </div>
  )
}

export default App
