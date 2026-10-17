"""AES-128 from FIPS 197, checked against the standard's example vector.

The AES page quotes its numbers from here. The S-box is built from its
definition (inversion in GF(2^8) followed by an affine map) rather than typed
in, the cipher is checked against FIPS 197 appendix C.1, and the avalanche
effect is measured: how many ciphertext bits change when one plaintext bit
does, round by round.
"""

from __future__ import annotations

from .arith import Rng


def gmul(a: int, b: int) -> int:
    """Multiplication in GF(2^8) modulo x^8 + x^4 + x^3 + x + 1."""
    r = 0
    while b:
        if b & 1:
            r ^= a
        a = (a << 1) ^ (0x11B if a & 0x80 else 0)
        b >>= 1
    return r


def build_sbox():
    inv = [0] * 256
    for a in range(1, 256):
        for b in range(1, 256):
            if gmul(a, b) == 1:
                inv[a] = b
                break
    sbox = []
    for a in range(256):
        x = inv[a]
        y = x
        for s in range(1, 5):
            y ^= ((x << s) | (x >> (8 - s))) & 0xFF
        sbox.append(y ^ 0x63)
    return sbox


SBOX = build_sbox()


def expand_key(key: bytes):
    w = [list(key[4 * i:4 * i + 4]) for i in range(4)]
    rcon = 1
    for i in range(4, 44):
        t = list(w[i - 1])
        if i % 4 == 0:
            t = [SBOX[b] for b in t[1:] + t[:1]]
            t[0] ^= rcon
            rcon = gmul(rcon, 2)
        w.append([a ^ b for a, b in zip(w[i - 4], t)])
    return [sum(w[4 * r:4 * r + 4], []) for r in range(11)]


def encrypt_rounds(block: bytes, key: bytes):
    """Returns the state after each round (index 0 is after the first AddRoundKey)."""
    rk = expand_key(key)
    s = [b ^ k for b, k in zip(block, rk[0])]
    states = [bytes(s)]
    for rnd in range(1, 11):
        s = [SBOX[b] for b in s]
        s = [s[(i + 4 * (i % 4)) % 16] for i in range(16)]  # ShiftRows, column-major
        if rnd < 10:
            t = []
            for c in range(4):
                a = s[4 * c:4 * c + 4]
                t += [gmul(a[0], 2) ^ gmul(a[1], 3) ^ a[2] ^ a[3],
                      a[0] ^ gmul(a[1], 2) ^ gmul(a[2], 3) ^ a[3],
                      a[0] ^ a[1] ^ gmul(a[2], 2) ^ gmul(a[3], 3),
                      gmul(a[0], 3) ^ a[1] ^ a[2] ^ gmul(a[3], 2)]
            s = t
        s = [b ^ k for b, k in zip(s, rk[rnd])]
        states.append(bytes(s))
    return states


def encrypt(block: bytes, key: bytes) -> bytes:
    return encrypt_rounds(block, key)[-1]


FIPS197_C1 = ("000102030405060708090a0b0c0d0e0f",
              "00112233445566778899aabbccddeeff",
              "69c4e0d86a7b0430d8cdb78070b4c55a")


def popcount(b: bytes) -> int:
    return sum(bin(x).count("1") for x in b)


def compute() -> dict:
    assert SBOX[0x00] == 0x63 and SBOX[0x53] == 0xED  # FIPS 197 section 5.1.1 example
    key, pt, ct = (bytes.fromhex(h) for h in FIPS197_C1)
    assert encrypt(pt, key) == ct

    rng = Rng("isogenylabs/schemes/aes")
    trials = 200
    per_round = [0] * 11
    for _ in range(trials):
        k = bytes(rng.below(256) for _ in range(16))
        m = bytes(rng.below(256) for _ in range(16))
        bit = rng.below(128)
        m2 = bytearray(m)
        m2[bit // 8] ^= 1 << (bit % 8)
        a, b = encrypt_rounds(m, k), encrypt_rounds(bytes(m2), k)
        for r in range(11):
            per_round[r] += popcount(bytes(x ^ y for x, y in zip(a[r], b[r])))
    means = [v / trials for v in per_round]
    rows = [[str(r), f"{means[r]:.1f}"] for r in range(1, 11)]
    full = next(r for r in range(1, 11) if means[r] > 60)

    values = {
        "key": FIPS197_C1[0], "pt": FIPS197_C1[1], "ct": FIPS197_C1[2],
        "trials": str(trials),
        "r1": f"{means[1]:.1f}", "r2": f"{means[2]:.1f}", "r10": f"{means[10]:.1f}",
        "full": str(full),
    }
    blocks = {"avalanche": [{"table": {
        "caption": f"Mean number of the 128 state bits that differ after each round, when two plaintexts "
                   f"differ in one bit, over {trials} random keys and plaintexts. A random pair would differ in 64.",
        "head": ["Round", "Bits changed"],
        "rows": rows,
        "numeric": [0, 1],
    }}]}
    return {"values": values, "blocks": blocks}
