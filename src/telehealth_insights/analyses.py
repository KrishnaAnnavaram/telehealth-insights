"""The analysis plan. Each question fits the skip logic of the survey.

* Q1 `describe`: weighted share of telemedicine users, and the weighted distribution of each
  outcome in its own universe.
* Q2 `tool_comparisons`: for an outcome asked only of users, compare the favourable share of
  users of each tool with users who did not use that tool. Tools are multi-select, so one
  ANOVA across tool groups is not valid. A joint model adds all tools and the controls.
* Q3 `exposure_comparisons`: for an outcome asked of all physicians, compare users with
  non-users, without and with controls.
* `run_all` collects the primary tests and adds Holm-adjusted p-values. Unweighted
  Mann-Whitney tests are a sensitivity check, not the primary result.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from telehealth_insights.codebook import Codebook, Variable
from telehealth_insights.design import SurveyDesign, holm
from telehealth_insights.models import ConvergenceError, design_matrix, weighted_logit


def favourable(df: pd.DataFrame, var: Variable) -> pd.Series:
    """1.0 if the answer is in the favourable codes, 0.0 if not, NaN if missing."""
    return df[var.name].isin(var.favourable).astype(float).where(df[var.name].notna())


def _users(df: pd.DataFrame, book: Codebook) -> np.ndarray:
    return (df[book.exposure.name] == 1.0).to_numpy()


def describe(df: pd.DataFrame, book: Codebook, design: SurveyDesign) -> dict:
    out = {"telemedicine_share": design.mean(df[book.exposure.name]).as_dict(), "outcomes": {}}
    users = _users(df, book)
    for var in book.by_role("outcome"):
        domain = users if var.users_only else None
        rows = []
        for code in var.codes:
            ind = (df[var.name] == code).astype(float).where(df[var.name].notna())
            est = design.mean(ind, domain)
            rows.append({"code": code, **est.as_dict()})
        fav = design.mean(favourable(df, var), domain)
        out["outcomes"][var.name] = {
            "label": var.label,
            "universe": var.universe,
            "distribution": rows,
            "favourable": {"label": var.favourable_label, **fav.as_dict()},
        }
    return out


def _model(df, y, numeric, categorical, design, mask) -> list[dict]:
    X, names, complete = design_matrix(df, numeric, categorical)
    try:
        res = weighted_logit(X, y, design, mask=mask & complete, names=names)
    except (ConvergenceError, ValueError) as exc:
        return [{"term": "model", "error": str(exc)}]
    table = res.table()
    table["n"] = res.n
    return table[table["term"] != "intercept"].to_dict(orient="records")


def _mann_whitney(a: pd.Series, b: pd.Series) -> dict:
    a, b = a.dropna(), b.dropna()
    if len(a) < 2 or len(b) < 2:
        return {"u": float("nan"), "p_value": float("nan"), "rank_biserial": float("nan")}
    u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    return {"u": float(u), "p_value": float(p), "rank_biserial": float(2 * u / (len(a) * len(b)) - 1)}


def tool_comparisons(df: pd.DataFrame, book: Codebook, design: SurveyDesign) -> dict:
    users = _users(df, book)
    tools = book.by_role("tool")
    controls = [v.name for v in book.by_role("control")]
    out = {}
    for var in book.by_role("outcome"):
        if not var.users_only:
            continue
        y = favourable(df, var)
        per_tool = []
        for tool in tools:
            est = design.difference(y, df[tool.name], domain=users)
            sens = _mann_whitney(df.loc[users & (df[tool.name] == 1.0).to_numpy(), var.name],
                                 df.loc[users & (df[tool.name] == 0.0).to_numpy(), var.name])
            per_tool.append({"tool": tool.name, "label": tool.label, **est.as_dict(), "unweighted_mann_whitney": sens})
        joint = _model(df, y, [t.name for t in tools], controls, design, users)
        out[var.name] = {"label": var.label, "favourable": var.favourable_label, "per_tool": per_tool, "adjusted_model": joint}
    return out


def exposure_comparisons(df: pd.DataFrame, book: Codebook, design: SurveyDesign) -> dict:
    exp = book.exposure.name
    controls = [v.name for v in book.by_role("control")]
    out = {}
    for var in book.by_role("outcome"):
        if var.users_only:
            continue
        y = favourable(df, var)
        est = design.difference(y, df[exp])
        sens = _mann_whitney(df.loc[df[exp] == 1.0, var.name], df.loc[df[exp] == 0.0, var.name])
        adjusted = _model(df, y, [exp], controls, design, np.ones(len(df), dtype=bool))
        out[var.name] = {
            "label": var.label,
            "favourable": var.favourable_label,
            "unadjusted_difference": est.as_dict(),
            "unweighted_mann_whitney": sens,
            "adjusted_model": adjusted,
        }
    return out


def primary_tests(tools: dict, exposure: dict, book: Codebook) -> pd.DataFrame:
    """The family of primary tests, with Holm-adjusted p-values."""
    rows = []
    for outcome, res in tools.items():
        for t in res["per_tool"]:
            rows.append({"question": "tool", "outcome": outcome, "term": t["tool"], "estimate": t["value"],
                         "effect": "difference in favourable share", "ci_low": t["ci_low"], "ci_high": t["ci_high"],
                         "p_value": t["p_value"]})
    exp = book.exposure.name
    for outcome, res in exposure.items():
        for m in res["adjusted_model"]:
            if m.get("term") == exp:
                rows.append({"question": "exposure", "outcome": outcome, "term": exp, "estimate": m["odds_ratio"],
                             "effect": "adjusted odds ratio", "ci_low": m["or_ci_low"], "ci_high": m["or_ci_high"],
                             "p_value": m["p_value"]})
    table = pd.DataFrame(rows)
    if not table.empty:
        table["p_holm"] = holm(table["p_value"].to_numpy())
    return table


def run_all(df: pd.DataFrame, book: Codebook, alpha: float = 0.05) -> dict:
    design = SurveyDesign.from_frame(df, book.weight, book.strata, book.psu, alpha)
    desc = describe(df, book, design)
    tools = tool_comparisons(df, book, design)
    exposure = exposure_comparisons(df, book, design)
    tests = primary_tests(tools, exposure, book)
    return {
        "design": {"rows": int(len(df)), "df": design.df, "singleton_strata": design.singleton_strata,
                   "weight": book.weight, "strata": book.strata, "psu": book.psu, "alpha": alpha},
        "describe": desc,
        "tools": tools,
        "exposure": exposure,
        "tests": tests.to_dict(orient="records"),
    }
