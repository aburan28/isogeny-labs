"""Coppersmith's method on RSA with e = 3: a stereotyped message recovered.

The Coppersmith page quotes its numbers from here. A 256-bit RSA modulus is
generated, a message is encrypted with e = 3, and the attacker knows all of
the message except its last few bits. The unknown part x0 is a small root of

    f(x) = (M0 + x)^3 - c   (mod N),

and Howgrave-Graham's lattice finds it: polynomials that all vanish at x0
modulo N^h are reduced with LLL until one is small enough to vanish at x0
over the integers, where its roots can simply be found. The run is repeated
with larger lattices to measure how many unknown bits each size can recover.
Every recovered message is checked by re-encrypting it.
"""

from __future__ import annotations

from .arith import Rng, is_prime
from .lwe import check_lll, lll

BITS = 128  # per prime
E = 3
H_VALUES = (1, 2, 3)


def randbits(rng: Rng, k: int) -> int:
    """Uniform in [0, 2^k), for k beyond the 256 bits Rng.below draws at once."""
    out, done = 0, 0
    while done < k:
        take = min(128, k - done)
        out |= rng.below(2 ** take) << done
        done += take
    return out


def random_prime(rng: Rng, bits: int) -> int:
    """A prime p of exactly `bits` bits with gcd(p - 1, 3) = 1, so e = 3 works.

    For numbers this large the Miller-Rabin test with fixed bases is a strong
    probable-prime test rather than a proof; nothing below depends on it."""
    while True:
        p = rng.below(2 ** (bits - 1)) | (2 ** (bits - 1)) | 1
        if p % 3 == 2 and is_prime(p):
            return p


# Integer polynomials as coefficient lists, lowest degree first.


def pmul(a, b):
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i + j] += x * y
    return out


def ppow(a, k):
    out = [1]
    for _ in range(k):
        out = pmul(out, a)
    return out


def peval(a, x):
    acc = 0
    for c in reversed(a):
        acc = acc * x + c
    return acc


def deriv(a):
    return [i * c for i, c in enumerate(a)][1:]


def integer_roots(g, lo: int, hi: int):
    """All integer roots of g in [lo, hi], exactly.

    Between consecutive roots of g' the polynomial is monotone, so each piece
    holds at most one root and binary search finds it. The derivative's roots
    are found the same way, recursively; only their integer neighbourhoods are
    needed, so each is widened by one on either side."""
    while g and g[-1] == 0:
        g = g[:-1]
    if len(g) <= 1:
        return []
    marks = {lo, hi}
    if len(g) > 2:
        for r in real_root_floors(deriv(g), lo, hi):
            marks.update(x for x in (r - 1, r, r + 1, r + 2) if lo <= x <= hi)
    marks = sorted(marks)
    roots = {x for x in marks if peval(g, x) == 0}
    for a, b in zip(marks, marks[1:]):
        ga, gb = peval(g, a), peval(g, b)
        if ga == 0 or gb == 0 or (ga > 0) == (gb > 0):
            continue
        while b - a > 1:
            mid = (a + b) // 2
            gm = peval(g, mid)
            if gm == 0:
                roots.add(mid)
                break
            if (gm > 0) == (ga > 0):
                a, ga = mid, gm
            else:
                b = mid
    return sorted(roots)


def real_root_floors(g, lo: int, hi: int):
    """Integers r in [lo, hi] such that g changes sign in [r, r + 1] or vanishes at r."""
    while g and g[-1] == 0:
        g = g[:-1]
    if len(g) <= 1:
        return []
    marks = {lo, hi}
    if len(g) > 2:
        for r in real_root_floors(deriv(g), lo, hi):
            marks.update(x for x in (r - 1, r, r + 1, r + 2) if lo <= x <= hi)
    marks = sorted(marks)
    out = [x for x in marks if peval(g, x) == 0]
    for a, b in zip(marks, marks[1:]):
        ga, gb = peval(g, a), peval(g, b)
        if ga == 0 or gb == 0 or (ga > 0) == (gb > 0):
            continue
        while b - a > 1:
            mid = (a + b) // 2
            if (peval(g, mid) > 0) == (ga > 0):
                a = mid
            else:
                b = mid
        out.append(a)
    return out


def howgrave_graham(f, N: int, X: int, h: int):
    """Rows x^j N^(h-i) f^i (0 <= i < h, 0 <= j < deg f) and f^h, x scaled by X.

    Each polynomial vanishes at x0 modulo N^h. A combination whose
    coefficients, scaled by powers of X, are small enough vanishes at x0 over
    the integers (Howgrave-Graham's condition)."""
    d = len(f) - 1
    dim = d * h + 1
    polys = []
    for i in range(h):
        base = [c * N ** (h - i) for c in ppow(f, i)]
        polys += [[0] * j + base for j in range(d)]
    polys.append(ppow(f, h))
    return [[c * X ** k for k, c in enumerate(p + [0] * (dim - len(p)))] for p in polys]


def predicted(nbits: int, h: int, d: int = E) -> float:
    """Bits of X at which det(L)^(1/dim) = N^h, ignoring the LLL factor.

    The lattice has dim = d h + 1 rows. The N-exponents on the diagonal add up
    to d (h + (h - 1) + ... + 1) = d h (h + 1)/2, and the X-exponents to
    0 + 1 + ... + (dim - 1) = dim (dim - 1)/2. Setting the determinant's
    dim-th root equal to N^h and solving for log X gives this."""
    dim = d * h + 1
    return nbits * (dim * h - d * h * (h + 1) / 2) / (dim * (dim - 1) / 2)


def attack(f, N: int, X: int, h: int):
    """Returns (root or None, lattice dimension, LLL swaps)."""
    rows = howgrave_graham(f, N, X, h)
    R, swaps = lll(rows)
    for v in R[:2]:
        g = [c // X ** k for k, c in enumerate(v)]
        assert all(c % X ** k == 0 for k, c in enumerate(v))
        for r in integer_roots(g, 0, X):
            if peval(f, r) % N == 0:
                return r, len(rows), swaps, R
    return None, len(rows), swaps, R


def compute() -> dict:
    rng = Rng("isogenylabs/cryptanalysis/coppersmith")
    p, q = random_prime(rng, BITS), random_prime(rng, BITS)
    N = p * q
    phi = (p - 1) * (q - 1)
    assert pow(E, -1, phi)
    nbits = N.bit_length()

    def trial(unknown_bits: int, h: int):
        x0 = randbits(rng, unknown_bits)
        M0 = (randbits(rng, nbits - 3 - unknown_bits) + 2 ** (nbits - 3 - unknown_bits)) << unknown_bits
        m = M0 + x0
        assert m < N
        c = pow(m, E, N)
        f = [(M0 ** 3 - c) % N, 3 * M0 ** 2 % N, 3 * M0 % N, 1]  # (M0 + x)^3 - c mod N
        root, dim, swaps, R = attack(f, N, 2 ** unknown_bits, h)
        if root is None:
            return False, dim, swaps, R, x0
        assert root == x0 and pow(M0 + root, E, N) == c, "re-encrypting the recovered message gives c"
        return True, dim, swaps, R, x0

    # How many unknown bits each lattice size can handle: binary search, in
    # steps of 4 bits, for the largest size at which two fresh messages in a
    # row are both recovered.
    rows, reach = [], {}
    for h in H_VALUES:
        lo, hi = 0, nbits // E // 4 + 1  # in units of 4 bits; lo works, hi fails
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if all(trial(4 * mid, h)[0] for _ in range(2)):
                lo = mid
            else:
                hi = mid
        reach[h] = 4 * lo
        rows.append([str(h), str(3 * h + 1), f"{predicted(nbits, h):.1f}", str(reach[h])])
        assert reach[h] <= predicted(nbits, h) + 4, "no better than the determinant bound allows"

    # One run shown in full, at the largest size, just inside its reach.
    h = H_VALUES[-1]
    ok, dim, swaps, R, x0 = trial(reach[h], h)
    assert ok
    check_lll(R)

    values = {
        "nbits": str(nbits),
        "pbits": str(BITS),
        "e": str(E),
        "limit_bits": str(nbits // E),
        "h_max": str(h),
        "dim_max": str(dim),
        "shown_bits": str(reach[h]),
        "shown_swaps": f"{swaps:,}",
        "reach_1": str(reach[1]),
        "pred_1": f"{predicted(nbits, 1):.1f}",
        "reach_max": str(reach[h]),
    }
    blocks = {
        "reach_table": [
            {
                "table": {
                    "caption": f"Predicted and recovered unknown low bits of a message from its e = 3 RSA ciphertext under a "
                               f"{nbits}-bit modulus: the largest multiple of 4 for which two fresh messages in "
                               "a row were recovered and checked. Coppersmith's limit is "
                               f"{nbits}/3 &asymp; {nbits // E} bits.",
                    "head": ["h", "Dimension", "Predicted", "Recovered"],
                    "rows": rows,
                    "numeric": [0, 1, 2, 3],
                }
            }
        ],
    }
    return {"values": values, "blocks": blocks}
