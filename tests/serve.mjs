// Test-only server: real PostgreSQL in CI; embedded PostgreSQL for local browser tests.
import { resolve } from 'node:path';
import { PGlite } from '@electric-sql/pglite';
import Redis from 'ioredis';
import { database } from '../server/db.mjs';
import { migrate, inquiryStore } from '../server/store.mjs';
import { createApp } from '../server/app.mjs';
const db=process.env.DATABASE_URL ? database() : new PGlite();
await migrate(db);
const redis=process.env.REDIS_URL ? new Redis(process.env.REDIS_URL) : undefined;
const app=await createApp({store:inquiryStore(db),root:resolve('_site'),origins:['http://127.0.0.1:3100'],redis,rateSecret:'test-rate-limits',rateMax:1000});
await app.listen({host:'127.0.0.1',port:3100});
for(const signal of ['SIGINT','SIGTERM'])process.on(signal,async()=>{await app.close();await (db.end?.() || db.close());if(redis)await redis.quit();process.exit(0)});
