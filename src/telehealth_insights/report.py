"""Markdown report and SVG charts, all computed from the analysis results."""

from __future__ import annotations

import json
from pathlib import Path

from telehealth_insights.charts import interval_chart
from telehealth_insights.codebook import Codebook


def _ci(d: dict, nd: int = 3) -> str:
    return f"{d['value']:.{nd}f} [{d['ci_low']:.{nd}f}, {d['ci_high']:.{nd}f}]"


def charts(results: dict, book: Codebook) -> dict[str, str]:
    out = {}
    fav = [
        {"label": book.variables[name].label, **res["favourable"]}
        for name, res in results["describe"]["outcomes"].items()
    ]
    out["favourable_shares.svg"] = interval_chart("Favourable share (weighted, 95 % CI)", fav, 0.0, 1.0)
    for outcome, res in results["tools"].items():
        rows = [{"label": t["label"], **t} for t in res["per_tool"]]
        out[f"tools_{outcome}.svg"] = interval_chart(
            f"{res['label']}: tool users minus other users", rows, reference=0.0
        )
    for outcome, res in results["exposure"].items():
        rows = [{"label": m["term"], "value": m["odds_ratio"], "ci_low": m["or_ci_low"], "ci_high": m["or_ci_high"]}
                for m in res["adjusted_model"] if "odds_ratio" in m]
        if rows:
            out[f"adjusted_{outcome}.svg"] = interval_chart(f"{res['label']}: adjusted odds ratios", rows, reference=1.0)
    return out


def markdown(results: dict, book: Codebook, source: str, decode_summary: str) -> str:
    d = results["design"]
    desc = results["describe"]
    lines = [
        "# telehealth-insights report",
        "",
        f"- Data: `{source}`",
        f"- Codebook: {book.name}",
        f"- Design: weight `{d['weight']}`, strata `{d['strata']}`, PSU `{d['psu']}`, {d['rows']} rows, "
        f"{d['df']} degrees of freedom, {d['singleton_strata']} strata with one PSU",
        f"- Codebook note: {book.verify}",
        "",
        "## Decoding",
        "",
        "```",
        decode_summary,
        "```",
        "",
        "## Q1. Weighted descriptives",
        "",
        f"Share of physicians who used telemedicine: {_ci(desc['telemedicine_share'])}",
        "",
        "| Outcome | Universe | Favourable answer | Weighted share [95 % CI] | n |",
        "|---|---|---|---|---|",
    ]
    for name, res in desc["outcomes"].items():
        f = res["favourable"]
        lines.append(f"| {res['label']} | {res['universe']} | {f['label']} | {_ci(f)} | {f['n']} |")
    lines += ["", "![Favourable shares](charts/favourable_shares.svg)", ""]

    lines += ["## Q2. Tools among telemedicine users", ""]
    for outcome, res in results["tools"].items():
        lines += [
            f"### {res['label']} ({res['favourable']})",
            "",
            "| Tool | Difference in favourable share [95 % CI] | p | Unweighted Mann-Whitney p | Rank-biserial |",
            "|---|---|---|---|---|",
        ]
        for t in res["per_tool"]:
            mw = t["unweighted_mann_whitney"]
            lines.append(f"| {t['label']} | {_ci(t)} | {t['p_value']:.4f} | {mw['p_value']:.4f} | {mw['rank_biserial']:.3f} |")
        lines += ["", "Adjusted model (all tools and the controls, users only):", "", "| Term | Odds ratio [95 % CI] | p |", "|---|---|---|"]
        for m in res["adjusted_model"]:
            if "error" in m:
                lines.append(f"| model | not estimated: {m['error']} | |")
            else:
                lines.append(f"| {m['term']} | {m['odds_ratio']:.3f} [{m['or_ci_low']:.3f}, {m['or_ci_high']:.3f}] | {m['p_value']:.4f} |")
        lines += ["", f"![Tools and {outcome}](charts/tools_{outcome}.svg)", ""]

    lines += ["## Q3. Users compared with non-users", ""]
    for outcome, res in results["exposure"].items():
        u = res["unadjusted_difference"]
        mw = res["unweighted_mann_whitney"]
        lines += [
            f"### {res['label']} ({res['favourable']})",
            "",
            f"- Unadjusted difference (users minus non-users): {_ci(u)}, p = {u['p_value']:.4f}",
            f"- Unweighted Mann-Whitney: p = {mw['p_value']:.4f}, rank-biserial = {mw['rank_biserial']:.3f}",
            "",
            "| Term | Adjusted odds ratio [95 % CI] | p |",
            "|---|---|---|",
        ]
        for m in res["adjusted_model"]:
            if "error" in m:
                lines.append(f"| model | not estimated: {m['error']} | |")
            else:
                lines.append(f"| {m['term']} | {m['odds_ratio']:.3f} [{m['or_ci_low']:.3f}, {m['or_ci_high']:.3f}] | {m['p_value']:.4f} |")
        lines += ["", f"![Adjusted {outcome}](charts/adjusted_{outcome}.svg)", ""]

    lines += [
        "## Primary tests with the Holm correction",
        "",
        "| Question | Outcome | Term | Effect | Estimate [95 % CI] | p | Holm p |",
        "|---|---|---|---|---|---|---|",
    ]
    for t in results["tests"]:
        lines.append(
            f"| {t['question']} | {t['outcome']} | {t['term']} | {t['effect']} | {t['estimate']:.3f} "
            f"[{t['ci_low']:.3f}, {t['ci_high']:.3f}] | {t['p_value']:.4f} | {t['p_holm']:.4f} |"
        )
    lines += [
        "",
        "## Limits",
        "",
        "- The survey is cross-sectional. The results are associations, not causal effects.",
        "- The outcomes are physician reports. They are not patient outcomes.",
        "- The controls remove only the measured differences between groups.",
        "- Item non-response is handled as missing at random inside each group.",
        "- This report is not medical advice and not a clinical decision tool.",
    ]
    return "\n".join(lines) + "\n"


def write(out_dir: str | Path, results: dict, book: Codebook, source: str, decode_summary: str) -> Path:
    out = Path(out_dir)
    (out / "charts").mkdir(parents=True, exist_ok=True)
    for name, svg in charts(results, book).items():
        (out / "charts" / name).write_text(svg, encoding="utf-8")
    (out / "results.json").write_text(json.dumps(results, indent=2, default=float), encoding="utf-8")
    (out / "report.md").write_text(markdown(results, book, source, decode_summary), encoding="utf-8")
    return out
