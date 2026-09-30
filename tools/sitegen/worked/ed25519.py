"""Ed25519 at full size: RFC 8032's test vectors, determinism, and key
recovery from a signer that takes the public key as a separate input.

The EdDSA page quotes its numbers from here.
"""

from __future__ import annotations

from .curve25519 import (G, L, RFC8032, compress, expand_secret, point_mul, public_key,
                         sha512_int, sign, verify)


def compute() -> dict:
    for sk, pk, msg, sig in RFC8032:
        sk, pk, msg, sig = map(bytes.fromhex, (sk, pk, msg, sig))
        assert public_key(sk) == pk
        assert sign(sk, msg) == sig
        assert verify(pk, msg, sig)
        assert not verify(pk, msg + b"!", sig)

    sk, pk = bytes.fromhex(RFC8032[1][0]), bytes.fromhex(RFC8032[1][1])
    msg = b"Pay Alice 10 coins"

    # Deterministic: the same message gives the same signature, byte for byte.
    s1 = sign(sk, msg)
    assert s1 == sign(sk, msg) and verify(pk, msg, s1)

    # A signing API that takes the public key as an argument. The nonce r
    # depends only on the secret prefix and the message, so signing the same
    # message with a wrong public key reuses r with a different challenge.
    wrong = bytes.fromhex(RFC8032[2][1])
    s2 = sign(sk, msg, public=wrong)
    assert s1[:32] == s2[:32], "same R"
    assert not verify(pk, msg, s2)
    k1 = sha512_int(s1[:32], pk, msg) % L
    k2 = sha512_int(s2[:32], wrong, msg) % L
    S1 = int.from_bytes(s1[32:], "little")
    S2 = int.from_bytes(s2[32:], "little")
    a = (S1 - S2) * pow(k1 - k2, -1, L) % L
    real_a, _ = expand_secret(sk)
    assert a == real_a % L and compress(point_mul(a, G)) == pk

    # The recovered scalar is enough to sign anything, with any nonce.
    forged_msg = b"Pay Mallory everything"
    r = sha512_int(b"any nonce will do", forged_msg) % L
    R = compress(point_mul(r, G))
    k = sha512_int(R, pk, forged_msg) % L
    forged = R + int.to_bytes((r + k * a) % L, 32, "little")
    assert verify(pk, forged_msg, forged)

    values = {
        "sk": RFC8032[1][0], "pk": RFC8032[1][1], "wrong": RFC8032[2][1],
        "t1_sig": RFC8032[0][3],
        "msg": msg.decode(), "forged_msg": forged_msg.decode(),
        "R": s1[:32].hex(), "S1": s1[32:].hex(), "S2": s2[32:].hex(),
        "a": f"{a:064x}",
        "vectors": str(len(RFC8032)),
    }
    return {"values": values, "blocks": {}}
