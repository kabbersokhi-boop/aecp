"use strict";
// Uses an isolated local demo database. Never point this at an operational instance.
const fs=require("node:fs"),assert=require("node:assert/strict");
const {chromium}=require(process.env.AECP_PLAYWRIGHT_MODULE||"@playwright/test");
(async()=>{
 const base=process.env.AECP_URL||"http://127.0.0.1:8769";
 const caps=JSON.parse(fs.readFileSync(process.env.AECP_TOKENS,"utf8"));
 const browser=await chromium.launch({headless:true,...(process.env.AECP_CHROME?{executablePath:process.env.AECP_CHROME}:{})});
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1000}}),errors=[];
  page.on("pageerror",e=>errors.push(e.message));
  const post=async(path,data)=>{const r=await page.request.post(base+path,{headers:{Authorization:`Bearer ${caps.operator.token}`},data});assert(r.ok());return r.json();};
  const identity=await post("/api/v1/admin/agents",{name:`browser-${Date.now()}`,budget:8});
  for(const [task,operation] of [["external-invoice-1","reconcile"],["protected-payment","release_payment"]])await post("/api/v1/admin/tasks",{agent_id:identity.agent_id,task_id:task,required_operation:operation});
  await page.goto(base+"/agent.html");await page.locator("#agent-token").fill(identity.token);await page.locator("#agent-connect button").click();await page.locator("#agent-workspace").waitFor({state:"visible"});
  await page.locator("#request-id").fill(`browser-success-${Date.now()}`);
  await page.route("**/api/v1/me/budget",route=>route.abort());
  await page.locator("#submit-request").click();await page.waitForFunction(()=>document.querySelector("#agent-response").textContent.includes("SETTLED")&&!document.querySelector("#submit-request").disabled);
  assert((await page.locator("#agent-error").innerText()).includes("API result above is definitive"));
  assert((await page.locator("#agent-raw pre").textContent()).includes('"status": 200'));
  assert((await page.locator("#agent-trace-raw pre").textContent()).includes('"events"'));
  await page.unroute("**/api/v1/me/budget");
  const before=await page.locator("#agent-timeline").innerText();assert(before.includes("Trusted receipt persisted"));assert(before.includes("Actual cost settled"));
  await page.locator("#replay-request").click();await page.waitForFunction(()=>!document.querySelector("#submit-request").disabled);assert.equal(await page.locator("#agent-timeline").innerText(),before);
  await page.locator("#request-id").fill(`browser-protected-${Date.now()}`);await page.locator("#request-task").fill("protected-payment");await page.locator("#request-operation").selectOption("release_payment");
  await page.locator("#submit-request").click();await page.waitForFunction(()=>!document.querySelector("#request-approval").disabled);assert((await page.locator("#agent-response").innerText()).includes("APPROVAL_REQUIRED"));
  await page.locator("#request-approval").click();await page.waitForFunction(()=>document.querySelector("#approval-status").textContent.includes("PENDING"));
  await page.locator("#request-task").fill("external-invoice-1");await page.locator("#request-operation").selectOption("reconcile");
  for(let n=0;n<2;n++){await page.locator("#request-id").fill(`browser-cap-${n}-${Date.now()}`);await page.locator("#submit-request").click();await page.waitForFunction(()=>!document.querySelector("#submit-request").disabled);}
  assert((await page.locator("#agent-response").innerText()).includes("BUDGET_EXHAUSTED"));assert((await page.locator("#agent-timeline").innerText()).includes("Budget admission denied"));
  assert(!await page.evaluate(token=>document.body.innerText.includes(token),identity.token));assert.equal(await page.evaluate(()=>sessionStorage.getItem("agent-token")),null);
  const shots=process.env.AECP_SCREENSHOT_DIR;if(shots){fs.mkdirSync(shots,{recursive:true});await page.screenshot({path:shots+"/agent-denial.png",fullPage:true});}
  await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,"agent mobile overflow");
  await page.goto(base);await page.locator("#token").fill(caps.viewer.token);await page.locator("#connect button").click();await page.locator("#workspace").waitFor({state:"visible"});await page.locator('[data-tab="failure"]').click();
  await page.locator("#failure-file").setInputFiles({name:"not-a-report.json",mimeType:"application/json",buffer:Buffer.from(JSON.stringify({version:"capabilities"}))});await page.locator("#failure-error").waitFor({state:"visible"});assert(!await page.locator("#failure-report").isVisible());
  await page.locator("#failure-file").setInputFiles(process.env.AECP_FAILURE_REPORT);await page.locator("#failure-report").waitFor({state:"visible"});
  assert.equal(await page.locator("#failure-scenario option").count(),12);
  for(const scenario of ["executed_response_lost","independently_funded_retry","worker_dies_after_provider_execution","trusted_reconciliation","provider_bound_breach"]){await page.locator("#failure-scenario").selectOption(scenario);assert((await page.locator("#failure-result").innerText()).includes("SEPARATE CONTROLLED SCENARIO"));}
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,"failure mobile overflow");
  await page.setViewportSize({width:1600,height:1000});await page.locator("#failure-scenario").selectOption("executed_response_lost");if(shots)await page.screenshot({path:shots+"/failure-evidence.png",fullPage:true});
  assert.deepEqual(errors,[]);console.log(JSON.stringify({agent_success:true,identical_replay_no_extra_events:true,mandatory_approval_pending:true,budget_denial_durable:true,invalid_report_rejected:true,controlled_scenarios:12,mobile_overflow:false,page_errors:errors,external_provider_calls:0}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
