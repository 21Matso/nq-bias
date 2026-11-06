"""Nettside-versjonen: lager docs/data.json som docs/index.html viser.

Kjøres av GitHub Actions (se .github/workflows/nq-bias.yml). Hver kjøring
bestemmer selv hva den skal gjøre ut fra klokka i New York:

    08:15–08:59 ET  forberedelse: tren modellen for dagen, oppdater backtest
    09:00–09:29 ET  dagens bias: beregn, logg i journalen, publiser
    ellers          oppfølging: fyll inn fasit, oppdater journal og backtest

Dagens bias blir stående på siden til neste handelsdags bias er klar.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, time, timedelta

import numpy as np
import pandas as pd

import config as C
import data as D
import journal as J
import report as R
from features import FEATURES

SITE_DIR = C.BASE_DIR / "docs"
DATA_JSON = SITE_DIR / "data.json"
PREP_START_ET = time(8, 15)
LIVE_START_ET = time(9, 0)


# ---------------------------------------------------------------------------
def clean(x):
    """Gjør alt JSON-vennlig: numpy -> python, NaN/inf -> None."""
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, (np.floating, float)):
        f = float(x)
        return None if not math.isfinite(f) else round(f, 6)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, (pd.Timestamp, datetime)):
        return x.isoformat()
    return x


def next_open(now_et: pd.Timestamp) -> pd.Timestamp:
    d = now_et.date()
    while d.weekday() >= 5 or (d == now_et.date() and now_et.time() >= C.OPEN_ET):
        d += timedelta(days=1)
    return pd.Timestamp(datetime.combine(d, C.OPEN_ET), tz=C.NY)


def verdict(tr) -> tuple[str, str]:
    m = tr.wf.metrics
    if not m:
        return "bad", "Ingen walk-forward-resultater ennå (for lite data)."
    c = m["p_cal"]
    if c["p_value"] < 0.05 and c["brier"] < c["brier_naive"]:
        return "good", "Modellen har slått gjetting på dager den ikke hadde sett, med statistisk dekning."
    if c["p_value"] < 0.20 and c["brier"] <= c["brier_naive"] * 1.002:
        return "meh", ("Svakt signal: litt bedre enn gjetting, men ikke statistisk sikkert. "
                       "Behandle biasen som én innsikt, ikke som en fasit.")
    return "bad", ("Modellen har ikke vist seg bedre enn gjetting på dager den ikke hadde sett. "
                   "Biasen krympes derfor nesten helt mot 50 %.")


# ---------------------------------------------------------------------------
def live_payload(ctx: dict) -> dict:
    row = ctx["row"].iloc[0]
    pred = ctx["pred"]
    tr = ctx["trained"]
    p = pred["p_cal"]
    bias, strength = R.bias_label(p)

    rs = pred["reasons"].copy()
    rs = rs[~rs["missing"]]
    rs = rs.drop(index=[n for n in R.BINARY if row.get(n, 0) != 1 and n in rs.index])
    rs = rs[rs["pp"].abs() >= 0.15]

    def arg(name, r):
        info = FEATURES[name]
        return {"key": name, "label": info.label, "value": R.feature_value_text(name, row),
                "pp": r["pp"], "why": info.why, "source": info.source, "group": info.group}

    bull = [arg(n, r) for n, r in rs[rs["pp"] > 0].sort_values("pp", ascending=False).iterrows()]
    bear = [arg(n, r) for n, r in rs[rs["pp"] < 0].sort_values("pp").iterrows()]

    cls = None
    bk = tr.wf.buckets
    if bk is not None and strength in bk.index and bk.loc[strength, "n"] > 0:
        b = bk.loc[strength]
        cls = {"name": strength, "hit_rate": b["hit_rate"], "n": int(b["n"]), "signed_bp": b["signed_bp"]}

    nq = ctx["nq_price"]
    med = row.get("raw_fh_abs_med_pct", np.nan)
    typical = nq * med / 100 if np.isfinite(nq) and np.isfinite(med) else None

    events = []
    for ev in ctx["events"]:
        t = ev["time"]
        where = "before" if t.time() < C.OPEN_ET else "first_hour" if t.time() <= C.FIRST_HOUR_END_ET else "after"
        events.append({"oslo": f"{t.tz_convert(C.OSLO):%H:%M}", "et": f"{t:%H:%M}", "title": ev["title"],
                       "impact": ev["impact"], "forecast": ev["forecast"], "previous": ev["previous"],
                       "actual": ev["actual"], "where": where})

    vt = row.get("raw_vix_ts", np.nan)
    regime = [{"name": k, "level": lvl, "chg": chg} for k, (lvl, chg) in ctx["regime"].items()]
    regime.append({"name": "VIX", "level": row.get("raw_vix", np.nan), "chg": None})
    regime.append({"name": "VIX / VIX3M", "level": 1 + vt if np.isfinite(vt) else None, "chg": None,
                   "note": ("backwardation (stress)" if np.isfinite(vt) and vt > 0 else "contango (normalt)")})

    missing = [FEATURES[m].label for m in pred["reasons"][pred["reasons"]["missing"]].index]
    open_oslo = ctx["open_et"].tz_convert(C.OSLO)
    return {
        "date": str(ctx["day"]),
        "weekday": R.UKEDAG[ctx["day"].weekday()],
        "run_oslo": f"{ctx['now_oslo']:%H:%M}",
        "run_et": f"{ctx['now_et']:%H:%M}",
        "open_oslo": f"{open_oslo:%H:%M}",
        "minutes_before_open": (ctx["open_et"] - ctx["now_et"]).total_seconds() / 60,
        "p": p, "p_raw": pred["p_raw"], "bias": bias, "strength": strength,
        "class_hist": cls,
        "nq_price": nq, "typical_points": typical,
        "bull": bull, "bear": bear,
        "market": [{"name": k, "last": last, "chg": chg} for k, (last, chg) in ctx["market"].items()],
        "regime": regime,
        "events": events,
        "flags": ctx["flags"],
        "headlines": [h for _, h in ctx["headlines"]],
        "warnings": ctx["warnings"],
        "missing": missing,
    }


def model_payload(tr) -> dict:
    wf = tr.wf
    level, text = verdict(tr)
    out = {"trained_on": tr.trained_on, "n_train": tr.n_train, "calib_b": wf.calib[1],
           "level": level, "verdict": text, "metrics": wf.metrics, "buckets": [], "features": []}
    if wf.buckets is not None:
        out["buckets"] = [{"name": str(k), "n": int(r["n"]), "hit_rate": r["hit_rate"], "signed_bp": r["signed_bp"]}
                          for k, r in wf.buckets.iterrows()]
    if wf.feature_stats is not None:
        coefs = pd.Series(tr.model.named_steps["lr"].coef_[0], index=wf.feature_stats.index)
        fs = wf.feature_stats.assign(a=wf.feature_stats["rho"].abs()).sort_values("a", ascending=False)
        for name, r in fs.iterrows():
            stable = bool(np.isfinite(r["rho_1"]) and np.isfinite(r["rho_2"]) and np.sign(r["rho_1"]) == np.sign(r["rho_2"]))
            out["features"].append({"label": FEATURES[name].label, "group": FEATURES[name].group,
                                    "rho": r["rho"], "t": r["t"], "rho_1": r["rho_1"], "rho_2": r["rho_2"],
                                    "stable": stable, "coef": coefs[name], "n": int(r["n"])})
    if not wf.preds.empty:
        pr = wf.preds.tail(250)
        hit = ((pr["p_cal"] > 0.5).astype(int) == pr["y"]).astype(float)
        out["rolling"] = [{"date": str(d), "hit60": h} for d, h in hit.rolling(60, min_periods=30).mean().dropna().items()]
    return out


def journal_payload() -> dict:
    s = J.summary()
    df = J.load()
    rows = []
    for _, r in df.sort_values("date", ascending=False).head(60).iterrows():
        rows.append({k: (None if pd.isna(r[k]) else r[k]) for k in
                     ("date", "run_time_oslo", "p_cal", "bias", "strength", "fh_ret_pct", "nq_points", "outcome", "correct")})
    by = [{"name": k, "n": n, "hit_rate": h} for k, (n, h) in s["by_strength"].items()]
    return {"logged": s["logged"], "with_outcome": s["with_outcome"], "directional": s["directional"],
            "hits": s["hits"], "hit_rate": s["hit_rate"], "neutral_days": s["neutral_days"],
            "by_strength": by, "rows": rows}


# ---------------------------------------------------------------------------
def load_existing() -> dict:
    try:
        return json.loads(DATA_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_payload(payload: dict) -> None:
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = DATA_JSON.with_suffix(".tmp")
    tmp.write_text(json.dumps(clean(payload), ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(DATA_JSON)


def decide_phase(now_et: pd.Timestamp, forced: str | None) -> str:
    if forced and forced != "auto":
        return forced
    if now_et.weekday() >= 5:
        return "followup"
    t = now_et.time()
    if LIVE_START_ET <= t < C.OPEN_ET:
        return "live"
    if PREP_START_ET <= t < LIVE_START_ET:
        return "prep"
    return "followup"


def run(args, nq) -> str:
    """nq = nqbias-modulen (for å gjenbruke load_bundle, get_model, compute_live)."""
    now_et = D.now_ny()
    phase = decide_phase(now_et, getattr(args, "mode", None))
    payload = load_existing()
    R.console.print(f"[bold]Nettside-kjøring[/bold]  {now_et:%Y-%m-%d %H:%M} ET  ·  fase: {phase}")

    from features import rth_daily_table
    from model import load_trained

    tr, error = None, None
    try:
        if phase == "live":
            ctx = nq.compute_live(args, quiet_weekend=True)
            if ctx is not None:
                nq.log_live(ctx)
                payload["today"] = live_payload(ctx)
                tr = ctx["trained"]
        else:
            bundle = nq.load_bundle(max_age_sec=300)
            J.fill_outcomes(rth_daily_table(bundle["rth"]["QQQ"]))
            tr = nq.get_model(bundle, retrain=False)   # trener på nytt én gang per dag
    except SystemExit:
        error = "Kjøringen feilet: " + ("; ".join(D.SOURCE_ERRORS) or "ukjent årsak (se loggen i GitHub Actions)")
    except Exception as e:  # siden skal fortsatt oppdateres med feilmeldingen
        error = f"Kjøringen feilet: {type(e).__name__}: {e}"
    if tr is None:
        tr = load_trained()

    if tr is not None:
        payload["model"] = model_payload(tr)
    payload["journal"] = journal_payload()
    nxt = next_open(now_et)
    nxt_oslo = nxt.tz_convert(C.OSLO)
    payload["meta"] = {
        "generated_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "generated_oslo": f"{now_et.tz_convert(C.OSLO):%Y-%m-%d %H:%M}",
        "phase": phase,
        "next_open_date": str(nxt.date()),
        "next_open_oslo": f"{nxt_oslo:%H:%M}",
        "next_open_label": f"{R.UKEDAG[nxt.weekday()]} {nxt:%d.%m}",
        "next_bias_oslo": f"{(nxt_oslo - pd.Timedelta(minutes=30)):%H:%M}–{(nxt_oslo - pd.Timedelta(minutes=5)):%H:%M}",
        "source_errors": list(D.SOURCE_ERRORS),
        "error": error,
    }
    write_payload(payload)
    R.console.print(f"Skrev {DATA_JSON}")
    if error:
        R.console.print(f"[red]{error}[/red]")
    return phase
