import { database } from './db.mjs';
import { migrate } from './store.mjs';
const db = database();
try { await migrate(db); console.log('Inquiry schema ready'); } finally { await db.end(); }
