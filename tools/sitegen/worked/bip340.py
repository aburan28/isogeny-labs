"""BIP-340 Schnorr signatures on secp256k1, at full size.

The Schnorr page quotes its numbers from here. The implementation follows
the BIP's reference code, and every one of the BIP's test vectors (copied
unmodified into bip340_vectors.csv from the bitcoin/bips repository) is run
at build time: signatures are regenerated where a secret key is given, and
every verification result, valid and invalid, must match.

Two properties of Schnorr signatures are then shown: linearity, through the
rogue-key attack on naive key aggregation, and nonce reuse.
"""

from __future__ import annotations

import csv
import hashlib
import pathlib

from .arith import Rng

P = 2 ** 256 - 2 ** 32 - 977
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
     0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)
VECTORS = pathlib.Path(__file__).with_name("bip340_vectors.csv")


def tagged_hash(tag: str, msg: bytes) -> bytes:
    t = hashlib.sha256(tag.encode()).digest()
    return hashlib.sha256(t + t + msg).digest()


def point_add(P1, P2):
    if P1 is None:
        return P2
    if P2 is None:
        return P1
    if P1[0] == P2[0] and P1[1] != P2[1]:
        return None
    if P1 == P2:
        lam = 3 * P1[0] * P1[0] * pow(2 * P1[1], P - 2, P) % P
    else:
        lam = (P2[1] - P1[1]) * pow(P2[0] - P1[0], P - 2, P) % P
    x3 = (lam * lam - P1[0] - P2[0]) % P
    return (x3, (lam * (P1[0] - x3) - P1[1]) % P)


def point_mul(Pt, n: int):
    R = None
    for i in range(256):
        if (n >> i) & 1:
            R = point_add(R, Pt)
        Pt = point_add(Pt, Pt)
    return R


def neg(Pt):
    return None if Pt is None else (Pt[0], P - Pt[1])


def bytes_from_int(x: int) -> bytes:
    return x.to_bytes(32, "big")


def int_from_bytes(b: bytes) -> int:
    return int.from_bytes(b, "big")


def lift_x(x: int):
    """The point with x-coordinate x and even y, or None."""
    if x >= P:
        return None
    y_sq = (pow(x, 3, P) + 7) % P
    y = pow(y_sq, (P + 1) // 4, P)
    if pow(y, 2, P) != y_sq:
        return None
    return (x, y if y & 1 == 0 else P - y)


def pubkey_gen(seckey: bytes) -> bytes:
    d0 = int_from_bytes(seckey)
    assert 1 <= d0 <= N - 1
    return bytes_from_int(point_mul(G, d0)[0])


def challenge(r: bytes, pk: bytes, msg: bytes) -> int:
    return int_from_bytes(tagged_hash("BIP0340/challenge", r + pk + msg)) % N


def sign(seckey: bytes, msg: bytes, aux_rand: bytes, k_override: int | None = None) -> bytes:
    d0 = int_from_bytes(seckey)
    assert 1 <= d0 <= N - 1
    Pt = point_mul(G, d0)
    d = d0 if Pt[1] % 2 == 0 else N - d0
    t = bytes(a ^ b for a, b in zip(bytes_from_int(d), tagged_hash("BIP0340/aux", aux_rand)))
    k0 = int_from_bytes(tagged_hash("BIP0340/nonce", t + bytes_from_int(Pt[0]) + msg)) % N
    if k_override is not None:  # only for the nonce-reuse demonstration
        k0 = k_override
    assert k0 != 0
    R = point_mul(G, k0)
    k = k0 if R[1] % 2 == 0 else N - k0
    e = challenge(bytes_from_int(R[0]), bytes_from_int(Pt[0]), msg)
    sig = bytes_from_int(R[0]) + bytes_from_int((k + e * d) % N)
    assert verify(bytes_from_int(Pt[0]), msg, sig)
    return sig


def verify(pubkey: bytes, msg: bytes, sig: bytes) -> bool:
    if len(pubkey) != 32 or len(sig) != 64:
        return False
    Pt = lift_x(int_from_bytes(pubkey))
    r, s = int_from_bytes(sig[:32]), int_from_bytes(sig[32:])
    if Pt is None or r >= P or s >= N:
        return False
    e = challenge(sig[:32], pubkey, msg)
    R = point_add(point_mul(G, s), neg(point_mul(Pt, e)))
    return R is not None and R[1] % 2 == 0 and R[0] == r


def run_vectors():
    signed = verified = 0
    with VECTORS.open() as f:
        for row in csv.DictReader(f):
            pk = bytes.fromhex(row["public key"])
            msg = bytes.fromhex(row["message"])
            sig = bytes.fromhex(row["signature"])
            expected = row["verification result"] == "TRUE"
            if row["secret key"]:
                sk = bytes.fromhex(row["secret key"])
                assert pubkey_gen(sk) == pk, row["index"]
                assert sign(sk, msg, bytes.fromhex(row["aux_rand"])) == sig, row["index"]
                signed += 1
            assert verify(pk, msg, sig) == expected, row["index"]
            verified += 1
    return signed, verified


def compute() -> dict:
    signed, verified = run_vectors()
    rng = Rng("isogenylabs/schemes/schnorr")

    def secret() -> bytes:
        return bytes_from_int(rng.between(1, N - 1))

    # Linearity: a naive "aggregate key" is the sum of the parties' keys.
    # Mallory, seeing Alice's key, announces P_M = xG - P_A. The sum is xG,
    # and Mallory alone knows its discrete logarithm.
    alice = secret()
    P_A = lift_x(int_from_bytes(pubkey_gen(alice)))
    x = rng.between(1, N - 1)
    P_M = point_add(point_mul(G, x), neg(P_A))
    agg = point_add(P_A, P_M)
    assert agg == point_mul(G, x)
    msg = b"Spend the 2-of-2 output to Mallory"
    forged = sign(bytes_from_int(x), msg, bytes(32))
    agg_pk = bytes_from_int(agg[0])
    assert verify(agg_pk, msg, forged)

    # Nonce reuse: s = k + e d, so two signatures with the same k give d.
    bob = secret()
    bob_pk = pubkey_gen(bob)
    k = rng.between(1, N - 1)
    m1, m2 = b"Pay Alice 10 coins", b"Pay Bob 20 coins"
    s1, s2 = sign(bob, m1, bytes(32), k_override=k), sign(bob, m2, bytes(32), k_override=k)
    assert s1[:32] == s2[:32]
    e1 = challenge(s1[:32], bob_pk, m1)
    e2 = challenge(s2[:32], bob_pk, m2)
    d = (int_from_bytes(s1[32:]) - int_from_bytes(s2[32:])) * pow(e1 - e2, -1, N) % N
    assert bytes_from_int(point_mul(G, d)[0]) == bob_pk

    values = {
        "signed": str(signed), "verified": str(verified),
        "invalid": str(verified - count_valid()),
        "valid": str(count_valid()),
        "alice_pk": bytes_from_int(P_A[0]).hex(),
        "mallory_pk": bytes_from_int(P_M[0]).hex(),
        "agg_pk": agg_pk.hex(),
        "msg": msg.decode(),
        "forged": forged.hex(),
        "m1": m1.decode(), "m2": m2.decode(),
    }
    return {"values": values, "blocks": {}}


def count_valid() -> int:
    with VECTORS.open() as f:
        return sum(row["verification result"] == "TRUE" for row in csv.DictReader(f))
