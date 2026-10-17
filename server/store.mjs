import { readFile } from 'node:fs/promises';
export async function migrate(db) {
  const sql = await readFile(new URL('./migrations/001_inquiries.sql', import.meta.url), 'utf8');
  // This migration contains only simple DDL statements, with no procedural bodies.
  for (const statement of sql.split(';').filter(s => s.trim())) await db.query(statement);
}
export function inquiryStore(db) {
  return {
    async save(id, hash, inquiry) {
      const { name, email, company, service, message, consent } = inquiry;
      const result = await db.query(`INSERT INTO enterprise_inquiries
        (id, request_hash, name, email, company, service, message, consent, notice_version)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) ON CONFLICT (id) DO NOTHING RETURNING id`,
      [id, hash, name, email, company, service, message, consent, '2026-09-28']);
      if (result.rows.length) return { id, created: true };
      const prior = await db.query('SELECT request_hash FROM enterprise_inquiries WHERE id = $1', [id]);
      if (prior.rows[0]?.request_hash !== hash) return { conflict: true };
      return { id, created: false };
    },
    async ready() { await db.query('SELECT 1'); }
  };
}
