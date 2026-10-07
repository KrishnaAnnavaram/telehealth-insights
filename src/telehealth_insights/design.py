"""Design-based estimates for a stratified, weighted sample (Taylor linearisation).

The variance of an estimator comes from its influence values z_i:

    V = sum over strata h of  n_h / (n_h - 1) * sum over PSUs j in h of (t_hj - mean_h)^2

where t_hj is the total of z in PSU j and n_h is the count of PSUs in stratum h. With no PSU
column, each row is its own PSU. A stratum with one PSU is centred on the mean of all PSU
totals (a conservative choice). Degrees of freedom = PSUs - strata.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from scipy import stats


@dataclass(frozen=True)
class Estimate:
    value: float
    se: float
    ci_low: float
    ci_high: float
    n: int
    df: int

    @property
    def p_value(self) -> float:
        """Two-sided p-value for the hypothesis value = 0."""
        if self.se <= 0 or not np.isfinite(self.se):
            return float("nan")
        return float(2 * stats.t.sf(abs(self.value / self.se), self.df))

    def as_dict(self) -> dict:
        d = asdict(self)
        d["p_value"] = self.p_value
        return d


class SurveyDesign:
    def __init__(self, weights, strata=None, psu=None, alpha: float = 0.05):
        self.w = np.asarray(weights, dtype=float)
        n = self.w.size
        if np.any(~np.isfinite(self.w)) or np.any(self.w <= 0):
            raise ValueError("weights must be finite and above 0")
        self.strata = pd.factorize(pd.Series(strata if strata is not None else np.zeros(n)).astype(str))[0]
        psu_key = (pd.Series(psu).astype(str) if psu is not None else pd.Series(np.arange(n)).astype(str))
        self.psu = pd.factorize(pd.Series(self.strata).astype(str) + "|" + psu_key.to_numpy())[0]
        self.alpha = alpha
        n_psu = len(np.unique(self.psu))
        n_strata = len(np.unique(self.strata))
        self.df = max(1, n_psu - n_strata)
        counts = pd.Series(self.psu).groupby(self.strata).nunique()
        self.singleton_strata = int((counts < 2).sum())

    @classmethod
    def from_frame(cls, df: pd.DataFrame, weight: str, strata: str | None, psu: str | None, alpha: float = 0.05):
        return cls(df[weight], df[strata] if strata else None, df[psu] if psu else None, alpha)

    def variance_of_total(self, z) -> np.ndarray:
        z = np.asarray(z, dtype=float)
        mat = z.reshape(len(z), -1)
        totals = pd.DataFrame(mat).groupby(self.psu).sum()
        psu_stratum = pd.Series(self.strata).groupby(self.psu).first().loc[totals.index].to_numpy()
        grand = totals.to_numpy().mean(axis=0)
        k = mat.shape[1]
        V = np.zeros((k, k))
        for h in np.unique(psu_stratum):
            t = totals.to_numpy()[psu_stratum == h]
            nh = t.shape[0]
            if nh >= 2:
                d = t - t.mean(axis=0)
                V += nh / (nh - 1) * d.T @ d
            else:
                d = t - grand
                V += d.T @ d
        return V if k > 1 else V[:1, :1]

    def _estimate(self, value: float, z, n: int) -> Estimate:
        se = float(np.sqrt(max(self.variance_of_total(z)[0, 0], 0.0)))
        q = stats.t.ppf(1 - self.alpha / 2, self.df)
        return Estimate(float(value), se, float(value - q * se), float(value + q * se), int(n), int(self.df))

    def mean(self, y, domain=None) -> Estimate:
        """Weighted mean of y in a domain. Rows with a missing y are outside the domain."""
        y = np.asarray(y, dtype=float)
        d = np.ones_like(y, dtype=bool) if domain is None else np.asarray(domain, dtype=bool)
        d = d & ~np.isnan(y)
        if d.sum() == 0:
            raise ValueError("the domain is empty")
        wd = self.w * d
        theta = float(np.sum(wd * np.nan_to_num(y)) / wd.sum())
        z = wd * (np.nan_to_num(y) - theta) / wd.sum()
        return self._estimate(theta, z, int(d.sum()))

    def difference(self, y, group, domain=None) -> Estimate:
        """Weighted mean of y for group == 1 minus the weighted mean for group == 0."""
        y = np.asarray(y, dtype=float)
        g = np.asarray(group, dtype=float)
        base = np.ones_like(y, dtype=bool) if domain is None else np.asarray(domain, dtype=bool)
        base = base & ~np.isnan(y) & ~np.isnan(g)
        parts = []
        for level in (1.0, 0.0):
            d = base & (g == level)
            if d.sum() == 0:
                raise ValueError("one group is empty")
            wd = self.w * d
            theta = float(np.sum(wd * np.nan_to_num(y)) / wd.sum())
            parts.append((theta, wd * (np.nan_to_num(y) - theta) / wd.sum()))
        (t1, z1), (t0, z0) = parts
        return self._estimate(t1 - t0, z1 - z0, int(base.sum()))


def holm(p_values) -> np.ndarray:
    """Holm step-down adjusted p-values (NaN stays NaN)."""
    p = np.asarray(p_values, dtype=float)
    out = np.full_like(p, np.nan)
    ok = np.flatnonzero(~np.isnan(p))
    if ok.size == 0:
        return out
    order = ok[np.argsort(p[ok], kind="mergesort")]
    m = order.size
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[idx]))
        out[idx] = running
    return out
