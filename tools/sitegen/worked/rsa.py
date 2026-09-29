"""RSA at toy size: a key pair, CRT decryption, and three ways it goes wrong.

The RSA page quotes its numbers from here. The primes are 64 bits, so every
number fits on a line; at real sizes they are 1024 bits or more. Everything
printed is checked: decryption against the plaintext, signatures by
verification, and every recovered factor by multiplying it back.
"""

from __future__ import annotations

from math import gcd

from .arith import Rng, is_prime

E = 65537
BITS = 64


def prime(rng: Rng, bits: int = BITS) -> int:
    """A prime of exactly `bits` bits with gcd(p - 1, e) = 1. At 64 bits the
    Miller-Rabin bases in arith.is_prime make the test deterministic."""
    while True:
        p = rng.below(2 ** (bits - 1)) | (2 ** (bits - 1)) | 1
        if (p - 1) % E and is_prime(p):
            return p


def keypair(rng: Rng, p: int | None = None):
    p = p or prime(rng)
    q = prime(rng)
    while q == p:
        q = prime(rng)
    N, phi = p * q, (p - 1) * (q - 1)
    d = pow(E, -1, phi)
    return {"p": p, "q": q, "N": N, "d": d,
            "dp": d % (p - 1), "dq": d % (q - 1), "qinv": pow(q, -1, p)}


def crt_power(c: int, k, fault: bool = False) -> int:
    """c^d mod N from the two halves mod p and mod q (Garner's recombination).
    With fault=True the half mod q is off by one, as if a bit flipped."""
    mp = pow(c, k["dp"], k["p"])
    mq = pow(c, k["dq"], k["q"])
    if fault:
        mq = (mq + 1) % k["q"]
    h = k["qinv"] * (mp - mq) % k["p"]
    return mq + h * k["q"]


def compute() -> dict:
    rng = Rng("isogenylabs/schemes/rsa")
    k = keypair(rng)
    p, q, N, d = k["p"], k["q"], k["N"], k["d"]
    assert E * d % ((p - 1) * (q - 1)) == 1

    # Encryption and decryption, directly and by CRT.
    m = rng.below(N)
    c = pow(m, E, N)
    assert pow(c, d, N) == m == crt_power(c, k)

    # Textbook RSA is multiplicative: two signatures give a third.
    m1, m2 = rng.below(N), rng.below(N)
    s1, s2 = pow(m1, d, N), pow(m2, d, N)
    forged_msg, forged_sig = m1 * m2 % N, s1 * s2 % N
    assert pow(forged_sig, E, N) == forged_msg

    # A fault in one CRT half: the signature is right mod p and wrong mod q.
    h = rng.below(N)  # stands in for the padded hash being signed
    good = crt_power(h, k)
    bad = crt_power(h, k, fault=True)
    assert pow(good, E, N) == h and pow(bad, E, N) != h
    leaked = gcd((pow(bad, E, N) - h) % N, N)
    assert leaked == p and N // leaked == q

    # Two keys generated with a shared prime, as by a device with too little
    # entropy at boot: one gcd factors both.
    shared = keypair(rng, p=prime(rng))
    other = keypair(rng, p=shared["p"])
    g = gcd(shared["N"], other["N"])
    assert g == shared["p"] and shared["N"] % g == 0 and other["N"] % g == 0
    assert shared["q"] != other["q"]

    values = {
        "bits": str(BITS),
        "nbits": str(N.bit_length()),
        "e": str(E),
        "p": str(p), "q": str(q), "N": str(N), "d": str(d),
        "dp": str(k["dp"]), "dq": str(k["dq"]),
        "m": str(m), "c": str(c),
        "m1": str(m1), "m2": str(m2), "fm": str(forged_msg), "fs": str(forged_sig),
        "h": str(h), "good": str(good), "bad": str(bad), "leaked": str(leaked),
        "N1": str(shared["N"]), "N2": str(other["N"]), "g": str(g),
        "N1q": str(shared["N"] // g), "N2q": str(other["N"] // g),
    }
    return {"values": values, "blocks": {}}
