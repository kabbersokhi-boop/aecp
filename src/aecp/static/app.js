"use strict";
let token = sessionStorage.getItem("aecp-token") || "";
let selectedRun = "";
let selectedTask = "";
let snapshot = null;
let runs = [];
let busy = false;
let providerSnapshot = {requests:[]};
let selectedProvider = "";
let semanticSnapshot = {cases:[],authorities:{}};
let selectedSemantic = "";
const element = id => document.getElementById(id);
const escapeHTML = value => String(value ?? "").replace(/[&<>"']/g, character => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[character]));
const number = value => (typeof value==="string"&&/^-?\d+$/.test(value)?BigInt(value):Number(value||0)).toLocaleString();
const json = value => `<pre>${escapeHTML(JSON.stringify(value, null, 2))}</pre>`;
const badge = state => `<span class="pill ${["DENIED","FAILED","ABANDONED","CAPACITY_DENIED","REJECTED"].includes(state)?"bad":["UNRESOLVED","PENDING","ESCROWED","ALLOCATED","OPEN","ABSTAIN","ESCALATE"].includes(state)?"warn":""}">${escapeHTML(state)}</span>`;
const table = (headers, rows) => `<div class="table-scroll"><table><thead><tr>${headers.map(header=>`<th>${escapeHTML(header)}</th>`).join("")}</tr></thead><tbody>${rows.length?rows.map(row=>`<tr>${row.map(cell=>`<td>${cell}</td>`).join("")}</tr>`).join(""):`<tr><td colspan="${headers.length}">No records yet.</td></tr>`}</tbody></table></div>`;
async function api(path, body) {
  const response = await fetch(path, {method:body?"POST":"GET",headers:{"Authorization":`Bearer ${token}`,"Content-Type":"application/json"},body:body?JSON.stringify(body):undefined});
  const data = await response.json();
  if (!response.ok) throw new Error(`${data.error}${data.detail?`: ${data.detail}`:""}`);
  return data;
}
function error(message) { element("error").textContent=message; element("error").hidden=false; setTimeout(()=>element("error").hidden=true,9000); }
async function refresh() {
  if (!token || busy) return;
  runs = await api("/api/v1/runs");
  const system = await api("/api/v1/system");
  providerSnapshot = await api("/api/v1/provider-executions");
  renderProvider();
  semanticSnapshot = await api("/api/v1/semantic-evidence");
  const admission = await api("/api/v1/admission");
  element("admission-state").textContent=`Gateway admission · ${admission.active}/${admission.limit} active connections · ${admission.rejected} rejected before authorization · no application waiting queue; admitted handlers may wait on the mutation lock.`;
  renderSemantic();
  element("system-totals").textContent=`SYSTEM TOTALS · ${number(system.funded)} funded / ${number(system.spent)} settled / ${number(system.reserved)} reserved / ${number(system.unresolved)} unresolved SIM_COST_MICRO across ${system.roots.length} root scopes. Cards below show the selected experiment.`;
  if (!selectedRun && runs.length) selectedRun=runs[0].id;
  element("run-select").innerHTML=runs.map(run=>`<option value="${escapeHTML(run.id)}" ${run.id===selectedRun?"selected":""}>${escapeHTML(run.id)}</option>`).join("");
  element("login").hidden=true; element("workspace").hidden=false;
  if (selectedRun) { snapshot=await api(`/api/v1/runs/${encodeURIComponent(selectedRun)}`); render(); }
  else { element("run-meta").textContent=semanticSnapshot.cases.length?"Persisted semantic workload available in Semantic autonomy; no simulation selected.":"No experiments yet. Create a run to begin."; element("numbers").innerHTML=""; element("integrity").textContent="No selected simulation audit · inspect persisted semantic authority and execution records."; }
  renderComparison();
}
function render() {
  const {run,account,metrics}=snapshot;
  element("run-meta").textContent=`${run.config.environment_version} · seed ${run.config.seed} · ${run.config.scheduler} / ${run.config.style} · corpus ${run.config.corpus_hash.slice(0,14)}`;
  element("run-state").textContent=`Tick ${run.checkpoint.tick} · ${run.checkpoint.finished?"Complete":"Paused at durable checkpoint"}`;
  element("step").disabled=run.checkpoint.finished; element("complete").disabled=run.checkpoint.finished;
  const values=[["Funded authority",account.funded,"Parent cap · SIM_COST_MICRO"],["Settled cost",account.spent,"Modeled operations, including coordination"],["Reserved liability",account.reserved,"Includes unresolved exposure"],["Unresolved exposure",metrics.unresolved_exposure,"No timeout refunds"],["Available headroom",account.headroom,"Funded − settled − reserved"]];
  element("numbers").innerHTML=values.map(([title,value,subtitle])=>`<article class="number ${title==="Unresolved exposure"&&value?"warning":""}"><span>${title}</span><strong>${number(value)}</strong><small>${subtitle}</small></article>`).join("");
  element("exposure-note").textContent=`Verified utility ${number(metrics.verified_value)} / ${number(metrics.total_task_value)} · ${metrics.verified_tasks} verified · ${metrics.failed_tasks} failed · ${metrics.abandoned_tasks} abandoned/denied · coordination ${metrics.coordination_cost} modeled units · actual provider cash spend: 0. ${metrics.unresolved_exposure?"Uncertain dispatches remain fully reserved across restart.":"No unresolved external-model liabilities in this run."}`;
  element("cases").innerHTML=snapshot.traces.map(trace=>`<tr class="case-row ${trace.task_id===selectedTask?"active":""}" data-task="${escapeHTML(trace.task_id)}"><td><button class="case-link" data-task="${escapeHTML(trace.task_id)}">${escapeHTML(trace.task_id)}</button><small>${escapeHTML(trace.observation.counterparty)}</small></td><td>${escapeHTML(trace.agent_id.split("/").at(-1))}</td><td>${escapeHTML(trace.resource)}</td><td>${badge(trace.status)}</td><td>${number(trace.verified_value)}<small>of ${number(trace.observation.value)}</small></td></tr>`).join("")||'<tr><td colspan="5">Step the run to generate decisions.</td></tr>';
  element("agent-table").innerHTML=table(["Agent / parent","Status","Own cap","Spent / reserved","Effective headroom","Beliefs"],snapshot.agents.map(agent=>[`${escapeHTML(agent.id)}<small>${escapeHTML(agent.parent_id)}</small>`,badge(agent.status==="FROZEN"?"FROZEN":agent.lifecycle),number(agent.funded),`${number(agent.spent)} / ${number(agent.reserved)}`,number(agent.effective_headroom),json(run.checkpoint.beliefs[agent.id]||{})]));
  element("market-table").innerHTML=`<p>${snapshot.market.consistent?"Journal reconciles":"JOURNAL MISMATCH"} · global issued ${number(snapshot.market.issued)} / conserved ${number(snapshot.market.total)} MARKET_CREDIT</p>`+table(["Auction / bidder","Own bid","Escrow / allocation"],snapshot.market.bids.map(bid=>[`${escapeHTML(bid.auction_id)}<small>${escapeHTML(bid.agent_id)}</small>`,number(bid.price),badge(bid.state)]));
  element("reviews").innerHTML=table(["Operation approval","Reviewer","State"],snapshot.approvals.map(approval=>[`${escapeHTML(approval.id)}<small>expires tick ${approval.expires_at}</small>`,escapeHTML(approval.reviewer||"Unavailable / pending"),badge(approval.state)]));
  element("expenditures").innerHTML=table(["Case / attempt","Resource","Upper bound","Settled","State"],snapshot.holds.map(hold=>[`<button class="case-link" data-task="${escapeHTML(hold.task_id)}">${escapeHTML(hold.task_id)}</button><small>${escapeHTML(hold.id.split("/").slice(-2).join("/"))}</small>`,escapeHTML(hold.resource),number(hold.upper_bound),hold.actual===null?"—":number(hold.actual),badge(hold.state)]));
  element("integrity").textContent=`${snapshot.audit.consistent?"✓ Ledger projections reconcile":"⚠ Ledger mismatch"} · ${snapshot.audit.within_funding?"Within funded authority":"FUNDING BREACH"} · digest ${snapshot.digest.slice(0,16)}`;
  if(selectedTask) inspect(selectedTask);
}
function inspect(taskId) {
  selectedTask=taskId;
  const trace=snapshot.traces.find(item=>item.task_id===taskId);
  if(!trace){element("inspector").textContent="Choose a case in this experiment.";return;}
  const holds=snapshot.holds.filter(hold=>hold.task_id===taskId);
  const events=snapshot.events.filter(event=>holds.some(hold=>hold.id===event.hold_id)||JSON.parse(event.payload).task_id===taskId);
  const steps=[
    ["01 · Case & permitted evidence",`${escapeHTML(trace.task_id)} · invoice ${(trace.observation.invoice_cents/100).toFixed(2)} synthetic currency units · deadline tick ${trace.observation.deadline}`,trace.observation],
    ["02 · Agent decision",`${escapeHTML(trace.agent_id)} · ${escapeHTML(trace.decision.resource)} · estimated utility ${trace.decision.expected_value}`,trace.decision.explanation],
    ["03 · Authorization & capacity",trace.approval_id?escapeHTML(trace.approval_id):"No mandatory authorization required",{allocation:trace.allocation,denial:trace.denial||null,requests:snapshot.requests.filter(request=>request.task_id===taskId)}],
    ["04 · Reservation → dispatch → settlement",`${number(holds.reduce((total,hold)=>total+(hold.actual||0),0))} settled SIM_COST_MICRO`,holds],
    ["05 · Verified outcome",`${escapeHTML(trace.proposed_resolution||"No resolution")} · ${escapeHTML(trace.status)} · utility ${trace.verified_value}`,trace.verification],
    ["06 · Durable event history",`${events.length} ledger events · includes attempt identifiers`,events.map(event=>({...event,payload:JSON.parse(event.payload)}))]
  ];
  element("inspector").innerHTML=steps.map(([title,detail,data])=>`<div class="trace-step"><h3>${title}</h3><p>${detail}</p><details><summary>Inspect structured evidence</summary>${json(data)}</details></div>`).join("");
}
function renderComparison(){element("comparison").innerHTML=table(["Run / configuration","Verified utility / all value","Modeled cost","Coordination","Unresolved","Coverage / fairness"],runs.map(run=>[`${escapeHTML(run.id)}<small>${escapeHTML(run.config.scheduler)} / ${escapeHTML(run.config.style)} · seed ${run.config.seed} · budget ${run.config.budget}</small><small>corpus ${run.config.corpus_hash.slice(0,12)}</small>`,`${number(run.metrics.verified_value)} / ${number(run.metrics.total_task_value)}<span class="bar"><progress value="${run.metrics.verified_value}" max="${run.metrics.total_task_value}"></progress></span>`,number(run.metrics.modeled_cost),number(run.metrics.coordination_cost),number(run.metrics.unresolved_exposure),`${run.metrics.verified_tasks}/${run.config.count} verified<small>Jain access ${run.metrics.jain_access_index.toFixed(3)}</small>`]));}
function renderProvider(){
  const requests=providerSnapshot.requests;
  const tokens=requests.reduce((total,request)=>total+(request.result?.provider_usage?.total_tokens||0),0);
  const modeled=requests.reduce((total,request)=>total+(request.reservation.actual||0),0);
  const exposure=requests.filter(request=>["DISPATCHED","UNRESOLVED"].includes(request.reservation.state)).reduce((total,request)=>total+request.reservation.upper_bound,0);
  element("provider-numbers").innerHTML=[["Actual cash spend","$0","Free prototype; not an invoice"],["Provider tokens",number(tokens),"Reported usage; missing usage excluded"],["Modeled settled cost",number(modeled),"SIM_COST_MICRO · not dollars"],["Unresolved liability",number(exposure),"Never refunded by timeout"]].map(([label,value,note])=>`<div class="number"><span>${label}</span><strong>${value}</strong><small>${note}</small></div>`).join("");
  element("provider-table").innerHTML=table(["Task / agent","Provider / model","Usage tokens","Modeled cost / bound","State / verification"],requests.map(request=>[`<button class="case-link" data-provider="${escapeHTML(request.id)}">${escapeHTML(request.task_id)}</button><small>${escapeHTML(request.agent_id)}</small>`,`${escapeHTML(request.result?.provider||request.quote_metadata?.details?.provider)}<small>${escapeHTML(request.quote_metadata?.details?.model)}</small>`,number(request.result?.provider_usage?.total_tokens),`${number(request.reservation.actual)} / ${number(request.reservation.upper_bound)}`,`${badge(request.reservation.state)}<small>${request.outcome?(request.outcome.verified?"Verified":"Not verified"):"No evaluated outcome"}</small>`]));
  if(selectedProvider)inspectProvider(selectedProvider);
}
function inspectProvider(identity){
  selectedProvider=identity;
  const request=providerSnapshot.requests.find(request=>request.id===identity);
  if(!request)return;
  const entries=[["Task and permitted observations",request.observation],["Agent request and authorization",{agent:request.agent_id,task:request.task_id,operation:request.operation,parameters:JSON.parse(request.parameters),fingerprint:request.fingerprint,policy:request.policy_version}],["Versioned liability quote",request.quote_metadata],["Dispatch and usage receipt",{reservation:request.reservation,receipt:request.receipt,result:request.result}],["Independent verification",request.outcome],["Durable provenance",request.events]];
  element("provider-inspector").innerHTML=entries.map(([title,data])=>`<details open><summary>${title}</summary>${json(data)}</details>`).join("");
}
element("provider-table").addEventListener("click",event=>{const button=event.target.closest("[data-provider]");if(button)inspectProvider(button.dataset.provider);});
function renderSemantic(){
  const cases=semanticSnapshot.cases;
  const rows=Object.entries(semanticSnapshot.authorities).sort(([left],[right])=>left.localeCompare(right)).map(([agent,authority])=>{
    const owned=cases.filter(item=>item.agent===agent);
    const actions=owned.flatMap(item=>item.actions);
    const receipts=actions.map(action=>action.result?.resource_result).filter(result=>result?.provider_usage);
    return [escapeHTML(agent),`${owned.filter(item=>item.outcome?.verified).length} / ${owned.length}`,number(owned.reduce((total,item)=>total+(item.outcome?.verified_value||0),0)),`${number(authority.spent)} / ${number(authority.reserved)}`,`${receipts.length} / ${receipts.filter(item=>item.schema_valid).length}`,number(receipts.reduce((total,item)=>total+item.provider_usage.total_tokens,0)),`${owned.filter(item=>item.outcome?.disposition==="abstain").length} / ${owned.filter(item=>item.outcome?.disposition==="escalate").length}`];
  });
  element("semantic-comparison").innerHTML=table(["Scoped policy","Verified / all cases","Verified value","Modeled spent / reserved","Provider receipts / schema valid","Provider tokens","Abstained / escalated"],rows);
  element("semantic-cases").innerHTML=table(["Task / policy","State","Verified value","Action count"],cases.map((item,index)=>[`<button class="case-link" data-semantic="${index}">${escapeHTML(item.task)}</button><small>${escapeHTML(item.agent)}</small>`,badge(item.observation.status),number(item.outcome?.verified_value),number(item.actions.length)]));
  if(selectedSemantic)inspectSemantic(Number(selectedSemantic)-1);
}
function inspectSemantic(index){
  const item=semanticSnapshot.cases[index];
  if(!item)return;
  selectedSemantic=String(index+1);
  const sections=[["Permitted evidence and authority",{observation:item.observation,authority:semanticSnapshot.authorities[item.agent],corpus:item.corpus}],["Independent outcome (not schema compliance)",item.outcome],...item.actions.map((action,index)=>[`${index+1} · ${action.proposal.action} · ${action.result?.denied||action.execution?.reservation?.state||"planning only"}`,action])];
  element("semantic-inspector").innerHTML=sections.map(([title,data])=>`<details><summary>${escapeHTML(title)}</summary>${json(data)}</details>`).join("");
}
element("semantic-cases").addEventListener("click",event=>{const button=event.target.closest("[data-semantic]");if(button)inspectSemantic(Number(button.dataset.semantic));});
async function mutate(path,body){if(busy)return;busy=true;try{await api(path,body);}finally{busy=false;}await refresh();}
element("connect").addEventListener("submit",async event=>{event.preventDefault();token=element("token").value.trim();try{await refresh();sessionStorage.setItem("aecp-token",token);element("token").value="";}catch(failure){error(failure.message);}});
element("disconnect").addEventListener("click",()=>{sessionStorage.removeItem("aecp-token");token="";element("workspace").hidden=true;element("login").hidden=false;});
element("run-select").addEventListener("change",event=>{selectedRun=event.target.value;selectedTask="";refresh().catch(failure=>error(failure.message));});
element("new-run").addEventListener("submit",event=>{event.preventDefault();selectedRun=`${element("scenario").value}-${element("scheduler").value}-${Date.now()}`;selectedTask="";mutate("/api/v1/admin/runs",{run_id:selectedRun,scenario:element("scenario").value,scheduler:element("scheduler").value,style:element("policy").value,seed:Number(element("seed").value),budget:Number(element("budget").value)}).catch(failure=>error(failure.message));});
for(const action of ["step","complete"])element(action).addEventListener("click",()=>{if(selectedRun)mutate(`/api/v1/admin/${action}`,{run_id:selectedRun}).catch(failure=>error(failure.message));});
element("cases").addEventListener("click",event=>{const row=event.target.closest("[data-task]");if(row)inspect(row.dataset.task);});
element("expenditures").addEventListener("click",event=>{const row=event.target.closest("[data-task]");if(row){document.querySelector('[data-tab="activity"]').click();inspect(row.dataset.task);element("inspector").scrollIntoView({behavior:"smooth",block:"start"});}});
document.querySelectorAll("[data-tab]").forEach(button=>button.addEventListener("click",()=>{document.querySelectorAll(".view").forEach(view=>view.hidden=view.id!==button.dataset.tab);document.querySelectorAll("[data-tab]").forEach(tab=>tab.classList.toggle("selected",tab===button));}));
if(token)refresh().catch(failure=>error(failure.message));
setInterval(()=>{if(!document.hidden&&token)refresh().catch(failure=>error(failure.message));},5000);
