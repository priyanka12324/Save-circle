import { useEffect, useState } from 'react'
import { Landmark, LoaderCircle, RefreshCw, WalletCards } from 'lucide-react'

type JsonRecord = Record<string, unknown>
type LedgerResponse = { group: JsonRecord; rows: JsonRecord[]; summary: JsonRecord; member_summary: JsonRecord; calculation_note: string }

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const TOKEN_KEY = 'savecircle_access_token'
const money = (value: unknown) => `₹${Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`

async function api(path: string, options: RequestInit = {}) {
  const token = localStorage.getItem(TOKEN_KEY)
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...options.headers },
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || 'Unable to load committee data.')
  return data
}

export default function CommitteeLedger() {
  const [groups, setGroups] = useState<JsonRecord[]>([])
  const [groupId, setGroupId] = useState('')
  const [ledger, setLedger] = useState<LedgerResponse | null>(null)
  const [advances, setAdvances] = useState<JsonRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)
  const [showRequest, setShowRequest] = useState(false)
  const [requestForm, setRequestForm] = useState({ amount: '', reason: '' })
  const [repayForm, setRepayForm] = useState<Record<string, { principal: string; interest: string }>>({})

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
    Promise.all([
      api(`/api/groups/${groupId}/committee-ledger`),
      api(`/api/advances?group_id=${groupId}`),
    ]).then(([ledgerData, advanceData]) => {
      setLedger(ledgerData)
      setAdvances(advanceData)
    }).catch(e => setError(e instanceof Error ? e.message : 'Unable to load committee ledger.')).finally(() => setLoading(false))
  }, [groupId, refreshKey])

  const refresh = () => setRefreshKey(k => k + 1)

  const requestAdvance = async () => {
    try {
      if (!requestForm.amount || Number(requestForm.amount) <= 0) throw new Error('Enter a valid advance amount.')
      await api('/api/advances', { method: 'POST', body: JSON.stringify({ group_id: Number(groupId), amount: Number(requestForm.amount), reason: requestForm.reason }) })
      setRequestForm({ amount: '', reason: '' }); setShowRequest(false); setNotice('Advance request submitted for approval.'); refresh()
    } catch (e) { setError(e instanceof Error ? e.message : 'Unable to request advance.') }
  }

  const decide = async (id: unknown, status: 'APPROVED' | 'REJECTED') => {
    try {
      await api(`/api/advances/${id}/decision`, { method: 'PUT', body: JSON.stringify({ status }) })
      setNotice(status === 'APPROVED' ? 'Advance approved and recorded in the committee ledger.' : 'Advance request rejected.'); refresh()
    } catch (e) { setError(e instanceof Error ? e.message : 'Unable to review advance.') }
  }

  const repay = async (row: JsonRecord) => {
    try {
      const f = repayForm[String(row.id)] || { principal: '', interest: '' }
      const principal = Number(f.principal || 0), interest = Number(f.interest || 0)
      if (principal <= 0 && interest <= 0) throw new Error('Enter principal or interest received.')
      await api(`/api/advances/${row.id}/repay`, { method: 'POST', body: JSON.stringify({ principal_amount: principal, interest_amount: interest }) })
      setNotice('Verified repayment recorded. Ledger totals have been updated.'); refresh()
    } catch (e) { setError(e instanceof Error ? e.message : 'Unable to record repayment.') }
  }

  if (loading && !ledger) return <div className="workspace-loading"><LoaderCircle className="spin" size={30}/>Loading committee ledger…</div>

  const selectedGroup = groups.find(g => String(g.id) === groupId)
  const canRequest = Boolean(selectedGroup?.is_member) || Boolean(selectedGroup?.is_creator)

  return <>
    <div className="section-actions ledger-select-row">
      <label>View savings group<select value={groupId} onChange={e => { setGroupId(e.target.value); setNotice('') }}>{groups.map(g => <option key={String(g.id)} value={String(g.id)}>{String(g.name)}</option>)}</select></label>
      <button onClick={refresh}><RefreshCw size={16}/> Refresh</button>
      {canRequest && <button className="primary-action" onClick={() => setShowRequest(v => !v)}>Request Advance / Withdraw</button>}
    </div>
    {notice && <div className="workspace-notice success">{notice}</div>}
    {error && <div className="workspace-notice error">{error}</div>}
    {!groups.length && !loading && <div className="empty-state"><Landmark size={28}/><b>No joined savings groups</b><p>Join or create a group to view its committee ledger.</p></div>}

    {showRequest && <section className="workspace-panel action-form"><h3>Request money from committee pool</h3><p>This is an advance/withdrawal from the committee pool. It reduces available cash after approval and becomes your outstanding advance until repaid.</p><div className="form-grid"><label>Amount<input type="number" min="1" value={requestForm.amount} onChange={e => setRequestForm({ ...requestForm, amount: e.target.value })}/></label><label className="wide">Reason<input placeholder="e.g. education, emergency, family expense" value={requestForm.reason} onChange={e => setRequestForm({ ...requestForm, reason: e.target.value })}/></label></div><button className="primary-action" onClick={requestAdvance}>Submit Advance Request</button></section>}

    {ledger && <>
      <section className="workspace-panel ledger-progress"><div className="panel-heading"><div><span>Committee duration</span><h2>{String(ledger.group.name)}</h2></div><b>Cycle {String(ledger.group.current_cycle)} / {String(ledger.group.total_cycles)}</b></div><p>The Group Creator selected this cycle limit when creating the committee. The ledger expands automatically to that limit.</p></section>

      {selectedGroup && <section className="workspace-panel"><div className="panel-heading"><div><span>Financial rules</span><h2>Advance and interest policy</h2></div></div><div className="settlement-grid"><div><small>Normal interest</small><strong>{String(selectedGroup.normal_interest_rate ?? 1)}%</strong></div><div><small>Overdue interest</small><strong>{String(selectedGroup.overdue_interest_rate ?? 2)}%</strong></div><div><small>Repayment period</small><strong>{String(selectedGroup.repayment_period_months ?? 6)} months</strong></div><div><small>Bank interest assumption</small><strong>{String(selectedGroup.bank_interest_rate ?? 0)}% p.a.</strong></div></div></section>}

      <section className="live-metrics ledger-metrics">
        <article><span><WalletCards size={21}/></span><div><small>Expected by final cycle</small><strong>{money(ledger.summary.expected_contributions)}</strong></div></article>
        <article><span><WalletCards size={21}/></span><div><small>Current bank balance</small><strong>{money(ledger.summary.bank_balance)}</strong></div></article>
        <article><span><WalletCards size={21}/></span><div><small>Outstanding advances</small><strong>{money(ledger.summary.outstanding_advances)}</strong></div></article>
        <article><span><WalletCards size={21}/></span><div><small>Committee interest received</small><strong>{money(ledger.summary.committee_interest_received)}</strong></div></article>
        <article><span><WalletCards size={21}/></span><div><small>Bank interest received</small><strong>{money(ledger.summary.bank_interest_received)}</strong></div></article>
        <article><span><WalletCards size={21}/></span><div><small>Missing contributions</small><strong>{money(ledger.summary.missing_contributions_due)}</strong></div></article>
      </section>

      <section className="workspace-panel"><div className="panel-heading"><div><span>Advance / withdrawal activity</span><h2>Requests, approvals and repayments</h2></div></div>{advances.length ? <div className="data-cards">{advances.map(row => {
        const f = repayForm[String(row.id)] || { principal: '', interest: '' }
        return <article key={String(row.id)}><div><span>{String(row.group_name)} · Cycle {String(row.cycle_number)}</span><h3>{String(row.member_name)} · {money(row.amount)}</h3><p>{String(row.reason || 'No reason provided')}</p><small>Status: {String(row.status)} · Outstanding: {money(row.outstanding_principal)} · Interest rule: {String(row.applied_interest_rate || 0)}% · Expected interest: {money(row.expected_interest)}</small>{row.due_date && <small> · Due: {String(row.due_date).slice(0,10)}</small>}</div><div className="row-actions"><em className={`state ${String(row.status).toLowerCase()}`}>{String(row.status)}</em>{Boolean(row.can_manage) && String(row.status) === 'PENDING' && <><button className="approve" onClick={() => decide(row.id, 'APPROVED')}>Approve</button><button className="reject" onClick={() => decide(row.id, 'REJECTED')}>Reject</button></>}{Boolean(row.can_manage) && ['APPROVED','OVERDUE'].includes(String(row.status)) && <div className="advance-repay"><input type="number" placeholder="Principal" value={f.principal} onChange={e => setRepayForm({ ...repayForm, [String(row.id)]: { ...f, principal: e.target.value } })}/><input type="number" placeholder="Interest" value={f.interest} onChange={e => setRepayForm({ ...repayForm, [String(row.id)]: { ...f, interest: e.target.value } })}/><button className="approve" onClick={() => repay(row)}>Record Repayment</button></div>}</div></article>
      })}</div> : <div className="empty-state"><WalletCards size={28}/><b>No advance requests</b><p>Members can request part of the committee pool here.</p></div>}</section>

      <section className="workspace-panel member-settlement-card">
        <div className="panel-heading"><div><span>My calculated settlement</span><h2>{String(ledger.member_summary.member_name)}</h2></div><em className={`state ${ledger.summary.ready_to_distribute ? 'verified' : 'pending'}`}>{ledger.summary.ready_to_distribute ? 'READY TO DISTRIBUTE' : 'SETTLEMENT PENDING'}</em></div>
        <div className="settlement-grid"><div><small>My verified contributions</small><strong>{money(ledger.member_summary.verified_contributions)}</strong></div><div><small>Final savings entitlement</small><strong>{money(ledger.member_summary.final_contribution_entitlement)}</strong></div><div><small>My realized profit share</small><strong>{money(ledger.member_summary.realized_profit_share)}</strong></div><div><small>My outstanding due</small><strong>{money(ledger.member_summary.outstanding_due)}</strong></div><div><small>Estimated final amount</small><strong>{money(ledger.member_summary.estimated_final_receipt)}</strong></div></div>
        <p className="ledger-note">Realized committee profit: <b>{money(ledger.summary.realized_total_profit)}</b> · Current committee assets: <b>{money(ledger.summary.total_committee_assets_now)}</b></p><p className="ledger-note">{String(ledger.summary.settlement_note)}</p>
      </section>

      <section className="workspace-panel"><div className="panel-heading"><div><span>Live committee ledger</span><h2>Cycle-by-cycle financial position</h2></div></div><div className="table-wrap committee-table"><table><thead><tr><th>Cycle</th><th>Expected</th><th>Actual Submitted</th><th>Missing</th><th>Missing By</th><th>Old Missing Collected</th><th>Total Cash Received</th><th>Advance</th><th>Advance By</th><th>Repayment</th><th>Committee Interest</th><th>Bank Interest</th><th>Status</th><th>Outstanding Advance</th><th>Interest Till Date</th><th>Bank Balance</th></tr></thead><tbody>{ledger.rows.map((r, index) => <tr key={index}><td><b>{String(r.cycle)}</b></td><td>{money(r.expected_amount)}</td><td>{money(r.actual_submission)}</td><td>{money(r.missing_contribution)}</td><td>{String(r.missing_by)}</td><td>{money(r.previous_missing_collected)}</td><td>{money(r.total_cash_received)}</td><td>{money(r.advance_taken)}</td><td>{String(r.advance_taken_by)}</td><td>{money(r.repayment_received)}</td><td>{money(r.interest_received)}</td><td>{money(r.bank_interest_received)}</td><td><em className={`state ${String(r.status).toLowerCase().replaceAll(' ', '_')}`}>{String(r.status)}</em></td><td>{money(r.outstanding_advance)}</td><td>{money(r.committee_interest_till_date)}</td><td><b>{money(r.bank_balance)}</b></td></tr>)}</tbody></table></div></section>
      <p className="ledger-demo-note">{ledger.calculation_note}</p>
    </>}
  </>
}
