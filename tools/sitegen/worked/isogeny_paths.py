"""Searching for a path in the supersingular 2-isogeny graph for p = 10007.

The supersingular path problem page measures its searches here. The graph is
built exactly as in the isogeny note (roots of Phi_2 over F_{p^2}, found by
breadth-first search from j = 1728), then a secret non-backtracking walk is
hidden between two curves and recovered three ways:

  * a one-sided breadth-first search from the start curve,
  * a bidirectional search that grows both ends until they meet,
  * the Delfs-Galbraith route through the curves defined over F_p.

Each search counts the distinct curves it had to look at, since for a real
attacker every one of those is an isogeny evaluation. Every recovered path is
checked edge by edge against Phi_2 before a number is printed.
"""

from __future__ import annotations

import math
from collections import deque

from .arith import Fp2, Rng, is_prime
from .isogenies import Poly, build_graph, phi2_at, supersingular_count

P = 10007
WALK = 12
TRIALS = 40


def fmt_int(n: int) -> str:
    return f"{n:,}"


def is_edge(F: Fp2, u, v) -> bool:
    """Phi_2(u, v) = 0: there is a 2-isogeny between the two curves."""
    coeffs = phi2_at(F, u)
    acc, power = (0, 0), (1, 0)
    for c in coeffs:
        acc = F.add(acc, F.mul(c, power))
        power = F.mul(power, v)
    return acc == (0, 0)


def check_path(F: Fp2, path, src, dst) -> None:
    assert path[0] == src and path[-1] == dst, "path joins the two curves"
    assert all(is_edge(F, u, v) for u, v in zip(path, path[1:])), "every step is a 2-isogeny"


def secret_walk(edges, start, length: int, rng: Rng):
    """A non-backtracking walk: never return along the edge just used."""
    path, prev = [start], None
    for _ in range(length):
        here = path[-1]
        choices = [w for w in edges[here] if w != prev] or edges[here]
        prev = here
        path.append(choices[rng.below(len(choices))])
    return path


def one_sided(edges, src, dst):
    """Breadth-first from src until dst is reached. Returns (path, visited)."""
    parent = {src: None}
    dq = deque([src])
    while dq:
        u = dq.popleft()
        if u == dst:
            break
        for w in edges[u]:
            if w not in parent:
                parent[w] = u
                dq.append(w)
    path, node = [], dst
    while node is not None:
        path.append(node)
        node = parent[node]
    return path[::-1], len(parent)


def bidirectional(edges, src, dst):
    """Grow a ball around each end, one full layer at a time, alternating."""
    if src == dst:
        return [src], 1
    par = [{src: None}, {dst: None}]
    frontier = [[src], [dst]]
    side = 0
    while True:
        nxt, meet = [], None
        for u in frontier[side]:
            for w in edges[u]:
                if w not in par[side]:
                    par[side][w] = u
                    nxt.append(w)
                if w in par[1 - side] and meet is None:
                    meet = w
        frontier[side] = nxt
        if meet is not None:
            break
        side = 1 - side

    def trace(tree, node):
        out = []
        while node is not None:
            out.append(node)
            node = tree[node]
        return out

    path = trace(par[0], meet)[::-1] + trace(par[1], meet)[1:]
    return path, len(set(par[0]) | set(par[1]))


def to_fp(edges, src, in_fp: set):
    """Walk from src by breadth-first search until a curve defined over F_p."""
    parent = {src: None}
    dq = deque([src])
    while dq:
        u = dq.popleft()
        if u in in_fp:
            path, node = [], u
            while node is not None:
                path.append(node)
                node = parent[node]
            return path[::-1], len(parent)
        for w in edges[u]:
            if w not in parent:
                parent[w] = u
                dq.append(w)
    raise AssertionError("the graph is connected")  # pragma: no cover


def mean(xs) -> float:
    return sum(xs) / len(xs)


def median(xs) -> float:
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def compute() -> dict:
    p = P
    assert is_prime(p) and p % 4 == 3
    F = Fp2(p, nonresidue=-1, symbol="i")
    poly = Poly(F)
    rng = Rng("isogenylabs/cryptanalysis/supersingular-path-problem")
    j1728 = (1728 % p, 0)
    vertices, edges = build_graph(F, poly, rng, j1728)
    n = len(vertices)
    assert n == supersingular_count(p)
    in_fp = {v for v in vertices if v[1] == 0}

    one, two, dg_walk, found_lengths = [], [], [], []
    for _ in range(TRIALS):
        start = vertices[rng.below(n)]
        walk = secret_walk(edges, start, WALK, rng)
        end = walk[-1]

        path1, seen1 = one_sided(edges, start, end)
        check_path(F, path1, start, end)
        path2, seen2 = bidirectional(edges, start, end)
        check_path(F, path2, start, end)
        assert len(path2) == len(path1), "both searches find a shortest path"

        # Delfs-Galbraith: send each end down to F_p, then join the two F_p curves.
        a, cost_a = to_fp(edges, start, in_fp)
        b, cost_b = to_fp(edges, end, in_fp)
        check_path(F, a, start, a[-1])
        check_path(F, b, end, b[-1])
        assert a[-1][1] == 0 and b[-1][1] == 0
        dg_walk.append(max(len(a), len(b)) - 1)

        one.append(seen1)
        two.append(seen2)
        found_lengths.append(len(path1) - 1)

    # How big a ball must be before it holds half the graph: the depth a
    # one-sided search reaches before it is looking at most of the curves.
    dist = {j1728: 0}
    dq = deque([j1728])
    while dq:
        u = dq.popleft()
        for w in edges[u]:
            if w not in dist:
                dist[w] = dist[u] + 1
                dq.append(w)
    depth = max(dist.values())

    ratio = mean(one) / mean(two)
    values = {
        "p": fmt_int(p),
        "vertices": fmt_int(n),
        "p_over_12": fmt_int(p // 12),
        "in_fp": fmt_int(len(in_fp)),
        "sqrt_p": f"{math.sqrt(p):.0f}",
        "sqrt_n": f"{math.sqrt(n):.0f}",
        "trials": str(TRIALS),
        "walk": str(WALK),
        "found_median": f"{median(found_lengths):g}",
        "found_max": str(max(found_lengths)),
        "shorter": str(sum(1 for f in found_lengths if f < WALK)),
        "depth": str(depth),
        "one_mean": fmt_int(round(mean(one))),
        "one_median": fmt_int(round(median(one))),
        "one_pct": f"{100 * mean(one) / n:.0f}",
        "two_mean": fmt_int(round(mean(two))),
        "two_median": fmt_int(round(median(two))),
        "two_pct": f"{100 * mean(two) / n:.1f}",
        "ratio": f"{ratio:.1f}",
        "dg_median": f"{median(dg_walk):g}",
        "dg_max": str(max(dg_walk)),
    }
    return {"values": values, "blocks": {}}
