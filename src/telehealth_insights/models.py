"""Survey-weighted logistic regression with design-based (sandwich) standard errors.

The coefficients maximise the weighted log-likelihood (pseudo-likelihood). The variance is
A^-1 B A^-1, where A is the weighted information matrix and B is the design-based variance of
the total of the score values w_i (y_i - p_i) x_i.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats
from scipy.special import expit

from telehealth_insights.design import SurveyDesign


class ConvergenceError(RuntimeError):
    """The Newton steps did not converge (for example, a perfect separation)."""


@dataclass
class LogitResult:
    names: list[str]
    coef: np.ndarray
    se: np.ndarray
    df: int
    n: int
    alpha: float = 0.05

    def table(self) -> pd.DataFrame:
        q = stats.t.ppf(1 - self.alpha / 2, self.df)
        with np.errstate(divide="ignore", invalid="ignore"):
            t = self.coef / self.se
        return pd.DataFrame(
            {
                "term": self.names,
                "coef": self.coef,
                "se": self.se,
                "odds_ratio": np.exp(self.coef),
                "or_ci_low": np.exp(self.coef - q * self.se),
                "or_ci_high": np.exp(self.coef + q * self.se),
                "p_value": 2 * stats.t.sf(np.abs(t), self.df),
            }
        )


def design_matrix(df: pd.DataFrame, numeric: list[str], categorical: list[str]) -> tuple[np.ndarray, list[str], np.ndarray]:
    """Intercept, numeric columns and dummy columns (the lowest code is the reference).

    Returns the matrix, the term names and a mask of complete rows.
    """
    parts = [pd.Series(1.0, index=df.index, name="intercept")]
    complete = pd.Series(True, index=df.index)
    for col in numeric:
        parts.append(df[col].astype(float).rename(col))
        complete &= df[col].notna()
    for col in categorical:
        complete &= df[col].notna()
        levels = sorted(df.loc[df[col].notna(), col].unique())
        for lev in levels[1:]:
            parts.append((df[col] == lev).astype(float).rename(f"{col}={int(lev) if float(lev).is_integer() else lev}"))
    X = pd.concat(parts, axis=1)
    return X.to_numpy(dtype=float), list(X.columns), complete.to_numpy()


def weighted_logit(X, y, design: SurveyDesign, mask=None, names=None, max_iter: int = 100, tol: float = 1e-9) -> LogitResult:
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    m = ~np.isnan(y) & ~np.isnan(X).any(axis=1)
    if mask is not None:
        m &= np.asarray(mask, dtype=bool)
    if m.sum() <= X.shape[1]:
        raise ValueError("not enough complete rows for the model")
    w = np.where(m, design.w, 0.0)
    Xc, yc = np.nan_to_num(X), np.nan_to_num(y)
    beta = np.zeros(X.shape[1])
    for _ in range(max_iter):
        p = expit(Xc @ beta)
        grad = Xc.T @ (w * (yc - p))
        A = (Xc * (w * p * (1 - p))[:, None]).T @ Xc
        try:
            step = np.linalg.solve(A, grad)
        except np.linalg.LinAlgError as exc:
            raise ConvergenceError("singular information matrix") from exc
        beta += step
        if np.max(np.abs(step)) < tol:
            break
    else:
        raise ConvergenceError("no convergence. Check for a perfect separation or an empty level")
    if np.max(np.abs(beta)) > 25:
        raise ConvergenceError("a coefficient is very large: probably a perfect separation")
    p = expit(Xc @ beta)
    A = (Xc * (w * p * (1 - p))[:, None]).T @ Xc
    scores = Xc * (w * (yc - p))[:, None]
    B = design.variance_of_total(scores)
    A_inv = np.linalg.inv(A)
    V = A_inv @ B @ A_inv
    names = names or [f"x{j}" for j in range(X.shape[1])]
    return LogitResult(names, beta, np.sqrt(np.clip(np.diag(V), 0, None)), design.df, int(m.sum()), design.alpha)
