import React, { useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
const endpoint = __CONTACT_API_URL__;
function ContactForm() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [receipt, setReceipt] = useState('');
  const [email, setEmail] = useState('');
  const request = useRef(null);
  const status = useRef(null);
  async function submit(event) {
    event.preventDefault(); if (pending) return;
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form)); data.consent = data.consent === 'on';
    const body = JSON.stringify(data);
    if (request.current?.body !== body) request.current = { body, id: crypto.randomUUID() };
    setPending(true); setError('');
    try {
      const response = await fetch(endpoint, { method: 'POST', headers: { 'Content-Type':'application/json', 'Idempotency-Key':request.current.id }, body, signal: AbortSignal.timeout(15000) });
      const result = await response.json();
      if (!response.ok) throw new Error(response.status === 429 ? 'Too many requests. Please try again in 10 minutes.' : result.error || 'We could not save your inquiry. Please try again.');
      if (!result.id) throw new Error('We could not confirm your inquiry. Please retry.');
      setReceipt(result.id); setEmail(data.email);
    } catch (err) {
      setError(err.name === 'TimeoutError' ? 'The request timed out. Your details are still here; retrying will not create a duplicate.' : err instanceof TypeError ? 'We could not reach the server. Your details are still here. Please try again.' : err.message);
    } finally { setPending(false); setTimeout(() => status.current?.focus(), 0); }
  }
  if (!endpoint) return <p role="status">Online inquiries are not available yet. Please check back when contact details are published.</p>;
  if (receipt) return <section ref={status} tabIndex={-1} role="status"><h2>Inquiry received</h2><p>Your inquiry has been saved. Our team can use <strong>{email}</strong> to follow up.</p><p>Reference: <code>{receipt}</code></p><p>No files were uploaded. This confirmation is not a service agreement.</p><button onClick={() => { setReceipt(''); request.current = null; }}>Start another inquiry</button></section>;
  return <form onSubmit={submit} aria-busy={pending}>
    <p>Tell us what your organization needs. Please do not include private keys, credentials, confidential datasets, or vulnerability details. We can arrange a suitable channel after an initial discussion.</p>
    <div className="contact-fields">
      <label>Your name<input name="name" autoComplete="name" required minLength={2} maxLength={120} /></label>
      <label>Work email<input name="email" type="email" autoComplete="email" required maxLength={254} /></label>
      <label>Organization<input name="company" autoComplete="organization" required minLength={2} maxLength={160} /></label>
      <label>What can we help with?<select name="service" required defaultValue=""><option value="" disabled>Select a service</option>{['Security review','Post-quantum migration','Cryptographic research','Implementation review','Other'].map(s => <option key={s}>{s}</option>)}</select></label>
      <label>Project overview<textarea name="message" rows={7} minLength={20} maxLength={5000} required aria-describedby="message-help" /></label>
      <p id="message-help">20–5,000 characters. Include your goals, project stage and any timing constraints.</p>
    </div>
    <div className="contact-trap" aria-hidden="true"><label>Website<input name="website" tabIndex={-1} autoComplete="off" /></label></div>
    <label className="contact-consent"><input type="checkbox" name="consent" required /> <span>I agree that Isogeny Labs may store these details and contact me about this inquiry. <a href="privacy.html">How we use inquiry information</a>.</span></label>
    {error && <p className="contact-error" ref={status} tabIndex={-1} role="alert">{error}</p>}
    <button type="submit" disabled={pending}>{pending ? 'Sending…' : 'Send inquiry'}</button>
  </form>;
}
createRoot(document.getElementById('contact-form')).render(<ContactForm />);
