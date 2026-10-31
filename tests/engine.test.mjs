import{test}from'node:test';import assert from'node:assert/strict';import{validate,pairs,metrics,demo}from'../dist/engine.mjs';
const now=Date.parse('2026-11-01T12:00:00+09:00'),f={region:'yeoju',issuedAt:'2026-10-30T11:00:00+09:00',validAt:'2026-10-31T11:00:00+09:00',temp:20,pop:80},o={region:'yeoju',validAt:f.validAt,temp:18,rainMm:1};const data=()=>({schemaVersion:1,forecasts:[{...f}],observations:[{...o}]});
test('known MAE, bias and Brier; wet event hit',()=>{const m=metrics(pairs(validate(data()),'yeoju',now));assert.equal(m.mae,2);assert.equal(m.bias,2);assert.ok(Math.abs(m.brier-.04)<1e-10);assert.equal(m.hit,1)});
test('missing observations and separate missing measurements excluded',()=>{const d=data();d.observations[0].rainMm=null;let m=metrics(pairs(d,'yeoju',now));assert.equal(m.n,1);assert.equal(m.rainN,0);assert.equal(m.brier,null);d.observations=[];assert.equal(pairs(d,'yeoju',now).length,0)});
test('no mixing horizons, locations, future or out of range',()=>{const d=data();d.forecasts[0].issuedAt='2026-10-30T08:00:00+09:00';assert.equal(pairs(d,'yeoju',now).length,0);assert.equal(pairs(data(),'busan',now).length,0);assert.equal(pairs(data(),'yeoju',now-2*86400000).length,0);assert.equal(pairs(data(),'yeoju',now+31*86400000).length,0)});
test('reject malformed, duplicate, negative rain, strings and null values',()=>{for(const mutate of[d=>d.forecasts.push({...f}),d=>d.observations[0].rainMm=-999,d=>d.forecasts[0].pop=101,d=>d.forecasts[0].temp='20',d=>d.forecasts[0].temp=null,d=>d.forecasts[0].validAt='bad',d=>d.observations.push({...o})]){const d=data();mutate(d);assert.throws(()=>validate(d))}});
test('rain threshold and four outcomes',()=>{const rows=[{pop:50,observation:{temp:1,rainMm:.1}},{pop:49,observation:{temp:1,rainMm:1}},{pop:50,observation:{temp:1,rainMm:0}},{pop:0,observation:{temp:1,rainMm:0}}].map(r=>({...r,temp:1}));const m=metrics(rows);for(const k of['hit','miss','falseAlarm','correctDry'])assert.equal(m[k],1)});
test('demo separate, valid and nonempty',()=>{const d=demo(now);assert.equal(d.forecasts.length,720);assert.ok(pairs(d,'yeoju',now).length>200);assert.equal(demo(now).forecasts[0].temp,d.forecasts[0].temp)});

test('official archived period has 240 exact 24h pairs per configured grid',async()=>{
 const fs=await import('node:fs/promises');
 const d=validate(JSON.parse(await fs.readFile(new URL('../dist/history-2026-09.json',import.meta.url),'utf8')));
 const end=Date.parse(d.period.end);
 for(const region of ['yeoju','seoul','busan']){
  const rows=pairs(d,region,end);assert.equal(rows.length,240);assert.equal(metrics(rows).n,240);assert.equal(metrics(rows).rainN,240);
  assert.equal(rows[0].validAt,'2026-09-01T11:00:00+09:00');assert.equal(rows.at(-1).validAt,d.period.end);
  assert.equal(pairs(d,region,Date.parse('2026-11-01T08:00:00+09:00')).length,0);
 }
});
