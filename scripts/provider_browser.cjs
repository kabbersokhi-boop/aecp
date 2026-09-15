"use strict";
const fs = require("node:fs");
const assert = require("node:assert/strict");
const {chromium} = require(process.env.AECP_PLAYWRIGHT_MODULE || "@playwright/test");

(async () => {
  const base = process.env.AECP_URL || "http://127.0.0.1:8766";
  const capabilities = JSON.parse(fs.readFileSync(process.env.AECP_TOKENS || "var/live-v2-final.capabilities.json"));
  const browser = await chromium.launch({headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1512,height:1050}});
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    await page.goto(base);
    await page.locator("#token").fill(capabilities.operator.token);
    await page.locator("#connect button").click();
    await page.locator("#workspace").waitFor({state:"visible"});
    await page.locator('[data-tab="provider"]').click();
    const response = await page.request.get(base + "/api/v1/provider-executions", {
      headers:{Authorization:"Bearer " + capabilities.operator.token}
    });
    const snapshot = await response.json();
    assert(snapshot.requests.some(request => request.result?.provider_usage?.total_tokens > 0));
    assert(snapshot.requests.some(request => request.reservation.state === "UNRESOLVED"));
    assert.equal(await page.locator("[data-provider]").count(), snapshot.requests.length);
    assert((await page.locator("#provider-numbers").innerText()).includes("$0"));
    const settled = snapshot.requests.find(request => request.outcome);
    await page.locator(`[data-provider="${settled.id}"]`).click();
    assert((await page.locator("#provider-inspector").innerText()).includes("provider_reported"));
    fs.mkdirSync("docs/reports/screenshots", {recursive:true});
    await page.screenshot({path:"docs/reports/screenshots/provider-v2.png",fullPage:true});
    const unknown = snapshot.requests.find(request => request.reservation.state === "UNRESOLVED");
    await page.locator(`[data-provider="${unknown.id}"]`).click();
    assert((await page.locator("#provider-inspector").innerText()).includes("UNRESOLVED"));
    await page.reload();
    await page.locator("#workspace").waitFor({state:"visible"});
    await page.locator('[data-tab="provider"]').click();
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await page.screenshot({path:"docs/reports/screenshots/provider-v2-mobile.png",fullPage:true});
    assert.deepEqual(errors, []);
    const evidence = {requests:snapshot.requests.length, source:"persisted real NIM executions",
      provider_tokens:snapshot.requests.reduce((total, request)=>total+(request.result?.provider_usage?.total_tokens||0),0),
      unresolved:snapshot.requests.filter(request=>request.reservation.state==="UNRESOLVED").length,
      actual_cash_spend:0, page_errors:errors, mobile_overflow:false, refreshed:true};
    fs.writeFileSync("var/evidence-v2/browser.json", JSON.stringify(evidence,null,2)+"\n");
    console.log(JSON.stringify(evidence));
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
