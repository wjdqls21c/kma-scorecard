export {REGIONS} from './regions.mjs?v=0.2.0';
import {REGIONS} from './regions.mjs?v=0.2.0';
const H=3600000;
const time=s=>typeof s==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:00:00\+09:00$/.test(s)&&Number.isFinite(Date.parse(s))&&new Date(Date.parse(s)+9*H).toISOString().slice(0,19)+'+09:00'===s;
const number=(n,a,b)=>typeof n==='number'&&Number.isFinite(n)&&n>=a&&n<=b;
export function validate(d){
 if(d?.schemaVersion!==1||!Array.isArray(d.forecasts)||!Array.isArray(d.observations))throw Error('지원하지 않는 자료 형식입니다. schemaVersion 1 JSON이 필요합니다.');
 if(d.forecasts.length>150000||d.observations.length>150000)throw Error('자료가 너무 큽니다. 최대 각 150,000행입니다.');
 const ids=new Set(REGIONS.map(r=>r.id)),fs=new Set(),os=new Set();
 for(const f of d.forecasts){const k=[f.region,f.issuedAt,f.validAt].join('|');if(!ids.has(f.region)||!time(f.issuedAt)||!time(f.validAt)||Date.parse(f.validAt)<=Date.parse(f.issuedAt)||!number(f.temp,-90,65)||!number(f.pop,0,100)||fs.has(k))throw Error('예보에 잘못된 값이나 중복이 있습니다.');fs.add(k);}
 for(const o of d.observations){const k=[o.region,o.validAt].join('|');if(!ids.has(o.region)||!time(o.validAt)||!(o.temp===null||number(o.temp,-90,65))||!(o.rainMm===null||number(o.rainMm,0,1000))||os.has(k))throw Error('관측에 잘못된 값이나 중복이 있습니다.');os.add(k);}
 return d;
}
export function pairs(d,region,now=Date.now(),days=30){const obs=new Map(d.observations.filter(o=>o.region===region).map(o=>[o.validAt,o]));return d.forecasts.filter(f=>f.region===region&&Date.parse(f.validAt)-Date.parse(f.issuedAt)===24*H&&Number(f.issuedAt.slice(11,13))%3===2&&Date.parse(f.validAt)<=now&&Date.parse(f.validAt)>now-days*24*H).map(f=>({...f,observation:obs.get(f.validAt)})).filter(f=>f.observation).sort((a,b)=>a.validAt.localeCompare(b.validAt));}
export function metrics(rows){const t=rows.filter(r=>r.observation.temp!==null),p=rows.filter(r=>r.observation.rainMm!==null),mean=arr=>arr.length?arr.reduce((a,b)=>a+b,0)/arr.length:null;let hit=0,miss=0,falseAlarm=0,correctDry=0;for(const r of p){const yes=r.pop>=50,wet=r.observation.rainMm>=0.1;if(yes&&wet)hit++;else if(!yes&&wet)miss++;else if(yes)falseAlarm++;else correctDry++;}const within1=t.filter(r=>Math.abs(r.temp-r.observation.temp)<=1).length,within2=t.filter(r=>Math.abs(r.temp-r.observation.temp)<=2).length;return {within1,within2,within1Rate:t.length?within1/t.length:null,within2Rate:t.length?within2/t.length:null,n:t.length,rainN:p.length,mae:mean(t.map(r=>Math.abs(r.temp-r.observation.temp))),bias:mean(t.map(r=>r.temp-r.observation.temp)),brier:mean(p.map(r=>(r.pop/100-Number(r.observation.rainMm>=0.1))**2)),hit,miss,falseAlarm,correctDry};}
export function demo(now=Date.now()){const forecasts=[],observations=[];const end=new Date(now+9*H);end.setUTCMinutes(0,0,0);for(const [j,r]of REGIONS.entries())for(let i=240;i>=1;i--){const v=new Date(+end-9*H-i*3*H);if(v.getUTCHours()%3!==2) v.setUTCHours(v.getUTCHours()+(2-v.getUTCHours()%3+3)%3);const stamp=t=>new Date(t+9*H).toISOString().slice(0,13)+':00:00+09:00';const validAt=stamp(+v),issuedAt=stamp(+v-24*H),temp=12+5*Math.sin(i/7)+(j%3)*2,pop=i%7<2?70:20;forecasts.push({region:r.id,issuedAt,validAt,temp:Math.round(temp),pop});observations.push({region:r.id,validAt,temp:Math.round((temp+Math.sin(i*2+j)*2)*10)/10,rainMm:i%8<2?1:0});}return validate({schemaVersion:1,kind:'synthetic',forecasts,observations});}

export function timingAssessment(minutes){
 if(typeof minutes!=='number'||!Number.isFinite(minutes))return {status:'unknown',label:'미확인'};
 const gap=Math.abs(minutes);
 return gap<=60?{status:'within',label:'허용 범위'}:gap<120?{status:'borderline',label:'경계'}:{status:'warning',label:'주의'};
}
