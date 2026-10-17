import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { resolve } from 'node:path';
import { database } from '../server/db.mjs';
import Redis from 'ioredis';
import { PGlite } from '@electric-sql/pglite';
import { createApp } from '../server/app.mjs';
import { inquiryStore, migrate } from '../server/store.mjs';
let db;
before(async () => { db = process.env.DATABASE_URL ? database() : new PGlite(); await migrate(db); });
after(async () => { await (db.end?.() || db.close()); });
const valid = () => ({name:'Example Person',email:'person@example.invalid',company:'Example Enterprise',service:'Security review',message:'We would like a review of our planned protocol integration.',consent:true,website:''});
const make = async (options={}) => createApp({store:inquiryStore(db),root:resolve('_site'),origins:['http://localhost:3000'],rateSecret:'testing-only',rateMax:100,...options});
function send(app, {body=valid(),key=randomUUID(),origin='http://localhost:3000',...other}={}) {
 return app.inject({method:'POST',url:'/api/inquiries',headers:{origin,'content-type':'application/json','idempotency-key':key},payload:body,...other});
}
test('stores normalized inquiry once and acknowledges only after insert', async () => {
 const app=await make(); const key=randomUUID(), body=valid(); body.email='PERSON@example.invalid';
 try {
  const one=await send(app,{key,body}), two=await send(app,{key,body});
  assert.equal(one.statusCode,201);assert.equal(two.statusCode,200);assert.deepEqual(one.json(),{id:key});
  const rows=await db.query('SELECT * FROM enterprise_inquiries WHERE id=$1',[key]);
  assert.equal(rows.rows.length,1);assert.equal(rows.rows[0].email,'person@example.invalid');assert.equal(rows.rows[0].consent,true);
  assert.equal((await send(app,{key,body:{...body,message:'A different project description for the same identifier.'}})).statusCode,409);
 } finally {await app.close();}
});
test('rejects invalid fields, absent consent, traps, cross-origin and oversized input', async () => {
 const app=await make(); try {
  for(const body of [{...valid(),consent:false},{...valid(),email:'invalid'},{...valid(),message:'short'},{...valid(),service:'bad'},{...valid(),website:'spam'}]) assert.equal((await send(app,{body})).statusCode,400);
  assert.equal((await send(app,{origin:'https://untrusted.invalid'})).statusCode,403);
  assert.equal((await send(app,{key:'bad'})).statusCode,400);
  assert.equal((await send(app,{body:{...valid(),message:'x'.repeat(20000)}})).statusCode,413);
  assert.equal((await app.inject({method:'POST',url:'/api/inquiries',payload:'malformed',headers:{'content-type':'application/json'}})).statusCode,400);
 } finally {await app.close();}
});
test('does not claim success if storage is unavailable; readiness fails', async () => {
 const app=await make({store:{save:async()=>{throw Error('sensitive internal error')},ready:async()=>{throw Error('offline')}}});
 try { const response=await send(app);assert.equal(response.statusCode,503);assert(!response.body.includes('sensitive'));assert.equal((await app.inject('/readyz')).statusCode,503); } finally {await app.close();}
});
test('limits requests without trusting arbitrary forwarded client IPs', async () => {
 const app=await make({rateMax:1});try {
  assert.equal((await send(app)).statusCode,201);
  const second=await send(app,{headers:{origin:'http://localhost:3000','content-type':'application/json','idempotency-key':randomUUID(),'x-forwarded-for':'198.51.100.20'}});
  assert.equal(second.statusCode,429);assert(second.headers['retry-after']);
 } finally {await app.close();}
});
test('serves only built public files and never exposes an inquiry-list endpoint', async () => {
 const app=await make();try {
  for(const path of ['/api/inquiries','/server/migrations/001_inquiries.sql','/package.json']) assert.equal((await app.inject(path)).statusCode,404);
  assert.equal((await app.inject('/.env')).statusCode,403);
  const response=await app.inject('/contact/index.html');assert.equal(response.statusCode,200);assert(response.headers['content-security-policy'].includes("frame-ancestors 'none'"));
 } finally {await app.close();}
});

test('Redis shares rate limits between two API instances', {skip: !process.env.REDIS_URL}, async () => {
 const redis = new Redis(process.env.REDIS_URL); const rateSecret=randomUUID();
 const first=await make({redis,rateMax:1,rateSecret}), second=await make({redis,rateMax:1,rateSecret});
 try { assert.equal((await send(first)).statusCode,201); assert.equal((await send(second)).statusCode,429); }
 finally {await first.close();await second.close();await redis.quit();}
});
