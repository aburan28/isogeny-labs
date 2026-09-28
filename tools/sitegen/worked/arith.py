"""Small, exact arithmetic for the worked examples: primes, F_p, F_{p^2}, curves.

Everything here is deliberately naive and readable. The groups involved are
tiny, and the point of the code is that a reader can check it line by line
against the page it produces.
"""

from __future__ import annotations

import hashlib


class Rng:
    """Deterministic randomness: SHA-256 in counter mode under a label.

    Python's `random` module is not guaranteed to produce the same stream on
    every interpreter version, and the pages must be byte-identical wherever
    CI runs them, so the examples draw from this instead.
    """

    def __init__(self, label: str) -> None:
        self.label = label.encode()
        self.counter = 0

    def _block(self) -> int:
        digest = hashlib.sha256(self.label + self.counter.to_bytes(8, "big")).digest()
        self.counter += 1
        return int.from_bytes(digest, "big")

    def below(self, n: int) -> int:
        """Uniform in [0, n), by rejection."""
        bits = max(1, (n - 1).bit_length())
        while True:
            value = self._block() >> (256 - bits)
            if value < n:
                return value

    def between(self, lo: int, hi: int) -> int:
        """Uniform in [lo, hi]."""
        return lo + self.below(hi - lo + 1)


def is_prime(n: int) -> bool:
    """Deterministic Miller-Rabin; exact for n < 3.3 * 10^24."""
    if n < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for q in small:
        if n % q == 0:
            return n == q
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in small:
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def factor(n: int) -> dict[int, int]:
    """Trial division. Only ever called on small numbers."""
    out: dict[int, int] = {}
    d = 2
    while d * d <= n:
        while n % d == 0:
            out[d] = out.get(d, 0) + 1
            n //= d
        d += 1
    if n > 1:
        out[n] = out.get(n, 0) + 1
    return out


def legendre(a: int, p: int) -> int:
    a %= p
    if a == 0:
        return 0
    return 1 if pow(a, (p - 1) // 2, p) == 1 else -1


def sqrt_mod(a: int, p: int) -> int | None:
    """A square root of a mod p (Tonelli-Shanks), or None if there is none."""
    a %= p
    if a == 0:
        return 0
    if legendre(a, p) != 1:
        return None
    if p % 4 == 3:
        return pow(a, (p + 1) // 4, p)
    q, s = p - 1, 0
    while q % 2 == 0:
        q //= 2
        s += 1
    z = 2
    while legendre(z, p) != -1:
        z += 1
    m, c, t, r = s, pow(z, q, p), pow(a, q, p), pow(a, (q + 1) // 2, p)
    while t != 1:
        i, t2 = 0, t
        while t2 != 1:
            t2 = t2 * t2 % p
            i += 1
        b = pow(c, 1 << (m - i - 1), p)
        m, c, t, r = i, b * b % p, t * b * b % p, r * b % p
    return r


# --------------------------------------------------------------------------
# Elliptic curves over F_p, written out with plain integers.
# A point is (x, y); the point at infinity is None.


def ec_add(P, Q, a: int, p: int):
    if P is None:
        return Q
    if Q is None:
        return P
    x1, y1 = P
    x2, y2 = Q
    if x1 == x2:
        if (y1 + y2) % p == 0:
            return None
        lam = (3 * x1 * x1 + a) * pow(2 * y1, -1, p) % p
    else:
        lam = (y2 - y1) * pow(x2 - x1, -1, p) % p
    x3 = (lam * lam - x1 - x2) % p
    return (x3, (lam * (x1 - x3) - y1) % p)


def ec_neg(P, p: int):
    return None if P is None else (P[0], (-P[1]) % p)


def ec_mul(k: int, P, a: int, p: int):
    """Double-and-add, most significant bit first."""
    R = None
    for bit in bin(k)[2:] if k > 0 else "":
        R = ec_add(R, R, a, p)
        if bit == "1":
            R = ec_add(R, P, a, p)
    return R


def ec_points(a: int, b: int, p: int) -> list[tuple[int, int]]:
    """Every affine point, by running over x. Only for small p."""
    roots: dict[int, list[int]] = {}
    for y in range(p):
        roots.setdefault(y * y % p, []).append(y)
    return [(x, y) for x in range(p) for y in roots.get((x * x * x + a * x + b) % p, [])]


# --------------------------------------------------------------------------
# F_{p^2} = F_p[t] / (t^2 - r) for a fixed non-residue r.
# An element u + v t is the tuple (u, v).


class Fp2:
    def __init__(self, p: int, nonresidue: int | None = None, symbol: str = "t") -> None:
        """F_p[t]/(t^2 - r). By default r is the smallest positive non-residue;
        for p = 3 mod 4 a caller can pass nonresidue=-1 to get the usual F_p(i)."""
        self.p = p
        if nonresidue is None:
            r = 2
            while legendre(r, p) != -1:
                r += 1
        else:
            r = nonresidue % p
            assert legendre(r, p) == -1, "t^2 - r must be irreducible"
        self.r = r
        self.symbol = symbol
        self.squares = {x * x % p for x in range(p)}

    def add(self, x, y):
        p = self.p
        return ((x[0] + y[0]) % p, (x[1] + y[1]) % p)

    def sub(self, x, y):
        p = self.p
        return ((x[0] - y[0]) % p, (x[1] - y[1]) % p)

    def neg(self, x):
        p = self.p
        return ((-x[0]) % p, (-x[1]) % p)

    def mul(self, x, y):
        p = self.p
        return ((x[0] * y[0] + self.r * x[1] * y[1]) % p, (x[0] * y[1] + x[1] * y[0]) % p)

    def scale(self, c: int, x):
        p = self.p
        return (c * x[0] % p, c * x[1] % p)

    def norm(self, x) -> int:
        return (x[0] * x[0] - self.r * x[1] * x[1]) % self.p

    def inv(self, x):
        n = pow(self.norm(x), -1, self.p)
        return (x[0] * n % self.p, (-x[1]) * n % self.p)

    def is_square(self, x) -> bool:
        """x is a square in F_{p^2} exactly when its norm is a square in F_p."""
        return self.norm(x) in self.squares

    def sqrt(self, x):
        """A square root in F_{p^2}, or None. Solves (c + d t)^2 = u + v t."""
        p, u, v = self.p, x[0], x[1]
        if x == (0, 0):
            return (0, 0)
        if not self.is_square(x):
            return None
        n = sqrt_mod(self.norm(x), p)
        for sign in (1, -1):
            c2 = (u + sign * n) * pow(2, -1, p) % p
            c = sqrt_mod(c2, p)
            if c is None:
                continue
            if c == 0:
                d = sqrt_mod(u * pow(self.r, -1, p) % p, p)
                if d is not None and self.mul((0, d), (0, d)) == x:
                    return (0, d)
                continue
            d = v * pow(2 * c, -1, p) % p
            if self.mul((c, d), (c, d)) == x:
                return (c, d)
        return None  # pragma: no cover - unreachable for a square

    def fmt(self, x) -> str:
        u, v = x
        s = self.symbol
        if v == 0:
            return str(u)
        if u == 0:
            return f"{v}{s}"
        return f"{u} + {v}{s}"


class CurveFp2:
    """y^2 = x^3 + a x + b over F_{p^2}, affine points or None."""

    def __init__(self, F: Fp2, a, b) -> None:
        self.F, self.a, self.b = F, a, b

    def rhs(self, x):
        F = self.F
        return F.add(F.add(F.mul(F.mul(x, x), x), F.mul(self.a, x)), self.b)

    def contains(self, P) -> bool:
        return P is None or self.F.mul(P[1], P[1]) == self.rhs(P[0])

    def neg(self, P):
        return None if P is None else (P[0], self.F.neg(P[1]))

    def add(self, P, Q):
        F = self.F
        if P is None:
            return Q
        if Q is None:
            return P
        (x1, y1), (x2, y2) = P, Q
        if x1 == x2:
            if F.add(y1, y2) == (0, 0):
                return None
            num = F.add(F.scale(3, F.mul(x1, x1)), self.a)
            lam = F.mul(num, F.inv(F.scale(2, y1)))
        else:
            lam = F.mul(F.sub(y2, y1), F.inv(F.sub(x2, x1)))
        x3 = F.sub(F.sub(F.mul(lam, lam), x1), x2)
        return (x3, F.sub(F.mul(lam, F.sub(x1, x3)), y1))

    def mul(self, k: int, P):
        R = None
        for bit in bin(k)[2:] if k > 0 else "":
            R = self.add(R, R)
            if bit == "1":
                R = self.add(R, P)
        return R

    def point_count(self) -> int:
        """#E(F_{p^2}) by counting square right-hand sides over all x."""
        F, p = self.F, self.F.p
        total = 1  # the point at infinity
        for u in range(p):
            for v in range(p):
                y2 = self.rhs((u, v))
                if y2 == (0, 0):
                    total += 1
                elif F.is_square(y2):
                    total += 2
        return total
