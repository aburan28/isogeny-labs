"""X25519 at full size: the RFC 7748 exchange, low-order inputs, and the twist.

The ECDH page quotes its numbers from here. Everything is checked against
RFC 7748's test vectors first, so the ladder that produces the other numbers
is known to be the standard one.
"""

from __future__ import annotations

from .arith import Rng, is_prime
from .curve25519 import L, P, RFC7748, decode_scalar, encode_u, x25519


def compute() -> dict:
    v = {k: bytes.fromhex(x) for k, x in RFC7748.items()}
    nine = encode_u(9)
    assert x25519(v["a"], nine) == v["A"]
    assert x25519(v["b"], nine) == v["B"]
    assert x25519(v["a"], v["B"]) == v["K"] == x25519(v["b"], v["A"])

    # Clamping, shown on Alice's key.
    k = decode_scalar(v["a"])
    assert k % 8 == 0 and k >> 254 == 1

    # Low-order inputs: u = 0 and u = 1 lie in the subgroup of order dividing 8,
    # which clamping kills, so the shared secret is all zeros whatever the key.
    rng = Rng("isogenylabs/schemes/ecdh")
    keys = [bytes(rng.below(256) for _ in range(32)) for _ in range(3)]
    for key in keys + [v["a"], v["b"]]:
        for u in (0, 1):
            assert x25519(key, encode_u(u)) == bytes(32)

    # The group orders: 8 L on the curve, 4 L' on its quadratic twist.
    curve_order = 8 * L
    twist_order = 2 * (P + 1) - curve_order
    assert twist_order % 4 == 0
    L_twist = twist_order // 4
    assert is_prime(L) and is_prime(L_twist)

    values = {k_: x for k_, x in RFC7748.items()}
    values.update({
        "p_bits": str(P.bit_length()),
        "L_bits": str(L.bit_length()),
        "Lt_bits": str(L_twist.bit_length()),
        "L": str(L),
        "Lt": str(L_twist),
        "random_keys": str(len(keys) + 2),
    })
    return {"values": values, "blocks": {}}
