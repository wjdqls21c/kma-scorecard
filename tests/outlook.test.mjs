import {test} from 'node:test';import assert from 'node:assert/strict';import {upcoming,reference,evidenceFor} from '../dist/outlook.mjs';
const now=Date.parse('2026-11-03T12:00:00+09:00');
const f=(issuedAt,validAt)=>({region:'seoul',issuedAt,validAt,temp:20,pop:20});
test('latest issue only, Seoul only, future only; missing days remain empty',()=>{
 const d={generatedAt:'2026-11-03T11:45:00+09:00',forecasts:[f('2026-11-03T08:00:00+09:00','2026-11-04T08:00:00+09:00'),f('2026-11-03T11:00:00+09:00','2026-11-04T11:00:00+09:00'),f('2026-11-03T11:00:00+09:00','2026-11-03T11:00:00+09:00'),{...f('2026-11-03T11:00:00+09:00','2026-11-04T14:00:00+09:00'),region:'busan'}]};
 const o=upcoming(d,'seoul',now);assert.equal(o.days.length,7);assert.equal(o.days[0].date,'2026-11-03');assert.equal(o.days[1].rows.length,1);assert.equal(o.days[6].rows.length,0);assert.equal(o.stale,false);
});
test('old generated data or old issue never displayed as current forecast',()=>{
 const f1=f('2026-11-03T05:00:00+09:00','2026-11-04T05:00:00+09:00');
 for(const d of [{generatedAt:'2026-11-03T11:50:00+09:00',forecasts:[f1]},{generatedAt:'2026-11-02T11:50:00+09:00',forecasts:[f('2026-11-03T11:00:00+09:00','2026-11-04T11:00:00+09:00')]}]){assert.equal(upcoming(d,'seoul',now).stale,true);assert.ok(upcoming(d,'seoul',now).days.every(x=>!x.rows.length));}
});
test('historical score requires API source, 30 temperatures and matching exact 24h horizon',()=>{
 const d={methodStatus:'experimental-api-publication-time',period:{start:'2026-10-01T00:00:00+09:00',end:'2026-10-31T23:59:59+09:00',days:31,label:'10월'},forecasts:[],observations:[]};
 for(let i=1;i<=31;i++){const day=String(i).padStart(2,'0'),validAt='2026-10-'+day+'T11:00:00+09:00',issuedAt=new Date(Date.parse(validAt)-15*3600000).toISOString().slice(0,19)+'+09:00';d.forecasts.push(f(issuedAt,validAt));d.observations.push({region:'seoul',validAt,temp:19,rainMm:0});}
 assert.equal(reference(d,'seoul','11').n,31);assert.equal(reference(d,'seoul','11').within2,31);
 assert.equal(evidenceFor(f('2026-11-03T11:00:00+09:00','2026-11-04T11:00:00+09:00'),d,'seoul').supported,true);
 assert.equal(evidenceFor(f('2026-11-03T11:00:00+09:00','2026-11-04T14:00:00+09:00'),d,'seoul').supported,false);
 assert.equal(evidenceFor(f('2026-11-03T11:00:00+09:00','2026-11-04T11:00:00+09:00'),d,'busan').supported,false);
 d.observations=d.observations.slice(0,29);assert.equal(reference(d,'seoul','11').enough,false);
 d.methodStatus='experimental-unvalidated';assert.equal(reference(d,'seoul'),null);
});
