import { useEffect, useState } from 'react'
import { Landmark, LoaderCircle, RefreshCw, WalletCards } from 'lucide-react'

type JsonRecord = Record<string, unknown>
type LedgerResponse = { group: JsonRecord; rows: JsonRecord[]; summary: JsonRecord; member_summary: JsonRecord; calculation_note: string }

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const TOKEN_KEY = 'savecircle_access_token'
const money = (value: unknown) => `₹${Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`

async function api(path: string) {
  const token = localStorage.getItem(TOKEN_KEY)
  const response = await fetch(`${API_URL}${path}`, { headers: { Authorization: `Bearer ${token}` } })
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || 'Unable to load committee ledger.')
  return data
}

export default function CommitteeLedger() {
  const [groups, setGroups] = useState<JsonRecord[]>([])
  const [groupId, setGroupId] = useState('')
  const [ledger, setLedger] = useState<LedgerResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    api('/api/groups').then((rows: JsonRecord[]) => {
      const visible = rows.filter(g => Boolean(g.is_member) || Boolean(g.is_creator) || Boolean(g.can_manage))
      setGroups(visible)
      if (visible.length) setGroupId(String(visible[0].id))
    }).catch(e => setError(e instanceof Error ? e.message : 'Unable to load groups.')).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!groupId) return
    setLoading(true); setError('')
    api(`/api/groups/${groupId}/committee-ledger`).then(setLedger).catch(e => setError(e instanceof Error ? e.message : 'Unable to load ledger.')).finally(() => setLoading(false))
  }, [groupId, refreshKey])

  if (loading && !ledger) return <div className="workspace-loading"><LoaderCircle className="spin" size={30}/>Loading committee ledger…</div>

  return <>
    <div className="section-actions ledger-select-row">
      <label>View savings group<select value={groupId} onChange={e => setGroupId(e.target.value)}>{groups.map(g => <option key={String(g.id)} value={String(g.id)}>{String(g.name)}</option>)}</select></label>
      <button onClick={() => setRefreshKey(k => k + 1)}><RefreshCw size={16}/> Refresh</button>
    </div>
    {error && <div className="workspace-notice error">{error}</div>}
    {!groups.length && !loading && <div className="empty-state"><Landmark size={28}/><b>No joined savings groups</b><p>Join or create a group to view its committee ledger.</p></div>}

    {ledger && <>
      <section className="workspace-panel ledger-progress"><div className="panel-heading"><div><span>Committee duration</span><h2>{String(ledger.group.name)}</h2></div><b>Cycle {String(ledger.group.current_cycle)} / {String(ledger.group.total_cycles)}</b></div><p>The Group Creator selected this cycle limit when creating the committee. The ledger expands automatically to that limit.</p></section>

      <section className="live-metrics ledger-metrics">
        <article><span><WalletCards size={21}/></span><div><small>Expected by final cycle</small><strong>{money(ledger.summary.expected_contributions)}</strong></div></article>
        <article><span><WalletCards size={21}/></span><div><small>Current bank balance</small><strong>{money(ledger.summary.bank_balance)}</strong></div></article>
        <article><span><WalletCards size={21}/></span><div><small>Outstanding advances</small><strong>{money(ledger.summary.outstanding_advances)}</strong></div></article>
        <article><span><WalletCards size={21}/></span><div><small>Committee interest received</small><strong>{money(ledger.summary.committee_interest_received)}</strong></div></article>
        <article><span><WalletCards size={21}/></span><div><small>Bank interest received</small><strong>{money(ledger.summary.bank_interest_received)}</strong></div></article>
        <article><span><WalletCards size={21}/></span><div><small>Missing contributions</small><strong>{money(ledger.summary.missing_contributions_due)}</strong></div></article>
      </section>

      <section className="workspace-panel member-settlement-card">
        <div className="panel-heading"><div><span>My calculated settlement</span><h2>{String(ledger.member_summary.member_name)}</h2></div><em className={`state ${ledger.summary.ready_to_distribute ? 'verified' : 'pending'}`}>{ledger.summary.ready_to_distribute ? 'READY TO DISTRIBUTE' : 'SETTLEMENT PENDING'}</em></div>
        <div className="settlement-grid">
          <div><small>My verified contributions</small><strong>{money(ledger.member_summary.verified_contributions)}</strong></div>
          <div><small>Final savings entitlement</small><strong>{money(ledger.member_summary.final_contribution_entitlement)}</strong></div>
          <div><small>My realized profit share</small><strong>{money(ledger.member_summary.realized_profit_share)}</strong></div>
          <div><small>My outstanding due</small><strong>{money(ledger.member_summary.outstanding_due)}</strong></div>
          <div><small>Estimated final amount</small><strong>{money(ledger.member_summary.estimated_final_receipt)}</strong></div>
        </div>
        <p className="ledger-note">Realized committee profit: <b>{money(ledger.summary.realized_total_profit)}</b> · Current committee assets: <b>{money(ledger.summary.total_committee_assets_now)}</b></p>
        <p className="ledger-note">{String(ledger.summary.settlement_note)}</p>
      </section>

      <section className="workspace-panel">
        <div className="panel-heading"><div><span>Live committee ledger</span><h2>Cycle-by-cycle financial position</h2></div></div>
        <div className="table-wrap committee-table"><table><thead><tr><th>Cycle</th><th>Expected</th><th>Actual Submitted</th><th>Missing</th><th>Missing By</th><th>Old Missing Collected</th><th>Total Cash Received</th><th>Advance</th><th>Advance By</th><th>Repayment</th><th>Committee Interest</th><th>Bank Interest</th><th>Status</th><th>Outstanding Advance</th><th>Interest Till Date</th><th>Bank Balance</th></tr></thead>
        <tbody>{ledger.rows.map((r, index) => <tr key={index}><td><b>{String(r.cycle)}</b></td><td>{money(r.expected_amount)}</td><td>{money(r.actual_submission)}</td><td>{money(r.missing_contribution)}</td><td>{String(r.missing_by)}</td><td>{money(r.previous_missing_collected)}</td><td>{money(r.total_cash_received)}</td><td>{money(r.advance_taken)}</td><td>{String(r.advance_taken_by)}</td><td>{money(r.repayment_received)}</td><td>{money(r.interest_received)}</td><td>{money(r.bank_interest_received)}</td><td><em className={`state ${String(r.status).toLowerCase().replaceAll(' ', '_')}`}>{String(r.status)}</em></td><td>{money(r.outstanding_advance)}</td><td>{money(r.committee_interest_till_date)}</td><td><b>{money(r.bank_balance)}</b></td></tr>)}</tbody></table></div>
      </section>
      <p className="ledger-demo-note">{ledger.calculation_note}</p>
    </>}
  </>
}
