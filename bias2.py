"""NQ Bias v2 – modellen bygget på 15 år med 5-minutters data (se research/).

Forskjell fra v1:
  - Historikk fra Dukascopy (Nasdaq 100 og S&P 500 i 5-min fra 2011, ~3700 handelsdager)
    i stedet for 2 år fra Yahoo.
  - Variablene velges med en fast prosedyre: hver hypotese testes for seg, korrigeres for
    multippel testing, og må ha samme fortegn i alle tre deler av perioden.
  - Forventet treffrate hentes fra en ærlig walk-forward-test der også variabelutvalget
    kun brukte fortiden (research/results.json).
"""
from __future__ import annotations

import json
import math
import sys
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "research"))
import analyze as A  # noqa: E402

import config as C  # noqa: E402

warnings.filterwarnings("ignore")
MODEL_PATH = C.DATA_DIR / "model_v2.joblib"
RESULTS_PATH = HERE / "research" / "results.json"
H1_KEYS = ["usdjpy", "xauusd", "lightcmdusd", "ustbondtrusd", "dollaridxusd"]
NEUTRAL = 0.06      # under 6 pp fra 50 % = nøytral (research: ingen fordel under dette)
STRONG = 0.10       # 10 pp eller mer = tydelig
MODEL_VERSION = 1

# Lesbare navn og begrunnelser for variablene modellen kan velge
LABELS: dict[str, tuple[str, str]] = {}
for col, name, _exp, why in A.CONT + A.BIN:
    LABELS[col] = (name, why)
LABELS.update({
    "gap_x_news": ("Gap på 08:30-nyhetsdag", "Gapet på dager med store makrotall har historisk blitt delvis reversert i første time."),
    "gap_x_nonews": ("Gap på dag uten nyhet", "Gap uten nyhet."),
    "pre_news_x_news": ("Reaksjon på 08:30-tallet", "Bevegelsen fra 08:25 til åpning på nyhetsdager har en tendens til å reverseres."),
    "gap_x_thufri": ("Gap torsdag/fredag", "Åpningsreverseringen er sterkest mot slutten av uka (Boyarchenko m.fl.)."),
    "gap_x_big": ("Stort gap (over 1σ)", "Store gap reverseres mer enn små."),
    "gap_x_outside": ("Gap utenfor gårsdagens range", "Åpning utenfor gårsdagens høy/lav har reversert oftere."),
    "gap_x_earn": ("Gap på earnings-dag", "Gap etter megacap-earnings."),
    "gap_x_vix": ("Gap når VIX er høy", "Reversering ved høy volatilitet."),
    "asia_z": ("Asia-økt (16:00→03:00)", "Bevegelse gjennom Asia-økta."),
    "london_z": ("London-økt (03:00→08:25)", "Bevegelse gjennom London-økta."),
})
for k, v in {"fh_mom5_z": "Første time har gått motsatt vei av de siste dagenes første time oftere enn tilfeldig.",
             "fh_mom20_z": "Første time har gått motsatt vei av snittet de siste 20 dagene oftere enn tilfeldig."}.items():
    LABELS[k] = (LABELS[k][0], v)
BINARY = set(A.CAND_BIN)


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def load_inputs(with_yahoo: bool = True) -> dict:
    nq = A.load_series("usatechidxusd", "m5")
    es = A.load_series("usa500idxusd", "m5")
    h1 = {k: A.load_series(k, "h1") for k in H1_KEYS}
    h1 = {k: v for k, v in h1.items() if not v.empty}
    ydaily = A.yahoo_daily() if with_yahoo else {}
    earn = A.earnings_dates() if with_yahoo else []
    return {"nq": nq, "es": es, "h1": h1, "ydaily": ydaily, "earn": earn}


def last_bar_end(inputs: dict) -> pd.Timestamp | None:
    nq = inputs["nq"]
    return pd.Timestamp(nq["end"].iloc[-1]) if len(nq) else None


def yahoo_bars(ticker: str) -> pd.DataFrame:
    """Reserve for dagens rad: 5-minutters barer fra Yahoo (samme format som Dukascopy)."""
    import yfinance as yf
    raw = yf.download(ticker, period="5d", interval="5m", prepost=True, progress=False, auto_adjust=False)
    if raw is None or raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    df = raw.rename(columns={"Open": "o", "High": "h", "Low": "l", "Close": "c"})[["o", "h", "l", "c"]].dropna()
    idx = pd.DatetimeIndex(df.index)
    df.index = (idx if idx.tz is not None else idx.tz_localize("UTC")).tz_convert(A.NY)
    df["end"] = df.index + pd.Timedelta(minutes=5)
    return df


def table(inputs: dict, live: pd.Timestamp | None = None, live_nq=None, live_es=None) -> pd.DataFrame:
    df = A.build_days(inputs["nq"], inputs["es"], inputs["h1"], inputs["ydaily"], inputs["earn"],
                      live=live, live_nq=live_nq, live_es=live_es)
    return A.add_features(df, list(inputs["h1"]))


# ---------------------------------------------------------------------------
# Modell
# ---------------------------------------------------------------------------
def train(df: pd.DataFrame) -> dict:
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    hist = df.dropna(subset=["y"])
    sel = A.select_features(hist)
    model = {"version": MODEL_VERSION, "features": sel, "trained_on": datetime.now(tz=C.OSLO).strftime("%Y-%m-%d %H:%M"),
             "n": int(len(hist)), "first": str(hist.index.min()), "last": str(hist.index.max()),
             "base_up": float(hist["y"].mean())}
    if sel:
        X = hist[sel].astype(float).clip(-5, 5)
        pipe = make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), StandardScaler(),
                             LogisticRegression(C=0.05, max_iter=2000))
        pipe.fit(X, hist["y"].astype(int))
        model["pipe"] = pipe
    return model


def save(model: dict) -> None:
    C.DATA_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)


def load() -> dict | None:
    try:
        m = joblib.load(MODEL_PATH)
        return m if m.get("version") == MODEL_VERSION else None
    except Exception:
        return None


def get_model(df: pd.DataFrame, force: bool = False) -> dict:
    m = load()
    today = datetime.now(tz=C.OSLO).strftime("%Y-%m-%d")
    if m is not None and not force and m["trained_on"].startswith(today):
        return m
    m = train(df)
    save(m)
    return m


def label(p: float) -> tuple[str, str]:
    d = p - 0.5
    if abs(d) < NEUTRAL:
        return "NØYTRAL", "Nøytral"
    return ("BULLISH" if d > 0 else "BEARISH"), ("Tydelig" if abs(d) >= STRONG else "Svak")


def value_text(col: str, row: pd.Series) -> str:
    v = row.get(col, np.nan)
    if col in BINARY:
        return "Ja" if v == 1 else "Nei"
    if not np.isfinite(v):
        return "–"
    if col.startswith("gap_x_"):
        return f"gap {row['gap'] * 100:+.2f} % ({row['gap_z']:+.1f}σ)" if v != 0 else "ikke aktiv i dag"
    if col == "pre_news_x_news":
        return f"{row['pre_news'] * 100:+.2f} % ({row['pre_news_z']:+.1f}σ)" if v != 0 else "ikke aktiv i dag"
    if col == "gap_z":
        return f"{row['gap'] * 100:+.2f} % ({v:+.1f}σ)"
    if col == "vix_ts":
        return f"{1 + v:.2f}"
    if col == "on_pos":
        return f"{v * 100:.0f} % av overnight-range"
    if col in ("y10_chg5",):
        return f"{v * 100:+.0f} bp"
    return f"{v:+.2f}σ"


def predict(model: dict, row: pd.DataFrame) -> dict:
    r = row.iloc[0]
    sel = model["features"]
    if not sel or "pipe" not in model:
        p = model["base_up"]
        return {"p": p, "reasons": []}
    X = row[sel].astype(float).clip(-5, 5)
    pipe = model["pipe"]
    p = float(pipe.predict_proba(X)[0, 1])
    z = pipe[:-1].transform(X)[0]
    coef = pipe[-1].coef_[0]
    reasons = []
    for col, zi, ci in zip(sel, z, coef):
        pp = ci * zi * p * (1 - p) * 100
        name, why = LABELS.get(col, (col, ""))
        reasons.append({"key": col, "label": name, "value": value_text(col, r), "pp": float(pp), "why": why,
                        "missing": bool(not np.isfinite(r.get(col, np.nan)))})
    return {"p": p, "reasons": reasons}


# ---------------------------------------------------------------------------
# Lignende dager
# ---------------------------------------------------------------------------
UKEDAGER = ["mandager", "tirsdager", "onsdager", "torsdager", "fredager"]


def similar_days(df: pd.DataFrame, row: pd.Series) -> list[dict]:
    h = df.dropna(subset=["y"])
    out = []

    def add(name, mask):
        s = h[mask.reindex(h.index).fillna(False).astype(bool)]
        if len(s) >= 20:
            rec = s[pd.DatetimeIndex(s.index) >= pd.Timestamp(h.index[-1]) - pd.Timedelta(days=3 * 365)]
            out.append({"name": name, "n": int(len(s)), "up": float(s["y"].mean()), "bp": float(s["fh"].mean() * 1e4),
                        "n_recent": int(len(rec)), "up_recent": float(rec["y"].mean()) if len(rec) >= 10 else None})

    add("Alle dager", pd.Series(True, index=h.index))
    wd = int(row["dow"])
    if wd < 5:
        add(f"Alle {UKEDAGER[wd]}", h["dow"] == wd)
    if row.get("opex") == 1:
        add("Opsjonsforfall-fredager", h["opex"] == 1)
    g = row.get("gap_z", np.nan)
    if np.isfinite(g):
        bins = [(-99, -1, "Stort gap ned (under −1σ)"), (-1, -0.3, "Gap ned (−1σ til −0,3σ)"), (-0.3, 0.3, "Nesten flat åpning"),
                (0.3, 1, "Gap opp (0,3σ til 1σ)"), (1, 99, "Stort gap opp (over 1σ)")]
        for lo, hi, name in bins:
            if lo <= g < hi:
                add(name, (h["gap_z"] >= lo) & (h["gap_z"] < hi))
                if row.get("news_day") == 1:
                    add(name + " på nyhetsdag", (h["gap_z"] >= lo) & (h["gap_z"] < hi) & (h["news_day"] == 1))
    if row.get("news_day") == 1:
        add("Dager med stor 08:30-bevegelse", h["news_day"] == 1)
    gv = row.get("gap_vs_range", np.nan)
    if gv == 1:
        add("Åpning over gårsdagens høy", h["gap_vs_range"] == 1)
    elif gv == -1:
        add("Åpning under gårsdagens lav", h["gap_vs_range"] == -1)
    m20 = row.get("fh_mom20_z", np.nan)
    if np.isfinite(m20):
        q = h["fh_mom20_z"].quantile([0.2, 0.8])
        if m20 <= q.iloc[0]:
            add("Første time har vært svak de siste 20 dagene (laveste 20 %)", h["fh_mom20_z"] <= q.iloc[0])
        elif m20 >= q.iloc[1]:
            add("Første time har vært sterk de siste 20 dagene (høyeste 20 %)", h["fh_mom20_z"] >= q.iloc[1])
    vt = row.get("vix_ts", np.nan)
    if np.isfinite(vt) and vt > 0:
        add("VIX over VIX3M (backwardation)", h["vix_ts"] > 0)
    if row.get("earn") == 1:
        add("Megacap-earnings over natten", h["earn"] == 1)
    if row.get("tom") == 1:
        add("Månedsskifte", h["tom"] == 1)
    return out


# ---------------------------------------------------------------------------
# Forskningsresultater til visning
# ---------------------------------------------------------------------------
def research_summary() -> dict:
    try:
        R = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    honest = next((m for m in R.get("models", []) if m["name"].startswith("Ærlig")), None)
    tests = sorted(R.get("tests", []), key=lambda t: t.get("q", 1))
    compact = []
    for t in tests:
        row = {"name": t["name"], "kind": t["kind"], "n": t["n"], "q": t.get("q"), "passes": t.get("passes"), "stable": t.get("stable")}
        if t["kind"] == "bin":
            row.update({"up1": t["up1"], "up0": t["up0"], "bp1": t["bp1"], "bp0": t["bp0"]})
        else:
            row.update({"rho": t["rho"], "t": t["t"], "r1": t.get("rho_2011"), "r2": t.get("rho_2016"), "r3": t.get("rho_2021")})
        compact.append(row)
    return {"generated": R.get("generated"), "n_days": R.get("n_days"), "first": R.get("first"), "last": R.get("last"),
            "base_up": R.get("base_up"), "honest": honest, "placebo": R.get("placebo_nested"),
            "tests": compact, "rolling": R.get("nested_rolling", [])}


def class_hist(summary: dict, strength: str) -> dict | None:
    """Historisk treff for dagens klasse, fra den ærlige walk-forward-testen."""
    h = (summary or {}).get("honest")
    if not h:
        return None
    groups = {"Nøytral": ["under 3 pp", "3–6 pp"], "Svak": ["6–10 pp"], "Tydelig": ["over 10 pp"]}[strength]
    rows = [t for t in h["tiers"] if t["tier"] in groups]
    n = sum(t["n"] for t in rows)
    if not n:
        return None
    return {"name": strength, "n": n, "hit_rate": sum(t["hit"] * t["n"] for t in rows) / n,
            "signed_bp": sum(t["bp"] * t["n"] for t in rows) / n}
