"""Pollard's rho on a small curve: one walk shown in full, then many measured.

The curve, the target, the walk and the statistics are all computed here at
build time. The page quotes nothing that this module did not produce.
"""

from __future__ import annotations

import math

from .arith import Rng, ec_add, ec_mul, ec_points, is_prime
from ..figures import rho_diagram

P_FIELD = 10007
A, B = 3, 6
TRIALS = 1000
TESKE_R = 20


def group():
    points = ec_points(A, B, P_FIELD)
    n = len(points) + 1
    assert is_prime(n), "the example needs a prime-order group"
    assert abs(n - (P_FIELD + 1)) <= 2 * math.isqrt(P_FIELD) + 1, "Hasse bound"
    generator = min(points)
    assert ec_mul(n, generator, A, P_FIELD) is None
    return n, generator


def partition(X, parts: int) -> int:
    """Which rule to apply at X. The point at infinity is a group element like
    any other; over thousands of walks the walk does land on it, so it gets a
    class of its own rather than an exception."""
    return 0 if X is None else X[0] % parts


def pollard_step(X, a, b, P, Q, n):
    """Pollard's original walk: the class of x mod 3 picks add-P, double, or add-Q."""
    s = partition(X, 3)
    if s == 0:
        return ec_add(X, P, A, P_FIELD), (a + 1) % n, b, "add P"
    if s == 1:
        return ec_add(X, X, A, P_FIELD), 2 * a % n, 2 * b % n, "double"
    return ec_add(X, Q, A, P_FIELD), a, (b + 1) % n, "add Q"


def walk_until_repeat(start, step):
    """Run a walk, remembering every point, until one repeats.

    Returns the list of (point, a, b, label) states and the index of the first
    visit to the repeated point. Real implementations do not store every point
    (see Floyd, Brent, and distinguished points); at this size storing them is
    the clearest way to show the shape of the walk.
    """
    seen = {}
    states = [start]
    while True:
        X = states[-1][0]
        if X in seen:
            return states, seen[X]
        seen[X] = len(states) - 1
        states.append(step(states[-1]))


def solve(state_i, state_j, n):
    (_, a1, b1, _), (_, a2, b2, _) = state_i, state_j
    if (b1 - b2) % n == 0:
        return None
    return (a2 - a1) * pow(b1 - b2, -1, n) % n


def fmt_point(X) -> str:
    return "O" if X is None else f"({X[0]}, {X[1]})"


def measure(n, P, rng, kind) -> tuple[float, float, int]:
    """Mean and standard error of (steps to first repeat)/sqrt(n), and failures."""
    ratios = []
    degenerate = 0
    for _ in range(TRIALS):
        k = rng.between(1, n - 1)
        Q = ec_mul(k, P, A, P_FIELD)
        if kind == "pollard":
            def step(state, P=P, Q=Q):
                return pollard_step(state[0], state[1], state[2], P, Q, n)
        else:
            mults = []
            for _ in range(TESKE_R):
                m1, m2 = rng.below(n), rng.below(n)
                mults.append((ec_add(ec_mul(m1, P, A, P_FIELD), ec_mul(m2, Q, A, P_FIELD), A, P_FIELD), m1, m2))

            def step(state, mults=mults):
                X, a, b, _ = state
                M, m1, m2 = mults[partition(X, TESKE_R)]
                return ec_add(X, M, A, P_FIELD), (a + m1) % n, (b + m2) % n, ""
        a0, b0 = rng.below(n), rng.below(n)
        X0 = ec_add(ec_mul(a0, P, A, P_FIELD), ec_mul(b0, Q, A, P_FIELD), A, P_FIELD)
        states, first = walk_until_repeat((X0, a0, b0, "start"), step)
        # The walk revisits a point after len(states) - 1 steps. A repeat with
        # b_i = b_j reveals nothing about k; it still counts as a repeat, and
        # how often it happens is reported separately.
        if solve(states[first], states[-1], n) != k:
            degenerate += 1
        ratios.append((len(states) - 1) / math.sqrt(n))
    mean = sum(ratios) / len(ratios)
    var = sum((r - mean) ** 2 for r in ratios) / (len(ratios) - 1)
    return mean, math.sqrt(var / len(ratios)), degenerate


def compute() -> dict:
    n, P = group()
    rng = Rng("isogenylabs/notes/pollard-rho/target")
    k = rng.between(1, n - 1)
    Q = ec_mul(k, P, A, P_FIELD)

    def step(state):
        return pollard_step(state[0], state[1], state[2], P, Q, n)

    # Draw starting points until the collision is usable (b_i != b_j). At this
    # size that almost always happens on the first try; the count is reported.
    attempts = 0
    while True:
        attempts += 1
        a0, b0 = rng.below(n), rng.below(n)
        X0 = ec_add(ec_mul(a0, P, A, P_FIELD), ec_mul(b0, Q, A, P_FIELD), A, P_FIELD)
        states, first = walk_until_repeat((X0, a0, b0, "start"), step)
        recovered = solve(states[first], states[-1], n)
        if recovered is not None:
            break
    assert recovered == k and ec_mul(recovered, P, A, P_FIELD) == Q

    last = len(states) - 1
    mu, lam = first, last - first
    Xi, ai, bi, _ = states[first]
    _, aj, bj, _ = states[-1]

    def row(i):
        X, a, b, _ = states[i]
        if i == last:
            nxt = f"repeats X<sub>{first}</sub>"
        else:
            nxt = states[i + 1][3]
        cls = partition(X, 3)
        return [str(i), fmt_point(X), str(a), str(b), str(cls), nxt]

    wanted = sorted({*range(0, 6), first - 1, first, first + 1, last - 1, last} & set(range(last + 1)))
    rows = []
    for position, i in enumerate(wanted):
        if position and i != wanted[position - 1] + 1:
            rows.append(["…", "", "", "", "", ""])
        rows.append(row(i))

    pollard_mean, pollard_se, pollard_bad = measure(n, P, Rng("isogenylabs/notes/pollard-rho/pollard"), "pollard")
    teske_mean, teske_se, teske_bad = measure(n, P, Rng("isogenylabs/notes/pollard-rho/teske"), "teske")
    predicted = math.sqrt(math.pi / 2)
    # Brent and Pollard's heuristic: an r-adding walk is slower than a random
    # function by a factor sqrt(1 - 1/r) (as stated by Bernstein, Lange and
    # Schwabe, "On the correct use of the negation map", PKC 2011).
    teske_predicted = predicted / math.sqrt(1 - 1 / TESKE_R)

    values = {
        "p": str(P_FIELD),
        "a": str(A),
        "b": str(B),
        "n": f"{n:,}",
        "n_plain": str(n),
        "trace": str(P_FIELD + 1 - n),
        "P": fmt_point(P),
        "Q": fmt_point(Q),
        "k": str(k),
        "sqrt_n": f"{math.sqrt(n):.1f}",
        "expected_steps": f"{predicted * math.sqrt(n):.0f}",
        "steps": str(last),
        "mu": str(mu),
        "lam": str(lam),
        "ratio": f"{last / math.sqrt(n):.2f}",
        "i": str(first),
        "j": str(last),
        "Xi": fmt_point(Xi),
        "ai": str(ai),
        "bi": str(bi),
        "aj": str(aj),
        "bj": str(bj),
        "num": str((aj - ai) % n),
        "den": str((bi - bj) % n),
        "den_inv": str(pow(bi - bj, -1, n)),
        "recovered": str(recovered),
        "start_attempts": str(attempts),
        "trials": f"{TRIALS:,}",
        "teske_r": str(TESKE_R),
        "predicted_S": f"{predicted:.4f}",
        "pollard_S": f"{pollard_mean:.3f}",
        "pollard_se": f"{pollard_se:.3f}",
        "teske_S": f"{teske_mean:.3f}",
        "teske_se": f"{teske_se:.3f}",
        "pollard_excess": f"{100 * (pollard_mean / predicted - 1):.0f}",
        "teske_excess": f"{100 * (teske_mean / predicted - 1):+.1f}",
        "teske_predicted": f"{teske_predicted:.3f}",
        "teske_penalty": f"{100 * (1 / math.sqrt(1 - 1 / TESKE_R) - 1):.1f}",
        "pollard_bad": str(pollard_bad),
        "teske_bad": str(teske_bad),
        "work_256": f"{predicted:.2f}",
    }
    blocks = {
        "walk_table": [{
            "table": {
                "caption": f"The walk from X<sub>0</sub>, with the rows around the repeat. Each row's last column is the step that produced the next row.",
                "head": ["i", "X<sub>i</sub>", "a<sub>i</sub>", "b<sub>i</sub>", "x mod 3", "next step"],
                "rows": rows,
                "numeric": [0, 2, 3, 4],
            }
        }],
        "rho_figure": [{
            "svg": rho_diagram(mu, lam),
            "caption": f"The walk drawn to scale: a tail of {mu} points, then a cycle of {lam}. "
                       f"X<sub>{first}</sub> is where the tail joins the cycle, and the only point the walk reaches twice.",
        }],
        "stats_table": [{
            "table": {
                "caption": f"Steps until the first repeated point, divided by &radic;n, over {TRIALS:,} random targets and starting points for each walk.",
                "head": ["Walk", "Mean", "Standard error"],
                "rows": [
                    ["Random function (prediction)", f"{predicted:.3f}", "—"],
                    [f"{TESKE_R}-adding walk (Brent–Pollard prediction)", f"{teske_predicted:.3f}", "—"],
                    [f"Teske, r = {TESKE_R} additions", f"{teske_mean:.3f}", f"{teske_se:.3f}"],
                    ["Pollard's original (add P, double, add Q)", f"{pollard_mean:.3f}", f"{pollard_se:.3f}"],
                ],
                "numeric": [1, 2],
            }
        }],
    }
    return {"values": values, "blocks": blocks}
