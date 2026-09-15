"use strict";
const fs = require("node:fs");
const assert = require("node:assert/strict");
const {chromium} = require(process.env.AECP_PLAYWRIGHT_MODULE || "@playwright/test");

(async () => {
  const base = process.env.AECP_URL || "http://127.0.0.1:8765";
  const capabilities = JSON.parse(fs.readFileSync(process.env.AECP_TOKENS || "var/local-capabilities.json", "utf8"));
  const screenshots = process.env.AECP_SCREENSHOT_DIR || "docs/reports/screenshots";
  const browser = await chromium.launch({headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1512,height:1050}});
    const errors = [];
    page.on("pageerror", failure => errors.push(failure.message));
    page.on("console", message => { if(message.type()==="error") errors.push(message.text()); });
    await page.goto(base);
    await page.locator("#token").fill(capabilities.operator.token);
    await page.locator("#connect button").click();
    await page.locator("#workspace").waitFor({state:"visible"});
    await page.locator("#scenario").selectOption("outage");
    await page.locator("#new-run button").click();
    await page.waitForFunction(() => document.querySelector("#run-state").textContent.includes("Tick 0"));
    await page.locator("#step").click();
    await page.waitForFunction(() => document.querySelector("#run-state").textContent.includes("Tick 1"));
    await page.locator("#complete").click();
    await page.waitForFunction(() => document.querySelector("#run-state").textContent.includes("Complete"));
    const identity = await page.locator("#run-select").inputValue();
    const response = await page.request.get(`${base}/api/v1/runs/${encodeURIComponent(identity)}`, {
      headers:{Authorization:`Bearer ${capabilities.operator.token}`}
    });
    const snapshot = await response.json();
    assert(snapshot.metrics.unresolved_exposure > 0);
    assert.equal(await page.locator("#cases tr").count(), snapshot.traces.length);
    const unresolved = snapshot.traces.find(trace=>trace.status==="UNRESOLVED").task_id;
    await page.locator("#cases").getByRole("button", {name:unresolved,exact:true}).click();
    await page.locator("#inspector details").nth(3).locator("summary").click();
    assert((await page.locator("#inspector").innerText()).includes("UNRESOLVED"));
    fs.mkdirSync(screenshots, {recursive:true});
    await page.screenshot({path:screenshots + "/financial-debugger.png",fullPage:true});
    for (const tab of ["agents","market","experiments"]) {
      await page.locator(`[data-tab="${tab}"]`).click();
      assert(await page.locator(`#${tab}`).isVisible());
    }
    const registration=await page.request.post(base+"/api/v1/admin/semantic-cases",{
      headers:{Authorization:`Bearer ${capabilities.operator.token}`},
      data:{agent_id:"gateway/passive",split:"development",workload:"v3"}
    });
    assert(registration.ok());
    const tasksResponse=await page.request.get(base+"/api/v1/semantic/tasks",{
      headers:{Authorization:`Bearer ${capabilities.passive.token}`}
    });
    const tasks=await tasksResponse.json();
    assert.equal(tasks.length,36);
    assert(tasks.every(task=>task.workload_version==="semantic-finops.v3.frozen-1"));
    assert(tasks.every(task=>task.valid_actions));
    const checked=await page.request.post(base+"/api/v1/semantic/actions",{
      headers:{Authorization:`Bearer ${capabilities.passive.token}`},
      data:{request_id:`browser-${identity}`,task_id:tasks[0].task_id,action:"check",payment_ids:[],reason:"Offline browser provenance regression."}
    });
    assert(checked.ok());
    await page.reload();
    await page.locator("#workspace").waitFor({state:"visible"});
    await page.locator('[data-tab="semantic"]').click();
    assert.equal(await page.locator("[data-semantic]").count(),36);
    await page.locator('[data-semantic="0"]').click();
    await page.locator("#semantic-inspector details").evaluateAll(nodes=>nodes.forEach(node=>node.open=true));
    assert((await page.locator("#semantic-inspector").innerText()).includes("planning_execution"));
    await page.reload();
    await page.locator("#workspace").waitFor({state:"visible"});
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:screenshots + "/financial-debugger-mobile.png",fullPage:true});
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
    assert.equal(overflow, false, "mobile document overflow");
    assert.deepEqual(errors, []);
    const evidence = {browser:"Chromium",run_id:identity,digest:snapshot.digest,
      cases:snapshot.traces.length,unresolved_exposure:snapshot.metrics.unresolved_exposure,
      console_errors:errors,mobile_overflow:overflow,views_checked:5,semantic_cases:36,
      semantic_workload:"semantic-finops.v3.frozen-1",live_provider_calls:0,refresh_preserved_state:true};
    fs.writeFileSync("var/browser-smoke.json",JSON.stringify(evidence,null,2)+"\n");
    console.log(JSON.stringify(evidence));
  } finally { await browser.close(); }
})().catch(failure=>{console.error(failure);process.exitCode=1;});
