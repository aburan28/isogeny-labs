"""The supersingular 2-isogeny graph for p = 431, computed and checked.

Everything the isogeny note shows comes from here: the vertices of the graph
(the supersingular j-invariants over F_{p^2}), its edges (roots of the modular
polynomial Phi_2), one 2-isogeny written out with Velu's formulas and checked
to be a group homomorphism, the group order of the starting curve counted
point by point, and a secret walk of the kind SIDH-style schemes used as keys.

p = 431 = 2^4 * 3^3 - 1 is the prime of Costello's "Supersingular isogeny key
exchange for beginners", which makes this graph easy to compare with.
"""

from __future__ import annotations

import math
from collections import deque

from ..figures import isogeny_graph
from .arith import CurveFp2, Fp2, Rng, is_prime

P = 431

# Phi_2(X, Y), the classical modular polynomial of level 2, as {(i, j): c}
# for the monomial X^i Y^j. It vanishes at (j(E), j(E')) exactly when there is
# a 2-isogeny E -> E'.
PHI2 = {
    (3, 0): 1, (0, 3): 1, (2, 2): -1,
    (2, 1): 1488, (1, 2): 1488,
    (2, 0): -162000, (0, 2): -162000,
    (1, 1): 40773375,
    (1, 0): 8748000000, (0, 1): 8748000000,
    (0, 0): -157464000000000,
}


def check_phi2() -> None:
    """Phi_2(1728, Y) = (Y - 1728)(Y - 287496)^2 over the integers.

    y^2 = x^3 + x (j = 1728) has one 2-isogeny to itself, with kernel (0, 0),
    and two to the curve with j = 66^3 = 287496, with kernels (+-i, 0). A wrong
    coefficient would break this identity.
    """
    coeffs = [0, 0, 0, 0]
    for (i, j), c in PHI2.items():
        coeffs[j] += c * 1728 ** i
    expected = [-1728 * 287496 ** 2, 287496 ** 2 + 2 * 1728 * 287496, -(1728 + 2 * 287496), 1]
    assert coeffs == expected, "Phi_2 coefficients"
    assert all(PHI2[(i, j)] == PHI2[(j, i)] for (i, j) in PHI2), "Phi_2 is symmetric"


# ---------------------------------------------------------------------------
# Polynomials over F_{p^2}: lists of field elements, lowest degree first.


class Poly:
    def __init__(self, F: Fp2) -> None:
        self.F = F
        self.zero = (0, 0)
        self.one = (1, 0)

    def trim(self, a):
        while a and a[-1] == self.zero:
            a = a[:-1]
        return a

    def sub(self, a, b):
        n = max(len(a), len(b))
        a = a + [self.zero] * (n - len(a))
        b = b + [self.zero] * (n - len(b))
        return self.trim([self.F.sub(x, y) for x, y in zip(a, b)])

    def mul(self, a, b):
        if not a or not b:
            return []
        out = [self.zero] * (len(a) + len(b) - 1)
        for i, x in enumerate(a):
            for j, y in enumerate(b):
                out[i + j] = self.F.add(out[i + j], self.F.mul(x, y))
        return self.trim(out)

    def divmod(self, a, b):
        F = self.F
        a, b = self.trim(list(a)), self.trim(list(b))
        inv = F.inv(b[-1])
        q = [self.zero] * max(len(a) - len(b) + 1, 1)
        while len(a) >= len(b) and a:
            coef = F.mul(a[-1], inv)
            shift = len(a) - len(b)
            q[shift] = coef
            for i, y in enumerate(b):
                a[i + shift] = F.sub(a[i + shift], F.mul(coef, y))
            a = self.trim(a)
        return self.trim(q), a

    def monic(self, a):
        inv = self.F.inv(a[-1])
        return [self.F.mul(c, inv) for c in a]

    def gcd(self, a, b):
        a, b = self.trim(a), self.trim(b)
        while b:
            a, b = b, self.divmod(a, b)[1]
        return self.monic(a) if a else a

    def powmod(self, base, e, mod):
        result, base = [self.one], self.divmod(base, mod)[1]
        while e:
            if e & 1:
                result = self.divmod(self.mul(result, base), mod)[1]
            base = self.divmod(self.mul(base, base), mod)[1]
            e >>= 1
        return result

    def roots(self, f, rng: Rng):
        """Distinct roots in F_{p^2}, by Cantor-Zassenhaus equal-degree splitting."""
        F, q = self.F, self.F.p ** 2
        f = self.monic(self.trim(f))
        x = [self.zero, self.one]
        # g = gcd(f, x^q - x) is the product of the distinct linear factors.
        g = self.gcd(f, self.sub(self.powmod(x, q, f), x))
        found = []

        def split(h):
            if len(h) == 2:
                found.append(F.neg(self.monic(h)[0]))
                return
            while True:
                delta = (rng.below(F.p), rng.below(F.p))
                t = self.sub(self.powmod([delta, self.one], (q - 1) // 2, h), [self.one])
                d = self.gcd(h, t)
                if 1 < len(d) < len(h):
                    split(d)
                    split(self.divmod(h, d)[0])
                    return

        if len(g) > 1:
            split(g)
        return sorted(found)

    def multiplicity(self, f, r):
        m = 0
        lin = [self.F.neg(r), self.one]
        while True:
            quotient, rem = self.divmod(f, lin)
            if rem:
                return m
            f, m = quotient, m + 1


def phi2_at(F: Fp2, j):
    """Phi_2(j, Y) as a polynomial in Y over F_{p^2}."""
    coeffs = [(0, 0)] * 4
    powers = [(1, 0), j, F.mul(j, j), F.mul(F.mul(j, j), j)]
    for (i, k), c in PHI2.items():
        coeffs[k] = F.add(coeffs[k], F.scale(c % F.p, powers[i]))
    return coeffs


def j_invariant(F: Fp2, a, b):
    a3 = F.mul(F.mul(a, a), a)
    num = F.scale(1728 * 4 % F.p, a3)
    den = F.add(F.scale(4, a3), F.scale(27, F.mul(b, b)))
    return F.mul(num, F.inv(den))


def supersingular_count(p: int) -> int:
    """floor(p/12) + 0, 1, 1, 2 for p = 1, 5, 7, 11 mod 12 (Silverman, AEC V.4.1)."""
    return p // 12 + {1: 0, 5: 1, 7: 1, 11: 2}[p % 12]


def build_graph(F: Fp2, poly: Poly, rng: Rng, start):
    """Breadth-first search from `start` over roots of Phi_2(j, Y)."""
    edges: dict = {}
    seen = [start]
    queue = deque([start])
    while queue:
        j = queue.popleft()
        f = phi2_at(F, j)
        nbrs = []
        for r in poly.roots(f, rng):
            nbrs += [r] * poly.multiplicity(f, r)
        assert len(nbrs) == 3, "Phi_2(j, Y) splits completely for supersingular j"
        edges[j] = nbrs
        for r in nbrs:
            if r not in edges and r not in queue:
                queue.append(r)
                seen.append(r)
    return seen, edges


def compute() -> dict:
    check_phi2()
    p = P
    assert is_prime(p) and p % 4 == 3 and p + 1 == 2 ** 4 * 3 ** 3
    F = Fp2(p, nonresidue=-1, symbol="i")
    poly = Poly(F)
    rng = Rng("isogenylabs/notes/isogenies")
    j1728 = (1728 % p, 0)

    vertices, edges = build_graph(F, poly, rng, j1728)
    assert len(vertices) == supersingular_count(p), "vertex count matches the formula"
    in_fp = [v for v in vertices if v[1] == 0]

    # Distances from j = 1728, and the diameter.
    def bfs(src):
        dist = {src: 0}
        dq = deque([src])
        while dq:
            u = dq.popleft()
            for w in edges[u]:
                if w not in dist:
                    dist[w] = dist[u] + 1
                    dq.append(w)
        return dist

    dist0 = bfs(j1728)
    layers = [sum(1 for d in dist0.values() if d == k) for k in range(max(dist0.values()) + 1)]
    diameter = max(max(bfs(v).values()) for v in vertices)
    loops = [v for v in vertices if v in edges[v]]

    # The starting curve y^2 = x^3 + x: count its points over F_{p^2} outright.
    E0 = CurveFp2(F, (1, 0), (0, 0))
    count = E0.point_count()
    assert count == (p + 1) ** 2

    # One 2-isogeny by Velu's formulas, from a curve in the middle of the graph.
    target = next(v for v in vertices if v[1] != 0 and v not in (j1728, (0, 0)) and dist0[v] == 3)
    jj = target
    k1728 = F.sub((1728 % p, 0), jj)
    a = F.scale(3, F.mul(jj, k1728))  # E_j: y^2 = x^3 + 3j(1728-j) x + 2j(1728-j)^2
    b = F.scale(2, F.mul(jj, F.mul(k1728, k1728)))
    assert j_invariant(F, a, b) == jj
    E = CurveFp2(F, a, b)
    x0 = poly.roots([b, a, (0, 0), (1, 0)], rng)[0]  # a root of x^3 + a x + b: a 2-torsion point
    t = F.add(F.scale(3, F.mul(x0, x0)), a)
    w = F.mul(x0, t)
    a2, b2 = F.sub(a, F.scale(5, t)), F.sub(b, F.scale(7, w))
    E2 = CurveFp2(F, a2, b2)
    j2 = j_invariant(F, a2, b2)
    assert j2 in edges[jj], "Velu's codomain is a 2-isogeny neighbour"

    def phi(Pt):
        if Pt is None or Pt[0] == x0:
            return None
        x, y = Pt
        u = F.inv(F.sub(x, x0))
        return (F.add(x, F.mul(t, u)), F.mul(y, F.sub((1, 0), F.mul(t, F.mul(u, u)))))

    def random_point():
        while True:
            x = (rng.below(p), rng.below(p))
            y = F.sqrt(E.rhs(x))
            if y is not None:
                return (x, y)

    samples = [(random_point(), random_point()) for _ in range(20)]
    for U, V in samples:
        assert E2.contains(phi(U)) and phi(E.add(U, V)) == E2.add(phi(U), phi(V)), "phi is a homomorphism"
    U0 = samples[0][0]
    image = phi(U0)

    # A secret walk: six non-backtracking steps from j = 1728.
    walk = [j1728]
    prev = None
    for _ in range(6):
        options = [v for v in edges[walk[-1]] if v != prev]
        nxt = options[rng.below(len(options))]
        prev = walk[-1]
        walk.append(nxt)

    index = {v: n for n, v in enumerate(vertices)}
    edge_list = sorted({tuple(sorted((index[u], index[v]))) for u in vertices for v in edges[u]})
    walk_idx = [index[v] for v in walk]

    fmt = F.fmt
    values = {
        "i_p": str(p),
        "i_p_factor": "2<sup>4</sup> &middot; 3<sup>3</sup> &minus; 1",
        "i_vertices": str(len(vertices)),
        "i_formula_floor": str(p // 12),
        "i_formula_eps": str(supersingular_count(p) - p // 12),
        "i_edges": str(len(edge_list)),
        "i_in_fp": str(len(in_fp)),
        "i_in_fp_list": ", ".join(fmt(v) for v in sorted(in_fp)),
        "i_layers": ", ".join(str(n) for n in layers),
        "i_radius": str(len(layers) - 1),
        "i_diameter": str(diameter),
        "i_loops": ", ".join(fmt(v) for v in loops) if loops else "none",
        "i_count": f"{count:,}",
        "i_count_sqrt": str(p + 1),
        "i_j": fmt(jj),
        "i_a": fmt(a),
        "i_b": fmt(b),
        "i_x0": fmt(x0),
        "i_t": fmt(t),
        "i_w": fmt(w),
        "i_a2": fmt(a2),
        "i_b2": fmt(b2),
        "i_j2": fmt(j2),
        "i_U": f"({fmt(U0[0])}, {fmt(U0[1])})",
        "i_phiU": f"({fmt(image[0])}, {fmt(image[1])})",
        "i_samples": str(len(samples)),
        "i_walk": " &rarr; ".join(fmt(v) for v in walk),
        "i_walk_end": fmt(walk[-1]),
        "i_walk_len": str(len(walk) - 1),
        "i_walk_degree": str(2 ** (len(walk) - 1)),
    }
    blocks = {
        "graph_figure": [{
            "svg": isogeny_graph(
                n=len(vertices),
                edges=edge_list,
                hollow=[index[v] for v in in_fp],
                walk=walk_idx,
                labels={index[j1728]: "1728 = 4"},
                rng=Rng("isogenylabs/notes/isogenies/layout"),
            ),
            "caption": f"The supersingular 2-isogeny graph for p = {p}: {len(vertices)} curves, one per j-invariant, joined when a "
                       f"2-isogeny connects them. Hollow vertices have j in F<sub>{p}</sub>. The coloured path is a walk of "
                       f"{len(walk) - 1} steps from j = 1728. Layout is by a force simulation, so distances in the picture mean nothing.",
        }],
        "layers_table": [{
            "table": {
                "caption": f"How many of the {len(vertices)} vertices lie at each distance from j = 1728.",
                "head": ["Distance from 1728"] + [str(k) for k in range(len(layers))],
                "rows": [["Vertices"] + [str(n) for n in layers]],
                "numeric": list(range(1, len(layers) + 1)),
            }
        }],
    }
    return {"values": values, "blocks": blocks}
