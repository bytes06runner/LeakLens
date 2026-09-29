"""Synthetic datasets for the injected benchmark, one generator per base pipeline.

Each generator is deterministic given `seed` and returns {relative path: DataFrame or ndarray}. Pipelines read
these files exactly as a real notebook would (`pd.read_csv("data.csv")`, a folder of `.npy` recordings), so the
analysed code never sees the generator. Signals are built so that each injected leak can inflate the metric:
entity effects for group leakage, autocorrelated series for temporal leakage, many noise features for supervised
selection, a rare class for oversampling.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


# ---------------------------------------------------------------- tabular


def tab_credit(seed: int) -> dict:
    """Binary credit default, 900 rows, 8 informative + 32 noise numeric features, one categorical, some NaNs."""
    r = _rng(seed)
    n, k_inf, k_noise = 900, 8, 32
    Xi = r.normal(size=(n, k_inf))
    logit = Xi @ r.normal(0.6, 0.2, k_inf) - 0.3
    y = (r.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    df = pd.concat([pd.DataFrame(Xi, columns=[f"f{i}" for i in range(k_inf)]),
                    pd.DataFrame(r.normal(size=(n, k_noise)), columns=[f"n{i}" for i in range(k_noise)])], axis=1)
    df["region"] = r.choice(["north", "south", "east", "west"], n)
    df.loc[r.random(n) < 0.05, "f1"] = np.nan
    df.insert(0, "customer_id", np.arange(100000, 100000 + n))  # unique per row: not an entity with repeats
    df["default"] = y
    return {"data.csv": df}


def tab_housing(seed: int) -> dict:
    """Regression, 800 rows, nonlinear signal in 6 features + 20 noise, NaNs in two columns."""
    r = _rng(seed)
    n = 800
    df = pd.DataFrame({
        "area": r.gamma(4, 30, n), "rooms": r.integers(1, 7, n), "age": r.integers(0, 80, n),
        "dist_center": r.exponential(8, n), "crime": r.gamma(2, 1.5, n), "school": r.normal(6, 2, n),
    })
    df = pd.concat([df, pd.DataFrame(r.normal(size=(n, 20)), columns=[f"n{i}" for i in range(20)])], axis=1)
    price = (2.0 * df["area"] + 15 * df["rooms"] - 0.8 * df["age"] - 6 * np.log1p(df["dist_center"])
             - 4 * df["crime"] + 5 * df["school"] + r.normal(0, 25, n))
    df.loc[r.random(n) < 0.06, "school"] = np.nan
    df.loc[r.random(n) < 0.04, "age"] = np.nan
    df["price"] = price
    return {"data.csv": df}


def tab_fraud(seed: int) -> dict:
    """Imbalanced binary (about 6% positive), 2000 rows, 10 features."""
    r = _rng(seed)
    n = 2000
    X = r.normal(size=(n, 10))
    logit = 1.2 * X[:, 0] - 0.9 * X[:, 1] + 0.7 * X[:, 2] * X[:, 3] - 3.4
    y = (r.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    df = pd.DataFrame(X, columns=[f"v{i}" for i in range(10)])
    df["amount"] = r.lognormal(3, 1, n) * (1 + y)
    df["is_fraud"] = y
    return {"data.csv": df}


def tab_churn(seed: int) -> dict:
    """Wide, small: 300 rows, 3 weak informative + 150 noise features (supervised selection leak matters)."""
    r = _rng(seed)
    n = 300
    Xi = r.normal(size=(n, 3))
    y = (Xi @ np.array([0.5, -0.4, 0.3]) + r.normal(0, 1.2, n) > 0).astype(int)
    df = pd.concat([pd.DataFrame(Xi, columns=["tenure_z", "usage_z", "complaints_z"]),
                    pd.DataFrame(r.normal(size=(n, 150)), columns=[f"usage_{i}" for i in range(150)])], axis=1)
    df["plan"] = r.choice(["basic", "plus", "pro"], n)
    df["churned"] = y
    return {"data.csv": df}


# ---------------------------------------------------------------- time series


def _ar_series(r, n, phi=0.9, scale=1.0):
    e = r.normal(0, scale, n)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + e[t]
    return x


def ts_sales(seed: int) -> dict:
    """Daily sales for one store over three years: trend + weekly season + AR noise."""
    r = _rng(seed)
    n = 1095
    t = np.arange(n)
    sales = 200 + 0.08 * t + 25 * np.sin(2 * np.pi * t / 7) + 12 * _ar_series(r, n, 0.85, 1.5)
    df = pd.DataFrame({"date": pd.date_range("2021-01-01", periods=n, freq="D"), "sales": sales,
                       "promo": (r.random(n) < 0.15).astype(int), "temperature": 15 + 10 * np.sin(2 * np.pi * t / 365)
                       + r.normal(0, 2, n)})
    df.loc[df["promo"] == 1, "sales"] += 30
    return {"data.csv": df}


def ts_sensor(seed: int) -> dict:
    """Hourly readings from 6 devices over 40 days; each device a slowly drifting AR process."""
    r = _rng(seed)
    hours = 40 * 24
    frames = []
    for d in range(6):
        base = r.normal(50, 5)
        temp = base + 3 * _ar_series(r, hours, 0.97, 0.5) + 2 * np.sin(2 * np.pi * np.arange(hours) / 24)
        vib = 0.3 * temp + _ar_series(r, hours, 0.8, 0.8)
        frames.append(pd.DataFrame({"timestamp": pd.date_range("2023-03-01", periods=hours, freq="h"),
                                    "device": f"dev{d}", "temp": temp, "vibration": vib,
                                    "load": r.uniform(0.2, 1.0, hours)}))
    df = pd.concat(frames).sort_values(["timestamp", "device"]).reset_index(drop=True)
    return {"data.csv": df}


def ts_energy(seed: int) -> dict:
    """Hourly building energy use for 200 days with daily and weekly cycles."""
    r = _rng(seed)
    n = 200 * 24
    t = np.arange(n)
    load = (100 + 30 * np.sin(2 * np.pi * t / 24) + 15 * np.sin(2 * np.pi * t / (24 * 7))
            + 8 * _ar_series(r, n, 0.95, 1.0))
    outside = 10 + 8 * np.sin(2 * np.pi * t / 24 - 1) + _ar_series(r, n, 0.9, 0.5)
    df = pd.DataFrame({"datetime": pd.date_range("2022-01-01", periods=n, freq="h"), "load_kw": load,
                       "outside_temp": outside, "occupancy": (np.sin(2 * np.pi * t / 24) > 0).astype(int)})
    return {"data.csv": df}


def ts_air(seed: int) -> dict:
    """Daily air quality with weather covariates over four years; classify high-pollution next day."""
    r = _rng(seed)
    n = 1460
    t = np.arange(n)
    wind = np.abs(r.normal(3, 1.5, n))
    pm = 40 + 15 * np.cos(2 * np.pi * t / 365) + 10 * _ar_series(r, n, 0.8, 1.2) - 3 * wind
    df = pd.DataFrame({"day": pd.date_range("2019-01-01", periods=n, freq="D"), "pm25": pm, "wind": wind,
                       "humidity": np.clip(r.normal(60, 15, n), 10, 100), "rain_mm": r.exponential(2, n)})
    return {"data.csv": df}


# ---------------------------------------------------------------- grouped


def grp_eeg(seed: int) -> dict:
    """EEG-style recordings: 16 subjects, one file each; subject identity is only in the file name.

    Each subject has a stable amplitude/spectral fingerprint and its own share of 'event' windows (5% to 80%);
    the event itself adds only a weak oscillation. Recognising the subject therefore predicts events far better
    than the event signal does, as in segment-based EEG evaluation (Brookshire et al. 2024).
    """
    r = _rng(seed)
    fs, seconds, win = 100, 120, 200
    files = {}
    for s in range(16):
        base, gain, tilt = r.normal(0, 1.0), r.uniform(0.6, 1.6), r.uniform(0.5, 3.0)
        rate = r.uniform(0.05, 0.8)
        n_win = fs * seconds // win
        events = (r.random(n_win) < rate).astype(int)
        t = np.linspace(0, 20 * np.pi, win)
        sig = []
        for e in events:
            w = base + gain * r.normal(0, 1.0, win) + 0.3 * np.sin(t / tilt) + (0.15 * e) * np.sin(t)
            sig.append(w)
        files[f"recordings/sub-{s:02d}_task-rest_eeg.npy"] = np.concatenate(sig).astype(np.float32)
        files[f"recordings/sub-{s:02d}_task-rest_events.npy"] = events.astype(np.int8)
    return files


def grp_patients(seed: int) -> dict:
    """Multi-visit clinical data: 180 patients x 2-6 visits.

    Stable per-patient traits (height, resting heart rate, a lab baseline) act as a fingerprint; the outcome has a
    strong patient-specific component unrelated to those traits' population-level effect, plus a modest effect of
    blood pressure. Seeing a patient in training reveals their personal risk.
    """
    r = _rng(seed)
    rows = []
    for p in range(180):
        height, hr0, lab0 = r.normal(170, 9), r.normal(68, 8), r.normal(1.0, 0.3)
        v = r.normal(0, 1.6)  # personal risk, not measured
        for visit in range(r.integers(2, 7)):
            bp = 125 + r.normal(0, 12)
            risk = 0.03 * (bp - 125) + v + r.normal(0, 0.5)
            rows.append({"patient_id": f"P{p:04d}", "visit": visit, "height_cm": height + r.normal(0, 0.3),
                         "resting_hr": hr0 + r.normal(0, 1.5), "creatinine": lab0 + r.normal(0, 0.03),
                         "bp_sys": bp, "age": 40 + p % 40 + visit, "complication": int(risk > 0.8)})
    return {"data.csv": pd.DataFrame(rows)}


def grp_users(seed: int) -> dict:
    """Web sessions: 250 users x 3-12 sessions; each user has a device fingerprint and a personal propensity."""
    r = _rng(seed)
    rows = []
    for u in range(250):
        prop = r.normal(-1.0, 1.8)
        screen, habit_hour, speed = r.choice([360, 390, 414, 1280, 1440, 1920]), r.integers(0, 24), r.lognormal(0, 0.4)
        for _ in range(r.integers(3, 13)):
            pages = max(1, int(r.poisson(5)))
            cart = int(r.random() < 0.3)
            logit = prop + 0.05 * pages + 0.6 * cart
            rows.append({"user_id": u, "pages": pages, "duration_s": abs(r.normal(120, 30)) * speed,
                         "added_to_cart": cart, "device": "mobile" if screen < 500 else "desktop",
                         "screen_width": screen, "hour": int((habit_hour + r.integers(-1, 2)) % 24),
                         "purchased": int(r.random() < 1 / (1 + np.exp(-logit)))})
    return {"data.csv": pd.DataFrame(rows)}


def grp_sites(seed: int) -> dict:
    """Multi-site study: 12 clinics x 120 patients; clinic-level batch effect on markers and on the base rate."""
    r = _rng(seed)
    rows = []
    for c in range(12):
        batch = r.normal(0, 1.5, 4)
        base_rate = r.normal(0, 1.5)
        for _ in range(120):
            m = r.normal(0, 1, 4)
            logit = 0.5 * m[0] - 0.4 * m[1] + base_rate
            rows.append({"site": f"clinic_{c:02d}", "marker_a": m[0] + batch[0], "marker_b": m[1] + batch[1],
                         "marker_c": m[2] + batch[2], "marker_d": m[3] + batch[3],
                         "diagnosis": int(r.random() < 1 / (1 + np.exp(-logit)))})
    return {"data.csv": pd.DataFrame(rows)}


GENERATORS = {
    f.__name__: f
    for f in (tab_credit, tab_housing, tab_fraud, tab_churn, ts_sales, ts_sensor, ts_energy, ts_air,
              grp_eeg, grp_patients, grp_users, grp_sites)
}


def write(base: str, seed: int, dest) -> list[str]:
    """Write the dataset for `base` and `seed` under directory `dest`; return relative paths written."""
    from pathlib import Path

    dest = Path(dest)
    written = []
    for rel, obj in GENERATORS[base](seed).items():
        path = dest / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(obj, pd.DataFrame):
            obj.to_csv(path, index=False)
        else:
            np.save(path, obj)
        written.append(rel)
    return written
