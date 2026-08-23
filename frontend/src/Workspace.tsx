import { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle, CheckCircle2, FileText, Landmark, LayoutDashboard, LoaderCircle,
  LogOut, ReceiptText, RefreshCw, ShieldCheck, Users, WalletCards,
} from 'lucide-react'
import './Workspace.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const TOKEN_KEY = 'savecircle_access_token'

type User = { id: number; full_name: string; email: string; role: string }
type Tab = 'overview' | 'groups' | 'members' | 'contributions' | 'receipts' | 'alerts' | 'audit'
type JsonRecord = Record<string, unknown>
type DashboardData = {
  metrics?: Record<string, number>
  recent_transactions?: JsonRecord[]
  recent_alerts?: JsonRecord[]
  recent_audits?: JsonRecord[]
  my_groups?: JsonRecord[]
  recent_contributions?: JsonRecord[]
}

const labels: Record<Tab, string> = {
  overview: 'Overview', groups: 'Savings groups', members: 'Members',
  contributions: 'Contributions', receipts: 'Digital receipts',
  alerts: 'AI risk alerts', audit: 'Audit trail',
}

const icons: Record<Tab, typeof LayoutDashboard> = {
  overview: LayoutDashboard, groups: Landmark, members: Users,
  contributions: WalletCards, receipts: ReceiptText,
  alerts: AlertTriangle, audit: FileText,
}

function value(record: JsonRecord, key: string, fallback = '—') {
  const output = record[key]
  return output === null || output === undefined || output === '' ? fallback : String(output)
}

function money(input: unknown) {
  return `₹${Number(input || 0).toLocaleString('en-IN')}`
}

async function api(path: string, options: RequestInit = {}) {
  const token = localStorage.getItem(TOKEN_KEY)
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...options.headers },
  })
  const data = await response.json()
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Request failed')
  return data
}

export default function Workspace({ user, apiOnline, onLogout }: { user: User; apiOnline: boolean | null; onLogout: () => void }) {
  const isAdmin = user.role.toUpperCase() === 'ADMIN'
  const tabs = useMemo<Tab[]>(() => isAdmin
    ? ['overview', 'groups', 'members', 'contributions', 'receipts', 'alerts', 'audit']
    : ['overview', 'groups', 'contributions', 'receipts'], [isAdmin])
  const [tab, setTab] = useState<Tab>('overview')
  const [data, setData] = useState<JsonRecord[] | DashboardData>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    const paths: Record<Tab, string> = {
      overview: '/api/analytics/dashboard',
      groups: '/api/groups',
      members: '/api/members',
      contributions: '/api/contributions',
      receipts: '/api/receipts',
      alerts: '/api/ai/alerts',
      audit: '/api/audit-logs?limit=100',
    }
    api(paths[tab])
      .then((response) => { if (active) setData(response) })
      .catch((requestError) => { if (active) setError(requestError instanceof Error ? requestError.message : 'Unable to load data') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [tab, reloadKey])

  const refresh = () => setReloadKey((key) => key + 1)

  const verifyContribution = async (id: unknown, status: 'VERIFIED' | 'REJECTED') => {
    try {
      await api(`/api/contributions/${id}/verify`, { method: 'PUT', body: JSON.stringify({ status, notes: 'Reviewed from SaveCircle dashboard' }) })
      setNotice(`Contribution ${status.toLowerCase()} successfully.`)
      refresh()
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Action failed') }
  }

  const reviewAlert = async (id: unknown, status: 'VALIDATED' | 'INVESTIGATING') => {
    try {
      await api(`/api/ai/alerts/${id}/review`, { method: 'PUT', body: JSON.stringify({ status, admin_notes: 'Reviewed from SaveCircle dashboard' }) })
      setNotice('Risk alert review saved.')
      refresh()
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Action failed') }
  }

  return (
    <div className="workspace">
      <header className="workspace-header">
        <div className="brand"><span className="brand-mark">S</span><span>SaveCircle</span></div>
        <div className="workspace-user">
          <span className={`role-chip ${isAdmin ? 'admin' : ''}`}>{user.role}</span>
          <div><b>{user.full_name}</b><small>{user.email}</small></div>
          <button onClick={onLogout}><LogOut size={17} /> Logout</button>
        </div>
      </header>

      <div className="workspace-grid">
        <aside className="workspace-sidebar">
          <span>Workspace</span>
          {tabs.map((item) => {
            const Icon = icons[item]
            return <button key={item} className={tab === item ? 'active' : ''} onClick={() => { setNotice(''); setTab(item) }}><Icon size={18} />{labels[item]}</button>
          })}
          <div className="sidebar-secure"><ShieldCheck size={19} /><p><b>Protected session</b><small>JWT verified by FastAPI</small></p></div>
        </aside>

        <main className="workspace-main">
          <div className="workspace-title">
            <div><span>{isAdmin ? 'Administrator workspace' : 'Member workspace'}</span><h1>{labels[tab]}</h1><p>{tab === 'overview' ? `Welcome back, ${user.full_name.split(' ')[0]}. Here is your live savings summary.` : 'Live records loaded securely from the SaveCircle API.'}</p></div>
            <div className="title-actions"><span className={`api-chip ${apiOnline ? 'online' : ''}`}><i />{apiOnline ? 'API online' : 'API offline'}</span><button onClick={refresh} aria-label="Refresh"><RefreshCw size={17} /></button></div>
          </div>

          {notice && <div className="workspace-notice success"><CheckCircle2 size={18} />{notice}</div>}
          {error && <div className="workspace-notice error"><AlertTriangle size={18} />{error}</div>}
          {loading ? <div className="workspace-loading"><LoaderCircle className="spin" size={30} /><span>Loading secure records…</span></div> : (
            <>
              {tab === 'overview' && <Overview data={data as DashboardData} isAdmin={isAdmin} />}
              {tab === 'groups' && <Groups rows={data as JsonRecord[]} isAdmin={isAdmin} />}
              {tab === 'members' && <Members rows={data as JsonRecord[]} />}
              {tab === 'contributions' && <Contributions rows={data as JsonRecord[]} isAdmin={isAdmin} onVerify={verifyContribution} />}
              {tab === 'receipts' && <Receipts rows={data as JsonRecord[]} />}
              {tab === 'alerts' && <Alerts rows={data as JsonRecord[]} onReview={reviewAlert} />}
              {tab === 'audit' && <Audit rows={data as JsonRecord[]} />}
            </>
          )}
        </main>
      </div>
    </div>
  )
}

function Empty({ text }: { text: string }) {
  return <div className="empty-state"><FileText size={28} /><b>No records yet</b><p>{text}</p></div>
}

function Overview({ data, isAdmin }: { data: DashboardData; isAdmin: boolean }) {
  const metrics = data.metrics || {}
  const cards = isAdmin
    ? [['Members', metrics.total_members, Users], ['Active groups', metrics.active_groups, Landmark], ['Verified savings', metrics.total_contributions, WalletCards], ['Pending reviews', metrics.pending_verifications, AlertTriangle]]
    : [['Total savings', metrics.total_savings, WalletCards], ['Monthly contribution', metrics.current_contribution, ReceiptText], ['Active groups', metrics.active_groups, Landmark], ['Receipts', metrics.verified_receipts_count, FileText]]
  const recent = (isAdmin ? data.recent_transactions : data.recent_contributions) || []
  return <>
    <section className="live-metrics">
      {cards.map(([label, metric, Icon]) => <article key={String(label)}><span><Icon size={21} /></span><div><small>{String(label)}</small><strong>{String(label).toLowerCase().includes('saving') || String(label).toLowerCase().includes('contribution') ? money(metric) : String(metric ?? 0)}</strong></div></article>)}
    </section>
    <section className="workspace-panel">
      <div className="panel-heading"><div><span>Latest activity</span><h2>Recent transactions</h2></div><CheckCircle2 size={23} /></div>
      {recent.length ? <div className="record-list">{recent.slice(0, 6).map((row) => <div key={value(row, 'id')}><span className="record-icon"><ReceiptText size={18} /></span><p><b>{value(row, isAdmin ? 'member_name' : 'group_name')}</b><small>{value(row, 'reference_id', value(row, 'transaction_ref'))}</small></p><strong>{money(row.amount)}</strong><em className={`state ${value(row, 'status').toLowerCase()}`}>{value(row, 'status')}</em></div>)}</div> : <Empty text="New activity will appear here." />}
    </section>
  </>
}

function Groups({ rows, isAdmin }: { rows: JsonRecord[]; isAdmin: boolean }) {
  if (!rows.length) return <Empty text="No active savings groups were found." />
  return <section className="card-grid">{rows.map((row) => <article key={value(row, 'id')}><div className="card-icon"><Landmark size={22} /></div><span>{value(row, 'contribution_frequency', value(row, 'frequency'))}</span><h3>{value(row, 'name')}</h3><p>{value(row, 'description', 'Community savings group')}</p><dl><div><dt>Contribution</dt><dd>{money(row.contribution_amount)}</dd></div><div><dt>Members</dt><dd>{value(row, 'member_count', isAdmin ? '0' : 'Joined')}</dd></div><div><dt>Cycle</dt><dd>{value(row, 'current_cycle')} / {value(row, 'total_cycles')}</dd></div></dl></article>)}</section>
}

function Members({ rows }: { rows: JsonRecord[] }) {
  if (!rows.length) return <Empty text="No members were found." />
  return <Table headers={['Member', 'Email', 'Phone', 'Role', 'Status']} rows={rows.map((row) => [value(row, 'full_name'), value(row, 'email'), value(row, 'phone'), value(row, 'role'), row.is_active ? 'Active' : 'Inactive'])} />
}

function Contributions({ rows, isAdmin, onVerify }: { rows: JsonRecord[]; isAdmin: boolean; onVerify: (id: unknown, status: 'VERIFIED' | 'REJECTED') => void }) {
  if (!rows.length) return <Empty text="No contribution records were found." />
  return <div className="data-cards">{rows.map((row) => <article key={value(row, 'id')}><div><span>{value(row, 'group_name')}</span><h3>{money(row.amount)}</h3><p>{value(row, 'member_name')} · {value(row, 'payment_method')}</p><small>{value(row, 'transaction_ref')}</small></div><div className="row-actions"><em className={`state ${value(row, 'status').toLowerCase()}`}>{value(row, 'status')}</em>{isAdmin && value(row, 'status') === 'PENDING' && <><button className="approve" onClick={() => onVerify(row.id, 'VERIFIED')}>Verify</button><button className="reject" onClick={() => onVerify(row.id, 'REJECTED')}>Reject</button></>}</div></article>)}</div>
}

function Receipts({ rows }: { rows: JsonRecord[] }) {
  if (!rows.length) return <Empty text="Receipts are generated after contribution verification." />
  return <Table headers={['Receipt', 'Amount', 'Transaction', 'Issued at']} rows={rows.map((row) => [value(row, 'receipt_number'), money(row.amount), value(row, 'transaction_ref'), value(row, 'created_at').slice(0, 10)])} />
}

function Alerts({ rows, onReview }: { rows: JsonRecord[]; onReview: (id: unknown, status: 'VALIDATED' | 'INVESTIGATING') => void }) {
  if (!rows.length) return <Empty text="No AI risk alerts require review." />
  return <div className="data-cards">{rows.map((row) => <article className="risk-card" key={value(row, 'id')}><div><span>{value(row, 'risk_level')} risk · {value(row, 'group_name')}</span><h3>{value(row, 'member_name')} · {money(row.amount)}</h3><p>{value(row, 'recommended_action')}</p><small>AI score: {value(row, 'anomaly_score')}</small></div><div className="row-actions"><em className="state pending_review">{value(row, 'status')}</em>{value(row, 'status') === 'PENDING_REVIEW' && <><button className="approve" onClick={() => onReview(row.id, 'VALIDATED')}>Mark valid</button><button onClick={() => onReview(row.id, 'INVESTIGATING')}>Investigate</button></>}</div></article>)}</div>
}

function Audit({ rows }: { rows: JsonRecord[] }) {
  if (!rows.length) return <Empty text="Audit events will appear here." />
  return <Table headers={['Actor', 'Action', 'Description', 'Date']} rows={rows.map((row) => [value(row, 'actor_name'), value(row, 'action'), value(row, 'description'), value(row, 'created_at').slice(0, 10)])} />
}

function Table({ headers, rows }: { headers: string[]; rows: string[][] }) {
  return <div className="table-wrap"><table><thead><tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={index}>{row.map((cell, cellIndex) => <td key={cellIndex}>{cell}</td>)}</tr>)}</tbody></table></div>
}
