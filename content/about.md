---
heading: About
description: Why Isogeny Labs exists, and who runs it.
standfirst: Isogeny Labs implements known attacks on elliptic-curve and isogeny-based cryptography and measures what they cost on hardware that exists now.
---

## Why the lab exists

The security of a cryptosystem is an estimate: the cost of the best known attack, worked out once and then cited for years. Those estimates age as hardware improves and cryptanalysis advances, and checking them is engineering work that the field does not reward. We do that work, and we publish the code and the measurements so anyone can check them.

## Why now

Quantum computing makes this more pressing. A large fault-tolerant quantum computer running Shor's algorithm would break every elliptic-curve and RSA key in use. Nobody can say when such a machine will exist, but the published estimates of what it would take keep falling, and encrypted traffic recorded today can be decrypted once one does. Replacing the cryptography in deployed systems takes years, so the migration has to start well before the threat arrives. That makes it a problem for today, not for whenever the machine is built.

The replacements are post-quantum schemes: lattice-based ML-KEM and ML-DSA, hash-based SLH-DSA, and isogeny-based schemes such as SQIsign. Their security levels are estimates too, made the same way and subject to the same ageing. Isogeny-based cryptography has already shown how fast an estimate can fail: SIDH was broken in 2022 by a classical attack after years of analysis. Measuring the cost of attacks on elliptic curves today, and on the isogeny-based systems proposed to replace parts of them, is the work this lab was set up to do.

[Quantum computers and post-quantum cryptography](../research/quantum-and-post-quantum.html) explains the background in more detail.

## People

### Adam Buran

Cofounder, Principal Cryptographer

[To come: bio.]

### Kevin Nguyen

Cofounder, Technical Programs

[To come: bio.]
