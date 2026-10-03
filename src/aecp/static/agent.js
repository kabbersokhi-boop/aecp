"use strict";
const P=window.AECPPresentation;
const el=id=>document.getElementById(id);
let agentToken="", submitted=null, busy=false, lastRequest=null;
const requestedApprovals=new Set();
function alertError(e){el("agent-error").textContent=e.message;el("agent-error").hidden=false;}
async function call(path,body){
  const response=await fetch(path,{method:body?"POST":"GET",headers:{Authorization:`Bearer ${agentToken}`,"Content-Type":"application/json"},body:body?JSON.stringify(body):undefined});
  const data=await response.json();return {status:response.status,ok:response.ok,data};
}
async function budget(){
  const r=await call("/api/v1/me/budget");if(!r.ok)throw new Error(r.data.error);
  const b=r.data.budget;
  el("agent-identity").textContent=`${b.id} · child of ${b.parent_id || "root"} · ${b.status}`;
  const cards=[["Own funded cap",b.funded],["Settled cost",b.spent],["Reserved liability",b.reserved],["Effective headroom",b.effective_headroom]];
  el("agent-budget").innerHTML=cards.map(([name,value])=>`<article class="number"><span>${P.escape(name)}</span><strong>${P.number(value)}</strong><small>Modeled units · ${P.escape(r.data.unit)}</small></article>`).join("");
}
function safeAmount(s){const n=Number(s);if(!/^\d+$/.test(s.trim())||!Number.isSafeInteger(n))throw new Error("Amounts must be nonnegative safe integers");return n;}
function body(){return {request_id:el("request-id").value.trim(),task_id:el("request-task").value.trim(),operation:el("request-operation").value,resource:el("request-resource").value,parameters:{invoice_cents:safeAmount(el("request-invoice").value),payments:el("request-payments").value.split(",").map(s=>safeAmount(s.trim()))}};}
function renderTrace(trace){
  lastRequest=trace.request;
  el("agent-timeline").innerHTML=`<h3>Persisted event order</h3><p class="muted">${P.escape(trace.source)}</p>`+P.timeline(trace.events);
  el("cancel-request").disabled=lastRequest?.reservation.state!=="RESERVED";
}
async function inspect(id){
  const r=await call("/api/v1/me/trace/"+encodeURIComponent(id));
  if(r.ok){renderTrace(r.data);el("agent-trace-raw").hidden=false;el("agent-trace-raw").querySelector("pre").textContent=JSON.stringify(r.data,null,2);}
  return r;
}
function lock(value){busy=value;el("submit-request").disabled=value;el("replay-request").disabled=value||!submitted;el("new-attempt").disabled=value;el("agent-disconnect").disabled=value;el("request-approval").disabled=true;el("cancel-request").disabled=value||lastRequest?.reservation.state!=="RESERVED";}
async function execute(request){
  if(busy)return;lock(true);lastRequest=null;
  el("agent-error").hidden=true;el("approval-status").textContent="";el("request-approval").disabled=true;el("cancel-request").disabled=true;
  el("agent-timeline").innerHTML="";el("agent-raw").hidden=true;el("agent-trace-raw").hidden=true;
  let definitive=false;
  try{
    const r=await call("/api/v1/resource-requests",request);
    definitive=true;
    const state=r.ok?r.data.reservation.state:r.data.error;
    el("agent-response").innerHTML=`<div class="response-summary ${r.ok?"":"denied"}"><span class="eyebrow">HTTP ${r.status} · ${r.ok?"ACTUAL API RESULT":"STRUCTURED DENIAL"}</span><h2>${P.escape(state)}</h2><p>Attempt: ${P.escape(request.request_id)}</p><p>${r.ok?`Result: ${P.escape(r.data.result?.resolution || "No definitive result")}`:P.escape(r.data.detail || "No execution authorized by this response.")}</p></div>`;
    if(r.ok){const h=r.data.reservation;el("agent-response").innerHTML+=`<div class="receipt-facts"><span>Reserved ceiling <strong>${P.number(h.upper_bound)}</strong></span><span>Settled actual <strong>${P.number(h.actual)}</strong></span><span>Receipt source <strong>${P.escape(r.data.receipt?.source || "No trusted receipt")}</strong></span></div>`;}
    if(r.data.error==="APPROVAL_REQUIRED"&&requestedApprovals.has(request.request_id))el("approval-status").textContent="Approval already requested. Retry the identical action after a separate reviewer decision; do not recreate its approval.";
    el("agent-raw").hidden=false;el("agent-raw").querySelector("pre").textContent=JSON.stringify(r,null,2);
    await inspect(request.request_id);el("inspect-id").value=request.request_id;await budget();
    lock(false);el("request-approval").disabled=r.data.error!=="APPROVAL_REQUIRED"||requestedApprovals.has(request.request_id);
  }catch(e){if(!definitive)el("agent-response").innerHTML='<div class="response-summary denied"><h2>TRANSPORT AMBIGUITY</h2><p>No definitive response. Inspect the original ID before considering a separately funded retry.</p></div>';alertError(new Error((definitive?"The API result above is definitive; follow-up inspection failed: ":"")+e.message));}
  finally{if(busy)lock(false);}
}
el("agent-connect").addEventListener("submit",async e=>{e.preventDefault();agentToken=el("agent-token").value.trim();el("agent-token").value="";try{await budget();el("agent-login").hidden=true;el("agent-workspace").hidden=false;el("agent-error").hidden=true;}catch(err){agentToken="";alertError(err);}});
el("agent-disconnect").addEventListener("click",()=>{if(busy)return;agentToken="";submitted=null;lastRequest=null;requestedApprovals.clear();for(const id of ["agent-response","agent-timeline","agent-budget","approval-status"])el(id).textContent="";for(const id of ["agent-raw","agent-trace-raw"]){el(id).querySelector("pre").textContent="";el(id).hidden=true;}el("agent-workspace").hidden=true;el("agent-login").hidden=false;lock(false);});
el("agent-request").addEventListener("submit",e=>{e.preventDefault();if(busy)return;try{submitted=body();execute(submitted);}catch(err){alertError(err);}});
el("new-attempt").addEventListener("click",()=>{el("request-id").value="agent-"+crypto.randomUUID();});
el("new-attempt").click();
el("replay-request").addEventListener("click",()=>{if(submitted)execute(submitted);});
el("inspect-attempt").addEventListener("submit",async e=>{e.preventDefault();if(busy)return;lock(true);try{const r=await inspect(el("inspect-id").value.trim());if(!r.ok)throw new Error(r.data.error);el("agent-response").innerHTML=`<div class="response-summary"><span class="eyebrow">READ ONLY · PERSISTED TRACE</span><h2>${P.escape(r.data.request?.reservation.state || "DENIED BEFORE DISPATCH")}</h2></div>`;await budget();}catch(err){alertError(err);}finally{lock(false);}});
el("request-approval").addEventListener("click",async()=>{
  if(!submitted||requestedApprovals.has(submitted.request_id)||busy)return;
  const action=submitted;lock(true);
  try{const r=await call("/api/v1/approval-requests",{...action,approval_id:"review-"+action.request_id});if(!r.ok)throw new Error(r.data.error);requestedApprovals.add(action.request_id);el("approval-status").textContent=`${r.data.state} · separate reviewer authority required. This agent cannot approve itself. Recreating this approval is not an automatic retry.`;}catch(e){alertError(e);}finally{lock(false);}
});
el("cancel-request").addEventListener("click",async()=>{if(!lastRequest||busy)return;const id=lastRequest.id;lock(true);try{const r=await call("/api/v1/requests/cancel",{request_id:id});if(!r.ok)throw new Error(r.data.error);await inspect(id);await budget();}catch(e){alertError(e);}finally{lock(false);}});
