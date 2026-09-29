"""Baby-step giant-step and Pollard's kangaroos, measured on the rho curve.

The baby-step giant-step and kangaroo page quotes its numbers from here. Both
algorithms run on the same prime-order group as the Pollard rho example, so
the three can be compared directly. Every logarithm is checked by scalar
multiplication before it is counted.
"""

from __future__ import annotations

import math

from .arith import Rng, ec_add, ec_mul, ec_neg
from .rho import A, P_FIELD, group

TRIALS = 200
INTERVAL = 1000  # the kangaroo's secret lies in [0, INTERVAL)


def fmt(x: float) -> str:
    return f"{round(x):,}"


def bsgs(P, Q, n):
    """Returns (k, group operations, table size). Q = kP with 0 <= k < n."""
    m = math.isqrt(n - 1) + 1
    table, R, ops = {}, None, 0
    for j in range(m):  # baby steps: jP for j = 0 .. m-1
        table.setdefault(R, j)
        R = ec_add(R, P, A, P_FIELD)
        ops += 1
    step = ec_neg(ec_mul(m, P, A, P_FIELD), P_FIELD)
    G = Q
    for i in range(m):  # giant steps: Q - i m P
        if G in table:
            return (i * m + table[G]) % n, ops, len(table)
        G = ec_add(G, step, A, P_FIELD)
        ops += 1
    raise AssertionError("BSGS always finds k")  # pragma: no cover


def kangaroo_r(width: int) -> int:
    r = 1
    while (2 ** r - 1) / r < math.sqrt(width) / 2:
        r += 1
    return r


def kangaroo(P, Q, width, n):
    """Pollard's lambda method with a tame and a wild kangaroo, stepping in turn.

    Jumps are powers of two chosen by the x-coordinate, with mean about
    sqrt(width)/2. At this size every visited point is remembered; a real
    implementation keeps only distinguished points, at a small cost in steps.
    Returns (k, group operations)."""
    r = kangaroo_r(width)  # the fewest powers of two with mean jump >= sqrt(width)/2
    jumps = [2 ** i for i in range(r)]
    jump_pts = [ec_mul(s, P, A, P_FIELD) for s in jumps]

    def idx(X):
        return 0 if X is None else X[0] % r

    tame = [ec_mul(width, P, A, P_FIELD), width]  # starts at the top of the interval
    wild = [Q, 0]  # at k, distance travelled 0
    seen = {tame[0]: ("tame", tame[1]), wild[0]: ("wild", wild[1])}
    ops = 0
    while True:
        for kind, roo in (("tame", tame), ("wild", wild)):
            i = idx(roo[0])
            roo[0] = ec_add(roo[0], jump_pts[i], A, P_FIELD)
            roo[1] += jumps[i]
            ops += 1
            hit = seen.get(roo[0])
            if hit and hit[0] != kind:
                t = roo[1] if kind == "tame" else hit[1]
                w = roo[1] if kind == "wild" else hit[1]
                return (t - w) % n, ops
            if hit is None:
                seen[roo[0]] = (kind, roo[1])


def compute() -> dict:
    n, P = group()
    rng = Rng("isogenylabs/cryptanalysis/baby-step-giant-step")

    b_ops, b_worst = [], 0
    for _ in range(TRIALS):
        k = rng.below(n)
        Q = ec_mul(k, P, A, P_FIELD)
        got, ops, size = bsgs(P, Q, n)
        assert got == k and ec_mul(got, P, A, P_FIELD) == Q
        b_ops.append(ops)
        b_worst = max(b_worst, ops)
    m = math.isqrt(n - 1) + 1

    k_ops = []
    for _ in range(TRIALS):
        k = rng.below(INTERVAL)
        Q = ec_mul(k, P, A, P_FIELD)
        got, ops = kangaroo(P, Q, INTERVAL, n)
        assert got == k and ec_mul(got, P, A, P_FIELD) == Q
        k_ops.append(ops)

    mean_b = sum(b_ops) / TRIALS
    mean_k = sum(k_ops) / TRIALS
    values = {
        "p": f"{P_FIELD:,}",
        "n": f"{n:,}",
        "sqrt_n": fmt(math.sqrt(n)),
        "m": f"{m:,}",
        "trials": str(TRIALS),
        "bsgs_mean": fmt(mean_b),
        "bsgs_worst": f"{b_worst:,}",
        "bsgs_bound": f"{2 * m:,}",
        "bsgs_ratio": f"{mean_b / math.sqrt(n):.2f}",
        "interval": f"{INTERVAL:,}",
        "sqrt_w": fmt(math.sqrt(INTERVAL)),
        "kang_mean": fmt(mean_k),
        "kang_median": fmt(sorted(k_ops)[TRIALS // 2]),
        "kang_max": f"{max(k_ops):,}",
        "kang_ratio": f"{mean_k / math.sqrt(INTERVAL):.2f}",
    }
    values["jump_mean"] = f"{(2 ** kangaroo_r(INTERVAL) - 1) / kangaroo_r(INTERVAL):.1f}"
    values["jump_count"] = str(kangaroo_r(INTERVAL))
    return {"values": values, "blocks": {}}
