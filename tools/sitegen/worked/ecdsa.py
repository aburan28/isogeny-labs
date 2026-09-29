"""ECDSA on P-256 at full size: a signature, a reused nonce, and malleability.

The ECDSA page quotes its numbers from here. Unlike the other worked examples
this one runs on the real curve: scalar multiplication on P-256 takes
milliseconds even in plain Python, and a reused nonce breaks a real key as
easily as a toy one. The curve constants are those of FIPS 186-5 / SP 800-186;
the checks below fail loudly if any is mistyped.
"""

from __future__ import annotations

import hashlib

from .arith import Rng, ec_add, ec_mul, is_prime

# P-256 (secp256r1).
P = 2 ** 256 - 2 ** 224 + 2 ** 192 + 2 ** 96 - 1
A = -3 % P
B = 0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B
G = (0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296,
     0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5)
N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551


def check_curve() -> None:
    x, y = G
    assert (y * y - (x ** 3 + A * x + B)) % P == 0, "G is on the curve"
    assert ec_mul(N, G, A, P) is None, "G has order n"
    # Deterministic Miller-Rabin in arith is exact only below 3.3e24; for
    # 256-bit numbers it is a 12-base probable-prime test, which suffices here.
    assert is_prime(P) and is_prime(N)


def z_of(message: bytes) -> int:
    """The hash as an integer. For P-256 with SHA-256 no truncation is needed."""
    return int.from_bytes(hashlib.sha256(message).digest(), "big")


def sign(d: int, message: bytes, k: int):
    z = z_of(message)
    R = ec_mul(k, G, A, P)
    r = R[0] % N
    s = pow(k, -1, N) * (z + r * d) % N
    assert r and s
    return r, s


def verify(Q, message: bytes, sig) -> bool:
    r, s = sig
    if not (0 < r < N and 0 < s < N):
        return False
    z = z_of(message)
    w = pow(s, -1, N)
    X = ec_add(ec_mul(z * w % N, G, A, P), ec_mul(r * w % N, Q, A, P), A, P)
    return X is not None and X[0] % N == r


def hexs(x: int) -> str:
    return f"{x:064x}"


def compute() -> dict:
    check_curve()
    rng = Rng("isogenylabs/schemes/ecdsa")
    d = rng.between(1, N - 1)
    Q = ec_mul(d, G, A, P)

    m1 = b"Pay Alice 10 coins"
    m2 = b"Pay Bob 20 coins"

    # An honest signature.
    k0 = rng.between(1, N - 1)
    sig0 = sign(d, m1, k0)
    assert verify(Q, m1, sig0)
    assert not verify(Q, m2, sig0)

    # Malleability: (r, n - s) verifies too.
    flipped = (sig0[0], N - sig0[1])
    assert verify(Q, m1, flipped) and flipped != sig0

    # The same nonce used twice.
    k = rng.between(1, N - 1)
    r1, s1 = sign(d, m1, k)
    r2, s2 = sign(d, m2, k)
    assert r1 == r2 and verify(Q, m1, (r1, s1)) and verify(Q, m2, (r2, s2))
    z1, z2 = z_of(m1), z_of(m2)
    k_rec = (z1 - z2) * pow(s1 - s2, -1, N) % N
    d_rec = (s1 * k_rec - z1) * pow(r1, -1, N) % N
    assert k_rec == k and d_rec == d and ec_mul(d_rec, G, A, P) == Q

    # With the key, anything can be signed.
    m3 = b"Pay Mallory everything"
    forged = sign(d_rec, m3, rng.between(1, N - 1))
    assert verify(Q, m3, forged)

    values = {
        "m1": m1.decode(), "m2": m2.decode(), "m3": m3.decode(),
        "Qx": hexs(Q[0]), "Qy": hexs(Q[1]),
        "r0": hexs(sig0[0]), "s0": hexs(sig0[1]), "s0f": hexs(flipped[1]),
        "r1": hexs(r1), "s1": hexs(s1), "s2": hexs(s2),
        "z1": hexs(z1), "z2": hexs(z2),
        "k": hexs(k_rec), "d": hexs(d_rec),
    }
    return {"values": values, "blocks": {}}
