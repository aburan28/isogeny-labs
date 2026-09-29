"""Curve25519 arithmetic shared by the X25519 and Ed25519 pages.

Both run at full size and are checked against the test vectors of RFC 7748
and RFC 8032, which are copied here byte for byte. A page that quotes a
number from these modules is quoting something that reproduced the RFC.
"""

from __future__ import annotations

import hashlib

P = 2 ** 255 - 19
L = 2 ** 252 + 27742317777372353535851937790883648493  # prime order of the base point
A24 = 121665  # (486662 - 2) / 4


# --------------------------------------------------------------------------
# X25519 (RFC 7748, section 5)


def decode_scalar(k: bytes) -> int:
    b = bytearray(k)
    b[0] &= 248
    b[31] &= 127
    b[31] |= 64
    return int.from_bytes(b, "little")


def decode_u(u: bytes) -> int:
    b = bytearray(u)
    b[31] &= 127
    return int.from_bytes(b, "little") % P


def encode_u(u: int) -> bytes:
    return (u % P).to_bytes(32, "little")


def ladder(k: int, u: int) -> int:
    """The Montgomery ladder exactly as RFC 7748 writes it, with cswap."""
    x1, x2, z2, x3, z3 = u, 1, 0, u, 1
    swap = 0
    for t in reversed(range(255)):
        kt = (k >> t) & 1
        swap ^= kt
        if swap:
            x2, x3, z2, z3 = x3, x2, z3, z2
        swap = kt
        A = (x2 + z2) % P
        AA = A * A % P
        B = (x2 - z2) % P
        BB = B * B % P
        E = (AA - BB) % P
        C = (x3 + z3) % P
        D = (x3 - z3) % P
        DA = D * A % P
        CB = C * B % P
        x3 = (DA + CB) ** 2 % P
        z3 = x1 * (DA - CB) ** 2 % P
        x2 = AA * BB % P
        z2 = E * (AA + A24 * E) % P
    if swap:
        x2, x3, z2, z3 = x3, x2, z3, z2
    return x2 * pow(z2, P - 2, P) % P


def x25519(k: bytes, u: bytes) -> bytes:
    return encode_u(ladder(decode_scalar(k), decode_u(u)))


RFC7748 = {
    "a": "77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a",
    "A": "8520f0098930a754748b7ddcb43ef75a0dbf3a0d26381af4eba4a98eaa9b4e6a",
    "b": "5dab087e624a8a4b79e17f8b83800ee66f3bb1292618b6fd1c2f8b27ff88e0eb",
    "B": "de9edb7d7b7dc1b4d35b61c2ece435373f8343c85b78674dadfc7e146f882b4f",
    "K": "4a5d9d5ba4ce2de1728e3bf480350f25e07e21c947d19e3376f09b3c1e161742",
}


# --------------------------------------------------------------------------
# Ed25519 (RFC 8032, section 5.1), extended twisted Edwards coordinates.

D = -121665 * pow(121666, P - 2, P) % P
SQRT_M1 = pow(2, (P - 1) // 4, P)


def point_add(Pt, Qt):
    A = (Pt[1] - Pt[0]) * (Qt[1] - Qt[0]) % P
    B = (Pt[1] + Pt[0]) * (Qt[1] + Qt[0]) % P
    C = 2 * Pt[3] * Qt[3] * D % P
    Dd = 2 * Pt[2] * Qt[2] % P
    E, F, G, H = B - A, Dd - C, Dd + C, B + A
    return (E * F % P, G * H % P, F * G % P, E * H % P)


def point_mul(s: int, Pt):
    Q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            Q = point_add(Q, Pt)
        Pt = point_add(Pt, Pt)
        s >>= 1
    return Q


def point_equal(Pt, Qt) -> bool:
    return (Pt[0] * Qt[2] - Qt[0] * Pt[2]) % P == 0 and (Pt[1] * Qt[2] - Qt[1] * Pt[2]) % P == 0


def recover_x(y: int, sign: int):
    if y >= P:
        return None
    x2 = (y * y - 1) * pow(D * y * y + 1, P - 2, P) % P
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (P + 3) // 8, P)
    if (x * x - x2) % P:
        x = x * SQRT_M1 % P
    if (x * x - x2) % P:
        return None
    if (x & 1) != sign:
        x = P - x
    return x


G_Y = 4 * pow(5, P - 2, P) % P
G_X = recover_x(G_Y, 0)
G = (G_X, G_Y, 1, G_X * G_Y % P)


def compress(Pt) -> bytes:
    zinv = pow(Pt[2], P - 2, P)
    x, y = Pt[0] * zinv % P, Pt[1] * zinv % P
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def decompress(s: bytes):
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = recover_x(y, sign)
    return None if x is None else (x, y, 1, x * y % P)


def sha512_int(*parts: bytes) -> int:
    return int.from_bytes(hashlib.sha512(b"".join(parts)).digest(), "little")


def expand_secret(secret: bytes):
    h = hashlib.sha512(secret).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def public_key(secret: bytes) -> bytes:
    a, _ = expand_secret(secret)
    return compress(point_mul(a, G))


def sign(secret: bytes, msg: bytes, public: bytes | None = None) -> bytes:
    """RFC 8032 signing. `public` lets a caller pass the public key separately,
    as some library APIs did; passing the wrong one is the attack on the page."""
    a, prefix = expand_secret(secret)
    A = public if public is not None else compress(point_mul(a, G))
    r = sha512_int(prefix, msg) % L
    R = compress(point_mul(r, G))
    k = sha512_int(R, A, msg) % L
    s = (r + k * a) % L
    return R + int.to_bytes(s, 32, "little")


def verify(public: bytes, msg: bytes, signature: bytes) -> bool:
    A = decompress(public)
    R = decompress(signature[:32])
    s = int.from_bytes(signature[32:], "little")
    if A is None or R is None or s >= L:
        return False
    k = sha512_int(signature[:32], public, msg) % L
    return point_equal(point_mul(s, G), point_add(R, point_mul(k, A)))


RFC8032 = [
    ("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
     "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
     "",
     "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155"
     "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"),
    ("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
     "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c",
     "72",
     "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da"
     "085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"),
    ("c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7",
     "fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025",
     "af82",
     "6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac"
     "18ff9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a"),
]
