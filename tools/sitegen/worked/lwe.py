"""Learning with errors, and the primal lattice attack on it, at toy sizes.

The lattices note shows its numbers from here. A small LWE instance is built
with the centred binomial noise ML-KEM uses; Gaussian elimination is shown
failing on it; then the secret is recovered with the primal (embedding)
attack: write the instance as a lattice in which the error vector is unusually
short, and find that vector with LLL. The last part repeats the attack across
dimensions to measure where LLL alone stops being enough.

The attack decides success the way an attacker would, without looking at the
secret: a candidate s is accepted when s and b - A s mod q are both small in
every coordinate. Only afterwards is the candidate compared with the real secret.
"""

from __future__ import annotations

from .arith import Rng, is_prime

Q = 31
ETA = 2
SHOW_N = 6
SCAN = (8, 14, 20, 26, 32)
TRIALS = 6


# ---------------------------------------------------------------------------
# Integral LLL: Cohen, "A Course in Computational Algebraic Number Theory",
# Algorithm 2.6.7. Everything stays an integer, so the result is exact and
# the same on every machine. Vectors are rows; d[i + 1] and lam[k][j] are
# Cohen's d_i and lambda_{k,j} with indices shifted to start at 0.


def lll(basis, num: int = 99, den: int = 100):
    """LLL-reduce linearly independent integer rows with delta = num/den."""
    B = [list(r) for r in basis]
    n = len(B)

    def dot(u, v):
        return sum(x * y for x, y in zip(u, v))

    d = [1] + [0] * n
    lam = [[0] * n for _ in range(n)]
    swaps = 0

    def reduce(k, l):
        if 2 * abs(lam[k][l]) > d[l + 1]:
            r = (2 * lam[k][l] + d[l + 1]) // (2 * d[l + 1])
            B[k] = [x - r * y for x, y in zip(B[k], B[l])]
            lam[k][l] -= r * d[l + 1]
            for i in range(l):
                lam[k][i] -= r * lam[l][i]

    def swap(k, kmax):
        B[k], B[k - 1] = B[k - 1], B[k]
        for j in range(k - 1):
            lam[k][j], lam[k - 1][j] = lam[k - 1][j], lam[k][j]
        mu = lam[k][k - 1]
        new = (d[k - 1] * d[k + 1] + mu * mu) // d[k]
        for i in range(k + 1, kmax + 1):
            t = lam[i][k]
            lam[i][k] = (d[k + 1] * lam[i][k - 1] - mu * t) // d[k]
            lam[i][k - 1] = (new * t + mu * lam[i][k]) // d[k + 1]
        d[k] = new

    d[1] = dot(B[0], B[0])
    k, kmax = 1, 0
    while k < n:
        if k > kmax:
            kmax = k
            for j in range(k + 1):
                u = dot(B[k], B[j])
                for i in range(j):
                    u = (d[i + 1] * u - lam[k][i] * lam[j][i]) // d[i]
                if j < k:
                    lam[k][j] = u
                else:
                    assert u != 0, "LLL needs independent vectors"
                    d[k + 1] = u
        while True:
            reduce(k, k - 1)
            if den * d[k + 1] * d[k - 1] < num * d[k] * d[k] - den * lam[k][k - 1] ** 2:
                swap(k, kmax)
                swaps += 1
                k = max(1, k - 1)
            else:
                for l in range(k - 2, -1, -1):
                    reduce(k, l)
                k += 1
                break
    return B, swaps


def check_lll(B, num: int = 99, den: int = 100) -> None:
    """Verify both LLL conditions exactly with rational Gram-Schmidt."""
    from fractions import Fraction

    n = len(B)
    star, mu = [], [[Fraction(0)] * n for _ in range(n)]
    for i in range(n):
        v = [Fraction(x) for x in B[i]]
        for j in range(i):
            mu[i][j] = sum(Fraction(x) * y for x, y in zip(B[i], star[j])) / sum(y * y for y in star[j])
            v = [a - mu[i][j] * b for a, b in zip(v, star[j])]
        star.append(v)
    norms = [sum(x * x for x in v) for v in star]
    for i in range(n):
        assert all(abs(mu[i][j]) <= Fraction(1, 2) for j in range(i)), "size reduced"
        if i:
            assert norms[i] >= (Fraction(num, den) - mu[i][i - 1] ** 2) * norms[i - 1], "Lovasz"


# ---------------------------------------------------------------------------
# LWE


def cbd(rng: Rng, eta: int = ETA) -> int:
    """Centred binomial noise, as in ML-KEM: a sum of eta coin flips minus another."""
    return sum(rng.below(2) for _ in range(eta)) - sum(rng.below(2) for _ in range(eta))


def centred(x: int, q: int) -> int:
    x %= q
    return x - q if x > q // 2 else x


def inverse_mod(M, q: int):
    """Inverse of a square matrix mod prime q, or None if it is singular."""
    n = len(M)
    W = [list(row) + [int(i == j) for j in range(n)] for i, row in enumerate(M)]
    for c in range(n):
        piv = next((r for r in range(c, n) if W[r][c] % q), None)
        if piv is None:
            return None
        W[c], W[piv] = W[piv], W[c]
        inv = pow(W[c][c], -1, q)
        W[c] = [x * inv % q for x in W[c]]
        for r in range(n):
            if r != c and W[r][c]:
                f = W[r][c]
                W[r] = [(x - f * y) % q for x, y in zip(W[r], W[c])]
    return [row[n:] for row in W]


def matvec(M, v, q: int):
    return [sum(a * x for a, x in zip(row, v)) % q for row in M]


def instance(n: int, m: int, q: int, rng: Rng):
    """A, s, e, b = A s + e mod q. A is redrawn until its top n x n block is
    invertible mod q, which the lattice basis below needs."""
    while True:
        A = [[rng.below(q) for _ in range(n)] for _ in range(m)]
        A1inv = inverse_mod(A[:n], q)
        if A1inv is not None:
            break
    s = [cbd(rng) for _ in range(n)]
    e = [cbd(rng) for _ in range(m)]
    b = [(x + y) % q for x, y in zip(matvec(A, s, q), e)]
    return A, A1inv, s, e, b


def embedding_basis(A, A1inv, b, q: int):
    """Rows spanning {A s mod q} + Z(b, 1), in dimension m + 1.

    Every vector A s mod q is determined by its first n coordinates u = A_1 s,
    and then its rest is A_2 A_1^{-1} u. So the q-ary lattice has the basis
    [I_n | (A_2 A_1^{-1})^T] together with q times the last m - n unit vectors.
    Adding the row (b, 1) puts (b - A s, 1) = (e, 1) in the lattice, and that
    vector is far shorter than anything else in it."""
    n, m = len(A[0]), len(A)
    C = [[sum(A[n + i][k] * A1inv[k][j] for k in range(n)) % q for j in range(n)] for i in range(m - n)]
    rows = [[int(i == j) for i in range(n)] + [C[i][j] for i in range(m - n)] + [0] for j in range(n)]
    rows += [[0] * n + [q * int(i == k) for k in range(m - n)] + [0] for i in range(m - n)]
    rows.append(list(b) + [1])
    return rows


def attack(A, A1inv, b, q: int, eta: int = ETA):
    """The primal attack. Returns (candidate s or None, reduced basis, swaps)."""
    n = len(A[0])
    R, swaps = lll(embedding_basis(A, A1inv, b, q))
    for v in R:
        if abs(v[-1]) != 1:
            continue
        e = [x * v[-1] for x in v[:-1]]
        if max(abs(x) for x in e) > eta:
            continue
        s = [centred(x, q) for x in matvec(A1inv, [(bi - ei) % q for bi, ei in zip(b[:n], e[:n])], q)]
        residual = [centred(bi - ai, q) for bi, ai in zip(b, matvec(A, s, q))]
        if max(abs(x) for x in s) <= eta and max(abs(x) for x in residual) <= eta:
            return s, R, swaps
    return None, R, swaps


def vec(v) -> str:
    return "(" + ", ".join(str(x) for x in v) + ")"


def compute() -> dict:
    q = Q
    assert is_prime(q)
    rng = Rng("isogenylabs/notes/lattices-and-lwe")

    # --- One instance, shown in full -------------------------------------
    n, m = SHOW_N, 2 * SHOW_N
    A, A1inv, s, e, b = instance(n, m, q, rng)

    # Without noise, the first n equations determine s. With it they do not.
    naive = [centred(x, q) for x in matvec(A1inv, b[:n], q)]
    naive_residual = [centred(bi - ai, q) for bi, ai in zip(b, matvec(A, naive, q))]
    assert naive != s

    basis = embedding_basis(A, A1inv, b, q)
    found, R, swaps = attack(A, A1inv, b, q)
    check_lll(R)
    assert found == s, "the attack recovered the secret"
    target = next(v for v in R if abs(v[-1]) == 1)
    sign = target[-1]
    assert [x * sign for x in target[:-1]] == e

    norm2_e = sum(x * x for x in e) + 1
    other = sorted(sum(x * x for x in v) for v in R if v is not target)
    brute = (2 * ETA + 1) ** n

    matrix = "\n".join(
        "  ".join(f"{x:2d}" for x in row) + f"   |  {bi:2d}" for row, bi in zip(A, b)
    )

    # --- The scan ----------------------------------------------------------
    scan_rows, scan_meta = [], []
    for dim in SCAN:
        wins, swap_counts = 0, []
        for _ in range(TRIALS):
            A_, A1inv_, s_, e_, b_ = instance(dim, 2 * dim, q, rng)
            cand, _, sw = attack(A_, A1inv_, b_, q)
            swap_counts.append(sw)
            if cand is not None:
                assert cand == s_, "an accepted candidate is the real secret"
                wins += 1
        scan_meta.append((dim, wins))
        scan_rows.append([
            str(dim), str(2 * dim + 1), f"{wins} of {TRIALS}",
            f"{round(sum(swap_counts) / TRIALS):,}",
        ])
    first_fail = next((dim for dim, w in scan_meta if w < TRIALS), None)
    assert first_fail is not None, f"the scan reaches the failures: {scan_meta}"
    assert scan_meta[-1][1] < scan_meta[0][1], "success falls with dimension"

    values = {
        "q": str(q),
        "eta": str(ETA),
        "n": str(n),
        "m": str(m),
        "dim": str(m + 1),
        "s": vec(s),
        "e": vec(e),
        "naive": vec(naive),
        "naive_residual": vec(naive_residual),
        "naive_max": str(max(abs(x) for x in naive_residual)),
        "swaps": f"{swaps:,}",
        "target": vec(target),
        "norm_e": f"{norm2_e ** 0.5:.2f}",
        "norm2_e": str(norm2_e),
        "next_norm": f"{other[0] ** 0.5:.2f}",
        "q_row": f"{q}",
        "brute": f"{brute:,}",
        "trials": str(TRIALS),
        "first_fail": str(first_fail),
        "top_n": str(scan_meta[-1][0]),
        "top_wins": str(scan_meta[-1][1]),
        "top_dim": str(2 * scan_meta[-1][0] + 1),
        "basis_rows": str(len(basis)),
    }
    blocks = {
        "lwe_instance": [
            {"pre": matrix, "label": f"A ({m} &times; {n}) and b = As + e mod {q}"},
        ],
        "lwe_scan": [
            {
                "table": {
                    "caption": f"The primal attack with LLL (&delta; = 0.99) against LWE with q = {q}, m = 2n, "
                               f"and centred binomial noise with &eta; = {ETA}. {TRIALS} fresh instances per row. "
                               "Success means the attack returned the secret and it was checked.",
                    "head": ["n", "Lattice dimension", "Secret recovered", "Mean LLL swaps"],
                    "rows": scan_rows,
                    "numeric": [0, 1, 3],
                }
            }
        ],
    }
    return {"values": values, "blocks": blocks}
