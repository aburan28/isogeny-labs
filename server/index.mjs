import { resolve } from 'node:path';
import Redis from 'ioredis';
import { database } from './db.mjs';
import { inquiryStore } from './store.mjs';
import { createApp } from './app.mjs';
const production = process.env.NODE_ENV === 'production';
const origins = (process.env.ALLOWED_ORIGINS || 'http://localhost:3000,http://127.0.0.1:3000').split(',');
for (const value of origins) { const url = new URL(value); if (url.origin !== value || (production && url.protocol !== 'https:')) throw new Error('ALLOWED_ORIGINS must contain exact origins; production requires HTTPS'); }
if (production && (!process.env.REDIS_URL || !process.env.ALLOWED_ORIGINS || (process.env.RATE_LIMIT_SECRET || '').length < 32)) throw new Error('Production requires Redis, explicit origins and a RATE_LIMIT_SECRET of at least 32 characters');
const redis = process.env.REDIS_URL ? new Redis(process.env.REDIS_URL, { maxRetriesPerRequest: 1, connectTimeout: 5000 }) : undefined;
if (redis) redis.on('error', () => {}); // Readiness/requests expose availability without printing connection details.
const db = database();
const app = await createApp({ store: inquiryStore(db), root: resolve('_site'), origins, redis,
  rateSecret: process.env.RATE_LIMIT_SECRET || 'local-development-only',
  trustProxy: process.env.TRUST_PROXY ? process.env.TRUST_PROXY.split(',') : false,
  apiOrigin: process.env.CONTACT_API_URL ? new URL(process.env.CONTACT_API_URL).origin : undefined,
  logger: true });
await app.listen({ host: '0.0.0.0', port: Number(process.env.PORT || 3000) });
for (const signal of ['SIGINT','SIGTERM']) process.on(signal, async () => { await app.close(); await db.end(); if (redis) await redis.quit(); process.exit(0); });
