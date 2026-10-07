"""SVG charts computed from the estimates. No plotting library and no typed-in numbers."""

from __future__ import annotations

from html import escape


def interval_chart(title: str, rows: list[dict], x_min: float | None = None, x_max: float | None = None,
                   reference: float | None = None, width: int = 640) -> str:
    """Horizontal chart: one dot (value) and one line (CI) for each row.

    Each row needs `label`, `value`, `ci_low` and `ci_high`.
    """
    if not rows:
        raise ValueError("no rows to draw")
    lo = min(r["ci_low"] for r in rows) if x_min is None else x_min
    hi = max(r["ci_high"] for r in rows) if x_max is None else x_max
    if reference is not None:
        lo, hi = min(lo, reference), max(hi, reference)
    if hi <= lo:
        hi = lo + 1.0
    left, right, top, row_h = 230, 30, 40, 28
    height = top + row_h * len(rows) + 30
    span = width - left - right

    def x(v: float) -> float:
        return left + (v - lo) / (hi - lo) * span

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" font-family="sans-serif" font-size="12">',
        f'<text x="{width / 2:.0f}" y="20" text-anchor="middle" font-size="14">{escape(title)}</text>',
    ]
    if reference is not None:
        parts.append(f'<line x1="{x(reference):.1f}" y1="{top - 5}" x2="{x(reference):.1f}" y2="{height - 25}" '
                     'stroke="#999" stroke-dasharray="4 3"/>')
    for i, r in enumerate(rows):
        y = top + row_h * i + row_h / 2
        parts.append(f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end">{escape(str(r["label"]))}</text>')
        parts.append(f'<line x1="{x(r["ci_low"]):.1f}" y1="{y:.1f}" x2="{x(r["ci_high"]):.1f}" y2="{y:.1f}" '
                     'stroke="#2E5FD9" stroke-width="2"/>')
        parts.append(f'<circle cx="{x(r["value"]):.1f}" cy="{y:.1f}" r="4" fill="#1F3864">'
                     f'<title>{r["value"]:.3f} [{r["ci_low"]:.3f}, {r["ci_high"]:.3f}]</title></circle>')
    axis_y = height - 22
    parts.append(f'<line x1="{left}" y1="{axis_y}" x2="{width - right}" y2="{axis_y}" stroke="#333"/>')
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        parts.append(f'<text x="{x(v):.1f}" y="{axis_y + 15}" text-anchor="middle">{v:.2f}</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"
