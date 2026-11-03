import {pairs,metrics} from './engine.mjs?v=0.3.0';
const H=3600000;
export const kstDay=t=>new Date(t+9*H).toISOString().slice(0,10);
export function upcoming(d,region,now=Date.now()){
 const candidates=d.forecasts.filter(f=>f.region===region&&Date.parse(f.issuedAt)<=now&&Date.parse(f.validAt)>now);
 const issue=candidates.map(f=>f.issuedAt).sort().at(-1)||null;
 const stale=!issue||now-Date.parse(issue)>6*H||!d.generatedAt||now-Date.parse(d.generatedAt)>6*H;
 const rows=stale?[]:candidates.filter(f=>f.issuedAt===issue).sort((a,b)=>a.validAt.localeCompare(b.validAt));
 const start=Date.parse(kstDay(now)+'T00:00:00+09:00');
 return {issue,stale,days:Array.from({length:7},(_,i)=>{const date=kstDay(start+i*24*H);return {date,rows:rows.filter(f=>f.validAt.slice(0,10)===date)}})};
}
export function reference(d,region,hour=null){
 if(!d?.period||d.methodStatus!=='experimental-api-publication-time')return null;
 const rows=pairs(d,region,Date.parse(d.period.end),d.period.days).filter(f=>hour===null||f.validAt.slice(11,13)===hour);
 const m=metrics(rows);return {...m,enough:m.n>=30,label:d.period.label,start:d.period.start,end:d.period.end};
}
export function evidenceFor(f,d,region){
 const lead=(Date.parse(f.validAt)-Date.parse(f.issuedAt))/H;
 if(lead!==24)return {supported:false,reason:'예측 간격에 맞는 과거 성적 부족',lead};
 const r=reference(d,region,f.validAt.slice(11,13));
 return {supported:!!r?.enough,lead,reference:r};
}
