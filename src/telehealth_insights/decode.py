"""Decode raw survey codes. No negative code reaches an analysis.

* A negative missing code becomes NaN, and the report counts it by reason.
* A binary item becomes 1.0 (yes) or 0.0 (no).
* A code that the codebook does not know raises `DecodeError` (strict) or becomes NaN.
* An item for telemedicine users only is NaN for non-users, whatever its raw value.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from telehealth_insights.codebook import Codebook


class DecodeError(ValueError):
    """The table breaks the codebook."""


@dataclass
class DecodeReport:
    rows: int = 0
    missing: dict[str, dict[str, int]] = field(default_factory=dict)
    unknown: dict[str, int] = field(default_factory=dict)
    out_of_universe: dict[str, int] = field(default_factory=dict)

    def summary(self) -> str:
        lines = [f"rows={self.rows}"]
        for col, counts in self.missing.items():
            parts = ", ".join(f"{k}: {v}" for k, v in counts.items())
            lines.append(f"{col}: {parts}")
        for col, n in self.unknown.items():
            lines.append(f"{col}: {n} unknown codes set to NaN")
        for col, n in self.out_of_universe.items():
            lines.append(f"{col}: {n} answers from non-users set to NaN")
        return "\n".join(lines)


def decode(raw: pd.DataFrame, book: Codebook, strict: bool = True) -> tuple[pd.DataFrame, DecodeReport]:
    missing_cols = [c for c in book.columns() if c not in raw.columns]
    if missing_cols:
        raise DecodeError(f"missing columns: {missing_cols}")
    rep = DecodeReport(rows=len(raw))
    out = pd.DataFrame(index=raw.index)
    if book.id:
        out[book.id] = raw[book.id].astype(str)

    weight = pd.to_numeric(raw[book.weight], errors="coerce")
    if weight.isna().any() or (weight <= 0).any():
        raise DecodeError(f"{book.weight}: weights must be numbers above 0")
    out[book.weight] = weight.astype(float)
    for col in (book.strata, book.psu):
        if col:
            if raw[col].isna().any():
                raise DecodeError(f"{col}: design column has missing values")
            out[col] = raw[col].astype(str)

    for name, var in book.variables.items():
        values = pd.to_numeric(raw[name], errors="coerce")
        counts: dict[str, int] = {}
        for code, reason in book.missing_codes.items():
            n = int((values == code).sum())
            if n:
                counts[f"{code} {reason}"] = n
        blank = int(values.isna().sum())
        if blank:
            counts["blank"] = blank
        values = values.where(~values.isin(list(book.missing_codes)))
        valid = values.isna() | values.isin(list(var.valid_codes))
        if not valid.all():
            bad = sorted(values[~valid].unique().tolist())
            if strict:
                raise DecodeError(f"{name}: unknown codes {bad[:5]} (valid: {list(var.valid_codes)})")
            rep.unknown[name] = int((~valid).sum())
            values = values.where(valid)
        if var.type == "binary":
            values = values.map({var.yes: 1.0, var.no: 0.0})
        out[name] = values.astype(float)
        if counts:
            rep.missing[name] = counts

    exposure = book.exposure.name
    non_users = out[exposure] != 1.0
    for name, var in book.variables.items():
        if var.users_only:
            n = int((non_users & out[name].notna()).sum())
            if n:
                rep.out_of_universe[name] = n
            out.loc[non_users, name] = np.nan

    numeric = out.select_dtypes("number")
    if (numeric < 0).any().any():
        raise AssertionError("a negative code survived decoding")
    return out, rep
