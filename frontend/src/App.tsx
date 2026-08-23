import { useEffect, useState } from 'react'
import { AlertTriangle, ArrowRight, CheckCircle2, FileCheck2, Landmark, ReceiptText, ShieldCheck, Users } from 'lucide-react'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

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

function App() {
  const [apiOnline, setApiOnline] = useState<boolean | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    fetch(`${API_URL}/health`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error('API unavailable')
        return response.json()
      })
      .then(() => setApiOnline(true))
      .catch(() => setApiOnline(false))
    return () => controller.abort()
  }, [])

  return (
    <main>
      <nav>
        <a className="brand" href="#top" aria-label="SaveCircle home">
          <span className="brand-mark">S</span>
          <span>SaveCircle</span>
        </a>
        <div className="nav-links">
          <a href="#features">Features</a>
          <a href={`${API_URL}/docs`} target="_blank" rel="noreferrer">API Docs</a>
          <a className="nav-button" href="#demo">Explore demo</a>
        </div>
      </nav>

      <section className="hero" id="top">
        <div className="hero-copy">
          <div className="eyebrow"><ShieldCheck size={16} /> Built for transparent community savings</div>
          <h1>Trust every contribution. Track every rupee.</h1>
          <p className="hero-text">
            SaveCircle replaces paper records with secure member management, verified contributions,
            digital receipts and explainable risk alerts.
          </p>
          <div className="hero-actions">
            <a className="primary" href="#demo">View dashboard <ArrowRight size={18} /></a>
            <a className="secondary" href={`${API_URL}/docs`} target="_blank" rel="noreferrer">Open API docs</a>
          </div>
          <div className="trust-row">
            <span><CheckCircle2 size={17} /> Human-reviewed alerts</span>
            <span><CheckCircle2 size={17} /> Synthetic demo data</span>
          </div>
        </div>

        <div className="dashboard-card" id="demo">
          <div className="card-top">
            <div>
              <span className="muted">Admin overview</span>
              <h2>Dehradun Community Savings</h2>
            </div>
            <span className={`status ${apiOnline ? 'online' : ''}`}>
              <i /> {apiOnline === null ? 'Checking API' : apiOnline ? 'API online' : 'Demo mode'}
            </span>
          </div>
          <div className="balance">
            <span>Total verified savings</span>
            <strong>₹2,48,000</strong>
            <small>Cycle 4 of 12 · Updated from shared records</small>
          </div>
          <div className="progress"><span /></div>
          <div className="activity">
            <div><span className="activity-icon good"><ReceiptText size={19} /></span><p><b>Contribution verified</b><small>Priya Patel · ₹2,000</small></p><time>Today</time></div>
            <div><span className="activity-icon warn"><AlertTriangle size={19} /></span><p><b>Review requested</b><small>Unusual amount · explanation ready</small></p><time>2h</time></div>
          </div>
        </div>
      </section>

      <section className="metrics" aria-label="Demo statistics">
        {metrics.map(({ label, value, icon: Icon }) => (
          <article key={label}><Icon size={21} /><div><strong>{value}</strong><span>{label}</span></div></article>
        ))}
      </section>

      <section className="features" id="features">
        <div className="section-heading">
          <span>One shared source of truth</span>
          <h2>Designed to reduce disputes, not just digitize paperwork.</h2>
        </div>
        <div className="feature-grid">
          {features.map(({ icon: Icon, title, text }) => (
            <article key={title}><span className="feature-icon"><Icon size={23} /></span><h3>{title}</h3><p>{text}</p></article>
          ))}
        </div>
      </section>

      <footer>
        <div className="brand"><span className="brand-mark">S</span><span>SaveCircle</span></div>
        <p>Omnikon 2026 · Omni_FinTech_9 · Demonstration only—no real money is processed.</p>
      </footer>
    </main>
  )
}

export default App
