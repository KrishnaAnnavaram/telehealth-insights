"""Reference problems 4 and 5: no survey weights, t-tests with no effect sizes or correction."""

import numpy as np
import pytest

from telehealth_insights.design import SurveyDesign, holm
from telehealth_insights.models import ConvergenceError, design_matrix, weighted_logit


def test_unweighted_mean_matches_the_classic_standard_error():
    rng = np.random.default_rng(0)
    y = rng.normal(5, 2, 400)
    est = SurveyDesign(np.ones(400)).mean(y)
    assert est.value == pytest.approx(y.mean())
    assert est.se == pytest.approx(y.std(ddof=1) / np.sqrt(400))
    assert est.df == 399 and est.ci_low < est.value < est.ci_high


def test_weights_change_the_estimate():
    y = np.array([0.0, 0.0, 1.0, 1.0])
    w = np.array([1.0, 1.0, 3.0, 3.0])
    assert SurveyDesign(w).mean(y).value == pytest.approx(0.75)
    with pytest.raises(ValueError):
        SurveyDesign([1.0, 0.0])


def test_strata_that_explain_the_outcome_reduce_the_variance():
    rng = np.random.default_rng(1)
    strata = np.repeat([0, 1], 300)
    y = np.where(strata == 1, 10.0, 0.0) + rng.normal(0, 1, 600)
    plain = SurveyDesign(np.ones(600)).mean(y)
    strat = SurveyDesign(np.ones(600), strata=strata).mean(y)
    assert strat.value == pytest.approx(plain.value)
    assert strat.se < plain.se / 3
    assert strat.df == 598


def test_psu_clusters_increase_the_variance():
    rng = np.random.default_rng(2)
    psu = np.repeat(np.arange(30), 20)
    y = rng.normal(0, 1, 30)[psu] + rng.normal(0, 0.3, 600)
    rows = SurveyDesign(np.ones(600)).mean(y)
    clustered = SurveyDesign(np.ones(600), psu=psu).mean(y)
    assert clustered.se > 2 * rows.se and clustered.df == 29


def test_domain_mean_and_difference():
    y = np.array([1.0, 0.0, 1.0, 1.0, 0.0, np.nan])
    g = np.array([1.0, 1.0, 1.0, 0.0, 0.0, 1.0])
    d = SurveyDesign(np.ones(6))
    assert d.mean(y, g == 1).value == pytest.approx(2 / 3)
    assert d.difference(y, g).value == pytest.approx(2 / 3 - 1 / 2)
    with pytest.raises(ValueError):
        d.mean(y, np.zeros(6, dtype=bool))


def test_p_value_and_holm():
    est = SurveyDesign(np.ones(200)).mean(np.r_[np.ones(120), np.zeros(80)])
    assert est.p_value < 1e-10
    assert np.allclose(holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])
    out = holm([0.5, np.nan, 0.01])
    assert np.isnan(out[1]) and out[2] == pytest.approx(0.02) and out[0] == pytest.approx(0.5)


def test_logit_on_a_two_by_two_table_gives_the_weighted_log_odds_ratio():
    x = np.array([1, 1, 1, 1, 0, 0, 0, 0], dtype=float)
    y = np.array([1, 1, 0, 0, 1, 0, 0, 0], dtype=float)
    w = np.array([2, 1, 1, 1, 1, 1, 2, 3], dtype=float)
    X = np.column_stack([np.ones(8), x])
    res = weighted_logit(X, y, SurveyDesign(w), names=["intercept", "x"])
    odds1 = (2 + 1) / (1 + 1)
    odds0 = 1 / (1 + 2 + 3)
    assert res.coef[1] == pytest.approx(np.log(odds1 / odds0), abs=1e-8)
    table = res.table()
    assert table.loc[1, "odds_ratio"] == pytest.approx(odds1 / odds0)
    assert table.loc[1, "or_ci_low"] < table.loc[1, "odds_ratio"] < table.loc[1, "or_ci_high"]


def test_logit_recovers_a_known_effect_and_refuses_separation():
    rng = np.random.default_rng(3)
    x = rng.normal(size=3000)
    y = (rng.random(3000) < 1 / (1 + np.exp(-(0.5 + 1.2 * x)))).astype(float)
    res = weighted_logit(np.column_stack([np.ones(3000), x]), y, SurveyDesign(np.ones(3000)))
    assert res.coef[1] == pytest.approx(1.2, abs=0.15)
    assert abs(res.coef[1] - 1.2) < 3 * res.se[1]
    sep_x = np.r_[np.zeros(50), np.ones(50)]
    with pytest.raises(ConvergenceError):
        weighted_logit(np.column_stack([np.ones(100), sep_x]), sep_x, SurveyDesign(np.ones(100)))


def test_design_matrix_uses_the_lowest_code_as_reference(decoded):
    df, _ = decoded
    X, names, complete = design_matrix(df, ["telemedicine"], ["specialty"])
    assert names == ["intercept", "telemedicine", "specialty=2", "specialty=3", "specialty=4"]
    assert X.shape == (len(df), 5) and complete.dtype == bool
