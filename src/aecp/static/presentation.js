"use strict";
// Pure projections. These helpers never authorize, execute, settle or reconcile.
(function (root) {
  const escape = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  function integer(value) {
    if(typeof value === "number" && Number.isSafeInteger(value)) return BigInt(value);
    if(typeof value === "string" && /^-?\d+$/.test(value)) return BigInt(value);
    throw new Error("Expected an exact integer accounting value");
  }
  const number = value => value === null || value === undefined ? "—" : integer(value).toLocaleString();
  const names = {reserved:"Liability reserved",dispatched:"Dispatch claimed",adapter_receipt:"Trusted receipt persisted",settled:"Actual cost settled",unresolved:"Uncertain result retained",released:"Authority released",reservation_denied:"Budget admission denied",policy_denied:"Policy admission denied",adapter_error:"Adapter result unavailable",liability_bound_breached:"Quote bound breached"};
  function timeline(events) {
    return `<ol class="event-timeline">${events.filter(e=>names[e.kind]).map(e=>{
      const p = typeof e.payload === "string" ? JSON.parse(e.payload) : e.payload;
      const detail = e.kind === "reserved" ? `${number(p.upper_bound)} modeled units held before dispatch` :
        e.kind === "adapter_receipt" ? `${number(p.actual_units)} modeled units · ${p.source}` :
        e.kind === "settled" ? `${number(p.actual)} modeled units charged` :
        e.kind === "reservation_denied" || e.kind === "policy_denied" ? p.reason || "No funded execution authorized" :
        e.kind === "unresolved" ? "No trusted receipt; the possible liability is not refunded" :
        e.kind === "dispatched" ? "One winner has claimed permission to call the adapter" : "Inspect the durable event below";
      return `<li><span class="sequence">#${escape(e.seq)}</span><div><strong>${escape(names[e.kind])}</strong><small>${escape(detail)}</small></div></li>`;
    }).join("")}</ol>`;
  }
  const api = {escape,integer,number,timeline};
  if(typeof module !== "undefined" && module.exports) module.exports=api;
  else root.AECPPresentation=api;
})(typeof window === "undefined" ? globalThis : window);
