"""SHA-256 from FIPS 180-4, with its constants derived rather than typed.

The SHA-2 page quotes its numbers from here. The 64 round constants are the
first 32 bits of the fractional parts of the cube roots of the first 64
primes, and the initial hash value the same for square roots of the first 8;
both are computed with integer roots. The function is checked against the
usual test vectors and against Python's hashlib on random inputs, and the
avalanche effect is measured.
"""

from __future__ import annotations

import hashlib

from .arith import Rng, is_prime

MASK = 0xFFFFFFFF


def iroot(n: int, k: int) -> int:
    """floor(n^(1/k)) by Newton's method on integers."""
    x = 1 << ((n.bit_length() + k - 1) // k)
    while True:
        y = ((k - 1) * x + n // x ** (k - 1)) // k
        if y >= x:
            return x
        x = y


def frac_bits(p: int, k: int) -> int:
    """First 32 bits of the fractional part of p^(1/k)."""
    return iroot(p << (32 * k), k) & MASK


PRIMES = [n for n in range(2, 320) if is_prime(n)][:64]
K = [frac_bits(p, 3) for p in PRIMES]
H0 = [frac_bits(p, 2) for p in PRIMES[:8]]


def rotr(x: int, n: int) -> int:
    return ((x >> n) | (x << (32 - n))) & MASK


def compress(state, block: bytes):
    w = [int.from_bytes(block[4 * i:4 * i + 4], "big") for i in range(16)]
    for t in range(16, 64):
        s0 = rotr(w[t - 15], 7) ^ rotr(w[t - 15], 18) ^ (w[t - 15] >> 3)
        s1 = rotr(w[t - 2], 17) ^ rotr(w[t - 2], 19) ^ (w[t - 2] >> 10)
        w.append((w[t - 16] + s0 + w[t - 7] + s1) & MASK)
    a, b, c, d, e, f, g, h = state
    for t in range(64):
        S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)
        ch = (e & f) ^ (~e & g)
        t1 = (h + S1 + ch + K[t] + w[t]) & MASK
        S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)
        maj = (a & b) ^ (a & c) ^ (b & c)
        t2 = (S0 + maj) & MASK
        h, g, f, e, d, c, b, a = g, f, e, (d + t1) & MASK, c, b, a, (t1 + t2) & MASK
    return [(x + y) & MASK for x, y in zip(state, (a, b, c, d, e, f, g, h))]


def pad(msg: bytes) -> bytes:
    """Append 0x80, zeros to 56 mod 64, then the bit length as 64 bits."""
    return msg + b"\x80" + b"\x00" * ((55 - len(msg)) % 64) + (8 * len(msg)).to_bytes(8, "big")


def sha256(msg: bytes) -> bytes:
    state = list(H0)
    data = pad(msg)
    for i in range(0, len(data), 64):
        state = compress(state, data[i:i + 64])
    return b"".join(x.to_bytes(4, "big") for x in state)


VECTORS = [
    (b"", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    (b"abc", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"),
    (b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
     "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"),
]


def compute() -> dict:
    assert K[0] == 0x428A2F98 and K[63] == 0xC67178F2 and H0[0] == 0x6A09E667
    for msg, digest in VECTORS:
        assert sha256(msg).hex() == digest
    rng = Rng("isogenylabs/schemes/sha-2")
    random_checks = 200
    for _ in range(random_checks):
        m = bytes(rng.below(256) for _ in range(rng.below(300)))
        assert sha256(m) == hashlib.sha256(m).digest()

    trials, flips, lo, hi = 500, [], 256, 0
    for _ in range(trials):
        m = bytearray(rng.below(256) for _ in range(32))
        a = sha256(bytes(m))
        bit = rng.below(256)
        m[bit // 8] ^= 1 << (bit % 8)
        b = sha256(bytes(m))
        d = sum(bin(x ^ y).count("1") for x, y in zip(a, b))
        flips.append(d)
        lo, hi = min(lo, d), max(hi, d)
    mean = sum(flips) / trials

    values = {
        "abc": VECTORS[1][1],
        "k0": f"{K[0]:08x}", "k63": f"{K[63]:08x}", "h0": f"{H0[0]:08x}",
        "p63": str(PRIMES[63]),
        "random_checks": str(random_checks),
        "trials": str(trials), "mean": f"{mean:.1f}", "lo": str(lo), "hi": str(hi),
    }
    return {"values": values, "blocks": {}}
