---
description: Isogeny Labs implements known cryptanalytic attacks on elliptic-curve and isogeny-based systems, measures what they cost on current hardware, and publishes the code and the measurements.
---

The move to post-quantum cryptography will replace the public-key cryptography in nearly every system in use. The new schemes are being deployed in new code against fixed deadlines, on cost estimates that have had little time to be tested, and that is why this lab exists.

Cryptographic hardness is estimated once and re-examined rarely. Someone computes the cost of the best known attack, publishes the figure, and the field cites it for decades. The algorithm is usually sound. The cost model ages, against hardware that does not stand still and against cryptanalysis that does not stop.

Most of the time nobody checks. Checking is engineering rather than mathematics, it produces no theorem, and the incentives in this field do not reward it. So the numbers that parameter choices, migration plans and procurement deadlines all rest on go unexamined for years at a time.

This lab builds the attacks and measures them. We implement known cryptanalytic methods against elliptic curve and isogeny based systems, report what they cost on hardware that exists now, and publish the code and the measurements so the figures can be checked by anyone who wants to. Where the estimate and the measurement disagree, the measurement is the finding.
