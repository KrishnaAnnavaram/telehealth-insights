"""The codebook: which column has which role, type, valid codes and labels.

The default codebook is `data/codebook_nehrs2021.json`. Point `TELEHEALTH_CODEBOOK` to your own
JSON file to map other column names or other code values.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

ROLES = ("exposure", "outcome", "tool", "control")
TYPES = ("binary", "ordinal", "categorical")


class CodebookError(ValueError):
    """The codebook file is not valid."""


@dataclass(frozen=True)
class Variable:
    name: str
    role: str
    type: str
    label: str
    universe: str = "all physicians"
    yes: int | None = None
    no: int | None = None
    codes: tuple[int, ...] = ()
    favourable: tuple[int, ...] = ()
    favourable_label: str = ""

    @property
    def valid_codes(self) -> tuple[int, ...]:
        return (self.yes, self.no) if self.type == "binary" else self.codes

    @property
    def users_only(self) -> bool:
        return self.universe == "telemedicine users"


@dataclass(frozen=True)
class Codebook:
    name: str
    verify: str
    missing_codes: dict[int, str]
    id: str | None
    weight: str
    strata: str | None
    psu: str | None
    variables: dict[str, Variable] = field(default_factory=dict)

    def by_role(self, role: str) -> list[Variable]:
        return [v for v in self.variables.values() if v.role == role]

    @property
    def exposure(self) -> Variable:
        return self.by_role("exposure")[0]

    def columns(self) -> list[str]:
        cols = [c for c in (self.id, self.weight, self.strata, self.psu) if c]
        return cols + list(self.variables)


def _variable(name: str, spec: dict) -> Variable:
    role, vtype = spec.get("role"), spec.get("type")
    if role not in ROLES:
        raise CodebookError(f"{name}: role must be one of {ROLES}")
    if vtype not in TYPES:
        raise CodebookError(f"{name}: type must be one of {TYPES}")
    var = Variable(
        name=name,
        role=role,
        type=vtype,
        label=str(spec.get("label", name)),
        universe=str(spec.get("universe", "all physicians")),
        yes=spec.get("yes"),
        no=spec.get("no"),
        codes=tuple(int(c) for c in spec.get("codes", ())),
        favourable=tuple(int(c) for c in spec.get("favourable", ())),
        favourable_label=str(spec.get("favourable_label", "")),
    )
    if vtype == "binary" and (var.yes is None or var.no is None or var.yes == var.no):
        raise CodebookError(f"{name}: a binary variable needs two different codes `yes` and `no`")
    if vtype in ("ordinal", "categorical") and len(var.codes) < 2:
        raise CodebookError(f"{name}: needs at least two `codes`")
    if any(c < 0 for c in var.valid_codes):
        raise CodebookError(f"{name}: valid codes must not be negative (negative codes are missing codes)")
    if vtype == "ordinal" and (not var.favourable or not set(var.favourable) < set(var.codes)):
        raise CodebookError(f"{name}: `favourable` must be a proper subset of `codes`")
    return var


def parse(data: dict) -> Codebook:
    try:
        design = data["design"]
        variables = {n: _variable(n, s) for n, s in data["variables"].items()}
        missing = {int(k): str(v) for k, v in data.get("missing_codes", {}).items()}
    except KeyError as exc:
        raise CodebookError(f"codebook misses the key {exc}") from exc
    if any(k >= 0 for k in missing):
        raise CodebookError("missing codes must be negative")
    if not design.get("weight"):
        raise CodebookError("design.weight is necessary")
    book = Codebook(
        name=str(data.get("name", "codebook")),
        verify=str(data.get("verify", "")),
        missing_codes=missing,
        id=design.get("id"),
        weight=design["weight"],
        strata=design.get("strata"),
        psu=design.get("psu"),
        variables=variables,
    )
    if len(book.by_role("exposure")) != 1:
        raise CodebookError("the codebook needs exactly one exposure variable")
    if book.exposure.type != "binary":
        raise CodebookError("the exposure must be binary")
    return book


def load(path: str | None = None) -> Codebook:
    if path:
        text = Path(path).read_text(encoding="utf-8")
    else:
        text = resources.files("telehealth_insights").joinpath("data/codebook_nehrs2021.json").read_text(encoding="utf-8")
    return parse(json.loads(text))
