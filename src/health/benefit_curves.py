"""
Health benefit curves for walk-to-transit scoring.

B(d) models the health benefit of walking distance d metres to a transit stop.
The curve is a Gaussian bell: benefit rises from near-zero at d=0, peaks at mu,
then decays symmetrically, reaching zero at d_max.

This is a synthesised model — no single published paper provides a ready-made B(d)
function for health benefit vs. walking distance to transit. Parameters are grounded in:
  - Besser & Dannenberg (2005): 85th-percentile walk to bus ~524m, median 19-min walk
  - Samitz et al. (2011): non-linear dose-response; biggest gains at moderate activity
  - WHO GAPPA (2018): 10-minute walk (≈800m at 1.4 m/s) as guideline target
  - Lars Bo Andersen et al. (2000): active travel reduces all-cause mortality in Danish cohort

Parameters are intentionally exposed for interactive tuning. See notebook 10 for
visualisation and literature calibration.
"""

import numpy as np


# ---------------------------------------------------------------------------
# Default parameters per demographic group
# ---------------------------------------------------------------------------

DEMOGRAPHIC_PARAMS: dict[str, dict] = {
    "working_age": {
        "label": "Working-age adults (15–64)",
        # Time-grounded parameters (Bohannon 1997): speed=1.40 m/s, peak=5 min, max=10 min
        # Metre equivalents used by B(d): peak=420m, d_max=840m, sigma=202m
        "mu": 420,       # peak benefit distance (m) — 5 min × 60 s × 1.40 m/s
        "sigma": 202,    # curve width (m) — 2.4 min × 60 s × 1.40 m/s
        "d_max": 840,    # zero benefit beyond this distance (m) — 10 min × 60 s × 1.40 m/s
        "pop_cols": ["pop_young_adults_15_29_mid", "pop_working_age_30_64_mid"],
        "pop_col_combined": "pop_working_age_combined",
        "color": "#2166ac",
    },
    "elderly": {
        "label": "Elderly (65+)",
        # Time-grounded parameters (Lusardi 2003): speed=0.90 m/s, peak=4 min, max=8 min
        # Metre equivalents: peak=216m, d_max=432m, sigma=108m
        "mu": 216,       # 4 min × 60 s × 0.90 m/s
        "sigma": 108,    # 2.0 min × 60 s × 0.90 m/s
        "d_max": 432,    # 8 min × 60 s × 0.90 m/s
        "pop_cols": ["pop_older_adults_65_79_mid", "pop_very_elderly_80plus_mid"],
        "pop_col_combined": "pop_elderly_combined",
        "color": "#d6604d",
    },
    "children": {
        "label": "Children (under 15)",
        # Time-grounded parameters (Plaut 2005): speed=1.00 m/s, peak=3.5 min, max=7 min
        # Metre equivalents: peak=210m, d_max=420m, sigma=105m
        "mu": 210,       # 3.5 min × 60 s × 1.00 m/s
        "sigma": 105,    # 1.75 min × 60 s × 1.00 m/s
        "d_max": 420,    # 7 min × 60 s × 1.00 m/s
        "pop_cols": ["pop_children_0_14_mid"],
        "pop_col_combined": "pop_children_combined",
        "color": "#4dac26",
    },
}


# ---------------------------------------------------------------------------
# Core B(d) function
# ---------------------------------------------------------------------------


def B(d: float | np.ndarray, mu: float, sigma: float, d_max: float) -> np.ndarray:
    """Health benefit of walking distance d metres to a transit stop.

    Shape: Gaussian bell, clamped to [0, 1] and zeroed beyond d_max.
    - d = 0:     low benefit (walks of metres provide no cardiovascular effect)
    - d = mu:    peak benefit = 1.0
    - d = d_max: benefit approaches 0 (tail cutoff)
    - d > d_max: 0.0

    Parameters
    ----------
    d : float or array
        Walking distance in metres.
    mu : float
        Distance at which benefit peaks (metres).
    sigma : float
        Standard deviation controlling curve width (metres).
        Larger sigma → flatter, wider curve.
    d_max : float
        Maximum useful catchment distance. Benefit is zeroed beyond this.

    Returns
    -------
    np.ndarray
        Benefit values in [0, 1].
    """
    d = np.asarray(d, dtype=float)
    benefit = np.exp(-0.5 * ((d - mu) / sigma) ** 2)
    benefit = np.where(d > d_max, 0.0, benefit)
    benefit = np.where(d < 0, 0.0, benefit)
    return benefit


def B_group(d: float | np.ndarray, group: str) -> np.ndarray:
    """Convenience wrapper: apply B(d) using default parameters for a named group.

    Parameters
    ----------
    d : float or array
        Walking distance in metres.
    group : str
        One of 'working_age', 'elderly', 'children'.

    Returns
    -------
    np.ndarray
        Benefit values in [0, 1].
    """
    params = DEMOGRAPHIC_PARAMS[group]
    return B(d, mu=params["mu"], sigma=params["sigma"], d_max=params["d_max"])


# ---------------------------------------------------------------------------
# Utility: distance axis at 20m resolution
# ---------------------------------------------------------------------------


def distance_axis(d_max: float = 800, step: float = 20) -> np.ndarray:
    """Return a distance array from 0 to d_max (inclusive) at step-m intervals."""
    return np.arange(0, d_max + step, step)
