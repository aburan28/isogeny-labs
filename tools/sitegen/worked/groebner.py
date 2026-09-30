"""Solving degree against the semi-regular prediction, measured with XL over F_2.

The Groebner-basis page quotes its numbers from here. Random quadratic systems
over F_2 with a planted solution are solved by XL, the simplest member of the
family F4 and F5 belong to: multiply every equation by every monomial up to
some degree D, treat each monomial as an unknown, and row-reduce. When D is
large enough the reduced matrix contains n independent linear equations,
which give the solution. The smallest such D is measured and compared with
the degree of regularity that a semi-regular system of that shape would have,
the number that complexity estimates for these attacks are built on.

Monomials are squarefree, because x^2 = x over F_2, and are written as bit
masks of the variables they contain. A polynomial is a set of monomials; a row
of the linear system is a Python integer, one bit per monomial, with the
monomials ordered by degree so that a row's highest bit is its leading term.
"""

from __future__ import annotations

from itertools import combinations
from math import comb

from .arith import Rng

SHAPES = ((8, 8), (10, 10), (12, 12), (14, 14), (8, 16), (10, 20), (12, 24), (14, 28))
TRIALS = 3


def monomials(n: int, max_deg: int):
    """Every squarefree monomial of degree <= max_deg, lowest degree first."""
    out = []
    for d in range(max_deg + 1):
        for vars_ in combinations(range(n), d):
            out.append(sum(1 << v for v in vars_))
    return out


def evaluate(poly, point_mask: int) -> int:
    """A monomial is 1 at a point exactly when all its variables are 1 there."""
    return sum(1 for mono in poly if mono & point_mask == mono) & 1


def random_system(n: int, m: int, rng: Rng):
    """m random quadratics in n variables, adjusted to vanish at a random point,
    redrawn until that point is the only solution (checked by trying all 2^n).
    With several solutions no degree yields n independent linear equations,
    and a solver has to find a Groebner basis of a larger ideal instead."""
    while True:
        system, solution = draw(n, m, rng)
        if sum(all(evaluate(f, x) == 0 for f in system) for x in range(2 ** n)) == 1:
            return system, solution


def draw(n: int, m: int, rng: Rng):
    quad = monomials(n, 2)
    solution = rng.below(2 ** n)
    system = []
    for _ in range(m):
        poly = {mono for mono in quad if rng.below(2)}
        if evaluate(poly, solution):
            poly ^= {0}  # flip the constant term
        assert evaluate(poly, solution) == 0
        system.append(poly)
    return system, solution


def mul(poly, mono: int):
    out = set()
    for term in poly:
        out ^= {term | mono}
    return out


def xl(system, n: int, D: int):
    """XL at degree D. Returns (solution or None, rows, columns, rank)."""
    cols = monomials(n, D)
    # Highest degree gets the highest bit, so a reduced row whose top bit is a
    # monomial of degree <= 1 is a linear equation.
    bit = {mono: i for i, mono in enumerate(cols)}
    shifts = monomials(n, D - 2)
    pivots: dict[int, int] = {}
    rows = 0
    for f in system:
        for u in shifts:
            row = 0
            for term in mul(f, u):
                row ^= 1 << bit[term]
            rows += 1
            while row:
                top = row.bit_length() - 1
                if top in pivots:
                    row ^= pivots[top]
                else:
                    pivots[top] = row
                    break
    rank = len(pivots)
    linear_limit = n + 1  # bits 0 .. n: the constant and the n variables
    linear = {top: row for top, row in pivots.items() if top < linear_limit}
    if len(linear) < n or 0 in linear:
        return None, rows, len(cols), rank
    # Bit 0 is the constant and bit i + 1 the variable x_i. With a pivot on
    # every variable, solve them in increasing order by back-substitution.
    value = {}
    for top in sorted(linear):
        row = linear[top]
        acc = row & 1
        for lower in range(1, top):
            if row >> lower & 1:
                acc ^= value[lower]
        value[top] = acc
    solution = 0
    for i in range(n):
        if value[bit[1 << i]]:
            solution |= 1 << i
    return solution, rows, len(cols), rank


def semi_regular_dreg(n: int, m: int) -> int:
    """First degree whose coefficient in (1 + z)^n / (1 + z^2)^m is <= 0.

    This is Bardet, Faugere and Salvy's degree of regularity for a
    semi-regular quadratic system over F_2 with the field equations."""
    series = [comb(n, k) for k in range(n + 2)]
    for _ in range(m):  # divide by (1 + z^2): c_k -= c_{k-2}, in increasing k
        for k in range(2, len(series)):
            series[k] -= series[k - 2]
    return next(k for k, c in enumerate(series) if c <= 0)


def compute() -> dict:
    rng = Rng("isogenylabs/cryptanalysis/groebner-first-fall-degree")
    table, notes = [], []
    at, above = 0, 0
    for n, m in SHAPES:
        dreg = semi_regular_dreg(n, m)
        solved = []
        last = None
        for _ in range(TRIALS):
            system, planted = random_system(n, m, rng)
            D = 2
            while True:
                found, rows, cols, rank = xl(system, n, D)
                if found is not None:
                    assert all(evaluate(f, found) == 0 for f in system), "XL's answer solves the system"
                    solved.append(D)
                    last = (rows, cols, rank)
                    break
                D += 1
                assert D <= n, "XL terminates by degree n"
        assert all(d <= dreg + 1 for d in solved), "within one of the prediction"
        at += all(d <= dreg for d in solved)
        above += any(d == dreg + 1 for d in solved)
        table.append([
            f"{n}", f"{m}", str(dreg),
            ", ".join(str(d) for d in solved),
            f"{last[1]:,}",
        ])
    values = {
        "trials": str(TRIALS),
        "shapes": str(len(SHAPES)),
        "at": str(at),
        "above": str(above),
        "largest_cols": table[len(SHAPES) // 2 - 1][4],
    }
    blocks = {
        "xl_table": [
            {
                "table": {
                    "caption": f"Random quadratic systems over F<sub>2</sub> with a planted solution, {TRIALS} per "
                               "row, solved by XL. D<sub>reg</sub> is the semi-regular prediction; the solving degree is the smallest D at which the reduced "
                               "matrix held n independent linear equations; every answer was checked against "
                               "the system. Columns is the number of monomials at the last solving degree.",
                    "head": ["n", "m", "D<sub>reg</sub>", "Solved at", "Columns"],
                    "rows": table,
                    "numeric": [0, 1, 2, 4],
                }
            }
        ],
    }
    return {"values": values, "blocks": blocks}
