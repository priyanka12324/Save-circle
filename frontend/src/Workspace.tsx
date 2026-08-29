import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, CheckCircle2, Crown, Eye, FileText, Landmark, LayoutDashboard, LoaderCircle, LogOut, ReceiptText, RefreshCw, ShieldCheck, Upload, Users, WalletCards } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import CommitteeLedger from './CommitteeLedger'
import './Workspace.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const TOKEN_KEY = 'savecircle_access_token'

type User = { id:number; full_name:string; email:string; role:string }
type Tab = 'overview'|'groups'|'ledger'|'members'|'contributions'|'receipts'|'alerts'|'audit'
type JsonRecord = Record<string, unknown>
type DashboardData = { metrics?:Record<string,number>; recent_transactions?:JsonRecord[]; recent_contributions?:JsonRecord[] }

const labels:Record<Tab,string> = {
  overview:'Overview', groups:'Savings groups', ledger:'Committee ledger', members:'Members',
  contributions:'Contributions', receipts:'Digital receipts', alerts:'AI risk alerts', audit:'Audit trail'
}
const icons:Record<Tab,typeof LayoutDashboard> = {
  overview:LayoutDashboard, groups:Landmark, ledger:FileText, members:Users,
  contributions:WalletCards, receipts:ReceiptText, alerts:AlertTriangle, audit:FileText
}

function value(r:JsonRecord,k:string,f='—'){ const v=r[k]; return v===null||v===undefined||v===''?f:String(v) }
function money(v:unknown){ return `₹${Number(v||0).toLocaleString('en-IN')}` }
async function api(path:string, options:RequestInit={}){
  const token=localStorage.getItem(TOKEN_KEY)
  const res=await fetch(`${API_URL}${path}`,{...options,headers:{'Content-Type':'application/json',Authorization:`Bearer ${token}`,...options.headers}})
  const data=await res.json()
  if(!res.ok) throw new Error(typeof data.detail==='string'?data.detail:'Request failed')
  return data
}

export default function Workspace({user,apiOnline,onLogout}:{user:User;apiOnline:boolean|null;onLogout:()=>void}){
  const isAdmin=user.role.toUpperCase()==='ADMIN'
  const tabs=useMemo<Tab[]>(()=>isAdmin
    ? ['overview','groups','ledger','members','contributions','receipts','alerts','audit']
    : ['overview','groups','ledger','contributions','receipts'],[isAdmin])
  const[tab,setTab]=useState<Tab>('overview')
  const[data,setData]=useState<JsonRecord[]|DashboardData>([])
  const[loading,setLoading]=useState(true)
  const[error,setError]=useState('')
  const[notice,setNotice]=useState('')
  const[reloadKey,setReloadKey]=useState(0)

  useEffect(()=>{
    if(tab==='ledger'){ setLoading(false); setError(''); return }
    let active=true
    setLoading(true); setError('')
    const p:Partial<Record<Tab,string>>={
      overview:'/api/analytics/dashboard',groups:'/api/groups',members:'/api/members',
      contributions:'/api/contributions',receipts:'/api/receipts',alerts:'/api/ai/alerts',audit:'/api/audit-logs?limit=100'
    }
    const path=p[tab]
    if(!path){ setLoading(false); return }
    api(path).then(r=>active&&setData(r)).catch(e=>active&&setError(e instanceof Error?e.message:'Unable to load data')).finally(()=>active&&setLoading(false))
    return()=>{active=false}
  },[tab,reloadKey])

  const refresh=()=>setReloadKey(k=>k+1)
  const verify=async(id:unknown,status:'VERIFIED'|'REJECTED')=>{
    try{
      await api(`/api/contributions/${id}/verify`,{method:'PUT',body:JSON.stringify({status,notes:'Payment proof reviewed from SaveCircle dashboard'})})
      setNotice(status==='VERIFIED'?'Payment verified. Digital receipt generated.':'Contribution rejected.')
      refresh()
    }catch(e){ setError(e instanceof Error?e.message:'Action failed') }
  }
  const review=async(id:unknown,status:'VALIDATED'|'INVESTIGATING')=>{
    try{
      await api(`/api/ai/alerts/${id}/review`,{method:'PUT',body:JSON.stringify({status,admin_notes:'Reviewed from dashboard'})})
      setNotice('Risk alert review saved.'); refresh()
    }catch(e){ setError(e instanceof Error?e.message:'Action failed') }
  }

  return <div className="workspace">
    <header className="workspace-header">
      <div className="brand"><span className="brand-mark">S</span><span>SaveCircle</span></div>
      <div className="workspace-user"><span className={`role-chip ${isAdmin?'admin':''}`}>{isAdmin?'PLATFORM ADMIN':'MEMBER'}</span><div><b>{user.full_name}</b><small>{user.email}</small></div><button onClick={onLogout}><LogOut size={17}/> Logout</button></div>
    </header>
    <div className="workspace-grid">
      <aside className="workspace-sidebar"><span>Workspace</span>{tabs.map(t=>{const I=icons[t];return <button key={t} className={tab===t?'active':''} onClick={()=>{setNotice('');setTab(t)}}><I size={18}/>{labels[t]}</button>})}<div className="sidebar-secure"><ShieldCheck size={19}/><p><b>Protected session</b><small>Role-based access enabled</small></p></div></aside>
      <main className="workspace-main">
        <div className="workspace-title"><div><span>{isAdmin?'Platform administrator':'Member workspace'}</span><h1>{labels[tab]}</h1><p>{tab==='overview'?`Welcome back, ${user.full_name.split(' ')[0]}.`:tab==='ledger'?'Transparent view of committee money, advances, dues and projected settlement.':'Secure SaveCircle records and actions.'}</p></div><div className="title-actions"><span className={`api-chip ${apiOnline?'online':''}`}><i/>{apiOnline?'API online':'API offline'}</span><button onClick={refresh}><RefreshCw size={17}/></button></div></div>
        {notice&&<div className="workspace-notice success"><CheckCircle2 size={18}/>{notice}</div>}
        {error&&<div className="workspace-notice error"><AlertTriangle size={18}/>{error}</div>}
        {loading?<div className="workspace-loading"><LoaderCircle className="spin" size={30}/>Loading…</div>:<>
          {tab==='overview'&&<Overview data={data as DashboardData} isAdmin={isAdmin}/>} 
          {tab==='groups'&&<Groups rows={data as JsonRecord[]} isAdmin={isAdmin} user={user} changed={m=>{setNotice(m);refresh()}} fail={setError}/>} 
          {tab==='ledger'&&<CommitteeLedger/>}
          {tab==='members'&&<Members rows={data as JsonRecord[]}/>} 
          {tab==='contributions'&&<Contributions rows={data as JsonRecord[]} isAdmin={isAdmin} verify={verify} changed={m=>{setNotice(m);refresh()}} fail={setError}/>} 
          {tab==='receipts'&&<Receipts rows={data as JsonRecord[]}/>} 
          {tab==='alerts'&&<Alerts rows={data as JsonRecord[]} review={review}/>} 
          {tab==='audit'&&<Audit rows={data as JsonRecord[]}/>} 
        </>}
      </main>
    </div>
  </div>
}

function Empty({text}:{text:string}){return <div className="empty-state"><FileText size={28}/><b>No records yet</b><p>{text}</p></div>}

function Overview({data,isAdmin}:{data:DashboardData;isAdmin:boolean}){
  const m=data.metrics||{}
  const cards:Array<[string,unknown,LucideIcon]>=isAdmin
    ? [['Members',m.total_members,Users],['Active groups',m.active_groups,Landmark],['Verified savings',m.total_contributions,WalletCards],['Pending reviews',m.pending_verifications,AlertTriangle]]
    : [['Total savings',m.total_savings,WalletCards],['Monthly contribution',m.current_contribution,ReceiptText],['Active groups',m.active_groups,Landmark],['Receipts',m.verified_receipts_count,FileText]]
  const recent=(isAdmin?data.recent_transactions:data.recent_contributions)||[]
  return <><section className="live-metrics">{cards.map(([l,v,I])=><article key={l}><span><I size={21}/></span><div><small>{l}</small><strong>{l.toLowerCase().includes('saving')||l.toLowerCase().includes('contribution')?money(v):String(v??0)}</strong></div></article>)}</section><section className="workspace-panel"><div className="panel-heading"><div><span>Latest activity</span><h2>Recent transactions</h2></div></div>{recent.length?<div className="record-list">{recent.slice(0,6).map(r=><div key={value(r,'id')}><span className="record-icon"><ReceiptText size={18}/></span><p><b>{value(r,isAdmin?'member_name':'group_name')}</b><small>{value(r,'reference_id',value(r,'transaction_ref'))}</small></p><strong>{money(r.amount)}</strong><em className={`state ${value(r,'status').toLowerCase()}`}>{value(r,'status')}</em></div>)}</div>:<Empty text="New activity will appear here."/>}</section></>
}

function Groups({rows,isAdmin,user,changed,fail}:{rows:JsonRecord[];isAdmin:boolean;user:User;changed:(m:string)=>void;fail:(m:string)=>void}){
  const[show,setShow]=useState(false)
  const[form,setForm]=useState({name:'',description:'',contribution_amount:'2000',contribution_frequency:'Monthly',max_members:'10',total_cycles:'12'})
  const create=async()=>{try{await api('/api/groups',{method:'POST',body:JSON.stringify({...form,contribution_amount:Number(form.contribution_amount),max_members:Number(form.max_members),total_cycles:Number(form.total_cycles)})});setShow(false);setForm({...form,name:'',description:''});changed(isAdmin?'Savings group created.':'Savings group created — you are now its Group Creator.')}catch(e){fail(e instanceof Error?e.message:'Unable to create group')}}
  const join=async(id:unknown)=>{try{await api(`/api/groups/${id}/members`,{method:'POST',body:JSON.stringify({user_id:user.id,role_in_group:'MEMBER'})});changed('You joined the group. You can now submit contributions.')}catch(e){fail(e instanceof Error?e.message:'Unable to join group')}}
  return <><div className="section-actions"><button className="primary-action" onClick={()=>setShow(!show)}>+ Create Savings Group</button></div>{show&&<div className="action-form"><h3>Create your savings group</h3><p>{isAdmin?'Create a platform-managed savings circle.':'You will automatically become the Group Creator and can review other members’ payments.'}</p><div className="form-grid"><label>Group name<input value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/></label><label>Contribution amount<input type="number" value={form.contribution_amount} onChange={e=>setForm({...form,contribution_amount:e.target.value})}/></label><label>Frequency<select value={form.contribution_frequency} onChange={e=>setForm({...form,contribution_frequency:e.target.value})}><option>Monthly</option><option>Weekly</option><option>Bi-Weekly</option></select></label><label>Max members<input type="number" value={form.max_members} onChange={e=>setForm({...form,max_members:e.target.value})}/></label><label>Total cycles<input type="number" value={form.total_cycles} onChange={e=>setForm({...form,total_cycles:e.target.value})}/></label><label className="wide">Description<input value={form.description} onChange={e=>setForm({...form,description:e.target.value})}/></label></div><button className="primary-action" onClick={create}>Create Group</button></div>}{rows.length?<section className="card-grid">{rows.map(r=><article key={value(r,'id')}><div className="card-icon">{r.is_creator?<Crown size={22}/>:<Landmark size={22}/>}</div><span>{r.is_creator?'GROUP CREATOR':value(r,'contribution_frequency')}</span><h3>{value(r,'name')}</h3><p>{value(r,'description','Community savings group')}</p><dl><div><dt>Contribution</dt><dd>{money(r.contribution_amount)}</dd></div><div><dt>Members</dt><dd>{value(r,'member_count')}</dd></div><div><dt>Total saved</dt><dd>{money(r.total_collected)}</dd></div><div><dt>Cycle</dt><dd>{value(r,'current_cycle')} / {value(r,'total_cycles')}</dd></div></dl>{!isAdmin&&!r.is_member&&!r.is_creator&&<button className="join-button" onClick={()=>join(r.id)}>Join Group</button>}{r.is_creator&&<div className="creator-note"><Crown size={14}/> You manage this group · verify other members in Contributions</div>}</article>)}</section>:<Empty text="No active savings groups were found."/>}</>
}

function Members({rows}:{rows:JsonRecord[]}){return rows.length?<Table headers={['Member','Email','Phone','Role','Status']} rows={rows.map(r=>[value(r,'full_name'),value(r,'email'),value(r,'phone'),value(r,'role'),r.is_active?'Active':'Inactive'])}/>:<Empty text="No members were found."/>}

function Contributions({rows,isAdmin,verify,changed,fail}:{rows:JsonRecord[];isAdmin:boolean;verify:(id:unknown,s:'VERIFIED'|'REJECTED')=>void;changed:(m:string)=>void;fail:(m:string)=>void}){
  const[groups,setGroups]=useState<JsonRecord[]>([]),[show,setShow]=useState(false),[proof,setProof]=useState<{name:string;type:string;data:string}|null>(null),[form,setForm]=useState({group_id:'',amount:'2000',payment_method:'UPI (Demo)',transaction_ref:'',notes:''})
  useEffect(()=>{if(!isAdmin)api('/api/groups').then(setGroups).catch(()=>{})},[isAdmin])
  const file=(f?:File)=>{if(!f)return;if(!f.type.startsWith('image/'))return fail('Please upload an image screenshot.');if(f.size>1400000)return fail('Payment proof must be smaller than 1.4 MB.');const rd=new FileReader();rd.onload=()=>setProof({name:f.name,type:f.type,data:String(rd.result)});rd.readAsDataURL(f)}
  const submit=async()=>{try{if(!form.group_id)throw new Error('Please select a savings group.');if(!form.transaction_ref.trim())throw new Error('Please enter your transaction/UTR ID.');if(!proof)throw new Error('Please upload the payment screenshot.');await api('/api/contributions',{method:'POST',body:JSON.stringify({...form,group_id:Number(form.group_id),amount:Number(form.amount),proof_filename:proof.name,proof_content_type:proof.type,proof_data_url:proof.data})});setShow(false);setProof(null);setForm({...form,transaction_ref:'',notes:''});changed('Contribution submitted — pending verification.')}catch(e){fail(e instanceof Error?e.message:'Unable to submit contribution')}}
  return <><div className="section-actions">{!isAdmin&&<button className="primary-action" onClick={()=>setShow(!show)}><WalletCards size={16}/> Add Contribution</button>}</div>{show&&<div className="action-form"><h3>Submit your contribution</h3><p>Upload payment proof. Your Group Creator or Platform Admin will review it.</p><div className="form-grid"><label>Savings group<select value={form.group_id} onChange={e=>{const id=e.target.value,g=groups.find(x=>String(x.id)===id);setForm({...form,group_id:id,amount:g?String(g.contribution_amount):form.amount})}}><option value="">Select group</option>{groups.filter(g=>Boolean(g.is_member)||Boolean(g.is_creator)).map(g=><option key={value(g,'id')} value={value(g,'id')}>{value(g,'name')} — {money(g.contribution_amount)}</option>)}</select></label><label>Amount<input type="number" value={form.amount} onChange={e=>setForm({...form,amount:e.target.value})}/></label><label>Payment method<select value={form.payment_method} onChange={e=>setForm({...form,payment_method:e.target.value})}><option>UPI (Demo)</option><option>Bank Transfer (Demo)</option><option>Cash (Demo)</option></select></label><label>Transaction / UTR ID<input placeholder="e.g. UTR123456789" value={form.transaction_ref} onChange={e=>setForm({...form,transaction_ref:e.target.value})}/></label><label className="wide">Notes<input value={form.notes} onChange={e=>setForm({...form,notes:e.target.value})}/></label><label className="wide upload-box"><Upload size={20}/> Payment proof screenshot<input type="file" accept="image/*" onChange={e=>file(e.target.files?.[0])}/><small>{proof?`Selected: ${proof.name}`:'PNG/JPG, max 1.4 MB'}</small></label></div><button className="primary-action" onClick={submit}>Submit for Verification</button></div>}{rows.length?<div className="data-cards">{rows.map(r=><article key={value(r,'id')}><div><span>{value(r,'group_name')}</span><h3>{money(r.amount)}</h3><p>{value(r,'member_name')} · {value(r,'payment_method')}</p><small>UTR/Ref: {value(r,'transaction_ref')}</small></div><div className="row-actions"><em className={`state ${value(r,'status').toLowerCase()}`}>{value(r,'status')}</em>{r.payment_proof_url&&<button onClick={()=>window.open(String(r.payment_proof_url),'_blank')}><Eye size={14}/> View Proof</button>}{Boolean(r.can_verify)&&value(r,'status')==='PENDING'&&<><button className="approve" onClick={()=>verify(r.id,'VERIFIED')}>Verify</button><button className="reject" onClick={()=>verify(r.id,'REJECTED')}>Reject</button></>}</div></article>)}</div>:<Empty text={isAdmin?'No contribution records were found.':'No contributions yet. Create/join a group and add a contribution.'}/>}</>
}

function Receipts({rows}:{rows:JsonRecord[]}){return rows.length?<Table headers={['Receipt','Group','Amount','Payment','Transaction','Verified by','Issued at']} rows={rows.map(r=>[value(r,'receipt_number'),value(r,'group_name'),money(r.amount),value(r,'payment_method'),value(r,'transaction_ref'),value(r,'verified_by_name'),value(r,'created_at').slice(0,10)])}/>:<Empty text="Receipts appear automatically after verification."/>}
function Alerts({rows,review}:{rows:JsonRecord[];review:(id:unknown,s:'VALIDATED'|'INVESTIGATING')=>void}){return rows.length?<div className="data-cards">{rows.map(r=><article className="risk-card" key={value(r,'id')}><div><span>{value(r,'risk_level')} risk · {value(r,'group_name')}</span><h3>{value(r,'member_name')} · {money(r.amount)}</h3><p>{value(r,'recommended_action')}</p></div><div className="row-actions"><em className="state pending_review">{value(r,'status')}</em>{value(r,'status')==='PENDING_REVIEW'&&<><button className="approve" onClick={()=>review(r.id,'VALIDATED')}>Mark valid</button><button onClick={()=>review(r.id,'INVESTIGATING')}>Investigate</button></>}</div></article>)}</div>:<Empty text="No AI risk alerts require review."/>}
function Audit({rows}:{rows:JsonRecord[]}){return rows.length?<Table headers={['Actor','Action','Description','Date']} rows={rows.map(r=>[value(r,'actor_name'),value(r,'action'),value(r,'description'),value(r,'created_at').slice(0,10)])}/>:<Empty text="Audit events will appear here."/>}
function Table({headers,rows}:{headers:string[];rows:string[][]}){return <div className="table-wrap"><table><thead><tr>{headers.map(h=><th key={h}>{h}</th>)}</tr></thead><tbody>{rows.map((r,i)=><tr key={i}>{r.map((c,j)=><td key={j}>{c}</td>)}</tr>)}</tbody></table></div>}
