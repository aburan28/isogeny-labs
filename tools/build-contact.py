import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from sitegen.shell import page
root=Path(__file__).resolve().parents[1]
(root/'contact').mkdir(exist_ok=True)
for name,title,body in [
 ('index','Enterprise inquiries','<article><h1>Enterprise inquiries</h1><p>Discuss a security review, post-quantum migration, cryptographic research, or implementation review.</p><div id="contact-form"><p>The inquiry form is loading. If it does not appear, enable JavaScript or try again later.</p></div><noscript><p>The online form requires JavaScript. Contact details will be published here when an alternative channel is available.</p></noscript></article><script defer src="./contact.js"></script>'),
 ('privacy','Inquiry information','<article><h1>How we use inquiry information</h1><p>The form asks for your name, work email, organization, service interest and project overview. These details are used to assess and respond to your inquiry. Consent is recorded with the submission.</p><p>Please share only information suitable for an initial business discussion. Do not submit private keys, credentials, confidential datasets or vulnerability details. This form does not accept attachments.</p><p>Submitting the form does not subscribe you to marketing or create a service agreement. A successful response means the inquiry was saved; it does not guarantee a response time.</p><p>The service applies temporary request limits to reduce spam. Inquiry details are not placed in a public page or response. Ask your Isogeny Labs contact to correct or remove your inquiry when a conversation is established.</p><p><a href="index.html">Return to inquiries</a></p></article>')]:
 html=page(prefix='../',here='contact',title=f'{title} · Isogeny Labs',description=title,body=body)
 (root/f'contact/{name}.html').write_text(html)
