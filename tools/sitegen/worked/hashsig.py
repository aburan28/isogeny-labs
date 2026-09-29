"""Hash-based signatures: WOTS+, a Merkle tree, and what reuse costs.

The SLH-DSA page quotes its numbers from here. Three things are computed:

  * A Winternitz one-time signature with the SLH-DSA-128 shape (n = 16 bytes,
    base-16 digits, 32 message digits and 3 checksum digits), signed and
    verified, over SHA-256 truncated to 16 bytes.
  * A Merkle tree over 16 such keys, with a signature carrying its
    authentication path, verified against the root.
  * The same one-time key used for several messages: how many random
    messages an attacker must try before one can be signed from the chain
    values already revealed. Each forgery found is turned into a real
    signature and verified.

It also derives every SLH-DSA signature size from its parameters and checks
the result against Table 2 of FIPS 205. The construction here is simplified
(one hash, simple tweaks, no FORS); the page says so.
"""

from __future__ import annotations

import hashlib

N_BYTES = 16
W = 16
LEN1 = 2 * N_BYTES  # base-16 digits of a 16-byte digest
LEN2 = 3            # checksum digits: max checksum 32 * 15 = 480 < 16^3
LEN = LEN1 + LEN2
TREE_HEIGHT = 4
FORGE_BUDGET = 300_000
REUSE = (1, 2, 3, 4, 6, 8)

# FIPS 205, Table 2: (n, h, d, a, k, lg w) -> (pk bytes, sig bytes)
FIPS205 = {
    "128s": ((16, 63, 7, 12, 14, 4), (32, 7856)),
    "128f": ((16, 66, 22, 6, 33, 4), (32, 17088)),
    "192s": ((24, 63, 7, 14, 17, 4), (48, 16224)),
    "192f": ((24, 66, 22, 8, 33, 4), (48, 35664)),
    "256s": ((32, 64, 8, 14, 22, 4), (64, 29792)),
    "256f": ((32, 68, 17, 9, 35, 4), (64, 49856)),
}


def H(*parts: bytes) -> bytes:
    return hashlib.sha256(b"".join(parts)).digest()[:N_BYTES]


def tweak(*ints: int) -> bytes:
    return b"".join(i.to_bytes(4, "big") for i in ints)


def chain(x: bytes, start: int, steps: int, key: int, pos: int) -> bytes:
    """Apply the chain function `steps` times from position `start`. Each step
    is tweaked with its key, chain and step index, as in SLH-DSA's ADRS."""
    for j in range(start, start + steps):
        x = H(tweak(key, pos, j), x)
    return x


def digits(message: bytes):
    d = H(b"msg", message)
    msg = [x for b in d for x in (b >> 4, b & 15)]
    csum = sum(W - 1 - x for x in msg)
    return msg + [(csum >> 8) & 15, (csum >> 4) & 15, csum & 15]


def wots_keygen(seed: bytes, key: int):
    sk = [H(b"sk", seed, tweak(key, i)) for i in range(LEN)]
    pk_chains = [chain(s, 0, W - 1, key, i) for i, s in enumerate(sk)]
    return sk, H(b"pk", *pk_chains)


def wots_sign(sk, message: bytes, key: int):
    return [chain(s, 0, v, key, i) for i, (s, v) in enumerate(zip(sk, digits(message)))]


def wots_pk_from_sig(sig, message: bytes, key: int) -> bytes:
    ends = [chain(x, v, W - 1 - v, key, i) for i, (x, v) in enumerate(zip(sig, digits(message)))]
    return H(b"pk", *ends)


def merkle(leaves):
    levels = [leaves]
    while len(levels[-1]) > 1:
        prev = levels[-1]
        levels.append([H(b"node", prev[i], prev[i + 1]) for i in range(0, len(prev), 2)])
    return levels


def auth_path(levels, index: int):
    return [levels[h][(index >> h) ^ 1] for h in range(len(levels) - 1)]


def root_from_path(leaf: bytes, index: int, path) -> bytes:
    node = leaf
    for h, sib in enumerate(path):
        node = H(b"node", sib, node) if (index >> h) & 1 else H(b"node", node, sib)
    return node


def fips_size(n: int, h: int, d: int, a: int, k: int, lgw: int):
    """Signature: randomiser R, FORS (k trees of height a: a secret and a path
    each), then d XMSS signatures (len WOTS+ values and h/d path nodes each).
    Public key: PK.seed and PK.root."""
    len1 = 8 * n // lgw
    w = 2 ** lgw
    len2 = ((len1 * (w - 1)).bit_length() + lgw - 1) // lgw
    wots_len = len1 + len2
    sig = n * (1 + k * (1 + a) + h + d * wots_len)
    return 2 * n, sig


def compute() -> dict:
    seed = b"isogenylabs/schemes/slh-dsa"

    # Every FIPS 205 size, from the parameters alone.
    size_rows = []
    for name, (params, expected) in FIPS205.items():
        got = fips_size(*params)
        assert got == expected, f"{name}: {got} != {expected}"
        n, h, d, a, k, lgw = params
        size_rows.append([f"SLH-DSA-{name}", str(n), str(h), str(d), f"{got[1]:,}"])
    assert fips_size(16, 63, 7, 12, 14, 4)[1] == 7856

    # One WOTS+ key, one signature.
    sk, pk = wots_keygen(seed, 0)
    msg = b"release v1.0"
    sig = wots_sign(sk, msg, 0)
    assert wots_pk_from_sig(sig, msg, 0) == pk
    assert wots_pk_from_sig(sig, b"release v1.1", 0) != pk
    dig = digits(msg)
    sign_hashes = sum(dig)
    verify_hashes = sum(W - 1 - v for v in dig)

    # A Merkle tree over 16 one-time keys.
    keys = [wots_keygen(seed, i) for i in range(2 ** TREE_HEIGHT)]
    levels = merkle([pk_ for _, pk_ in keys])
    root = levels[-1][0]
    leaf = 5
    msg2 = b"release v2.0"
    s2 = wots_sign(keys[leaf][0], msg2, leaf)
    path = auth_path(levels, leaf)
    assert root_from_path(wots_pk_from_sig(s2, msg2, leaf), leaf, path) == root
    tree_sig_bytes = N_BYTES * (LEN + TREE_HEIGHT)

    # Reuse: sign several messages with key 0, then search for a message
    # whose every digit is at least the smallest revealed at that position.
    reuse_rows, reuse_found = [], {}
    for count in REUSE:
        signed = [f"message {i}".encode() for i in range(count)]
        sigs = [wots_sign(sk, m_, 0) for m_ in signed]
        digs = [digits(m_) for m_ in signed]
        low = [min(dg[i] for dg in digs) for i in range(LEN)]
        found = None
        for t in range(FORGE_BUDGET):
            cand = f"forged {t}".encode()
            dc = digits(cand)
            if all(x >= y for x, y in zip(dc, low)):
                found = (t + 1, cand, dc)
                break
        if found:
            tries, cand, dc = found
            forged = []
            for i in range(LEN):
                j = next(s for s in range(count) if digs[s][i] == low[i])
                forged.append(chain(sigs[j][i], low[i], dc[i] - low[i], 0, i))
            assert wots_pk_from_sig(forged, cand, 0) == pk, "the forgery verifies"
            reuse_found[count] = tries
            reuse_rows.append([str(count), f"{tries:,}", "Yes"])
        else:
            reuse_rows.append([str(count), f"none in {FORGE_BUDGET:,}", "&mdash;"])
    assert 1 not in reuse_found and 2 not in reuse_found

    values = {
        "n": str(N_BYTES), "w": str(W), "len1": str(LEN1), "len2": str(LEN2), "len": str(LEN),
        "wots_bytes": f"{N_BYTES * LEN:,}",
        "sign_hashes": str(sign_hashes), "verify_hashes": str(verify_hashes),
        "chain_total": str(LEN * (W - 1)),
        "tree_leaves": str(2 ** TREE_HEIGHT), "tree_height": str(TREE_HEIGHT),
        "leaf": str(leaf), "tree_sig_bytes": f"{tree_sig_bytes:,}",
        "root": root.hex(), "pk": pk.hex(),
        "budget": f"{FORGE_BUDGET:,}",
        "min_found": str(min(reuse_found)),
        "below_found": str(max(c for c in REUSE if c < min(reuse_found))),
        "tries_min": f"{reuse_found[min(reuse_found)]:,}",
        "tries_max_reuse": f"{reuse_found[max(reuse_found)]:,}",
        "max_reuse": str(max(reuse_found)),
    }
    blocks = {
        "size_table": [{
            "table": {
                "caption": "Signature sizes computed from each parameter set's n, h, d, a, k and lg w "
                           "with the formula below, which the build checks against Table 2 of FIPS 205. "
                           "The SHA2 and SHAKE variants of each set have the same sizes.",
                "head": ["Parameter set", "n", "h", "d", "Signature bytes"],
                "rows": size_rows,
                "numeric": [1, 2, 3, 4],
            }
        }],
        "reuse_table": [{
            "table": {
                "caption": f"One WOTS+ key used for several messages. Tries: random messages the attacker "
                           f"hashed before finding one it could sign from the revealed values, up to "
                           f"{FORGE_BUDGET:,}. Every forgery found was verified against the public key.",
                "head": ["Messages signed", "Tries to a forgery", "Verified"],
                "rows": reuse_rows,
                "numeric": [0, 1],
            }
        }],
    }
    return {"values": values, "blocks": blocks}
