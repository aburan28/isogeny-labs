"""Numbers and figures for the elliptic-curve and ECDLP notes.

A small curve over F_97 is used for everything that has to be looked at: its
points, one addition carried out by hand, and a scalar multiplication traced
bit by bit. Standard curves supply the table of real sizes; their published
group orders are checked here (prime, and inside the Hasse interval of their
field) before any cost is computed from them.
"""

from __future__ import annotations

import math

from ..figures import finite_curve, real_curve_addition
from .arith import ec_add, ec_mul, ec_neg, ec_points, is_prime

SMALL_P, SMALL_A, SMALL_B = 97, 3, 2

# name, field prime, cofactor, prime subgroup order, automorphisms used by rho
STANDARD = [
    (
        "P-256",
        2**256 - 2**224 + 2**192 + 2**96 - 1,
        1,
        0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551,
        2,
    ),
    (
        "secp256k1",
        2**256 - 2**32 - 977,
        1,
        0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141,
        6,
    ),
    (
        "Curve25519",
        2**255 - 19,
        8,
        2**252 + 27742317777372353535851937790883648493,
        2,
    ),
    (
        "P-384",
        2**384 - 2**128 - 2**96 + 2**32 - 1,
        1,
        0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFC7634D81F4372DDF581A0DB248B0A77AECEC196ACCC52973,
        2,
    ),
    (
        "Curve448",
        2**448 - 2**224 - 1,
        4,
        2**446 - 13818066809895115352007386748515426880336692474882178609894547503885,
        2,
    ),
]


def check_standard() -> list[list[str]]:
    rows = []
    for name, p, h, n, aut in STANDARD:
        assert is_prime(p), f"{name}: field prime"
        assert is_prime(n), f"{name}: subgroup order is not prime (typo?)"
        # h * n = p + 1 - t with |t| <= 2 sqrt(p): the order must sit in the
        # Hasse interval, which a mistyped constant would almost never do.
        assert abs(h * n - (p + 1)) <= 2 * math.isqrt(p) + 2, f"{name}: outside the Hasse interval"
        # Expected rho work with the automorphism group of size `aut`:
        # sqrt(pi n / (2 aut)), in group operations.
        bits = 0.5 * (math.log2(math.pi) + math.log2(n) - math.log2(2 * aut))
        rows.append([name, str(p.bit_length()), str(h), str(n.bit_length()), f"2<sup>{bits:.1f}</sup>"])
    return rows


def embedding_degree(p: int, n: int) -> int:
    """Smallest k with n | p^k - 1."""
    k, acc = 1, p % n
    while acc != 1:
        acc = acc * p % n
        k += 1
    return k


def compute() -> dict:
    p, a, b = SMALL_P, SMALL_A, SMALL_B
    points = ec_points(a, b, p)
    order = len(points) + 1
    assert is_prime(order) and abs(order - (p + 1)) <= 2 * math.isqrt(p) + 1

    P = min(points)
    Q = ec_mul(5, P, a, p)
    # One addition by hand: P + Q.
    lam = (Q[1] - P[1]) * pow(Q[0] - P[0], -1, p) % p
    x3 = (lam * lam - P[0] - Q[0]) % p
    y3 = (lam * (P[0] - x3) - P[1]) % p
    assert (x3, y3) == ec_add(P, Q, a, p) == ec_mul(6, P, a, p)
    # One doubling by hand: 2P.
    lam2 = (3 * P[0] * P[0] + a) * pow(2 * P[1], -1, p) % p
    dx = (lam2 * lam2 - 2 * P[0]) % p
    dy = (lam2 * (P[0] - dx) - P[1]) % p
    assert (dx, dy) == ec_mul(2, P, a, p)

    # Double-and-add, traced.
    k = 77
    trace_rows = []
    R = None
    acc = 0
    for position, bit in enumerate(bin(k)[2:]):
        if position == 0:
            R, acc, op = P, 1, "start at P"
        else:
            R = ec_add(R, R, a, p)
            acc *= 2
            op = "double"
            if bit == "1":
                R = ec_add(R, P, a, p)
                acc += 1
                op = "double, then add P"
        trace_rows.append([bit, op, f"{acc}P", f"({R[0]}, {R[1]})"])
    assert R == ec_mul(k, P, a, p)

    trace = p + 1 - order
    emb = embedding_degree(p, order)
    multiples = []
    X = None
    for i in range(1, 7):
        X = ec_add(X, P, a, p)
        multiples.append(f"{i}P = ({X[0]}, {X[1]})")

    values = {
        "c_p": str(p),
        "c_a": str(a),
        "c_b": str(b),
        "c_points": str(len(points)),
        "c_order": str(order),
        "c_trace": str(trace),
        "c_hasse": f"{2 * math.sqrt(p):.1f}",
        "c_hasse_lo": f"{p + 1 - 2 * math.sqrt(p):.1f}",
        "c_hasse_hi": f"{p + 1 + 2 * math.sqrt(p):.1f}",
        "c_P": f"({P[0]}, {P[1]})",
        "c_negP": f"({P[0]}, {(-P[1]) % p})",
        "c_Q": f"({Q[0]}, {Q[1]})",
        "c_Px": str(P[0]), "c_Py": str(P[1]), "c_Qx": str(Q[0]), "c_Qy": str(Q[1]),
        "c_lam": str(lam),
        "c_lam_num": str((Q[1] - P[1]) % p),
        "c_lam_den": str((Q[0] - P[0]) % p),
        "c_lam_den_inv": str(pow(Q[0] - P[0], -1, p)),
        "c_x3": str(x3),
        "c_y3": str(y3),
        "c_lam2": str(lam2),
        "c_dx": str(dx),
        "c_dy": str(dy),
        "c_k": str(k),
        "c_k_bits": bin(k)[2:],
        "c_kP": f"({R[0]}, {R[1]})",
        "c_multiples": ", ".join(multiples),
        "c_emb": str(emb),
        "c_emb_bits": f"{emb * math.log2(p):.0f}",
        "c_doublings": str(len(bin(k)) - 3),
        "c_additions": str(bin(k).count("1") - 1),
        "c_naive": str(k - 1),
    }
    blocks = {
        "real_figure": [{
            "svg": real_curve_addition(),
            "caption": "y<sup>2</sup> = x<sup>3</sup> &minus; x + 1 over the real numbers. The line through P and Q meets "
                       "the curve in exactly one more point; its reflection in the x-axis is P + Q.",
        }],
        "finite_figure": [{
            "svg": finite_curve(points, p, (P, ec_neg(P, p))),
            "caption": f"All {len(points)} affine points of y<sup>2</sup> = x<sup>3</sup> + {a}x + {b} over F<sub>{p}</sub>. "
                       f"The picture is symmetric about the dashed line because (x, y) and (x, &minus;y) = (x, {p} &minus; y) are both points; "
                       f"P = ({P[0]}, {P[1]}) and &minus;P are marked.",
        }],
        "trace_table": [{
            "table": {
                "caption": f"Computing {k}P from the bits of {k} = {bin(k)[2:]}<sub>2</sub>, most significant first. "
                           f"Each row doubles the running total, and adds P when the bit is 1.",
                "head": ["bit", "operation", "running total", "point"],
                "rows": trace_rows,
                "numeric": [0],
            }
        }],
        "standard_table": [{
            "table": {
                "caption": "Standard curves. Expected rho work is &radic;(&pi;n / 2|Aut|) group operations, where n is the prime "
                           "subgroup order and |Aut| counts the automorphisms rho can exploit: 2 for &plusmn;P on every curve, "
                           "6 on secp256k1, whose extra endomorphism has order 3. Each order is checked at build time to be prime "
                           "and to lie in its field's Hasse interval.",
                "head": ["Curve", "Field (bits)", "Cofactor", "Subgroup order n (bits)", "Expected rho work"],
                "rows": check_standard(),
                "numeric": [1, 2, 3, 4],
            }
        }],
    }
    return {"values": values, "blocks": blocks}
