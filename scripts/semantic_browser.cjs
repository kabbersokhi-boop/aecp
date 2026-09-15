"use strict";
const fs = require("node:fs");
const assert = require("node:assert/strict");
const {chromium} = require(process.env.AECP_PLAYWRIGHT_MODULE || "@playwright/test");

(async()=>{
  const base=process.env.AECP_URL||"http://127.0.0.1:8767";
  const expectedCases=Number(process.env.AECP_SEMANTIC_CASES||36);
  const screenshots=process.env.AECP_SCREENSHOT_DIR||"docs/reports/screenshots";
  const evidenceOutput=process.env.AECP_EVIDENCE_OUTPUT||"var/evidence-v21/semantic-browser.json";
  const capabilities=JSON.parse(fs.readFileSync(process.env.AECP_TOKENS||"var/semantic-dashboard-capabilities.json"));
  const browser=await chromium.launch({headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1512,height:1050}});
    const errors=[];
    page.on("pageerror",error=>errors.push(error.message));
    await page.goto(base);
    await page.locator("#token").fill(capabilities.operator.token);
    await page.locator("#connect button").click();
    await page.locator("#workspace").waitFor({state:"visible"});
    await page.locator('[data-tab="semantic"]').click();
    const response=await page.request.get(base+"/api/v1/semantic-evidence",{headers:{Authorization:"Bearer "+capabilities.operator.token}});
    const snapshot=await response.json();
    assert.equal(snapshot.cases.length,expectedCases);
    assert.equal(await page.locator("[data-semantic]").count(),expectedCases);
    const index=snapshot.cases.findIndex(item=>item.actions.some(action=>action.execution?.resource==="nim_chat"));
    assert(index>=0);
    await page.locator(`[data-semantic="${index}"]`).click();
    await page.locator("#semantic-inspector details").evaluateAll(nodes=>nodes.forEach(node=>node.open=true));
    const inspector=await page.locator("#semantic-inspector").innerText();
    for(const field of ["permitted_at_decision","planning_execution","schema_valid","provider_usage","actual_cash_spend","quote_metadata"]){
      assert(inspector.includes(field),field);
    }
    assert((await page.locator("#semantic").innerText()).includes("$0"));
    assert((await page.locator("#admission-state").innerText()).includes("rejected before authorization"));
    fs.mkdirSync(screenshots,{recursive:true});
    await page.locator("#semantic-inspector details").evaluateAll(nodes=>nodes.forEach(node=>node.open=false));
    await page.screenshot({path:screenshots+"/semantic-desktop.png",fullPage:true});
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    await page.screenshot({path:screenshots+"/semantic-mobile.png",fullPage:true});
    await page.reload();
    await page.locator("#workspace").waitFor({state:"visible"});
    await page.locator('[data-tab="semantic"]').click();
    assert.equal(await page.locator("[data-semantic]").count(),expectedCases);
    assert.deepEqual(errors,[]);
    const attempts=snapshot.cases.flatMap(item=>item.actions).filter(action=>action.execution?.resource==="nim_chat");
    const evidence={cases:snapshot.cases.length,workload:snapshot.workload,provider_attempts:attempts.length,
      provider_receipts:attempts.filter(action=>action.execution?.receipt).length,page_errors:errors,
      mobile_overflow:false,source:"persisted frozen held-out NIM study",refreshed:true};
    fs.writeFileSync(evidenceOutput,JSON.stringify(evidence,null,2)+"\n");
    console.log(JSON.stringify(evidence));
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
