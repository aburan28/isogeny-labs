import pg from 'pg';
export function database() {
  if (!process.env.DATABASE_URL) throw new Error('DATABASE_URL is required');
  // Use a trusted CA through the connection configuration. Never disable TLS verification.
  const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL, max: 10,
    connectionTimeoutMillis: 5000, idleTimeoutMillis: 30000, statement_timeout: 5000 });
  pool.on('error', () => console.error('Database connection unavailable'));
  return pool;
}
