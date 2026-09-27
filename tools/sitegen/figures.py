"""SVG figures, drawn from computed data.

Every figure here is generated from numbers the worked examples compute, and
is inlined into the page so it inherits the site's colours: strokes and fills
use classes that the stylesheet maps onto the same custom properties as the
text, so the dark scheme needs no second copy of any figure.
"""

from __future__ import annotations

import math


def _fmt(v: float) -> str:
    return f"{v:.1f}".rstrip("0").rstrip(".")


def svg(width: int, height: int, label: str, body: str) -> str:
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{label}" '
        f'xmlns="http://www.w3.org/2000/svg">{body}</svg>'
    )


def rho_diagram(mu: int, lam: int) -> str:
    """The walk as the letter rho: a tail of mu points, then a cycle of lam points.

    Consecutive points are the same distance apart along the path, on the tail
    and on the cycle alike, so the drawing is to scale in the one dimension
    that matters: path length. The tail leaves the bottom of the cycle, runs
    down, turns through a quarter circle, and runs left to X_0.
    """
    # Geometry in units of one step, with y pointing down as in SVG.
    r = lam / (2 * math.pi)  # cycle radius
    down = 0.35 * mu  # first straight piece of the tail
    turn = 0.30 * mu  # quarter-circle piece
    bend = turn / (math.pi / 2)  # its radius
    left = mu - down - turn  # last straight piece

    def tail_point(s: float) -> tuple[float, float]:
        """Point at arc length s from the junction (0, 0), heading away from the cycle."""
        if s <= down:
            return 0.0, s
        if s <= down + turn:
            phi = (s - down) / bend  # 0 .. pi/2, turning from downward to leftward
            return -bend + bend * math.cos(phi), down + bend * math.sin(phi)
        return -bend - (s - down - turn), down + bend

    xmin, xmax = -(bend + left), r
    ymin, ymax = -2 * r, down + bend
    width, pad = 600, 40
    scale = min((width - 2 * pad - 150) / (xmax - xmin), 380 / (ymax - ymin))
    height = int((ymax - ymin) * scale + 2 * pad)
    ox = pad + 20 + (width - 2 * pad - 150 - (xmax - xmin) * scale) / 2 - xmin * scale
    oy = pad - ymin * scale

    def X(x):
        return ox + x * scale

    def Y(y):
        return oy + y * scale

    parts = [
        f'<circle class="rule" cx="{_fmt(X(0))}" cy="{_fmt(Y(-r))}" r="{_fmt(r * scale)}" stroke-width="1.5"/>',
    ]
    path = " L".join(f"{_fmt(X(x))} {_fmt(Y(y))}" for x, y in (tail_point(mu * i / 200) for i in range(201)))
    parts.append(f'<path class="rule" d="M{path}" stroke-width="1.5"/>')
    for i in range(1, mu + 1):  # tail points X_{mu-1} .. X_0, walking back from the junction
        x, y = tail_point(i)
        parts.append(f'<circle class="muted-fill" cx="{_fmt(X(x))}" cy="{_fmt(Y(y))}" r="2.3"/>')
    for j in range(lam):  # cycle points, starting at the junction
        theta = math.pi / 2 + 2 * math.pi * j / lam
        x, y = r * math.cos(theta), -r + r * math.sin(theta)
        cls, rad = ("accent-fill", 5) if j == 0 else ("ink-fill", 2.3)
        parts.append(f'<circle class="{cls}" cx="{_fmt(X(x))}" cy="{_fmt(Y(y))}" r="{rad}"/>')

    x0, y0 = tail_point(mu)
    parts.append(f'<text x="{_fmt(X(x0) - 10)}" y="{_fmt(Y(y0) + 5)}" text-anchor="end">X₀</text>')
    parts.append(f'<text class="label" x="{_fmt(X(0) + 14)}" y="{_fmt(Y(0) + 22)}">first repeated point</text>')
    parts.append(f'<text x="{_fmt(X(r) + 14)}" y="{_fmt(Y(-r) + 5)}">cycle: {lam} steps</text>')
    xm, ym = tail_point(down + turn + left / 2)
    parts.append(f'<text x="{_fmt(X(xm))}" y="{_fmt(Y(ym) + 28)}" text-anchor="middle">tail: {mu} steps</text>')
    return svg(width, height, f"A rho-shaped walk: a tail of {mu} points leading into a cycle of {lam} points.", "".join(parts))


def real_curve_addition(a: float = -1.0, b: float = 1.0) -> str:
    """The chord rule on y^2 = x^3 + a x + b over the reals, with exact geometry."""
    f = lambda x: x ** 3 + a * x + b  # noqa: E731
    P = (-1.0, math.sqrt(f(-1.0)))
    Q = (0.25, math.sqrt(f(0.25)))
    lam = (Q[1] - P[1]) / (Q[0] - P[0])
    x3 = lam * lam - P[0] - Q[0]
    y3 = lam * (P[0] - x3) - P[1]
    third = (x3, -y3)  # the chord's third intersection with the curve
    total = (x3, y3)  # P + Q

    xmin, xmax, ymin, ymax = -1.75, 2.6, -3.4, 3.4
    width, height = 600, 440

    def X(x):
        return (x - xmin) / (xmax - xmin) * width

    def Y(y):
        return height - (y - ymin) / (ymax - ymin) * height

    # Sample the curve on a fine grid; the real locus is one component here.
    root = xmin
    lo, hi = xmin, 0.0
    for _ in range(80):  # bisect for the real root of f
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) < 0 else (lo, mid)
    root = hi
    xs = [root + (xmax - root) * (i / 400) ** 1.6 for i in range(401)]
    upper = [(X(x), Y(math.sqrt(max(f(x), 0)))) for x in xs if math.sqrt(max(f(x), 0)) <= ymax]
    lower = [(X(x), Y(-math.sqrt(max(f(x), 0)))) for x in xs if math.sqrt(max(f(x), 0)) <= ymax]
    path = "M" + " L".join(f"{_fmt(x)} {_fmt(y)}" for x, y in reversed(lower))
    path += " L" + " L".join(f"{_fmt(x)} {_fmt(y)}" for x, y in upper)

    line_x0, line_x1 = xmin, xmax
    parts = [
        f'<line class="rule" x1="0" y1="{_fmt(Y(0))}" x2="{width}" y2="{_fmt(Y(0))}"/>',
        f'<line class="rule" x1="{_fmt(X(0))}" y1="0" x2="{_fmt(X(0))}" y2="{height}"/>',
        f'<path class="ink" d="{path}" stroke-width="2"/>',
        f'<line class="muted" x1="{_fmt(X(line_x0))}" y1="{_fmt(Y(P[1] + lam * (line_x0 - P[0])))}" '
        f'x2="{_fmt(X(line_x1))}" y2="{_fmt(Y(P[1] + lam * (line_x1 - P[0])))}" stroke-width="1.5"/>',
        f'<line class="accent" x1="{_fmt(X(x3))}" y1="{_fmt(Y(third[1]))}" x2="{_fmt(X(x3))}" '
        f'y2="{_fmt(Y(total[1]))}" stroke-width="1.5" stroke-dasharray="5 4"/>',
    ]
    # Labels sit where the curve and the chord are not: the chord runs almost
    # horizontally through P, Q and the third point, and at both of the right-
    # hand points the curve leaves towards the upper or lower right.
    for (x, y), name, dx, dy, anchor, cls in [
        (P, "P", -12, -12, "end", "ink-fill"),
        (Q, "Q", 0, -16, "middle", "ink-fill"),
        (third, "−(P + Q)", 14, 30, "start", "muted-fill"),
        (total, "P + Q", 16, -8, "start", "accent-fill"),
    ]:
        parts.append(f'<circle class="{cls}" cx="{_fmt(X(x))}" cy="{_fmt(Y(y))}" r="5"/>')
        parts.append(
            f'<text class="label" x="{_fmt(X(x) + dx)}" y="{_fmt(Y(y) + dy)}" text-anchor="{anchor}">{name}</text>'
        )
    return svg(
        width, height,
        "The curve y squared equals x cubed minus x plus one. The line through P and Q meets the curve a third time; "
        "reflecting that point in the x-axis gives P plus Q.",
        "".join(parts),
    )


def finite_curve(points: list[tuple[int, int]], p: int, pair: tuple[tuple[int, int], tuple[int, int]]) -> str:
    """Every affine point of a curve over F_p, with one point and its negative marked."""
    size = 520
    margin = 34
    cell = (size - 2 * margin) / (p - 1)

    def X(x):
        return margin + x * cell

    def Y(y):
        return size - margin - y * cell

    parts = [
        f'<rect class="rule" x="{margin - 6}" y="{margin - 6}" width="{_fmt(size - 2 * margin + 12)}" '
        f'height="{_fmt(size - 2 * margin + 12)}" stroke-width="1"/>',
        f'<line class="rule" x1="{margin - 6}" y1="{_fmt(Y(p / 2))}" x2="{_fmt(size - margin + 6)}" '
        f'y2="{_fmt(Y(p / 2))}" stroke-dasharray="4 4"/>',
    ]
    (px, py), (nx, ny) = pair
    parts.append(
        f'<line class="accent" x1="{_fmt(X(px))}" y1="{_fmt(Y(py))}" x2="{_fmt(X(nx))}" y2="{_fmt(Y(ny))}" '
        f'stroke-width="1.5"/>'
    )
    for x, y in points:
        marked = (x, y) in pair
        cls = "accent-fill" if marked else "ink-fill"
        r = 4.2 if marked else 2.6
        parts.append(f'<circle class="{cls}" cx="{_fmt(X(x))}" cy="{_fmt(Y(y))}" r="{r}"/>')
    parts.append(f'<text x="{margin}" y="{size - 10}">0</text>')
    parts.append(f'<text x="{_fmt(X(p - 1))}" y="{size - 10}" text-anchor="end">x = {p - 1}</text>')
    parts.append(f'<text x="8" y="{_fmt(Y(p - 1) + 5)}">{p - 1}</text>')
    parts.append(f'<text class="label" x="{_fmt(X(px) + 8)}" y="{_fmt(Y(py) - 6)}">P</text>')
    parts.append(f'<text class="label" x="{_fmt(X(nx) + 8)}" y="{_fmt(Y(ny) + 16)}">−P</text>')
    return svg(
        size, size,
        f"The {len(points)} affine points of the curve over the field with {p} elements, "
        "symmetric about the horizontal line y = p/2.",
        "".join(parts),
    )


def sparsity(rows: list[list[int]], columns: int, label: str) -> str:
    """Nonzero pattern of a relation matrix: one dot per nonzero entry."""
    count = len(rows)
    width = 600
    cell = min(3.2, (width - 20) / columns)
    height = int(count * cell + 20)
    draw_w = columns * cell
    x0 = (width - draw_w) / 2
    parts = [
        f'<rect class="rule" x="{_fmt(x0 - 3)}" y="7" width="{_fmt(draw_w + 6)}" '
        f'height="{_fmt(count * cell + 6)}" stroke-width="1"/>'
    ]
    for r, cols in enumerate(rows):
        for c in cols:
            parts.append(
                f'<rect class="ink-fill" x="{_fmt(x0 + c * cell)}" y="{_fmt(10 + r * cell)}" '
                f'width="{_fmt(cell)}" height="{_fmt(cell)}"/>'
            )
    return svg(width, height, label, "".join(parts))


def size_dotplot(rows: list[dict]) -> str:
    """Public-key and signature sizes per scheme, as two dots on one log axis.

    One axis, two series. Series colours come from --series-1 and --series-2,
    validated against both page surfaces; values stay in text colours, and a
    table with every number follows the figure, so hover titles only enhance.
    """
    width, left, right, top, row_h = 600, 150, 22, 44, 30
    lo, hi = 16, 32768  # bytes; a log axis, since the values span three decades
    plot_w = width - left - right
    height = top + row_h * len(rows) + 40

    def X(v):
        return left + (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * plot_w

    parts = []
    for tick, label in [(100, "100"), (1000, "1,000"), (10000, "10,000")]:
        x = X(tick)
        parts.append(f'<line class="rule" x1="{_fmt(x)}" y1="{top - 8}" x2="{_fmt(x)}" y2="{height - 34}" stroke-width="1"/>')
        parts.append(f'<text x="{_fmt(x)}" y="{height - 14}" text-anchor="middle">{label}</text>')
    parts.append(f'<text x="{width - right}" y="21" text-anchor="end">bytes, log scale</text>')

    # Legend: always present for two series, marks mirroring the plot's dots.
    parts.append(f'<circle class="series-1" cx="{left + 6}" cy="16" r="5"/>')
    parts.append(f'<text class="label" x="{left + 18}" y="21">public key</text>')
    parts.append(f'<circle class="series-2" cx="{left + 132}" cy="16" r="5"/>')
    parts.append(f'<text class="label" x="{left + 144}" y="21">signature</text>')

    for i, row in enumerate(rows):
        y = top + row_h * i + row_h / 2
        pk, sig = row["public_key"], row["signature"]
        parts.append(f'<text class="label" x="{left - 14}" y="{_fmt(y + 5)}" text-anchor="end">{row["name"]}</text>')
        parts.append(
            f'<line class="rule" x1="{_fmt(X(min(pk, sig)))}" y1="{_fmt(y)}" x2="{_fmt(X(max(pk, sig)))}" '
            f'y2="{_fmt(y)}" stroke-width="2"/>'
        )
        # Dots closer than a marker's width would hide one another (RSA's
        # public key and signature are the same size), so they split vertically.
        split = 4.5 if abs(X(pk) - X(sig)) < 11 else 0
        for value, cls, what, dy in [(pk, "series-1", "public key", -split), (sig, "series-2", "signature", split)]:
            title = f"{row['name']}: {what} {value:,} bytes"
            parts.append(
                f'<g class="hit"><title>{title}</title>'
                f'<circle cx="{_fmt(X(value))}" cy="{_fmt(y + dy)}" r="12" fill="transparent"/>'
                f'<circle class="{cls} ringed" cx="{_fmt(X(value))}" cy="{_fmt(y + dy)}" r="5.5"/></g>'
            )
    return svg(
        width, height,
        "Public-key and signature sizes of eight signature schemes on a logarithmic axis, from 32 bytes to 17,088 bytes. "
        "The same numbers are in the table below.",
        "".join(parts),
    )
