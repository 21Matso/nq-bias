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


def flags_v2(day, row: pd.Series, earnings: dict) -> list[str]:
    flags = []
    if day in set(C.FOMC_DECISION_DATES):
        t = pd.Timestamp(datetime.combine(day, time(14, 0)), tz=C.NY).tz_convert(C.OSLO)
        flags.append(f"FOMC-rentebeslutning i dag kl. {t:%H:%M} norsk tid (etter første time)")
    if row.get("opex") == 1:
        flags.append("Månedlig opsjonsforfall (OPEX) i dag")
    if row.get("news_day") == 1:
        flags.append("Stor bevegelse rundt 08:30-tallene i dag – modellen behandler dette som en nyhetsdag")
    if row.get("earn") == 1:
        flags.append("Earnings fra et av de største Nasdaq-selskapene siden i går kveld")
    later = sorted({t for t, lst in (earnings or {}).items() for ts in lst if ts.date() == day and ts.time() >= C.CLOSE_ET})
    if later:
        flags.append(f"Earnings etter stengning i dag: {', '.join(later)}")
    if row.get("tom") == 1:
        flags.append("Månedsskifte-vindu")
    return flags


def live_payload_v2(day, now_et, row_df, model, pred, summary, ctx_y, warnings, source) -> dict:
    import bias2 as B
    row = row_df.iloc[0]
    p = pred["p"]
    bias, strength = B.label(p)
    def active(r):   # ja/nei-variabler og interaksjoner vises bare når de faktisk gjelder i dag
        v = row.get(r["key"], np.nan)
        if r["key"] in B.BINARY or "_x_" in r["key"]:
            return np.isfinite(v) and v != 0
        return True
    rs = [r for r in pred["reasons"] if not r["missing"] and abs(r["pp"]) >= 0.15 and active(r)]
    bull = sorted([r for r in rs if r["pp"] > 0], key=lambda r: -r["pp"])
    bear = sorted([r for r in rs if r["pp"] < 0], key=lambda r: r["pp"])
    open_et = pd.Timestamp(datetime.combine(day, C.OPEN_ET), tz=C.NY)
    nq = ctx_y.get("nq_price", np.nan)
    med = ctx_y.get("fh_abs_med", np.nan)
    events = []
    for ev in ctx_y.get("events", []):
        t = ev["time"]
        where = "before" if t.time() < C.OPEN_ET else "first_hour" if t.time() <= C.FIRST_HOUR_END_ET else "after"
        events.append({"oslo": f"{t.tz_convert(C.OSLO):%H:%M}", "et": f"{t:%H:%M}", "title": ev["title"],
                       "impact": ev["impact"], "forecast": ev["forecast"], "previous": ev["previous"],
                       "actual": ev["actual"], "where": where})
    vix = row.get("vix", np.nan)
    vt = row.get("vix_ts", np.nan)
    regime = [{"name": k, "level": lvl, "chg": chg} for k, (lvl, chg) in ctx_y.get("regime", {}).items()]
    regime.append({"name": "VIX (i går)", "level": vix, "chg": None})
    regime.append({"name": "VIX / VIX3M", "level": 1 + vt if np.isfinite(vt) else None, "chg": None,
                   "note": ("backwardation (stress)" if np.isfinite(vt) and vt > 0 else "contango (normalt)")})
    return {
        "model_version": 2,
        "date": str(day), "weekday": R.UKEDAG[day.weekday()],
        "run_oslo": f"{now_et.tz_convert(C.OSLO):%H:%M}", "run_et": f"{now_et:%H:%M}",
        "open_oslo": f"{open_et.tz_convert(C.OSLO):%H:%M}",
        "minutes_before_open": (open_et - now_et).total_seconds() / 60,
        "p": p, "p_raw": p, "bias": bias, "strength": strength,
        "class_hist": B.class_hist(summary, strength),
        "nq_price": nq, "typical_points": nq * med if np.isfinite(nq) and np.isfinite(med) else None,
        "bull": bull, "bear": bear,
        "similar": B.similar_days(ctx_y["table"], row),
        "market": [{"name": k, "last": last, "chg": chg} for k, (last, chg) in ctx_y.get("market", {}).items()],
        "regime": regime, "events": events, "flags": flags_v2(day, row, ctx_y.get("earnings", {})),
        "headlines": [h for _, h in ctx_y.get("headlines", [])],
        "warnings": warnings, "missing": [r["label"] for r in pred["reasons"] if r["missing"]],
        "data_source": source,
    }


def model_payload_v2(model: dict | None, summary: dict) -> dict:
    h = (summary or {}).get("honest") or {}
    pl = (summary or {}).get("placebo") or {}
    base = (summary or {}).get("base_up") or 0.5
    level, text = "bad", "Ingen forskningsresultater ennå."
    conf = None
    if h:
        tiers = {t["tier"]: t for t in h.get("tiers", [])}
        rows = [tiers[k] for k in ("6–10 pp", "over 10 pp") if k in tiers]
        n = sum(t["n"] for t in rows)
        if n:
            conf = {"n": n, "share": n / h["n"], "hit": sum(t["hit"] * t["n"] for t in rows) / n,
                    "bp": sum(t["bp"] * t["n"] for t in rows) / n}
        avg_edge = h["hit"] - max(base, 1 - base)
        if conf and pl.get("conf_p95") and conf["hit"] > pl["conf_p95"]:
            level = "good"
            text = (f"I snitt over alle dager er modellen ikke bedre enn å alltid gjette opp ({h['hit'] * 100:.1f} % mot "
                    f"{base * 100:.1f} %). Men på dagene den gir bias (minst 6 pp fra 50 %, ca. {conf['share'] * 100:.0f} % av dagene) "
                    f"traff den {conf['hit'] * 100:.1f} %, over flaksnivået på {pl['conf_p95'] * 100:.1f} %. "
                    "Bruk biasen bare på disse dagene; NØYTRAL betyr at modellen ikke vet.")
        elif conf:
            level = "meh"
            text = (f"Dagene med bias traff {conf['hit'] * 100:.1f} %, men det er ikke sikkert over flaksnivået "
                    f"({(pl.get('conf_p95') or 0) * 100:.1f} %). Behandle biasen som en svak indikasjon.")
        if avg_edge > 0.02 and level == "good":
            text = text.replace("I snitt over alle dager er modellen ikke bedre enn å alltid gjette opp", "Modellen er også bedre enn å alltid gjette opp i snitt")
    out = {"version": 2, "level": level, "verdict": text, "research": summary, "confident": conf}
    if model:
        coefs = []
        if model.get("pipe") is not None:
            import bias2 as B
            for col, c in zip(model["features"], model["pipe"][-1].coef_[0]):
                coefs.append({"key": col, "label": B.LABELS.get(col, (col, ""))[0], "coef": float(c)})
        out.update({"trained_on": model["trained_on"], "n_train": model["n"], "features": coefs,
                    "first": model["first"], "last": model["last"]})
    return out


def run(args, nq) -> str:
    """nq = nqbias-modulen (for å gjenbruke load_bundle, markedsbilde, kalender)."""
    import bias2 as B
    from features import rth_daily_table

    now_et = D.now_ny()
    phase = decide_phase(now_et, getattr(args, "mode", None))
    payload = load_existing()
    R.console.print(f"[bold]Nettside-kjøring[/bold]  {now_et:%Y-%m-%d %H:%M} ET  ·  fase: {phase}")

    model, error = None, None
    summary = B.research_summary()
    try:
        bundle = nq.load_bundle(max_age_sec=300)          # Yahoo: markedsbilde, kalender, fasit
        J.fill_outcomes(rth_daily_table(bundle["rth"]["QQQ"]))
        inputs = B.load_inputs()
        if phase == "live" and now_et.weekday() < 5:
            warnings, source = [], "Dukascopy"
            last = B.last_bar_end(inputs)
            live_nq = live_es = None
            if last is None or (now_et - last) > pd.Timedelta(minutes=20):
                live_nq, live_es = B.yahoo_bars("NQ=F"), B.yahoo_bars("ES=F")
                source = "Yahoo (Dukascopy var forsinket)"
                warnings.append(f"Dukascopy-data var forsinket (siste bar {last}); dagens rad er beregnet med Yahoo-priser.")
            df = B.table(inputs, live=now_et, live_nq=live_nq, live_es=live_es)
            model = B.get_model(df)
            row = df.iloc[[-1]]
            if row.index[0] != now_et.date():
                raise RuntimeError("fant ikke dagens rad i dataene")
            pred = B.predict(model, row)
            if not np.isfinite(row.iloc[0].get("gap", np.nan)):
                warnings.insert(0, "VIKTIG: mangler fersk pris for NQ – biasen er usikker.")
            prev_days = [d for d in rth_daily_table(bundle["rth"]["QQQ"]).index if d < now_et.date()]
            nq_price = D.live_price(bundle["h24"].get("NQ=F"), now_et)
            ctx_y = {"table": df, "nq_price": nq_price,
                     "fh_abs_med": float(df["fh"].dropna().abs().iloc[-20:].median()),
                     "market": nq.market_snapshot(bundle, now_et, prev_days[-1], strict=False) if prev_days else {},
                     "regime": nq.regime_snapshot(bundle["fred"], bundle["daily"]),
                     "events": nq.todays_events(now_et.date()), "earnings": bundle.get("earnings", {}),
                     "headlines": D.fetch_headlines()}
            payload["today"] = live_payload_v2(now_et.date(), now_et, row, model, pred, summary, ctx_y,
                                               warnings + list(D.SOURCE_ERRORS), source)
            bias, strength = B.label(pred["p"])
            top = "; ".join(f"{r['label']} {r['pp']:+.1f}pp" for r in sorted(pred["reasons"], key=lambda r: -abs(r["pp"]))[:4])
            open_et = pd.Timestamp(datetime.combine(now_et.date(), C.OPEN_ET), tz=C.NY)
            J.log_prediction({"date": str(now_et.date()), "run_time_oslo": f"{now_et.tz_convert(C.OSLO):%H:%M}",
                              "run_time_et": f"{now_et:%H:%M}",
                              "minutes_before_open": round((open_et - now_et).total_seconds() / 60, 1),
                              "p_raw": round(pred["p"], 4), "p_cal": round(pred["p"], 4), "bias": bias,
                              "strength": strength, "top_reasons": top,
                              "nq_price": round(nq_price, 2) if np.isfinite(nq_price) else np.nan})
        else:
            df = B.table(inputs)
            model = B.get_model(df)          # trener på nytt én gang per dag
    except SystemExit:
        error = "Kjøringen feilet: " + ("; ".join(D.SOURCE_ERRORS) or "ukjent årsak (se loggen i GitHub Actions)")
    except Exception as e:  # siden skal fortsatt oppdateres med feilmeldingen
        import traceback
        traceback.print_exc()
        error = f"Kjøringen feilet: {type(e).__name__}: {e}"
    if model is None:
        model = B.load()

    payload["model"] = model_payload_v2(model, summary)
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
