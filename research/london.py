"""Hypotesetesting for NQ i første time etter London-åpning (08:00–09:00 London-tid).

Helt adskilt fra NY-modellen: eget mål, egne variabler, egne filer
(research/LONDON.md og research/london_results.json). Gjenbruker bare
hjelpefunksjonene i analyze.py.
"""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import analyze as A

LDN = ZoneInfo("Europe/London")
NY = A.NY


def at_ldn(d, hh, mm=0) -> pd.Timestamp:
    return pd.Timestamp(datetime.combine(d, time(hh, mm)), tz=LDN).tz_convert(NY)


def build_london(nq, es, h1, ydaily, live: pd.Timestamp | None = None) -> pd.DataFrame:
    """Én rad per handelsdag (mandag–fredag). Alle variabler er kjent før 08:00 London."""
    P = A.Px(nq, pd.Timedelta(minutes=15))
    E = A.Px(es, pd.Timedelta(minutes=15))
    X = {k: A.Px(v, pd.Timedelta(hours=3)) for k, v in h1.items()}
    live_day = live.tz_convert(LDN).date() if live is not None else None
    cand = sorted({ts.tz_convert(LDN).date() for ts in nq.index if ts.tz_convert(LDN).weekday() < 5})
    days = [d for d in cand if np.isfinite(P.at(at_ldn(d, 8))) and np.isfinite(P.at(at_ldn(d, 9)))]
    if live_day is not None:
        days = [d for d in days if d < live_day] + [live_day]
    # amerikanske handelsdager (for «forrige US-dag»)
    rows = []
    for i, d in enumerate(days):
        if i == 0:
            continue
        is_live = d == live_day
        t0 = min(live, at_ldn(d, 8)) if is_live else at_ldn(d, 8)
        o = P.at(t0)
        # forrige amerikanske stengning: siste 16:00 ET før London-åpning
        prev_us = (t0.tz_convert(NY) - timedelta(days=1)).date()
        while prev_us.weekday() >= 5:
            prev_us -= timedelta(days=1)
        c_us = P.at(A.at(prev_us, 16, 0))
        r = {
            "date": d,
            "fh": np.nan if is_live else A.logr(P.at(at_ldn(d, 9)), o),
            "on_us": A.logr(o, c_us),                                          # US-stengning → London-åpning
            "asia": A.logr(P.at(at_ldn(d, 6)), P.at(at_ldn(d, 0))),            # Tokyo-økt ca. 09–15 Tokyo
            "pre_ldn": A.logr(o, P.at(at_ldn(d, 7))),                          # siste time før åpning
            "us_rth": A.logr(c_us, P.at(A.at(prev_us, 9, 30))),
            "us_last": A.logr(c_us, P.at(A.at(prev_us, 15, 0))),
            "us_fh": A.logr(P.at(A.at(prev_us, 10, 30)), P.at(A.at(prev_us, 9, 30))),
            "rel_es": A.logr(o, c_us) - A.logr(E.at(t0), E.at(A.at(prev_us, 16, 0))),
            "dow": d.weekday(),
        }
        hi, lo = P.hl(A.at(prev_us, 16, 0), t0)
        r["on_pos"] = (o - lo) / (hi - lo) if np.isfinite(hi) and hi > lo else np.nan
        r["on_range"] = A.logr(hi, lo)
        for k in X:
            r[f"x_{k}"] = A.logr(X[k].at(t0), X[k].at(A.at(prev_us, 16, 0)))
        rows.append(r)
    df = pd.DataFrame(rows).set_index("date")
    # volatilitet: std av London-første-time og av døgnavkastning, kun fortid
    close = pd.Series([P.at(at_ldn(d, 8)) for d in df.index], index=df.index)
    ret = np.log(close / close.shift(1))
    s = ret.rolling(20, min_periods=15).std().shift(1)
    s = s.fillna(ret.expanding(10).std().shift(1))
    df["sigma"] = s
    for c in ["on_us", "asia", "pre_ldn", "us_rth", "us_last", "us_fh", "rel_es", "on_range"]:
        df[c + "_z"] = df[c] / s
    df["fh_mom5_z"] = df["fh"].shift(1).rolling(5).mean() / s
    df["fh_mom20_z"] = df["fh"].shift(1).rolling(20, min_periods=15).mean() / s
    df["ret5_z"] = np.log(close / close.shift(5)) / (s * np.sqrt(5))
    for k in h1:
        col = f"x_{k}"
        df[col + "_z"] = df[col] / df[col].rolling(60, min_periods=30).std().shift(1)
    df["monday"] = (df["dow"] == 0).astype(int)
    df["thu_fri"] = df["dow"].isin([3, 4]).astype(int)
    df["friday"] = (df["dow"] == 4).astype(int)
    idx = pd.DatetimeIndex(df.index)
    months = pd.Series(idx.to_period("M"), index=df.index)
    pos = months.groupby(months).cumcount()
    rev = months.groupby(months).cumcount(ascending=False)
    df["tom"] = ((pos < 3) | (rev == 0)).astype(int)
    df["opex"] = [int(x.weekday() == 4 and 15 <= x.day <= 21) for x in df.index]
    df["big_on"] = df["on_us_z"] * (df["on_us_z"].abs() > 1)
    # VIX fra Yahoo (forrige US-dag)
    vix = ydaily.get("^VIX") if ydaily else None
    if vix is not None and len(vix):
        v = vix.copy(); v.index = v.index.date
        keys = np.array(sorted(v.index)); vals = v.reindex(keys).to_numpy(float)
        df["vix"] = [vals[np.searchsorted(keys, d, side="left") - 1] if np.searchsorted(keys, d) > 0 else np.nan for d in df.index]
        df["vix_z"] = (df["vix"] - df["vix"].rolling(252, min_periods=120).mean()) / df["vix"].rolling(252, min_periods=120).std()
        v3 = ydaily.get("^VIX3M")
        if v3 is not None and len(v3):
            w = v3.copy(); w.index = w.index.date
            k3 = np.array(sorted(w.index)); x3 = w.reindex(k3).to_numpy(float)
            df["vix3m"] = [x3[np.searchsorted(k3, d, side="left") - 1] if np.searchsorted(k3, d) > 0 else np.nan for d in df.index]
            df["vix_ts"] = df["vix"] / df["vix3m"] - 1
    df["y"] = (df["fh"] > 0).astype(float)
    df.loc[df["fh"].isna(), "y"] = np.nan
    return df


CONT = [
    ("on_us_z", "US-stengning → London-åpning", 0, "Overnight-bevegelse så langt"),
    ("asia_z", "Tokyo-økta (00–06 London)", 0, "Asia-flyt"),
    ("pre_ldn_z", "Siste time før London-åpning", 0, "Pre-open-flyt / Frankfurt 07:00"),
    ("us_rth_z", "Gårsdagens US-dag (RTH)", 0, "Reversering/momentum"),
    ("us_last_z", "Gårsdagens siste US-time", 0, "Sen flyt"),
    ("us_fh_z", "Gårsdagens NY første time", 0, ""),
    ("rel_es_z", "NQ vs ES siden US-stengning", -1, "Relativ verdi"),
    ("fh_mom5_z", "London første time, snitt 5 dager", 0, "Tidsmønster"),
    ("fh_mom20_z", "London første time, snitt 20 dager", 0, "Tidsmønster"),
    ("ret5_z", "Avkastning 5 dager", -1, "Kortsiktig reversering"),
    ("on_pos", "Posisjon i overnight-range", 0, ""),
    ("on_range_z", "Overnight-range (størrelse)", 0, ""),
    ("big_on", "Store overnight-bevegelser (>1σ)", -1, "Overstrekk"),
    ("x_usdjpy_z", "USD/JPY over natten", 1, "Risk-on/carry"),
    ("x_xauusd_z", "Gull over natten", -1, ""),
    ("x_lightcmdusd_z", "Olje over natten", 0, ""),
    ("x_ustbondtrusd_z", "T-bond over natten (2018+)", 1, ""),
    ("x_dollaridxusd_z", "DXY over natten (2017+)", -1, ""),
    ("vix_z", "VIX-nivå (z)", 1, ""),
    ("vix_ts", "VIX/VIX3M − 1", 1, ""),
]
BIN = [
    ("monday", "Mandag", 0, ""), ("friday", "Fredag", 0, ""), ("thu_fri", "Torsdag/fredag", 0, ""),
    ("tom", "Månedsskifte", 1, ""), ("opex", "Opsjonsforfall-fredag", 0, ""),
]


def main() -> None:
    A.PERIODS = [(2014, 2017), (2018, 2021), (2022, 2026)]
    nq = A.load_series("usatechidxusd", "m5")
    es = A.load_series("usa500idxusd", "m5")
    h1 = {k: A.load_series(k, "h1") for k in ["usdjpy", "xauusd", "lightcmdusd", "ustbondtrusd", "dollaridxusd"]}
    h1 = {k: v for k, v in h1.items() if not v.empty}
    yd = A.yahoo_daily() if os.environ.get("NO_YAHOO") != "1" else {}
    df = build_london(nq, es, h1, yd)
    # Dukascopy har flate (manglende) data i London-timen 2011–2013: bruk 2014 og senere
    df = df[pd.DatetimeIndex(df.index) >= pd.Timestamp("2014-01-01")]
    R = {"generated": datetime.utcnow().isoformat() + "Z", "n_days": int(df["y"].notna().sum()),
         "first": str(df.index.min()), "last": str(df.index.max()), "base_up": float(df["y"].mean()),
         "mean_fh_bp": float(df["fh"].mean() * 1e4), "sd_fh_bp": float(df["fh"].std() * 1e4)}
    tests = []
    for col, name, exp, why in CONT:
        if col in df:
            r = A.test_cont(df, col, exp)
            if r:
                tests.append({"kind": "cont", "col": col, "name": name, "exp": exp, "why": why, **r})
    for col, name, exp, why in BIN:
        r = A.test_bin(df, col)
        if r:
            tests.append({"kind": "bin", "col": col, "name": name, "exp": exp, "why": why, **r})
    for t, q in zip(tests, A.bh([t["p"] for t in tests])):
        t["q"] = q
        if t["kind"] == "bin":
            ups = [t.get(f"up_{a}") for a, _ in A.PERIODS]; bases = [t.get(f"base_{a}") for a, _ in A.PERIODS]
            sg = np.sign(t["up1"] - t["up0"])
            t["stable"] = all(u is not None and b is not None and np.sign(u - b) == sg for u, b in zip(ups, bases))
        else:
            t["stable"] = all(t.get(f"rho_{a}") is not None and np.sign(t[f"rho_{a}"]) == np.sign(t["rho"]) for a, _ in A.PERIODS)
        t["passes"] = bool(t["q"] < 0.10 and t["stable"])
    R["tests"] = tests

    # ærlig walk-forward med samme regel som NY-modellen, men London-kandidater
    A.CAND_CONT = [c for c, *_ in CONT if c in df]
    A.CAND_BIN = [c for c, *_ in BIN if c in df]
    res, pred, chosen = A.walk_forward_nested(df)
    R["honest"] = res
    R["selection"] = chosen
    exc = []
    rng = np.random.default_rng(11)
    for _ in range(int(os.environ.get("N_PERM_NESTED", "20"))):
        dp = df.copy(); ok = dp["y"].notna().to_numpy()
        vals = dp.loc[ok, ["fh", "y"]].to_numpy()
        dp.loc[ok, ["fh", "y"]] = vals[rng.permutation(len(vals))]
        r, _, _ = A.walk_forward_nested(dp)
        exc.append((r["hit"], r["conf6"]["excess"], r["conf10"]["excess"]))
    if exc:
        a = np.array(exc)
        R["placebo"] = {"n": len(a), "hit_p95": float(np.percentile(a[:, 0], 95)),
                        "excess6_p95": float(np.percentile(a[:, 1], 95)), "excess10_p95": float(np.percentile(a[:, 2], 95))}
    (A.HERE / "london_results.json").write_text(json.dumps(R, indent=1, default=lambda o: None if isinstance(o, float) and not math.isfinite(o) else str(o)), encoding="utf-8")
    write_report(R)
    print((A.HERE / "LONDON.md").read_text(encoding="utf-8"))


def write_report(R):
    f = A.f
    L = ["# NQ første time etter London-åpning – hypotesetester\n",
         f"Generert {R['generated'][:16]} UTC. Data: {R['first']} → {R['last']}, **{R['n_days']} dager**. "
         f"Mål: NQ fra 08:00 til 09:00 London-tid (09:00–10:00 norsk tid). NQ steg {f(R['base_up'], 1, pct=True)} av dagene, "
         f"snitt {f(R['mean_fh_bp'], 1, sign=True)} bp, standardavvik {f(R['sd_fh_bp'], 0)} bp.\n",
         "| Variabel | n | Effekt | t | q | 2014–17 | 2018–21 | 2022–26 | Bestått |", "|---|---|---|---|---|---|---|---|---|"]
    for t in sorted(R["tests"], key=lambda t: t["q"]):
        if t["kind"] == "bin":
            eff = f"{f(t['up1'], 1, pct=True)} opp vs {f(t['up0'], 1, pct=True)}"
            per = " | ".join(f(t.get(f"up_{a}"), 0, pct=True) for a, _ in A.PERIODS)
        else:
            eff = f"ρ {f(t['rho'], 3, sign=True)}"
            per = " | ".join(f(t.get(f"rho_{a}"), 3, sign=True) for a, _ in A.PERIODS)
        L.append(f"| {t['name']} | {t['n']} | {eff} | {f(t['t'], 1, sign=True)} | {f(t['q'], 3)} | {per} | {'✅' if t['passes'] else ''} |")
    h = R["honest"]
    L.append(f"\n## Ærlig walk-forward\nTreff {f(h['hit'], 1, pct=True)} over {h['n']} dager (grunnrate {f(R['base_up'], 1, pct=True)}).  ")
    for key, lab in (("conf6", "minst 6 pp"), ("conf10", "minst 10 pp")):
        c = h[key]
        if c["n"]:
            L.append(f"Dager med {lab}: {c['n']} dager, treff {f(c['hit'], 1, pct=True)} mot {f(c['expected'], 1, pct=True)} ved tilfeldighet, "
                     f"{c['excess']:+.0f} ekstra treff, p = {f(c['p'], 4)}.  ")
    pl = R.get("placebo")
    if pl:
        L.append(f"Placebo ({pl['n']}): treff 95-persentil {f(pl['hit_p95'], 1, pct=True)}, ekstra treff 6 pp: {pl['excess6_p95']:+.1f}, 10 pp: {pl['excess10_p95']:+.1f}.\n")
    L.append("| Hvor sikker | dager | treff | bp |\n|---|---|---|---|")
    for t in h["tiers"]:
        L.append(f"| {t['tier']} | {t['n']} | {f(t['hit'], 1, pct=True)} | {f(t['bp'], 1, sign=True)} |")
    L.append("\nVariabler valgt per år: " + "; ".join(f"{y}: {', '.join(c) or '–'}" for y, c in R["selection"].items()))
    (A.HERE / "LONDON.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
