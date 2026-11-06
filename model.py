"""Modellen: regularisert logistisk regresjon, testet med walk-forward.

Hvorfor så enkel modell? Med ~2 år timesdata (~480 dager) og svakt signal er
risikoen for overtilpasning det største problemet. Logistisk regresjon med
sterk L2-krymping trekker alt mot 50 % med mindre dataene tydelig sier noe
annet, og hver variabels bidrag kan forklares i klartekst.

Kalibrering: walk-forward-prediksjonene (som modellen aldri har trent på)
brukes til å skalere hvor mye vi stoler på modellen. Har den ikke slått
tilfeldig gjetting historisk, krympes dagens sannsynlighet mot 50 %.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import warnings
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from scipy.stats import binomtest, spearmanr
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

import config as C
from features import FEATURE_COLS

warnings.filterwarnings("ignore", message=".*constant.*")
warnings.filterwarnings("ignore", category=RuntimeWarning)


def _clip(x):
    return np.clip(x, -C.Z_CLIP, C.Z_CLIP)


def make_pipeline(c: float = 0.03) -> Pipeline:
    return Pipeline([
        ("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
        ("scale", StandardScaler()),
        ("clip", FunctionTransformer(_clip)),
        ("lr", LogisticRegression(C=c, max_iter=2000)),
    ])


def fit_model(X: pd.DataFrame, y: pd.Series) -> Pipeline:
    """Velger krympingsstyrke med tidsserie-kryssvalidering (bare treningsdata)."""
    n_splits = 5 if len(X) >= 150 else 3
    gs = GridSearchCV(
        make_pipeline(),
        {"lr__C": C.C_GRID},
        cv=TimeSeriesSplit(n_splits=n_splits),
        scoring="neg_log_loss",
        n_jobs=1,
    )
    gs.fit(X, y)
    return gs.best_estimator_


def _xy(df: pd.DataFrame):
    d = df.dropna(subset=["y"])
    return d[FEATURE_COLS].astype(float), d["y"].astype(int), d


# ---------------------------------------------------------------------------
# Walk-forward backtest
# ---------------------------------------------------------------------------
@dataclass
class WalkForward:
    preds: pd.DataFrame                       # dato, p_raw, y, fh_ret
    metrics: dict = field(default_factory=dict)
    buckets: pd.DataFrame | None = None
    calib: tuple[float, float] = (0.0, 1.0)  # (a, b) i logit(p_cal) = a + b*logit(p_raw)
    feature_stats: pd.DataFrame | None = None


def _logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def _sigmoid(z):
    return 1 / (1 + np.exp(-z))


def fit_calibration(p_raw: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Plattskalering på ut-av-utvalg-prediksjoner. b klippes til [0, 1.5]:
    b≈0 betyr 'modellen har ingen verdi' → alt krympes mot grunnraten."""
    if len(y) < 60 or len(np.unique(y)) < 2:
        return 0.0, 0.5
    lr = LogisticRegression(C=1.0)
    lr.fit(_logit(p_raw).reshape(-1, 1), y)
    a, b = float(lr.intercept_[0]), float(lr.coef_[0, 0])
    b = float(np.clip(b, 0.0, 1.5))
    # re-estimer a gitt klippet b (så gjennomsnittet stemmer)
    if b == 0.0:
        base = float(np.mean(y))
        a = float(_logit(base))
    return a, b


def calibrate(p_raw, calib: tuple[float, float]):
    a, b = calib
    return _sigmoid(a + b * _logit(np.asarray(p_raw, dtype=float)))


def walk_forward(df: pd.DataFrame, progress=None) -> WalkForward:
    X, y, d = _xy(df)
    n = len(X)
    start = min(C.MIN_TRAIN_DAYS, max(60, n // 2))
    out = []
    i = start
    steps = list(range(start, n, C.REFIT_EVERY))
    for k, i in enumerate(steps):
        j = min(i + C.REFIT_EVERY, n)
        if y.iloc[:i].nunique() < 2:
            continue
        m = fit_model(X.iloc[:i], y.iloc[:i])
        p = m.predict_proba(X.iloc[i:j])[:, 1]
        for idx, pi in zip(X.index[i:j], p):
            out.append({"date": idx, "p_raw": pi, "y": int(y.loc[idx]), "fh_ret": float(d.loc[idx, "fh_ret"])})
        if progress:
            progress(k + 1, len(steps))
    preds = pd.DataFrame(out).set_index("date") if out else pd.DataFrame(columns=["p_raw", "y", "fh_ret"])
    wf = WalkForward(preds=preds)
    if preds.empty:
        return wf

    # Kalibrering med "nøstet" walk-forward: hver dag kalibreres kun med tidligere OOS-prediksjoner
    p_cal = []
    pr, yy = preds["p_raw"].to_numpy(), preds["y"].to_numpy()
    for t in range(len(preds)):
        cal = fit_calibration(pr[:t], yy[:t]) if t >= 60 else (float(_logit(max(0.01, min(0.99, yy[:t].mean() if t else 0.5)))), 0.0)
        p_cal.append(float(calibrate([pr[t]], cal)[0]))
    preds["p_cal"] = p_cal
    wf.calib = fit_calibration(pr, yy)          # brukes for dagens prediksjon

    wf.metrics = evaluate(preds)
    wf.buckets = bucket_table(preds)
    wf.feature_stats = feature_stats(df)
    return wf


def evaluate(preds: pd.DataFrame) -> dict:
    y = preds["y"].to_numpy()
    res = {"n": int(len(y)), "start": str(preds.index.min()), "end": str(preds.index.max()),
           "base_up": float(y.mean())}
    for col in ("p_raw", "p_cal"):
        p = preds[col].to_numpy()
        hit = (p > 0.5).astype(int) == y
        # naiv referanse: grunnraten fra fortiden (ekspanderende snitt, ingen fremtidsinfo)
        past_base = pd.Series(y).expanding().mean().shift(1).fillna(0.5).to_numpy()
        res[col] = {
            "accuracy": float(hit.mean()),
            "p_value": float(binomtest(int(hit.sum()), len(hit), 0.5, alternative="greater").pvalue),
            "brier": float(brier_score_loss(y, p)),
            "brier_naive": float(brier_score_loss(y, past_base)),
            "logloss": float(log_loss(y, np.clip(p, 1e-4, 1 - 1e-4))),
            "auc": float(roc_auc_score(y, p)) if len(np.unique(y)) > 1 else float("nan"),
            # gj.snitt første-time-avkastning i retning av biasen (bp, før kostnader)
            "signed_bp": float(np.mean(np.sign(p - 0.5) * preds["fh_ret"].to_numpy()) * 1e4),
        }
    res["always_up_accuracy"] = float(y.mean())
    return res


def bucket_table(preds: pd.DataFrame, col: str = "p_cal") -> pd.DataFrame:
    conf = (preds[col] - 0.5).abs()
    bins = [-0.001, C.NEUTRAL_BAND, C.STRONG_BAND, 1.0]
    labels = ["Nøytral", "Svak", "Tydelig"]
    g = preds.assign(conf=pd.cut(conf, bins=bins, labels=labels),
                     hit=((preds[col] > 0.5).astype(int) == preds["y"]).astype(float),
                     signed=np.sign(preds[col] - 0.5) * preds["fh_ret"] * 1e4)
    t = g.groupby("conf", observed=False).agg(n=("hit", "size"), hit_rate=("hit", "mean"), signed_bp=("signed", "mean"))
    return t


def feature_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Rangkorrelasjon mellom hver variabel og første-time-avkastningen,
    for hele perioden og hver halvdel (stabilitetssjekk)."""
    d = df.dropna(subset=["fh_ret"])
    half = len(d) // 2
    rows = []
    for c in FEATURE_COLS:
        x = d[c].astype(float)
        ok = x.notna()
        if ok.sum() < 30 or x[ok].nunique() < 2:
            rows.append({"feature": c, "rho": np.nan, "t": np.nan, "rho_1": np.nan, "rho_2": np.nan, "n": int(ok.sum())})
            continue
        rho, _ = spearmanr(x[ok], d.loc[ok, "fh_ret"])
        n = int(ok.sum())
        t = rho * np.sqrt((n - 2) / max(1e-9, 1 - rho ** 2))
        r1 = spearmanr(x.iloc[:half][ok.iloc[:half]], d["fh_ret"].iloc[:half][ok.iloc[:half]])[0] if ok.iloc[:half].sum() > 20 else np.nan
        r2 = spearmanr(x.iloc[half:][ok.iloc[half:]], d["fh_ret"].iloc[half:][ok.iloc[half:]])[0] if ok.iloc[half:].sum() > 20 else np.nan
        rows.append({"feature": c, "rho": rho, "t": t, "rho_1": r1, "rho_2": r2, "n": n})
    return pd.DataFrame(rows).set_index("feature")


# ---------------------------------------------------------------------------
# Endelig modell + lagring
# ---------------------------------------------------------------------------
@dataclass
class Trained:
    model: Pipeline
    wf: WalkForward
    trained_on: str
    n_train: int
    version: int = 2


def train_and_save(df: pd.DataFrame, progress=None) -> Trained:
    wf = walk_forward(df, progress=progress)
    X, y, _ = _xy(df)
    final = fit_model(X, y)
    tr = Trained(model=final, wf=wf, trained_on=datetime.now(tz=C.OSLO).strftime("%Y-%m-%d %H:%M"), n_train=len(X))
    C.DATA_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(tr, C.MODEL_PATH)
    return tr


def load_trained() -> Trained | None:
    if not C.MODEL_PATH.exists():
        return None
    try:
        tr = joblib.load(C.MODEL_PATH)
        return tr if getattr(tr, "version", 0) == 2 else None
    except Exception:
        return None


def predict_with_reasons(tr: Trained, row: pd.DataFrame) -> dict:
    """Sannsynlighet for at NQ er høyere 10:30 enn 09:30, pluss hvert bidrag."""
    X = row[FEATURE_COLS].astype(float)
    m = tr.model
    p_raw = float(m.predict_proba(X)[0, 1])
    p_cal = float(calibrate([p_raw], tr.wf.calib)[0])

    # bidrag i log-odds: koeffisient × standardisert (og klippet) verdi
    z = m[:-1].transform(X)[0]
    coefs = m.named_steps["lr"].coef_[0]
    b = tr.wf.calib[1]
    contrib = coefs * z * b                         # skalert med hvor mye vi stoler på modellen
    pp = contrib * p_cal * (1 - p_cal) * 100        # ≈ prosentpoeng
    reasons = pd.DataFrame({
        "feature": FEATURE_COLS,
        "z": z,
        "coef": coefs,
        "pp": pp,
        "missing": X.iloc[0].isna().to_numpy(),
    }).set_index("feature")
    return {"p_raw": p_raw, "p_cal": p_cal, "reasons": reasons}
