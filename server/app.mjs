import Fastify, { LogController } from 'fastify';
import staticFiles from '@fastify/static';
import cors from '@fastify/cors';
import helmet from '@fastify/helmet';
import rateLimit from '@fastify/rate-limit';
import { createHash, createHmac } from 'node:crypto';
import { z } from 'zod';

const inquirySchema = z.object({
  name: z.string().trim().min(2).max(120),
  email: z.email().max(254).transform(v => v.toLowerCase()),
  company: z.string().trim().min(2).max(160),
  service: z.enum(['Security review', 'Post-quantum migration', 'Cryptographic research', 'Implementation review', 'Other']),
  message: z.string().trim().min(20).max(5000),
  consent: z.literal(true),
  website: z.string().max(200).default('')
}).strict();

export async function createApp({ store, root, origins, redis, rateSecret, trustProxy = false, logger = false, apiOrigin, rateMax = 5 }) {
  const app = Fastify({ logger, logController: new LogController({ disableRequestLogging: true }), trustProxy, bodyLimit: 16 * 1024 });
  await app.register(helmet, { contentSecurityPolicy: { directives: {
    defaultSrc: ["'self'"], scriptSrc: ["'self'"], styleSrc: ["'self'", 'https://fonts.googleapis.com'],
    fontSrc: ["'self'", 'https://fonts.gstatic.com'], imgSrc: ["'self'", 'data:'],
    connectSrc: ["'self'", ...(apiOrigin ? [apiOrigin] : [])], formAction: ["'self'"],
    objectSrc: ["'none'"], frameAncestors: ["'none'"]
  } } });
  await app.register(cors, { origin: origins, methods: ['POST'], allowedHeaders: ['Content-Type','Idempotency-Key'], credentials: false });
  await app.register(rateLimit, { global: false, max: rateMax, timeWindow: '10 minutes', redis,
    keyGenerator: req => createHmac('sha256', rateSecret).update(req.ip).digest('hex'),
    skipOnError: false });
  app.get('/healthz', async () => ({ status: 'ok' }));
  app.get('/readyz', async (_req, reply) => {
    try { await store.ready(); if (redis) await redis.ping(); return { status: 'ready' }; }
    catch { return reply.code(503).send({ status: 'unavailable' }); }
  });
  app.post('/api/inquiries', { config: { rateLimit: { max: rateMax, timeWindow: '10 minutes' } } }, async (req, reply) => {
    reply.header('Cache-Control', 'no-store');
    if (!origins.includes(req.headers.origin)) return reply.code(403).send({ error: 'Origin not allowed.' });
    if (!req.headers['content-type']?.toLowerCase().startsWith('application/json')) return reply.code(415).send({ error: 'Send JSON.' });
    const key = z.uuid().safeParse(req.headers['idempotency-key']);
    if (!key.success) return reply.code(400).send({ error: 'A valid request identifier is required.' });
    const parsed = inquirySchema.safeParse(req.body);
    if (!parsed.success) return reply.code(400).send({ error: 'Check the required fields and consent.', fields: [...new Set(parsed.error.issues.map(issue => issue.path[0]))] });
    if (parsed.data.website) return reply.code(400).send({ error: 'Unable to accept this submission.' });
    const { website: _website, ...inquiry } = parsed.data;
    const hash = createHash('sha256').update(JSON.stringify(inquiry)).digest('hex');
    try {
      const result = await store.save(key.data, hash, inquiry);
      if (result.conflict) return reply.code(409).send({ error: 'This request identifier has already been used. Please start a new inquiry.' });
      return reply.code(result.created ? 201 : 200).send({ id: result.id });
    } catch {
      // Avoid logging submitted text, contact details, connection strings, or database errors.
      req.log.error({ requestId: req.id }, 'Inquiry persistence unavailable');
      return reply.code(503).send({ error: 'We could not save your inquiry. Please retry shortly.' });
    }
  });
  app.setErrorHandler((error, _req, reply) => {
    const status = error.statusCode && error.statusCode >= 400 && error.statusCode < 500 ? error.statusCode : 503;
    if (status === 429) reply.header('Retry-After', '600');
    reply.header('Cache-Control','no-store').code(status).send({ error: status === 429 ? 'Too many requests. Please try again in 10 minutes.' : 'Unable to process this request. Please try again.' });
  });
  await app.register(staticFiles, { root, index: ['index.html'], dotfiles: 'deny' });
  return app;
}
