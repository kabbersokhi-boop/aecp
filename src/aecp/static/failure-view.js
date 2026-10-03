"use strict";
(function(){
 const P=window.AECPPresentation,el=id=>document.getElementById(id);
 let report=null;
 const titles={normal_settlement:"01 · Normal settlement",executed_response_lost:"02 · Executed, response lost",independently_funded_retry:"03 · Each retry needs separate authority",worker_dies_after_provider_execution:"04 · Worker dies after provider execution",durable_receipt_before_worker_death:"05 · Durable receipt survives worker death",expiry_cannot_erase_uncertainty:"06 · Expiry cannot refund uncertainty",trusted_reconciliation:"07 · Trusted charged / no-charge reconciliation",concurrent_parent_authority:"Shared-parent budget contention",duplicate_immutable_identity:"Duplicate immutable request",changed_parameters_conflict:"Changed parameters rejected",provider_bound_breach:"Declared quote breached: record and freeze",provider_idempotency_modes:"Explicit provider idempotency modes"};
 const descriptions={normal_settlement:"A delivered receipt permits settlement; the unused ceiling is released.",executed_response_lost:"The provider journal records execution and a charge, but no delivered response. AECP retains the full declared liability rather than assuming a free failure.",independently_funded_retry:"Two potentially chargeable attempts each retain a reservation. The third attempt is denied when funded headroom is exhausted.",worker_dies_after_provider_execution:"The worker exits after the provider executes. Reopening the ledger preserves UNRESOLVED liability; no automatic redispatch is justified.",durable_receipt_before_worker_death:"The receipt was durable before the worker died. Recovery can settle that evidence without issuing another provider execution.",expiry_cannot_erase_uncertainty:"Elapsed time and cancellation do not prove no charge. The original uncertain attempt remains reserved.",trusted_reconciliation:"Only explicitly exposed, trusted provider evidence permits settling a charged attempt or releasing an independently proven no-charge attempt.",provider_bound_breach:"The provider exceeded its declaration. AECP records the full charge, freezes affected authority and preserves the breach; this is not a successful funding guarantee.",provider_idempotency_modes:"Provider deduplication is explicitly configured. A correlation identifier alone is not exactly-once external execution."};
 function validate(data){
  if(data.version!=="failure-conformance.v1"||data.simulated_cost_unit!=="SIM_COST_MICRO"||!data.scenarios||typeof data.scenarios!=="object"||Array.isArray(data.scenarios))throw Error("Expected a failure-conformance.v1 report, not a capability or arbitrary JSON file");
  if(Object.keys(data.scenarios).some(k=>!Object.hasOwn(titles,k)))throw Error("Unknown scenario; use the versioned conformance format");
  for(const s of Object.values(data.scenarios)){
   if(s.budget)for(const k of ["funded","spent","reserved","headroom"])P.integer(s.budget[k]);
   if(s.provider_journal && (!Array.isArray(s.provider_journal)||s.provider_journal.length>1000))throw Error("Invalid provider journal");
   for(const row of s.provider_journal||[])for(const k of ["charge","received","executed","delivered"])P.integer(row[k]);
  }
  for(const k of ["external_provider_calls","simulated_provider_executions"])P.integer(data[k]);
 }
 function table(headers,rows){return `<div class="table-scroll"><table><thead><tr>${headers.map(h=>`<th>${P.escape(h)}</th>`).join("")}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(c=>`<td>${P.escape(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;}
 function render(){
  const key=el("failure-scenario").value,s=report.scenarios[key],b=s.budget;
  const mode=el("failure-provenance").value==="historical"?"HISTORICAL FROZEN REPORT":"LOCAL EXPORTED REPORT";
  const figures=b?[["Funded authority",b.funded],["Settled modeled cost",b.spent],["Reserved liability",b.reserved],["Available headroom",b.headroom]]:[];
  el("failure-numbers").innerHTML=figures.map(([name,v])=>`<article class="number"><span>${P.escape(name)}</span><strong>${P.number(v)}</strong><small>SIM_COST_MICRO · this scenario only</small></article>`).join("");
  const rows=s.provider_journal||[];
  el("failure-provider").innerHTML=rows.length?table(["Attempt","Executed","Receipt delivered","Modeled charge"],rows.map(r=>[r.attempt_id,r.executed?"Yes":"No",r.delivered?"Yes":"No",P.number(r.charge)])):'<p class="muted">No provider journal in this scenario; inspect its shared-authority audit below.</p>';
  let facts=[...Object.entries(s).filter(([k])=>!["budget","audit","metrics","provider_journal","unaffected_audit"].includes(k)).map(([k,v])=>[k.replaceAll("_"," "),typeof v==="object"?JSON.stringify(v):String(v)])];
  if(b)facts.push(["Account state",b.status],["Modeled unit",b.unit]);
  if(s.audit)facts.push(["Ledger projections consistent",String(s.audit.consistent)],["Within funded authority",String(s.audit.within_funding)],["Bound breaches recorded",String(s.audit.bound_breach_count)]);
  el("failure-ledger").innerHTML=table(["Stored fact","Value"],facts);
  el("failure-result").innerHTML=`<p class="eyebrow">${mode} · SEPARATE CONTROLLED SCENARIO</p><p class="story-note">${P.escape(descriptions[key]||"Inspect the independent journal and accounting records for this controlled boundary.")}</p><p class="muted">${P.number(report.external_provider_calls)} external provider calls · ${P.number(report.simulated_provider_executions)} simulated provider executions across the complete suite. This file is evidence to inspect, not a live accounting authority or industry certification.</p>`;
  el("failure-raw").textContent=JSON.stringify(s,null,2);
 }
 el("failure-file").addEventListener("change",async e=>{
  el("failure-error").hidden=true;el("failure-report").hidden=true;report=null;
  try{
   const file=e.target.files[0];if(!file)return;if(file.size>2*1024*1024)throw Error("Report exceeds the 2 MiB inspection limit");
   const bytes=await file.arrayBuffer(),data=JSON.parse(new TextDecoder().decode(bytes));validate(data);
   const hash=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",bytes))).map(b=>b.toString(16).padStart(2,"0")).join("");
   report=data;el("failure-source").textContent=`${file.name} · ${file.size.toLocaleString()} bytes · SHA-256 ${hash}. Export time is not attested; a hash identifies the file, not its truth.`;
   el("failure-provenance").value="local";
   el("failure-scenario").innerHTML=Object.entries(titles).filter(([key])=>Object.hasOwn(report.scenarios,key)).map(([key,label])=>`<option value="${key}">${P.escape(label)}</option>`).join("");
   if(!el("failure-scenario").options.length)throw Error("No controlled scenarios present");
   render();el("failure-report").hidden=false;
  }catch(err){report=null;el("failure-source").textContent="No valid conformance report loaded.";el("failure-error").textContent=err.message;el("failure-error").hidden=false;}
 });
 el("failure-scenario").addEventListener("change",()=>{if(report)render();});
 el("failure-provenance").addEventListener("change",()=>{if(report)render();});
})();
