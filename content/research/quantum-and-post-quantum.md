---
title: Quantum computers and post-quantum cryptography
order: 4
meta: Survey · Shor, Grover, the migration deadline, and isogenies
summary: What a quantum computer breaks and what it does not, why the move away from RSA and elliptic curves has to start before one exists, and where isogeny-based cryptography fits.
authors:
eprint:
code:
---

A large enough quantum computer would break every elliptic-curve and RSA key in use. Nobody can say when one will exist, but data encrypted today can be recorded and decrypted later, and replacing the cryptography in deployed systems takes years. So the deadline that matters is set by the migration, not by the machine.

<dl class="facts">
  <div><dt>Breaks</dt><dd>RSA, finite-field Diffie&ndash;Hellman, and every elliptic-curve scheme (ECDH, ECDSA, EdDSA, Schnorr), with Shor's algorithm</dd></div>
  <div><dt>Weakens</dt><dd>Symmetric ciphers and hashes, at most by a square root with Grover's algorithm; doubling the key length restores the margin</dd></div>
  <div><dt>Resources needed for P-256</dt><dd>About 2,330 logical qubits for the discrete logarithm on P-256 (Roetteler et al., 2017)</dd></div>
  <div><dt>Replacements</dt><dd>ML-KEM (FIPS 203), ML-DSA (FIPS 204) and SLH-DSA (FIPS 205), published by NIST in August 2024</dd></div>
</dl>

## What a quantum computer changes

Public-key cryptography rests on problems that are easy to set and hard to undo: multiplying two primes but not factoring the product, or computing Q = kP on an elliptic curve but not recovering k from Q. For a classical computer, the best known attack on a well-chosen 256-bit curve is a <a href="../cryptanalysis/pollard-rho.html">collision search</a> costing about 2<sup>128</sup> group operations, which is far out of reach.

In 1994 Peter Shor showed that a quantum computer could solve both factoring and discrete logarithms in polynomial time. The algorithm finds the period of a function, and both problems reduce to period finding. On an elliptic curve the speed-up is total: the work goes from exponential in the key size to a small polynomial. No choice of curve or key length avoids it, because the attack uses only the group structure that every elliptic-curve scheme needs in order to work.

> <span class="note-label">What it needs.</span> Shor's algorithm needs a large, fault-tolerant quantum computer: thousands of logical qubits, each built from many physical qubits with error correction, running a long computation without losing coherence. No such machine exists today, and the public demonstrations so far have factored only trivially small numbers.

## What it does not break

Symmetric ciphers such as AES and hash functions such as SHA-256 have no hidden period to find. The best known quantum attack on them is Grover's search, which at most square-roots the cost of a brute-force key search, and it parallelises badly: splitting the search across many machines reduces the speed-up. Using 256-bit keys keeps a large margin, so symmetric cryptography needs larger parameters rather than replacement.

Nor does a quantum computer break every public-key system. Schemes built on other problems, such as lattices, hash functions, and isogenies between elliptic curves, have no known efficient quantum attack. These are what <em>post-quantum cryptography</em> means: cryptography that runs on ordinary computers and is designed to resist attackers who have a quantum one.

## Why it is a problem now

An attacker does not need a quantum computer today to benefit from one later. Encrypted traffic can be recorded now and stored until it can be decrypted. Anything sent today under an elliptic-curve key exchange that still needs to be secret when a large quantum computer exists is already exposed.

Michele Mosca put the arithmetic simply. Let <em>x</em> be how long the data must stay secret, <em>y</em> how long it takes to migrate the systems that protect it, and <em>z</em> how long until a quantum computer can break the current keys. If <em>x</em> + <em>y</em> &gt; <em>z</em>, the data will be readable while it still matters, and nothing done after the fact can change that.

<div class="math">x + y &gt; z &nbsp;&rArr;&nbsp; already too late
  <span class="math-label">x: how long the data must stay secret; y: time to migrate; z: time until a cryptographically relevant quantum computer</span></div>

Nobody can date <em>z</em>, and published estimates of what Shor's algorithm needs keep falling. In 2019 Gidney and Eker&aring; estimated that factoring a 2048-bit RSA modulus would take about 20 million noisy physical qubits running for eight hours; in 2025 Gidney revised that to under a million, running for under a week. <em>y</em>, on the other hand, is known to be long: replacing the cryptography in protocols, hardware, certificates and long-lived devices has historically taken a decade or more. NIST's transition plan proposes deprecating elliptic-curve and RSA keys at the 112-bit security level after 2030 and disallowing all of them after 2035.

Key exchange is the urgent part, because recorded ciphertext can be attacked later. A signature only has to resist forgery for as long as it is relied on, so signatures can move second, except where they protect something that lasts, such as firmware or a root certificate.

## The replacements

In August 2024 NIST published its first three post-quantum standards: <a href="../schemes/ml-kem.html">ML-KEM</a> for key establishment and <a href="../schemes/ml-dsa.html">ML-DSA</a> for signatures, both built on module lattices, and <a href="../schemes/slh-dsa.html">SLH-DSA</a>, a signature that relies only on the security of a hash function. Deployments are adopting them first as <em>hybrids</em>, alongside X25519 or ECDSA, so that a connection stays secure as long as either half holds.

The new schemes are larger. An ML-KEM-768 public key is 1,184 bytes against 32 for X25519, and an ML-DSA signature is a few kilobytes against 64 bytes for Ed25519. Their security levels are estimates of the cost of the best known attacks, made by the same method as the estimates for elliptic curves, and they will need re-examining in the same way. The <a href="../schemes/index.html">catalogue of schemes</a> lists what each one rests on and what it costs.

## Where isogenies fit

Isogeny-based cryptography is a post-quantum family, not one of the systems that quantum computers break. It works with maps between elliptic curves rather than with points on one curve, and recovering a secret isogeny is not a period-finding problem, so Shor's algorithm does not apply. Its appeal is size: <a href="../schemes/sqisign.html">SQIsign</a> has the smallest keys and signatures of any post-quantum signature candidate.

The family also shows why estimates have to be checked. SIDH, an isogeny-based key exchange whose encapsulation form SIKE was an alternate candidate in the fourth round of NIST's process, was broken in 2022 by Castryck and Decru with a <em>classical</em> attack that recovered a level-1 key in about an hour on a single core; the <a href="../cryptanalysis/sidh-torsion-attacks.html">torsion-point attacks</a> page explains how. <a href="../schemes/csidh.html">CSIDH</a> resists that attack but has a commutative structure that gives quantum computers a subexponential attack through <a href="../cryptanalysis/kuperberg-csidh.html">Kuperberg's algorithm</a>, and how large its parameters must be is still disputed. SQIsign is affected by neither, though a classical attack published in 2026 forced its parameters up.

> <span class="note-label">Two different problems.</span> Elliptic-curve cryptography as deployed today, the discrete logarithm on a curve, falls to Shor's algorithm. Isogeny-based cryptography also uses elliptic curves, but rests on a different problem that has no known efficient quantum attack. The two are easy to confuse because they share the vocabulary.

## Primary sources

1. [P. W. Shor, "Polynomial-time algorithms for prime factorization and discrete logarithms on a quantum computer", SIAM Journal on Computing 26 (1997)](https://arxiv.org/abs/quant-ph/9508027)
1. [M. Roetteler, M. Naehrig, K. M. Svore and K. Lauter, "Quantum resource estimates for computing elliptic curve discrete logarithms", ASIACRYPT 2017](https://eprint.iacr.org/2017/598)
1. [C. Gidney and M. Eker&aring;, "How to factor 2048 bit RSA integers in 8 hours using 20 million noisy qubits", Quantum 5 (2021)](https://arxiv.org/abs/1905.09749)
1. [C. Gidney, "How to factor 2048 bit RSA integers with less than a million noisy qubits" (2025)](https://arxiv.org/abs/2505.15917)
1. [M. Mosca, "Cybersecurity in an era with quantum computers: will we be ready?", IEEE Security &amp; Privacy 16 (2018)](https://eprint.iacr.org/2015/1075)
1. [NIST, FIPS 203, 204 and 205: ML-KEM, ML-DSA and SLH-DSA (August 2024)](https://csrc.nist.gov/pubs/fips/203/final)
1. [NIST IR 8547 (initial public draft), "Transition to post-quantum cryptography standards" (November 2024)](https://csrc.nist.gov/pubs/ir/8547/ipd)
1. [W. Castryck and T. Decru, "An efficient key recovery attack on SIDH", EUROCRYPT 2023](https://eprint.iacr.org/2022/975)

## Related

- [The elliptic-curve discrete logarithm problem](../notes/ecdlp.html)
- [Isogenies and the supersingular graph](../notes/isogenies.html)
- [SQIsign](../schemes/sqisign.html)
- [Kuperberg's algorithm and CSIDH](../cryptanalysis/kuperberg-csidh.html)
