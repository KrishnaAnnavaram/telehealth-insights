"""Synthetic physician survey with the layout of the default codebook.

The rows are fake. They follow the skip logic of the real survey: non-users get the code -6
on every item for users only, and a few answers get -8 or -9. The generator has known effects:

* video and EHR-integrated platforms raise the quality and the satisfaction answers;
* specialty changes both telemedicine use and documentation time (a confounder);
* telemedicine use itself adds a small amount of documentation time.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _ordinal(latent: np.ndarray, cuts=(-1.5, -0.5, 0.5, 1.5)) -> np.ndarray:
    return 1 + np.searchsorted(np.asarray(cuts), latent)


def generate(n: int = 4000, seed: int = 0, n_strata: int = 20, item_missing: float = 0.03) -> pd.DataFrame:
    if n < 100:
        raise ValueError("n must be at least 100")
    rng = np.random.default_rng(seed)
    specialty = rng.choice([1, 2, 3, 4], size=n, p=[0.4, 0.25, 0.2, 0.15])
    size = rng.choice([1, 2, 3], size=n, p=[0.45, 0.35, 0.2])
    setting = rng.choice([1, 2, 3], size=n, p=[0.5, 0.3, 0.2])
    strata = 1 + (specialty - 1) * 5 + rng.integers(0, max(1, n_strata // 4), size=n)
    weight = np.round(rng.lognormal(mean=4.0 + 0.15 * specialty, sigma=0.35, size=n), 3)

    spec_use = np.array([0.0, 0.6, 1.4, -0.6])[specialty - 1]
    use = rng.random(n) < 1 / (1 + np.exp(-(0.3 + spec_use + 0.3 * (setting == 2))))

    tools = {
        "telemedtool1": rng.random(n) < 0.55,
        "telemedtool2": rng.random(n) < 0.70,
        "telemedtool3": rng.random(n) < 0.40,
        "telemedtool4": rng.random(n) < 0.30,
    }
    spec_q = np.array([0.0, 0.2, 0.3, -0.2])[specialty - 1]
    q_latent = (0.2 - 0.25 * tools["telemedtool1"] + 0.6 * tools["telemedtool2"] + 0.1 * tools["telemedtool3"]
                + 0.45 * tools["telemedtool4"] + spec_q + rng.logistic(0, 0.8, n))
    s_latent = (0.1 - 0.15 * tools["telemedtool1"] + 0.4 * tools["telemedtool2"] + 0.7 * tools["telemedtool4"]
                + 0.4 * (q_latent - q_latent.mean()) + rng.logistic(0, 0.8, n))
    spec_doc = np.array([0.0, 0.5, 0.9, -0.3])[specialty - 1]
    d_latent = -0.2 + spec_doc + 0.25 * use + 0.2 * (size == 1) + rng.logistic(0, 0.9, n)

    df = pd.DataFrame(
        {
            "phyid_p": [f"P{i:05d}" for i in range(n)],
            "mailwgt": weight,
            "strat_p": strata,
            "telemedicine": np.where(use, 1, 2),
            "telemedqual": np.where(use, _ordinal(q_latent), -6),
            "telemedsat": np.where(use, _ordinal(s_latent), -6),
            "timedoc": _ordinal(d_latent),
            **{k: np.where(use, np.where(v, 1, 2), -6) for k, v in tools.items()},
            "specialty": specialty,
            "practice_size": size,
            "setting": setting,
        }
    )
    for col in ("telemedqual", "telemedsat", "timedoc", "telemedtool1", "telemedtool2", "telemedtool3", "telemedtool4"):
        hit = (df[col] > 0) & (rng.random(n) < item_missing)
        df.loc[hit, col] = rng.choice([-8, -9], size=int(hit.sum()))
    return df
