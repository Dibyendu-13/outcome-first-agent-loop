'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num = value => Number(value || 0).toLocaleString('en-IN');
const pct = value => value == null ? '—' : (100 * value).toFixed(1) + '%';
const human = value => String(value || '').replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
const labels = {voice:'Voice',welcome_message:'Welcome message',caller_id:'Caller ID',prompt_version:'Prompt',schedule:'Schedule',cohorts:'Cohorts'};
const titles = {overview:['Workflow overview','Understand performance. Follow the evidence. Stay in control.'],experiments:['Learning, with evidence','See what ran, how much we learned, and where uncertainty remains.'],approvals:['Governance & approvals','Every proposal, its evidence, and its recorded decision.'],activity:['Decision history','Understand why a workflow changed and what happened next.']};
let data = null, page = 'overview', chartMetric = 'engagement_rate', fetching = false, lastUpdate = null, returnFocus = null, activeDetail = null;
function date(value, withTime = false) {
  if (!value) return '—';
  const normalized = /^\d{4}-\d{2}-\d{2}T\d{2}$/.test(value) ? value + ':00:00+05:30' : /^\d{4}-\d{2}-\d{2}$/.test(value) ? value+'T00:00:00+05:30' : value;
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) return '—';
  return new Intl.DateTimeFormat('en-IN', {timeZone:'Asia/Kolkata',day:'numeric',month:'short',...(withTime ? {hour:'2-digit',minute:'2-digit',hour12:false} : {})}).format(parsed);
}
function workflowName(w) {
  const use = (w?.use_case || '').toLowerCase();
  if (use.includes('renewal')) return 'Renewal reminders';
  if (use.includes('kyc')) return 'KYC follow-ups';
  if (use.includes('cancellation')) return 'Cancellation checks';
  return human(w?.workflow_id || 'Workflow');
}
function proposalSummary(p) {return (p?.summary || '').replaceAll('welcome_message','welcome message').replaceAll('caller_id','caller ID');}
function workflow(id) {return data.workflows.find(w => w.workflow_id === id);}
function displayWorkflow(id) {const w = workflow(id); return w ? `${human(w.tenant_id)} · ${workflowName(w)}` : human(id);}
function badge(status) {
  const map = {applied:['Applied','good'],approved:['Approved','good'],pending:['Pending review','warning'],prepared:['Prepared','neutral'],unknown:['Needs reconciliation','warning'],rejected:['Declined','neutral'],expired:['Expired','warning'],lapsed:['Lapsed','warning'],stale:['Stale base','warning'],failed:['Failed','danger'],exploring:['Collecting evidence','warning'],promoted:['Monitoring winner','good'],completed:['Completed','good'],ended_inconclusive:['Ended · no promotion','neutral']};
  const [text,tone] = map[status] || [human(status),'neutral'];
  return `<span class="badge ${tone}">${esc(text)}</span>`;
}
function delta(current, reference) {
  if (current == null || reference == null) return '<span class="kpi-note">No historical reference</span>';
  const pp = 100*(current-reference), cls = pp < -.05 ? 'down' : pp > .05 ? '' : 'flat';
  return `<span class="delta ${cls}">${pp > .05 ? '↗ +' : pp < -.05 ? '↘ ' : ''}${pp.toFixed(1)} pp</span><span class="kpi-note">vs history</span>`;
}
function selectedWorkflows() {
  const tenant = $('tenant').value, wid = $('workflow').value;
  return data.workflows.filter(w => (!tenant || w.tenant_id===tenant) && (!wid || w.workflow_id===wid));
}
function ids() {return new Set(selectedWorkflows().map(w=>w.workflow_id));}
function queryMatch(value) {return String(value || '').toLowerCase().includes($('search').value.trim().toLowerCase());}
function totals(items, key = 'kpis') {
  const t = {dials:0,connected:0,engaged:0,flags:0,uploaded:0,enrolled:0,concluded:0};
  items.forEach(w => Object.keys(t).forEach(k => t[k] += w[key]?.[k] || 0));
  t.pickup_rate = t.dials ? t.connected/t.dials : null;
  t.engagement_rate = t.connected ? t.engaged/t.connected : null;
  t.flag_rate = t.connected ? t.flags/t.connected : null;
  t.conclusion_rate = t.uploaded ? t.concluded/t.uploaded : null;
  return t;
}
function fillFilters() {
  const tenant = $('tenant').value, wid = $('workflow').value;
  const tenants = [...new Set(data.workflows.map(w => w.tenant_id))].sort();
  $('tenant').innerHTML = '<option value="">All tenants</option>'+tenants.map(t=>`<option value="${esc(t)}">${esc(human(t))}</option>`).join('');
  if (tenants.includes(tenant)) $('tenant').value = tenant;
  const available = data.workflows.filter(w=>!$('tenant').value || w.tenant_id===$('tenant').value);
  $('workflow').innerHTML = '<option value="">All workflows</option>'+available.map(w=>`<option value="${esc(w.workflow_id)}">${esc(human(w.tenant_id)+' · '+workflowName(w))}</option>`).join('');
  if (available.some(w=>w.workflow_id===wid)) $('workflow').value = wid;
}
function render() {
  if (!data) return;
  const selected = selectedWorkflows(), selectedIds = ids(), t = totals(selected), h = totals(selected,'history');
  const finished = data.state?.finished;
  $('loading').hidden = true; $('content').hidden = false;
  const periodEnd=data.period.end ? new Date(new Date(data.period.end).getTime()-(finished?1:0)).toISOString() : null;
  $('period').textContent = data.period.start ? `${date(data.period.start)} – ${date(periodEnd)} ${new Intl.DateTimeFormat('en',{year:'numeric',timeZone:'Asia/Kolkata'}).format(new Date(periodEnd))} · IST` : 'Awaiting run initialization';
  $('period').title = data.period.start ? `Run window: ${data.period.start} to ${data.period.end} (end exclusive).` : '';
  $('experiment-count').textContent = data.experiments.length;
  $('approval-count').textContent = data.proposals.filter(p=>['pending','approved','prepared','unknown'].includes(p.status)).length;
  $('run-banner').innerHTML = `<div><span aria-hidden="true">${finished ? '✓' : '◉'}</span><strong>${finished ? 'Simulation complete' : data.state ? 'Monitoring in progress' : 'Waiting for the controller'}</strong><span>· ${esc(human(data.state?.scenario || 'No run loaded'))}</span></div><span class="run-detail">${num(data.ingestion.events)} events recorded · ${data.ingestion.event_lag==null?'—':num(data.ingestion.event_lag)} events behind</span>`;
  $('kpi-cards').innerHTML = [
    `<article class="kpi-card featured"><div class="kpi-heading">Lead conclusion rate<span class="metric-icon" aria-hidden="true">◎</span></div><div class="kpi-number">${pct(t.conclusion_rate)}</div><div class="kpi-note">${num(t.concluded)} concluded / ${num(t.uploaded)} uploaded</div><div class="kpi-context">Campaigns uploaded during this run</div></article>`,
    `<article class="kpi-card"><div class="kpi-heading">Pickup rate<span class="metric-icon" aria-hidden="true">↗</span></div><div class="kpi-number">${pct(t.pickup_rate)}</div><div>${delta(t.pickup_rate,h.pickup_rate)}</div><div class="kpi-context">${num(t.connected)} connected / ${num(t.dials)} dials</div></article>`,
    `<article class="kpi-card"><div class="kpi-heading">Engagement rate<span class="metric-icon" aria-hidden="true">◌</span></div><div class="kpi-number">${pct(t.engagement_rate)}</div><div>${delta(t.engagement_rate,h.engagement_rate)}</div><div class="kpi-context">${num(t.engaged)} engaged / ${num(t.connected)} connected</div></article>`,
    `<article class="kpi-card"><div class="kpi-heading">Hallucination flag rate<span class="metric-icon" aria-hidden="true">◇</span></div><div class="kpi-number">${pct(t.flag_rate)}</div><div class="kpi-note">${num(t.flags)} flags / ${num(t.connected)} connected</div><div class="kpi-context">Automated QA flags · not confirmed incidents</div></article>`
  ].join('');
  renderChart(selected);
  renderAttention(selected,selectedIds);
  const visible = selected.filter(w=>queryMatch([workflowName(w),w.tenant_id,w.workflow_id,w.use_case].join(' ')));
  $('workflow-count').textContent = `(${visible.length})`;
  $('workflow-cards').innerHTML = visible.map(w=>{
    const k=w.kpis, ref=w.history, primary=w.objective.primary==='pickup_rate' ? 'Pickup' : 'Engagement';
    return `<article class="workflow-card"><div class="workflow-title"><span class="workflow-symbol" aria-hidden="true">${primary==='Pickup' ? '↗' : '◈'}</span><div><h3>${esc(workflowName(w))}</h3><div class="tenant">${esc(human(w.tenant_id))}</div></div></div><div class="workflow-status"><span class="badge ${w.incident?'danger':'neutral'}">${w.incident?'Open safety incident':finished?'Run complete':'Monitoring'}</span><span class="workflow-id">${esc(w.workflow_id)}</span></div><div class="workflow-outcome"><span>LEADS CONCLUDED</span><strong>${pct(k.conclusion_rate)}<small>${num(k.concluded)} of ${num(k.uploaded)}</small></strong></div><div class="workflow-metrics"><div><span>Pickup rate</span><strong>${pct(k.pickup_rate)}</strong><em>${ref.pickup_rate==null?'No history':((k.pickup_rate-ref.pickup_rate)*100).toFixed(1)+' pp vs history'}</em></div><div><span>Engagement rate</span><strong>${pct(k.engagement_rate)}</strong><em>${ref.engagement_rate==null?'No history':((k.engagement_rate-ref.engagement_rate)*100).toFixed(1)+' pp vs history'}</em></div></div><div class="workflow-card-footer"><span>Primary · ${primary}</span><button class="text-button" data-workflow="${esc(w.workflow_id)}">View workflow <span aria-hidden="true">→</span></button></div></article>`;
  }).join('') || '<div class="panel empty">No workflows match these filters.</div>';
  const recent = data.proposals.filter(p=>selectedIds.has(p.workflow)&&p.status==='applied'&&queryMatch(p.summary+' '+displayWorkflow(p.workflow))).sort((a,b)=>(b.applied_event?.ts || b.created).localeCompare(a.applied_event?.ts || a.created)).slice(0,4);
  $('recent-changes').innerHTML = recent.map(p=>`<div class="change-row"><span class="change-icon" aria-hidden="true">✓</span><div class="change-main"><strong>${esc(proposalSummary(p))}</strong><span>${esc(displayWorkflow(p.workflow))} · ${p.approval ? esc(p.approval) : 'Policy-permitted auto-apply'}</span></div><time>${date(p.applied_event?.ts || p.created,true)}</time><button class="text-button" data-proposal="${esc(p.id)}">Evidence →</button></div>`).join('') || '<div class="empty">No applied changes in this selection.</div>';
  renderExperiments(selectedIds); renderProposals(selectedIds); renderActivity(selectedIds);
  $('updated').textContent = `Snapshot refreshed ${lastUpdate?.toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'}) || '—'} · Auto-refresh 15s`;
}
function renderChart(selected) {
  const days = new Map();
  selected.forEach(w=>w.daily.forEach(d=>{
    const current=days.get(d.date)||{date:d.date,dials:0,connected:0,engaged:0};
    ['dials','connected','engaged'].forEach(k=>current[k]+=d[k]); days.set(d.date,current);
  }));
  const rows=[...days.values()].sort((a,b)=>a.date.localeCompare(b.date));
  const values=rows.map(d=>chartMetric==='pickup_rate' ? d.dials ? d.connected/d.dials : null : d.connected ? d.engaged/d.connected : null);
  const label=chartMetric==='pickup_rate' ? 'Pickup rate' : 'Engagement rate';
  $('chart-label').textContent=label;
  if (!values.some(v=>v!=null)) {$('chart').innerHTML='<div class="empty">No call observations for this selection yet.</div>';return;}
  const width=640,height=200,left=42,right=15,top=14,bottom=35,plotW=width-left-right,plotH=height-top-bottom;
  const valid=values.filter(v=>v!=null), min=Math.max(0,Math.floor((Math.min(...valid)-.06)*10)/10), max=Math.min(1,Math.ceil((Math.max(...valid)+.06)*10)/10);
  const x=i=>rows.length===1?left+plotW/2:left+i*plotW/(rows.length-1), y=v=>top+(max-v)/(max-min || .1)*plotH;
  const points=values.map((v,i)=>v==null?null:[x(i),y(v)]).filter(Boolean);
  const path=points.map(([px,py],i)=>`${i?'L':'M'}${px.toFixed(1)},${py.toFixed(1)}`).join(' ');
  const area=points.length>1 ? `${path} L${points.at(-1)[0]},${height-bottom} L${points[0][0]},${height-bottom} Z` : '';
  const ticks=Array.from({length:4},(_,i)=>min+(max-min)*i/3);
  const description=rows.map((d,i)=>`${date(d.date)}: ${pct(values[i])}`).join('; ');
  $('chart').innerHTML=`<svg viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="trend-title trend-description"><title id="trend-title">${label} by day</title><desc id="trend-description">${esc(description)}</desc><defs><linearGradient id="chart-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#ed7044" stop-opacity=".13"/><stop offset="1" stop-color="#ed7044" stop-opacity="0"/></linearGradient></defs>${ticks.map(v=>`<line x1="${left}" y1="${y(v)}" x2="${width-right}" y2="${y(v)}" stroke="#edf0f3" stroke-dasharray="3 4"/><text x="${left-9}" y="${y(v)+3}" text-anchor="end">${Math.round(v*100)}%</text>`).join('')}${area?`<path d="${area}" fill="url(#chart-fill)"/>`:''}<path d="${path}" fill="none" stroke="#ed7044" stroke-width="2.5" stroke-linejoin="round"/>${rows.map((d,i)=>values[i]==null?'':`<circle cx="${x(i)}" cy="${y(values[i])}" r="3.5" fill="white" stroke="#ed7044" stroke-width="2"><title>${esc(date(d.date))}: ${pct(values[i])} · ${num(d.connected)} connected</title></circle>`).join('')}${rows.filter((_,i)=>rows.length<8 || i%2===0 || i===rows.length-1).map(d=>`<text x="${x(rows.indexOf(d))}" y="${height-10}" text-anchor="middle">${esc(date(d.date))}</text>`).join('')}</svg>`;
}
function renderAttention(selected, selectedIds) {
  const attention=[];
  selected.filter(w=>w.incident).forEach(w=>attention.push({title:'Open hallucination incident',description:displayWorkflow(w.workflow_id)+' · Detected '+date(w.incident.detected,true),workflow:w.workflow_id}));
  data.proposals.filter(p=>selectedIds.has(p.workflow)&&['prepared','pending','approved','unknown','failed'].includes(p.status)).forEach(p=>attention.push({title:p.status==='prepared'?'Proposal awaiting submission':p.status==='approved'?'Approved · awaiting application':p.status==='pending'?'Awaiting client review':p.status==='unknown'?'Reconciliation required':'Proposal failed',description:p.summary,proposal:p.id}));
  data.paid_operations.filter(c=>c.status==='unknown'&&selected.some(w=>c.key.includes(':'+w.workflow_id+':'))).forEach(c=>attention.push({title:'Uncertain paid operation',description:'Acknowledgement missing; the controller will not charge again automatically.'}));
  if (data.ingestion.event_lag) attention.push({title:'Event backlog',description:num(data.ingestion.event_lag)+' simulator events are not yet ingested.'});
  $('attention-count').textContent=attention.length;
  $('attention').innerHTML=attention.length ? attention.slice(0,5).map(a=>`<div class="attention-item"><strong>${esc(a.title)}</strong><p>${esc(a.description)}</p>${a.proposal?`<button data-proposal="${esc(a.proposal)}">Review evidence →</button>`:a.workflow?`<button data-workflow="${esc(a.workflow)}">View workflow →</button>`:''}</div>`).join('') : '<div class="attention-empty"><div class="check-ring" aria-hidden="true">✓</div><h3>No open incidents or pending reviews</h3><p>Recorded changes and historical incidents remain available in decision history.</p></div>';
  $('attention').innerHTML+=`<div class="health-strip"><span>Credits remaining <strong>${data.state?.credits_remaining==null?'—':num(data.state.credits_remaining)}</strong></span><span>Event backlog <strong>${data.ingestion.event_lag==null?'—':num(data.ingestion.event_lag)}</strong></span></div>`;
}
function renderExperiments(selectedIds) {
  const experiments=data.experiments.filter(e=>selectedIds.has(e.workflow)&&queryMatch(displayWorkflow(e.workflow)+' '+e.dimension));
  $('experiment-list').innerHTML=experiments.map(e=>`<article class="panel experiment-card"><div class="panel-heading"><div><h2>${esc(labels[e.dimension]||human(e.dimension))} experiment</h2><p>${esc(displayWorkflow(e.workflow))}</p></div>${badge(e.status)}</div><div class="experiment-meta"><span>Started ${date(e.started,true)} IST</span><span>Shared cohort · default</span><span>${e.looks} of ${e.maximum_looks} evaluation looks</span></div><div class="experiment-explanation">${esc(e.explanation)}</div><div class="arm-grid">${e.arms.map(a=>`<div class="arm-card"><div class="arm-heading">${esc(a.option)}<small>${pct(a.allocation)} current allocation</small></div><div class="arm-rate">${pct(e.metric==='pickup'?a.pickup_rate:a.engagement_rate)}</div><div class="arm-rate-label">${e.metric==='pickup'?'pickup':'engagement'} · ${num(a.dials)} actual dials</div><div class="progress-track" role="progressbar" aria-label="${esc(a.option)} minimum connected-call sample" aria-valuemin="0" aria-valuemax="400" aria-valuenow="${Math.min(400,a.connected)}"><div class="progress-fill ${a.sample_ready?'ready':''}" style="width:${Math.min(100,a.connected/4)}%"></div></div><div class="sample-count">${num(a.connected)} / 400 connected<br>${a.sample_ready?'Sample minimum reached':'More observations needed'}</div></div>`).join('')}</div><div class="panel-bottom">Only actual calls count as evidence. Allocation shown is the last recorded configuration; historical exposure may differ. ${data.state?.finished?'The run has ended; these experiments are not still receiving traffic.':''}</div></article>`).join('')||'<div class="panel empty">No experiments match this selection.</div>';
}
function renderProposals(selectedIds) {
  const status=$('proposal-status').value;
  const rows=data.proposals.filter(p=>selectedIds.has(p.workflow)&&(!status||p.status===status)&&queryMatch(p.summary+' '+displayWorkflow(p.workflow)+' '+p.approval));
  $('proposal-list').innerHTML=rows.length?`<table><thead><tr><th scope="col">Proposed change</th><th scope="col">Status</th><th scope="col">Affected leads</th><th scope="col">Approval</th><th scope="col">Evidence</th></tr></thead><tbody>${rows.map(p=>`<tr><td><span class="proposal-summary">${esc(proposalSummary(p))}</span><span class="cell-sub">${esc(displayWorkflow(p.workflow))} · ${date(p.created,true)} IST</span></td><td>${badge(p.status)}</td><td>${p.affected_leads==null?'—':num(p.affected_leads)}<span class="cell-sub">Upper-bound estimate</span></td><td>${esc(p.approval||(p.plan.auto?'Policy route':'Not assigned'))}<span class="cell-sub">${p.decision?date(p.decision.ts,true)+' IST':'No decision recorded'}</span></td><td><button class="text-button" data-proposal="${esc(p.id)}">Inspect →</button></td></tr>`).join('')}</tbody></table>`:'<div class="empty">No proposals match this selection.</div>';
}
const routine=new Set(['insufficient_evidence','post_apply_verification','credit_operation','applied','incident_prompt_replaced']);
function describe(a) {
  const ev=a.evidence,p=data.proposals.find(p=>p.id===ev.proposal_id || p.approval&&p.approval===ev.approval_id);
  if(a.kind==='config_changed') return {title:ev.actor==='supervisor'?'Supervisor updated '+(ev.changed_dims||[]).map(d=>labels[d]||human(d)).join(', '):p?proposalSummary(p):'Configuration updated',description:ev.actor==='supervisor'?'Client edit recorded; controller reassesses the current configuration.':`${p?.approval?'Approved via '+p.approval:'Policy-permitted change'} · Configuration v${ev.version}`,tone:'applied',proposal:p?.id};
  if(a.kind==='approval_decided')return {title:'Client approver '+(ev.status==='approved'?'approved':ev.status==='rejected'?'declined':ev.status)+' a proposal',description:(p?proposalSummary(p):'')||(ev.reasons||[]).join('; ')||ev.approval_id,tone:'',proposal:p?.id};
  if(a.kind==='hallucination_incident')return {title:'Sustained hallucination flags detected',description:`${num(ev.recent?.hallucinations)} flags across ${num(ev.recent?.connected)} connected calls. Validation and human review required.`,tone:'incident'};
  if(a.kind==='proposal_prepared')return {title:'New change proposed',description:p?proposalSummary(p):ev.summary||'Evidence packaged for governance review.',tone:'',proposal:p?.id};
  if(a.kind==='supervisor_reassessment')return {title:'Controller reassessed a supervisor edit',description:'Experiments paused for 24 hours; explicitly edited allocation dimensions are protected.',tone:''};
  if(a.kind==='insufficient_evidence')return {title:'No winner declared',description:`${labels[ev.dimension]||human(ev.dimension)} · Evaluation ${ev.look||'—'} · Sample or separation requirements not met.`,tone:''};
  if(a.kind==='post_apply_verification')return {title:ev.harmful?'Post-change degradation detected':'Post-change outcomes reviewed',description:`${num(ev.after?.connected)} connected calls reviewed. ${ev.harmful?'Rollback requires governance.':'No separated-interval degradation detected; temporal comparison may be confounded.'}`,tone:ev.harmful?'incident':'',proposal:p?.id};
  if(a.kind==='credit_operation'&&ev.status>=400)return {title:'Prompt safety operation failed',description:`Request returned HTTP ${ev.status}; no successful result recorded.`,tone:'incident'};
  if(a.kind==='credit_operation')return {title:'Prompt safety operation recorded',description:ev.result?.validation_run_id?`Validation ${ev.result.validation_run_id} · ${pct(ev.result.pass_rate)} safety pass rate`:'Prompt candidate suggestion completed.',tone:''};
  return {title:human(a.kind),description:ev.summary||ev.response?.error||'Recorded controller evidence.',tone:a.kind.startsWith('alert_')?'incident':'',proposal:p?.id};
}
function renderActivity(selectedIds) {
  const rows=data.activity.filter(a=>(!a.workflow||selectedIds.has(a.workflow))&&($('include-routine').checked||!routine.has(a.kind))).map(a=>({...a,presentation:describe(a)})).filter(a=>queryMatch(a.presentation.title+' '+a.presentation.description+' '+displayWorkflow(a.workflow)));
  $('activity-list').innerHTML=rows.slice(0,100).map(a=>`<article class="timeline-item"><span class="timeline-dot ${a.presentation.tone}" aria-hidden="true">${a.presentation.tone==='applied'?'✓':a.presentation.tone==='incident'?'!':'↗'}</span><div class="timeline-copy"><h3>${esc(a.presentation.title)}</h3><p>${esc(a.presentation.description)}</p><small>${esc(a.workflow?displayWorkflow(a.workflow):'Controller')} · ${esc(human(a.kind))}</small>${a.presentation.proposal?`<button class="text-button" data-proposal="${esc(a.presentation.proposal)}">View linked proposal →</button>`:''}<details><summary>Technical evidence</summary><pre class="technical">${esc(JSON.stringify(a.evidence,null,2))}</pre></details></div><time>${date(a.ts,true)} IST</time></article>`).join('')||'<div class="empty">No decisions match these filters.</div>';
  $('activity-footnote').textContent=`Showing ${Math.min(100,rows.length)} matching events from ${data.activity.length} most recent records (${num(data.activity_total)} total). Routine evaluations are ${$('include-routine').checked?'included':'hidden'}.`;
}
function drawer(content) {
  const wasOpen=!$('drawer').hidden, scroll=$('drawer').scrollTop;
  const expanded=[...$('drawer-content').querySelectorAll('details')].map(d=>d.open);
  if(!wasOpen)returnFocus=document.activeElement;
  $('drawer-content').innerHTML=content;$('drawer').hidden=false;$('drawer-backdrop').hidden=false;document.body.style.overflow='hidden';
  if(wasOpen){$('drawer-content').querySelectorAll('details').forEach((d,i)=>d.open=expanded[i]||false);$('drawer').scrollTop=scroll;}
  else $('close-drawer').focus();
}
function closeDrawer() {$('drawer').hidden=true;$('drawer-backdrop').hidden=true;document.body.style.overflow='';activeDetail=null;(returnFocus?.isConnected?returnFocus:$('main')).focus();}
function showProposal(id) {
  const p=data.proposals.find(p=>p.id===id);if(!p)return;activeDetail={type:'proposal',id};
  const old=p.plan.previous_config||{};
  const diff=Object.entries(p.diff).map(([dim,value])=>{
    const before=dim==='prompt_version'?old.prompt_version:old.allocations?.default?.[dim];
    const format=v=>v==null?'Not recorded':typeof v==='object'?Object.entries(v).map(([k,x])=>`${k}: ${typeof x==='number'?pct(x):JSON.stringify(x)}`).join(' · '):v;
    return `<div class="diff-row"><strong>${esc(labels[dim]||human(dim))}</strong><div class="diff-values">Before · ${esc(format(before))}<br>Proposed · ${esc(format(value))}</div></div>`;
  }).join('');
  const verifications=data.activity.filter(a=>a.kind==='post_apply_verification'&&a.evidence.proposal_id===p.id);
  const last=verifications[0];
  drawer(`${badge(p.status)}<h2 id="drawer-title">${esc(proposalSummary(p))}</h2><p class="description">${esc(displayWorkflow(p.workflow))}</p><div class="drawer-grid"><div><span>Submitted</span><strong>${date(p.created,true)} IST</strong></div><div><span>Approval reference</span><strong>${esc(p.approval||(p.plan.auto?'Policy-permitted route':'No approval recorded'))}</strong></div><div><span>Affected enrollments</span><strong>${num(p.affected_leads)} · upper bound</strong></div><div><span>Estimated impact</span><strong>${p.impact_score? (p.impact_score*100).toFixed(1)+' pp measured lift':'Benefit not estimated'}</strong></div></div><section class="drawer-section"><h3>Configuration diff</h3>${diff||'<p>No diff recorded.</p>'}<p>Based on configuration v${esc(p.base_version)}. Only the approved full configuration may be applied.</p></section><section class="drawer-section"><h3>Approval & application</h3><p>${p.decision?`${esc(human(p.decision.evidence.status))} at ${date(p.decision.ts,true)} IST.`:'No client decision recorded.'} ${p.applied_event?`Applied at ${date(p.applied_event.ts,true)} IST as v${esc(p.applied_event.evidence.version)}.`:''}</p>${p.decision?.evidence.reasons?.length?`<p>${esc(p.decision.evidence.reasons.join('; '))}</p>`:''}<p>The API records an approval ID and actor; it does not expose a named human approver.</p></section><section class="drawer-section"><h3>Rationale & evidence</h3><p>${esc(proposalSummary(p))}</p><p>${esc(p.dry_run.evidence?.uncertainty||p.dry_run.evidence?.candidate_selection||'Recorded population measurements support this proposal. Review the evidence for its scope and uncertainty.')}</p>${p.evidence.validation_run_id?`<p>Safety validation · <strong>${esc(p.evidence.validation_run_id)}</strong>. Safety evidence does not establish engagement improvement.</p>`:''}<p>Affected enrollments may include leads whose retry cadence has expired. The dry run is aggregate evidence, not a causal replay.</p><details><summary class="text-button">Inspect full recorded evidence</summary><pre class="technical">${esc(JSON.stringify({rationale:p.rationale,dry_run:p.dry_run,evidence:p.evidence},null,2))}</pre></details></section><section class="drawer-section"><h3>What happened next</h3>${!p.applied_event&&p.status!=='applied'?'<p>No configuration was applied from this proposal.</p>':last?`<p>Latest verification · ${date(last.ts,true)} IST</p><div class="workflow-detail-grid"><div class="detail-stat"><span>Connections reviewed</span><strong>${num(last.evidence.after.connected)}</strong></div><div class="detail-stat"><span>Post-change engagement</span><strong>${pct(last.evidence.after.connected?last.evidence.after.engaged/last.evidence.after.connected:null)}</strong></div></div><p>${last.evidence.harmful?'Degradation detected; inspect the rollback proposal and validation.':'No separated-interval degradation detected in this verification.'} Temporal comparisons can be confounded.</p>`:'<p>No post-apply verification is recorded for this proposal in the recent evidence window.</p>'}</section><p class="footnote">Proposal ${esc(p.id)}</p>`);
}
function showWorkflow(id) {
  const w=workflow(id);if(!w)return;activeDetail={type:'workflow',id};const k=w.kpis;
  const related=data.proposals.filter(p=>p.workflow===id).slice(0,5);
  drawer(`<span class="badge ${w.incident?'danger':'neutral'}">${w.incident?'Open safety incident':data.state?.finished?'Run complete':'Monitoring'}</span><h2 id="drawer-title">${esc(workflowName(w))}</h2><p class="description">${esc(human(w.tenant_id))} · ${esc(w.workflow_id)}</p><p class="description">${esc(w.use_case)}</p><div class="workflow-detail-grid">${[['Lead conclusion rate',pct(k.conclusion_rate),`${num(k.concluded)} / ${num(k.uploaded)} uploaded`],['Pickup rate',pct(k.pickup_rate),`${num(k.connected)} / ${num(k.dials)} dials`],['Engagement rate',pct(k.engagement_rate),`${num(k.engaged)} / ${num(k.connected)} connected`],['Hallucination flag rate',pct(k.flag_rate),`${num(k.flags)} automated QA flags`]].map(([label,value,note])=>`<div class="detail-stat"><span>${label}</span><strong>${value}</strong><small>${note}</small></div>`).join('')}</div><section class="drawer-section"><h3>Objective & governance</h3><p>Primary KPI · ${esc(human(w.objective.primary))}</p><p>Guardrail · ${esc(Object.entries(w.objective.guardrail).map(([k,v])=>`${human(k)}: ${(v*100).toFixed(1)} pp`).join('; '))}</p><p>Client approver hours · ${num(w.governance.approver_hours[0])}:00–${num(w.governance.approver_hours[1])}:00 IST<br>Policy quota · ${num(w.governance.max_requests_per_24h)} requests / 24h<br>Current configuration · v${esc(w.config?.version||w.current_version)}${w.config?.available===false?' · details awaiting reconciliation':''}</p><p>Auto-apply · ${w.governance.auto_apply.enabled?'Permitted for '+w.governance.auto_apply.allowed_dims.map(d=>labels[d]||human(d)).map(esc).join(', '):'Disabled by client policy'}</p></section><section class="drawer-section"><h3>Recent proposals</h3>${related.map(p=>`<div class="diff-row">${badge(p.status)}<p>${esc(proposalSummary(p))}</p><button class="text-button" data-proposal="${esc(p.id)}">Inspect evidence →</button></div>`).join('')||'<p>No proposals recorded.</p>'}</section><section class="drawer-section"><h3>Measurement context</h3><p>${esc(data.definitions.outcome)}</p><p>Call KPIs cover calls made during the run, including follow-ups to earlier campaigns. The conclusion metric follows the uploaded campaign population.</p><p>${esc(data.definitions.reference)} ${esc(data.definitions.flags)}</p></section>`);
}
function navigate(target) {
  page=target;document.querySelectorAll('.page').forEach(el=>el.hidden=el.id!==target+'-page');
  document.querySelectorAll('.nav').forEach(button=>{button.classList.toggle('active',button.dataset.page===target);if(button.dataset.page===target)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');});
  $('breadcrumb').textContent=target==='activity'?'Decision history':human(target);$('page-title').textContent=titles[target][0];$('page-description').textContent=titles[target][1];
  history.replaceState(null,'','#'+target);if(data)render();
}
async function load() {
  if(fetching)return;fetching=true;$('refresh').disabled=true;
  try {
    const response=await fetch('/api/dashboard',{signal:AbortSignal.timeout(30000),cache:'no-store'});
    if(!response.ok)throw new Error('HTTP '+response.status);
    data=await response.json();lastUpdate=new Date();fillFilters();render();if(activeDetail){if(activeDetail.type==='proposal')showProposal(activeDetail.id);else showWorkflow(activeDetail.id);}$('error').hidden=true;
    $('connection').innerHTML='<i></i>Connected';$('connection').classList.remove('offline');
  } catch(error) {
    $('error').textContent=`Unable to refresh controller data. ${data?'The last successful snapshot remains visible.':'Check the database path and server log.'} Retry with the refresh button.`;$('error').hidden=false;
    $('connection').innerHTML='<i></i>Disconnected';$('connection').classList.add('offline');
    if(!data){$('loading').innerHTML='<h2>Workspace unavailable</h2><p>No data has been substituted. Refresh once the controller database is available.</p>';}
  } finally {fetching=false;$('refresh').disabled=false;}
}
function exportRate(value) {return value==null?'':Number((100*value).toFixed(4));}
function exportReport() {
  if(!data)return;
  const csvCell=value=>'"'+String(typeof value==='string'&&/^[=+@-]/.test(value)?"'"+value:value??'').replaceAll('"','""')+'"';
  const rows=[['Workflow','Tenant','Period start IST','Period end IST','Uploaded','Concluded','Conclusion rate (%)','Dials','Connected','Engaged','Pickup rate (%)','Engagement rate (%)','QA flags','QA flag rate (%)'],...selectedWorkflows().map(w=>[w.workflow_id,w.tenant_id,data.period.start,data.period.end,w.kpis.uploaded,w.kpis.concluded,exportRate(w.kpis.conclusion_rate),w.kpis.dials,w.kpis.connected,w.kpis.engaged,exportRate(w.kpis.pickup_rate),exportRate(w.kpis.engagement_rate),w.kpis.flags,exportRate(w.kpis.flag_rate)])];
  const blob=new Blob(['\uFEFF'+rows.map(row=>row.map(csvCell).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download='formi-outcomes-'+(data.state?.scenario||'snapshot')+'.csv';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);$('announcement').textContent='Workflow report exported. Rates are stored as percentages in the CSV.';
}
document.addEventListener('click',event=>{
  const button=event.target.closest('button');if(!button)return;
  if(button.dataset.page)navigate(button.dataset.page);
  if(button.dataset.goto)navigate(button.dataset.goto);
  if(button.dataset.proposal)showProposal(button.dataset.proposal);
  if(button.dataset.workflow)showWorkflow(button.dataset.workflow);
  if(button.dataset.chart){chartMetric=button.dataset.chart;document.querySelectorAll('[data-chart]').forEach(b=>{b.classList.toggle('selected',b===button);b.setAttribute('aria-pressed',String(b===button));});if(data)renderChart(selectedWorkflows());}
});
$('tenant').addEventListener('change',()=>{fillFilters();render();});$('workflow').addEventListener('change',render);$('search').addEventListener('input',render);$('proposal-status').addEventListener('change',render);$('include-routine').addEventListener('change',render);$('refresh').addEventListener('click',load);$('export').addEventListener('click',exportReport);$('close-drawer').addEventListener('click',closeDrawer);$('drawer-backdrop').addEventListener('click',closeDrawer);
document.addEventListener('keydown',event=>{
  if($('drawer').hidden)return;
  if(event.key==='Escape')closeDrawer();
  if(event.key==='Tab'){
    const all=[...$('drawer').querySelectorAll('button,a,input,select,summary,[tabindex="0"]')].filter(el=>el.getClientRects().length);
    const first=all[0],last=all.at(-1);
    if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}
  }
});
window.addEventListener('hashchange',()=>{const target=location.hash.slice(1);if(Object.hasOwn(titles,target))navigate(target);});
navigate(Object.hasOwn(titles,location.hash.slice(1))?location.hash.slice(1):'overview');load();setInterval(load,15000);
