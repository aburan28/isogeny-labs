import { build } from 'esbuild';
import { cp, mkdir, rm } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
const api = process.env.CONTACT_API_URL || '';
if (api && api !== '/api/inquiries') { const url = new URL(api); if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash) throw new Error('CONTACT_API_URL must be /api/inquiries or a credential-free HTTPS endpoint'); }
execFileSync('python3', ['tools/build-contact.py'], { stdio:'inherit' });
await rm('_site',{recursive:true,force:true}); await mkdir('_site');
for (const path of ['index.html','styles.css','script.js','favicon.svg','notes','schemes','cryptanalysis','contact']) await cp(path,`_site/${path}`,{recursive:true});
await build({entryPoints:['web/contact.jsx'],bundle:true,minify:true,outfile:'_site/contact/contact.js',define:{__CONTACT_API_URL__:JSON.stringify(api),'process.env.NODE_ENV':'"production"'},legalComments:'none'});
