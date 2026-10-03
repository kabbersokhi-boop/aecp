"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const P=require("../src/aecp/static/presentation.js");
test("accounting integers remain exact",()=>{
 assert.equal(P.integer("9007199254740993"),9007199254740993n);
 assert.equal(P.number(null),"—");
 for(const value of [9007199254740992,0.5,"1.5",true])assert.throws(()=>P.integer(value));
});
test("durable event text is escaped and keeps sequence",()=>{
 const html=P.timeline([{seq:4,kind:"reserved",payload:{upper_bound:4}},{seq:5,kind:"policy_denied",payload:{reason:"<script>alert(1)</script>"}}]);
 assert(html.includes("#4"));assert(html.includes("#5"));
 assert(html.includes("&lt;script&gt;"));assert(!html.includes("<script>"));
 assert(P.timeline([{kind:"unresolved",seq:6,payload:{}}]).includes("not refunded"));
});
