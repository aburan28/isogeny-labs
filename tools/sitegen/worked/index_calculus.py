"""Index calculus, end to end, twice: in F_p^* and on an elliptic curve over F_{p^2}.

Part A is the classical algorithm on a 14-bit safe prime. Part B is Gaudry's
version for a curve over a quadratic extension, using Semaev's third summation
polynomial, a Weil restriction to F_p, and a resultant to solve the resulting
system. Both run completely at build time, and both check their own answers:
every factor-base logarithm is verified by exponentiation or scalar
multiplication before the page is allowed to print it.
"""

from __future__ import annotations

import math

from ..figures import sparsity
from .arith import CurveFp2, Fp2, Rng, factor, is_prime, legendre, sqrt_mod

# ---------------------------------------------------------------------------
# Part A: the multiplicative group of F_p

A_P = 10163  # a safe prime: (p - 1) / 2 = 5081 is prime
A_BOUND = 13  # factor base: the primes up to 13


def primitive_root_outside(p: int, q: int, avoid: set[int]) -> int:
    # A prime generator outside the factor base keeps every factor-base
    # logarithm unknown; a composite like 15 would itself be smooth.
    for g in range(2, p):
        if g in avoid or not is_prime(g):
            continue
        if pow(g, 2, p) != 1 and pow(g, q, p) != 1:
            return g
    raise ValueError("no primitive root")  # pragma: no cover


def smooth_exponents(value: int, base: list[int]) -> list[int] | None:
    exps = []
    for ell in base:
        e = 0
        while value % ell == 0:
            value //= ell
            e += 1
        exps.append(e)
    return exps if value == 1 else None


def solve_mod_prime(rows: list[list[int]], rhs: list[int], m: int) -> tuple[list[int | None], int]:
    """Gaussian elimination over Z/mZ for prime m.

    Returns the value of every variable that the system determines uniquely
    (None for the rest) and the rank.
    """
    ncols = len(rows[0])
    mat = [list(r) + [c] for r, c in zip(rows, rhs)]
    pivots = []
    row = 0
    for col in range(ncols):
        pivot = next((i for i in range(row, len(mat)) if mat[i][col] % m), None)
        if pivot is None:
            continue
        mat[row], mat[pivot] = mat[pivot], mat[row]
        inv = pow(mat[row][col], -1, m)
        mat[row] = [v * inv % m for v in mat[row]]
        for i in range(len(mat)):
            if i != row and mat[i][col] % m:
                factor_ = mat[i][col]
                mat[i] = [(vi - factor_ * vr) % m for vi, vr in zip(mat[i], mat[row])]
        pivots.append(col)
        row += 1
        if row == len(mat):
            break
    values: list[int | None] = [None] * ncols
    pivot_set = set(pivots)
    for r, col in enumerate(pivots):
        # A pivot variable is determined when its row mentions no free column.
        if all(mat[r][c] % m == 0 for c in range(ncols) if c not in pivot_set):
            values[col] = mat[r][ncols]
    return values, len(pivots)


def part_a() -> tuple[dict, dict]:
    p = A_P
    q = (p - 1) // 2
    assert is_prime(p) and is_prime(q)
    base = [ell for ell in range(2, A_BOUND + 1) if is_prime(ell)]
    g = primitive_root_outside(p, q, set(base))
    rng = Rng("isogenylabs/notes/index-calculus/part-a")

    # Relation collection: random exponents until the logs are pinned down mod q.
    relations = []
    tried = 0
    values: list[int | None] = [None] * len(base)
    while True:
        e = rng.between(1, p - 2)
        tried += 1
        exps = smooth_exponents(pow(g, e, p), base)
        if exps is None:
            continue
        relations.append((e, pow(g, e, p), exps))
        if len(relations) >= len(base):
            values, rank = solve_mod_prime([r[2] for r in relations], [r[0] % q for r in relations], q)
            if all(v is not None for v in values):
                break

    # The mod-2 part of each logarithm is free: log(ell) is even exactly when
    # ell is a square mod p, because g is a primitive root.
    logs = []
    for ell, mod_q in zip(base, values):
        mod_2 = 0 if legendre(ell, p) == 1 else 1
        # Chinese remainder theorem: x = mod_q (mod q), x = mod_2 (mod 2).
        x = mod_q if mod_q % 2 == mod_2 else mod_q + q
        assert pow(g, x, p) == ell, "factor-base logarithm fails verification"
        logs.append((ell, mod_q, mod_2, x))

    # Exact smoothness probability for comparison with what the search saw.
    smooth_count = sum(1 for v in range(1, p) if smooth_exponents(v, base) is not None)

    # The individual logarithm: find s with h * g^s smooth.
    h = rng.between(2, p - 1)
    s_tries = 0
    while True:
        s = rng.between(0, p - 2)
        s_tries += 1
        exps = smooth_exponents(h * pow(g, s, p) % p, base)
        if exps is not None:
            break
    x = (sum(c * lg for c, (_, _, _, lg) in zip(exps, logs)) - s) % (p - 1)
    assert pow(g, x, p) == h, "target logarithm fails verification"

    def factor_html(exps: list[int]) -> str:
        terms = [f"{ell}<sup>{c}</sup>" if c > 1 else str(ell) for ell, c in zip(base, exps) if c]
        return " &middot; ".join(terms)

    relation_rows = [[str(i + 1), str(e), str(v), factor_html(ex)] for i, (e, v, ex) in enumerate(relations)]
    log_rows = [
        [str(ell), str(mq), "yes" if m2 == 0 else "no", str(m2), str(x_)]
        for ell, mq, m2, x_ in logs
    ]
    target_value = h * pow(g, s, p) % p
    target_expr = " + ".join(
        f"{c}&middot;{lg}" if c > 1 else str(lg) for c, (_, _, _, lg) in zip(exps, logs) if c
    )
    vals = {
        "a_p": str(p),
        "a_q": str(q),
        "a_g": str(g),
        "a_bound": str(A_BOUND),
        "a_base": ", ".join(str(ell) for ell in base),
        "a_base_size": str(len(base)),
        "a_tried": str(tried),
        "a_found": str(len(relations)),
        "a_rate": f"{100 * len(relations) / tried:.1f}",
        "a_exact_rate": f"{100 * smooth_count / (p - 1):.1f}",
        "a_smooth_count": f"{smooth_count:,}",
        "a_h": str(h),
        "a_s": str(s),
        "a_s_tries": str(s_tries),
        "a_target_value": str(target_value),
        "a_target_factor": factor_html(exps),
        "a_target_expr": target_expr,
        "a_x": str(x),
        "a_rank": str(len(base)),
        "a_pm1": str(p - 1),
        "a_expected_found": f"{tried * smooth_count / (p - 1):.1f}",
        "a_luck": "more" if len(relations) > tried * smooth_count / (p - 1) else "fewer",
    }
    blocks = {
        "a_relations": [{
            "table": {
                "caption": f"Every relation the search found, in order. Each says e &equiv; &Sigma; c<sub>i</sub>&middot;log(&ell;<sub>i</sub>) (mod {p - 1}).",
                "head": ["#", "e", f"{g}<sup>e</sup> mod {p}", "factorisation"],
                "rows": relation_rows,
                "numeric": [0, 1, 2],
            }
        }],
        "a_logs": [{
            "table": {
                "caption": f"The factor base's logarithms: the linear algebra gives them mod {q}, the Legendre symbol gives them mod 2, and the Chinese remainder theorem combines the two. The build checks {g}<sup>log</sup> = &ell; for every row.",
                "head": ["&ell;", f"log mod {q}", f"square mod {p}?", "log mod 2", f"log<sub>{g}</sub> &ell;"],
                "rows": log_rows,
                "numeric": [0, 1, 3, 4],
            }
        }],
    }
    return vals, blocks


# ---------------------------------------------------------------------------
# Part B: an elliptic curve over F_{p^2}

B_P = 263
B_A = (1, 0)  # a = 1
B_B = (1, 1)  # b = 1 + t
B_ORDER = 69383


def summation_s3(F: Fp2, a, b, x1, x2, x3):
    """Semaev's S_3 for y^2 = x^3 + a x + b, evaluated in F_{p^2}."""
    d = F.sub(x1, x2)
    s = F.add(x1, x2)
    pr = F.mul(x1, x2)
    t1 = F.mul(F.mul(d, d), F.mul(x3, x3))
    t2 = F.scale(2, F.mul(F.add(F.mul(s, F.add(pr, a)), F.scale(2, b)), x3))
    u = F.sub(pr, a)
    t3 = F.sub(F.mul(u, u), F.scale(4, F.mul(b, s)))
    return F.add(F.sub(t1, t2), t3)


def s3_in_symmetric(F: Fp2, a, b, x3) -> dict[str, tuple[int, int]]:
    """S_3(x1, x2, x3) rewritten in e1 = x1 + x2 and e2 = x1 x2.

    S_3 = (e1^2 - 4 e2) x3^2 - 2 (e1 (e2 + a) + 2 b) x3 + (e2 - a)^2 - 4 b e1.
    Returns the coefficient of each monomial, as elements of F_{p^2}.
    """
    x3sq = F.mul(x3, x3)
    return {
        "e1^2": x3sq,
        "e1e2": F.scale(-2, x3),
        "e2^2": (1, 0),
        "e1": F.sub(F.scale(-2, F.mul(a, x3)), F.scale(4, b)),
        "e2": F.sub(F.scale(-4, x3sq), F.scale(2, a)),
        "1": F.sub(F.mul(a, a), F.scale(4, F.mul(b, x3))),
    }


def poly_eval(coeffs: list[int], x: int, p: int) -> int:
    acc = 0
    for c in reversed(coeffs):
        acc = (acc * x + c) % p
    return acc


def poly_mul(u: list[int], v: list[int], p: int) -> list[int]:
    out = [0] * (len(u) + len(v) - 1)
    for i, a in enumerate(u):
        for j, b in enumerate(v):
            out[i + j] = (out[i + j] + a * b) % p
    return out


def poly_add(u: list[int], v: list[int], p: int) -> list[int]:
    n = max(len(u), len(v))
    return [((u[i] if i < len(u) else 0) + (v[i] if i < len(v) else 0)) % p for i in range(n)]


def poly_fmt(coeffs: list[int], var: str) -> str:
    """Polynomial with ascending coefficients, printed highest degree first."""
    terms = []
    for deg in range(len(coeffs) - 1, -1, -1):
        c = coeffs[deg]
        if c == 0:
            continue
        mono = "" if deg == 0 else (var if deg == 1 else f"{var}<sup>{deg}</sup>")
        coef = str(c) if (c != 1 or deg == 0) else ""
        terms.append(f"{coef}{mono}")
    return " + ".join(terms) if terms else "0"


class Decomposer:
    """Write a point as a sum of two factor-base points, if it can be done."""

    def __init__(self, E: CurveFp2) -> None:
        self.E = E
        self.F = E.F
        p = self.F.p
        # The factor base: points whose x-coordinate lies in the subfield F_p.
        # Each x contributes a pair {P, -P}; the class is named by x, and the
        # representative is the member whose y is smaller as a (u, v) tuple.
        self.base: dict[int, tuple] = {}
        for x0 in range(p):
            y = self.F.sqrt(E.rhs((x0, 0)))
            if y is None:
                continue
            rep = min(y, self.F.neg(y))
            self.base[x0] = ((x0, 0), rep)
        self.index = {x0: i for i, x0 in enumerate(sorted(self.base))}

    def system(self, xR):
        """The Weil restriction of S_3(x1, x2, xR) = 0 as polynomials in e1.

        S_3 = C0 + C1 t with C0, C1 over F_p. C1 is linear in e2, and C0 is
        monic quadratic in e2:  C1 = alpha e2 + beta,  C0 = e2^2 + delta e2 + phi.
        """
        c = s3_in_symmetric(self.F, self.E.a, self.E.b, xR)
        part = lambda key, i: c[key][i]  # noqa: E731  (0: F_p part, 1: t part)
        alpha = [part("e2", 1), part("e1e2", 1)]
        beta = [part("1", 1), part("e1", 1), part("e1^2", 1)]
        delta = [part("e2", 0), part("e1e2", 0)]
        phi = [part("1", 0), part("e1", 0), part("e1^2", 0)]
        assert part("e2^2", 0) == 1 and part("e2^2", 1) == 0
        return alpha, beta, delta, phi

    def resultant(self, alpha, beta, delta, phi) -> list[int]:
        """Res_{e2}(C0, C1) = beta^2 - alpha beta delta + alpha^2 phi, a quartic in e1."""
        p = self.F.p
        t1 = poly_mul(beta, beta, p)
        t2 = poly_mul(poly_mul(alpha, beta, p), delta, p)
        t3 = poly_mul(poly_mul(alpha, alpha, p), phi, p)
        return poly_add(poly_add(t1, [(-c) % p for c in t2], p), t3, p)

    def decompose(self, R, trace: bool = False):
        """Return (relation, detail) with relation = [(sign, x0), (sign, x0)] or None."""
        F, E, p = self.F, self.E, self.F.p
        if R is None:
            return None, None
        alpha, beta, delta, phi = self.system(R[0])
        res = self.resultant(alpha, beta, delta, phi)
        roots = [e1 for e1 in range(p) if poly_eval(res, e1, p) == 0]
        detail = {"alpha": alpha, "beta": beta, "delta": delta, "phi": phi, "res": res, "roots": roots}
        for e1 in roots:
            a_val = poly_eval(alpha, e1, p)
            b_val = poly_eval(beta, e1, p)
            if a_val:
                e2s = [(-b_val) * pow(a_val, -1, p) % p]
            elif b_val == 0:
                # C1 vanishes for this e1; solve the quadratic C0 for e2.
                dd, ff = poly_eval(delta, e1, p), poly_eval(phi, e1, p)
                disc = sqrt_mod(dd * dd - 4 * ff, p)
                e2s = [] if disc is None else sorted({(-dd + disc) * pow(2, -1, p) % p, (-dd - disc) * pow(2, -1, p) % p})
            else:
                e2s = []
            for e2 in e2s:
                root = sqrt_mod(e1 * e1 - 4 * e2, p)
                if root is None:
                    continue
                x1 = (e1 + root) * pow(2, -1, p) % p
                x2 = (e1 - root) * pow(2, -1, p) % p
                if x1 not in self.base or x2 not in self.base:
                    continue
                P1, P2 = self.base[x1], self.base[x2]
                for s1 in (1, -1):
                    for s2 in (1, -1):
                        S = E.add(P1 if s1 == 1 else E.neg(P1), P2 if s2 == 1 else E.neg(P2))
                        if S == R:
                            detail.update({"e1": e1, "e2": e2, "x1": x1, "x2": x2, "s1": s1, "s2": s2})
                            return [(s1, x1), (s2, x2)], detail
        return None, detail


def part_b() -> tuple[dict, dict]:
    p = B_P
    F = Fp2(p)
    E = CurveFp2(F, B_A, B_B)
    n = B_ORDER
    rng = Rng("isogenylabs/notes/index-calculus/part-b")

    # Establish the group order without counting 69,000 x-coordinates: n is
    # prime, it lies in the Hasse interval, and a point of order n exists.
    # The interval is 4p wide, narrower than n, so #E = n exactly.
    assert is_prime(n)
    assert abs(n - (p * p + 1)) <= 2 * p
    while True:
        x = (rng.below(p), rng.below(p))
        y = F.sqrt(E.rhs(x))
        if y is not None:
            P = (x, y)
            break
    assert E.contains(P) and E.mul(n, P) is None

    # Check the summation polynomial against the group law before using it.
    for _ in range(5):
        U, V = E.mul(rng.between(1, n - 1), P), E.mul(rng.between(1, n - 1), P)
        W = E.add(U, V)
        assert summation_s3(F, E.a, E.b, U[0], V[0], W[0]) == (0, 0)

    k = rng.between(1, n - 1)
    Q = E.mul(k, P)
    D = Decomposer(E)
    classes = len(D.base)

    # Exactly which points decompose: add every pair of factor-base points.
    # At this size that is 40,000 additions and settles the question the
    # heuristic only estimates.
    members = [pt for x0 in sorted(D.base) for pt in (D.base[x0], E.neg(D.base[x0]))]
    sums = {E.add(members[i], members[j]) for i in range(len(members)) for j in range(i, len(members))}
    sums.discard(None)
    pairs = len(members) * (len(members) + 1) // 2

    # Relation collection: R = a P for random a, decomposed over the factor base.
    rows, rhs, shown = [], [], None
    attempts = 0
    target_relations = classes + 10
    while len(rows) < target_relations:
        a = rng.between(1, n - 1)
        R = E.mul(a, P)
        attempts += 1
        relation, detail = D.decompose(R)
        if relation is None:
            continue
        row = [0] * classes
        for sign, x0 in relation:
            row[D.index[x0]] = (row[D.index[x0]] + sign) % n
        if not any(row):
            continue  # R = P1 - P1: carries no information
        if shown is None and relation[0][1] != relation[1][1] and detail["roots"]:
            shown = (a, R, relation, detail)
        rows.append(row)
        rhs.append(a)

    logs, rank = solve_mod_prime(rows, rhs, n)
    determined = [x0 for x0 in sorted(D.base) if logs[D.index[x0]] is not None]
    for x0 in determined:
        assert E.mul(logs[D.index[x0]], P) == D.base[x0], "factor-base logarithm fails verification"

    # Descent: find c with Q + c P decomposing over determined classes.
    descent_tries = 0
    while True:
        c = rng.between(1, n - 1)
        descent_tries += 1
        R = E.add(Q, E.mul(c, P))
        relation, _ = D.decompose(R)
        if relation is None:
            continue
        if all(logs[D.index[x0]] is not None for _, x0 in relation):
            break
    k_found = (sum(sign * logs[D.index[x0]] for sign, x0 in relation) - c) % n
    assert k_found == k and E.mul(k_found, P) == Q

    # ---- presentation ----
    a_shown, R_shown, rel_shown, det = shown

    def sgn(s):
        return "+" if s == 1 else "&minus;"

    def pt(x0):
        return f"P<sub>{x0}</sub>"

    def relation_html(row) -> str:
        out = ""
        for x0 in sorted(D.base):
            coef = row[D.index[x0]]
            if not coef:
                continue
            signed = coef if coef <= n // 2 else coef - n
            mag = "" if abs(signed) == 1 else f"{abs(signed)}&thinsp;"
            term = f"{mag}log {pt(x0)}"
            if not out:
                out = ("&minus;" if signed < 0 else "") + term
            else:
                out += (" &minus; " if signed < 0 else " + ") + term
        return out

    rel_rows = [[str(i + 1), str(a), relation_html(row)] for i, (row, a) in enumerate(zip(rows[:8], rhs[:8]))]

    def signed_sum(terms: list[tuple[int, str]]) -> str:
        out = ""
        for sign, text in terms:
            if not out:
                out = ("&minus;" if sign < 0 else "") + text
            else:
                out += (" &minus; " if sign < 0 else " + ") + text
        return out

    shown_terms = [(det["s1"], pt(det["x1"])), (det["s2"], pt(det["x2"]))]
    desc_terms = [(s, pt(x0)) for s, x0 in relation]
    desc_logs = [(s, str(logs[D.index[x0]])) for s, x0 in relation]

    nnz = [[j for j, v in enumerate(row) if v] for row in rows]
    two_term = sum(1 for cols in nnz if len(cols) == 2)
    rho_steps = math.sqrt(math.pi * n / 2)
    vals = {
        "b_p": str(p),
        "b_r": str(F.r),
        "b_n": f"{n:,}",
        "b_n_plain": str(n),
        "b_hasse_lo": f"{p * p + 1 - 2 * p:,}",
        "b_hasse_hi": f"{p * p + 1 + 2 * p:,}",
        "b_P": f"({F.fmt(P[0])}, {F.fmt(P[1])})",
        "b_Q": f"({F.fmt(Q[0])}, {F.fmt(Q[1])})",
        "b_classes": str(classes),
        "b_points": str(2 * classes),
        "b_half_p": f"{p / 2:.1f}",
        "b_a": str(a_shown),
        "b_xR": F.fmt(R_shown[0]),
        "b_alpha": poly_fmt(det["alpha"], "e<sub>1</sub>"),
        "b_beta": poly_fmt(det["beta"], "e<sub>1</sub>"),
        "b_delta": poly_fmt(det["delta"], "e<sub>1</sub>"),
        "b_phi": poly_fmt(det["phi"], "e<sub>1</sub>"),
        "b_res": poly_fmt(det["res"], "e<sub>1</sub>"),
        "b_roots": ", ".join(str(r) for r in det["roots"]),
        "b_nroots": str(len(det["roots"])),
        "b_e1": str(det["e1"]),
        "b_e2": str(det["e2"]),
        "b_x1": str(det["x1"]),
        "b_x2": str(det["x2"]),
        "b_s1": sgn(det["s1"]),
        "b_s2": sgn(det["s2"]),
        "b_rel_x1": pt(rel_shown[0][1]),
        "b_rel_x2": pt(rel_shown[1][1]),
        "b_attempts": str(attempts),
        "b_relations": str(len(rows)),
        "b_rows": str(len(rows)),
        "b_cols": str(classes),
        "b_two_term": str(two_term),
        "b_rank": str(rank),
        "b_determined": str(len(determined)),
        "b_k": str(k),
        "b_c": str(c),
        "b_descent_tries": str(descent_tries),
        "b_desc_x1": pt(relation[0][1]),
        "b_desc_x2": pt(relation[1][1]),
        "b_desc_s1": sgn(relation[0][0]),
        "b_desc_s2": sgn(relation[1][0]),
        "b_log1": str(logs[D.index[relation[0][1]]]),
        "b_log2": str(logs[D.index[relation[1][1]]]),
        "b_rho_steps": f"{rho_steps:.0f}",
        "b_members": str(len(members)),
        "b_pairs": f"{pairs:,}",
        "b_pairs_frac": f"{100 * pairs / (n - 1):.1f}",
        "b_decomposable": f"{len(sums):,}",
        "b_nonzero": f"{n - 1:,}",
        "b_exact_frac": f"{100 * len(sums) / (n - 1):.1f}",
        "b_poisson_frac": f"{100 * (1 - math.exp(-pairs / (n - 1))):.1f}",
        "b_sampled_frac": f"{100 * len(rows) / attempts:.1f}",
        "b_roots_phrase": (f"exactly one root in F<sub>{p}</sub>, e<sub>1</sub> = {det['roots'][0]}"
                           if len(det["roots"]) == 1
                           else f"{len(det['roots'])} roots in F<sub>{p}</sub>: e<sub>1</sub> = {', '.join(map(str, det['roots']))}; the one that leads to factor-base points is e<sub>1</sub> = {det['e1']}"),
        "b_shown_expr": signed_sum(shown_terms),
        "b_shown_log_expr": signed_sum([(s, "log " + x) for s, x in shown_terms]),
        "b_desc_expr": signed_sum(desc_terms),
        "b_desc_log_expr": signed_sum([(s, "log " + x) for s, x in desc_terms]),
        "b_desc_num_expr": signed_sum(desc_logs) + f" &minus; {c}",
        "b_undetermined": str(classes - len(determined)),
        "b_rows_minus_cols": str(len(rows) - classes),
    }
    blocks = {
        "b_relations_table": [{
            "table": {
                "caption": f"The first eight of the {len(rows)} relations. Each row is one random multiple mP that decomposed; P<sub>x</sub> is the factor-base point with x-coordinate x.",
                "head": ["#", "m", f"m &equiv; &hellip; (mod {n:,})"],
                "rows": rel_rows,
                "numeric": [0, 1],
            }
        }],
        "b_sparsity": [{
            "svg": sparsity(
                nnz, classes,
                f"The relation matrix: {len(rows)} rows and {classes} columns, with one or two nonzero entries per row.",
            ),
            "caption": f"The whole relation matrix, {len(rows)} rows by {classes} columns: one mark per nonzero entry. "
                       f"{two_term} rows have two entries and the rest have one.",
        }],
    }
    return vals, blocks


def compute() -> dict:
    a_vals, a_blocks = part_a()
    b_vals, b_blocks = part_b()
    return {"values": {**a_vals, **b_vals}, "blocks": {**a_blocks, **b_blocks}}
