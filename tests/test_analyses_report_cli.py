"""Reference problems 2, 3, 6 and 7: overlapping tool groups, typed-in chart values, confounding."""

import json

import numpy as np
import pytest

from telehealth_insights.analyses import favourable, run_all
from telehealth_insights.charts import interval_chart
from telehealth_insights.cli import main
from telehealth_insights.report import charts, write


@pytest.fixture(scope="module")
def results(decoded, book):
    return run_all(decoded[0], book)


def test_tool_groups_overlap_so_one_anova_is_not_valid(decoded):
    df, _ = decoded
    users = df[df["telemedicine"] == 1]
    both = ((users["telemedtool1"] == 1) & (users["telemedtool2"] == 1)).mean()
    assert both > 0.2


def test_tool_effects_follow_the_simulated_truth(results):
    per_tool = {t["tool"]: t for t in results["tools"]["telemedqual"]["per_tool"]}
    assert per_tool["telemedtool2"]["value"] > 0 and per_tool["telemedtool2"]["p_value"] < 0.01
    assert per_tool["telemedtool1"]["value"] < 0
    sat = {t["tool"]: t for t in results["tools"]["telemedsat"]["per_tool"]}
    assert sat["telemedtool4"]["ci_low"] > 0


def test_tool_comparisons_use_users_only(results, decoded):
    df, _ = decoded
    n_users_answered = int(((df["telemedicine"] == 1) & df["telemedqual"].notna() & df["telemedtool1"].notna()).sum())
    assert results["tools"]["telemedqual"]["per_tool"][0]["n"] == n_users_answered


def test_controls_shrink_the_confounded_exposure_effect(results, decoded, book):
    df, _ = decoded
    res = results["exposure"]["timedoc"]
    terms = [m["term"] for m in res["adjusted_model"]]
    assert "telemedicine" in terms and "specialty=3" in terms
    y = favourable(df, book.variables["timedoc"])
    users, non = y[df["telemedicine"] == 1].mean(), y[df["telemedicine"] == 0].mean()
    unadjusted_or = (users / (1 - users)) / (non / (1 - non))
    adjusted_or = next(m["odds_ratio"] for m in res["adjusted_model"] if m["term"] == "telemedicine")
    assert 1.0 < adjusted_or < unadjusted_or


def test_primary_tests_have_holm_p_values(results):
    tests = results["tests"]
    assert len(tests) == 9
    for t in tests:
        assert t["p_holm"] >= t["p_value"] - 1e-12
        assert t["ci_low"] <= t["estimate"] <= t["ci_high"]


def test_descriptives_are_weighted_shares(results, decoded):
    df, _ = decoded
    share = results["describe"]["telemedicine_share"]["value"]
    assert share == pytest.approx(np.average(df["telemedicine"], weights=df["mailwgt"]))
    dist = results["describe"]["outcomes"]["telemedqual"]["distribution"]
    assert sum(r["value"] for r in dist) == pytest.approx(1.0)


def test_charts_are_drawn_from_the_results(results, book):
    svgs = charts(results, book)
    assert set(svgs) == {"favourable_shares.svg", "tools_telemedqual.svg", "tools_telemedsat.svg", "adjusted_timedoc.svg"}
    tool_svg = svgs["tools_telemedqual.svg"]
    assert tool_svg.count("<circle") == 4
    v = results["tools"]["telemedqual"]["per_tool"][1]["value"]
    assert f"{v:.3f}" in tool_svg
    with pytest.raises(ValueError):
        interval_chart("empty", [])


def test_write_report(tmp_path, results, book):
    out = write(tmp_path / "rep", results, book, "test-source", "rows=3000")
    report = (out / "report.md").read_text(encoding="utf-8")
    assert "Holm" in report and "not a clinical decision tool" in report
    assert (out / "charts" / "favourable_shares.svg").is_file()
    assert json.loads((out / "results.json").read_text(encoding="utf-8"))["design"]["rows"] == 3000


def test_cli_end_to_end(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("TELEHEALTH_DATA", raising=False)
    csv = tmp_path / "s.csv"
    assert main(["synth", "--rows", "1500", "--seed", "3", "--out", str(csv)]) == 0
    assert main(["codebook"]) == 0
    assert "telemedtool4" in capsys.readouterr().out
    assert main(["decode", str(csv)]) == 0
    assert "-6 not applicable" in capsys.readouterr().out
    out = tmp_path / "rep"
    assert main(["analyze", "--data", str(csv), "--out", str(out)]) == 0
    assert (out / "report.md").is_file()
    assert main(["analyze", "--rows", "800", "--seed", "1", "--out", str(tmp_path / "r2")]) == 0
    assert main(["decode", str(tmp_path / "missing.csv")]) == 1
    monkeypatch.setenv("TELEHEALTH_ALPHA", "0.9")
    assert main(["codebook"]) == 1
