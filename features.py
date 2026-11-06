"""Bygger én rad med forklaringsvariabler per handelsdag, pluss målet
(retningen på QQQ/NQ i første time, 09:30–10:30 ET).

Alle variabler er kjent FØR 09:30 ET samme dag. Prisene hentes med
`price_asof`, som bare bruker barer som er ferdige før tidspunktet, slik at
backtesten ikke får se inn i første time.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta

import numpy as np
import pandas as pd

import config as C
from data import price_asof, live_price


# ---------------------------------------------------------------------------
# Beskrivelse av hver variabel: kort navn, forklaring, og forskningsgrunnlag
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class FeatureInfo:
    label: str          # vises i terminalen
    why: str            # hvorfor den er med
    source: str         # kort kildehenvisning
    group: str


FEATURES: dict[str, FeatureInfo] = {
    # --- Pris og flyt rundt åpningen ---------------------------------------
    "on_ret": FeatureInfo("Overnight-bevegelse NQ (gap)",
        "Stort overnight-trekk har historisk en tendens til å delvis reverseres tidlig i RTH.",
        "Liu & Tse (2017); Yu, Rentzler & Wolf (NQ-futures)", "Pris"),
    "premkt_trend": FeatureInfo("Premarket-trend siste 1,5 t",
        "Fanger reaksjonen på 08:30-tall og flyt rett før åpning.",
        "Gao m.fl. (2018): momentum sterkere på nyhetsdager", "Pris"),
    "prev_day": FeatureInfo("Gårsdagens RTH-bevegelse",
        "Gårsdagens retning kan gi både momentum og reversering inn i neste åpning.",
        "Yu, Rentzler & Wolf (NQ-futures)", "Pris"),
    "prev_last30": FeatureInfo("Gårsdagens siste halvtime",
        "Sen flyt (rebalansering, gamma-hedging) som kan smitte over i neste åpning.",
        "Baltussen m.fl. (2021)", "Pris"),
    "fh_mom5": FeatureInfo("Første time siste 5 dager",
        "Samme tidspunkt på dagen har vist seg å gjenta seg over flere dager.",
        "Heston, Korajczyk & Sadka (2010)", "Pris"),
    "fh_mom20": FeatureInfo("Første time siste 20 dager",
        "Lengre versjon av samme tidsmønster.",
        "Heston, Korajczyk & Sadka (2010)", "Pris"),
    "ret5": FeatureInfo("Avkastning siste 5 dager",
        "Kortsiktig reversering på dagsnivå.",
        "Kortsiktig reverserings-litteratur", "Pris"),
    "trend50": FeatureInfo("Avstand til 50-dagers snitt",
        "Trendregime: markedet over eller under mellomlang trend.",
        "Tidsserie-momentum", "Pris"),
    # --- Relativ styrke -------------------------------------------------------
    "qqq_spy_rel": FeatureInfo("NQ vs ES overnight",
        "NQ som har stukket av fra ES har en tendens til å trekke seg mot ES.",
        "Lead-lag / relativ verdi", "Relativ styrke"),
    "smh_rel": FeatureInfo("Halvledere vs NQ overnight",
        "Halvledere leder ofte risikoappetitten i Nasdaq.",
        "Sektorledelse", "Relativ styrke"),
    # --- Kryssmarkeder (makro) ------------------------------------------------
    "zn_on": FeatureInfo("Obligasjoner overnight (ZN)",
        "Stigende obligasjonspris (fallende renter) er normalt medvind for long-duration tech.",
        "Rente/aksje-kobling", "Makro"),
    "dxy_on": FeatureInfo("Dollar overnight (DXY)",
        "Sterkere dollar strammer finansielle forhold og er ofte motvind for NQ.",
        "Finansielle forhold", "Makro"),
    "jpy_on": FeatureInfo("USD/JPY overnight",
        "Rask yen-styrking (fallende USD/JPY) henger ofte sammen med risk-off og carry-avvikling.",
        "Carry/risk-off", "Makro"),
    "btc_on": FeatureInfo("Bitcoin overnight",
        "Døgnåpent mål på spekulativ risikoappetitt.",
        "Risikoappetitt", "Makro"),
    "y10_chg5": FeatureInfo("10-års rente, endring 5 dager",
        "Rentetrend over uken (FRED).",
        "FRED DGS10", "Makro"),
    "hy_chg5": FeatureInfo("High yield-spread, endring 5 dager",
        "Økende kredittspread signaliserer stress.",
        "FRED BAMLH0A0HYM2", "Makro"),
    # --- Volatilitet ----------------------------------------------------------
    "vix_z": FeatureInfo("VIX-nivå (z, 1 år)",
        "Høy VIX betyr større bevegelser og sterkere momentum/reversering.",
        "Gao m.fl. (2018); Martello & Ribeiro", "Volatilitet"),
    "vix_ts": FeatureInfo("VIX / VIX3M (terminstruktur)",
        "Over 1 = backwardation = akutt stress i markedet.",
        "Volatilitets-terminstruktur", "Volatilitet"),
    "vix_chg": FeatureInfo("VIX endring i går",
        "Rask økning i frykt dagen før.",
        "Volatilitet", "Volatilitet"),
    "on_x_vix": FeatureInfo("Gap × høy VIX",
        "Reversering/momentum etter gap kan være sterkere når VIX er høy.",
        "Gao m.fl. (2018)", "Volatilitet"),
    # --- Kalender og hendelser --------------------------------------------------
    "monday": FeatureInfo("Mandag",
        "Mandager har vist annerledes åpningsmønster i NQ.",
        "Yu, Rentzler & Wolf (NQ-futures)", "Kalender"),
    "tom": FeatureInfo("Månedsskifte",
        "Siste handelsdag + tre første: historisk sterkere på grunn av pengeflyt.",
        "Lakonishok & Smidt; Etula m.fl. (2020)", "Kalender"),
    "opex": FeatureInfo("Opsjonsforfall (3. fredag)",
        "Forfall endrer dealers gamma-posisjon.",
        "Gamma/opsjonsflyt", "Kalender"),
    "fomc": FeatureInfo("FOMC-dag",
        "Før-FOMC-drift (svekket etter 2015).",
        "Lucca & Moench (2015); Kurov m.fl. (2021)", "Kalender"),
    "fomc_hivix": FeatureInfo("FOMC-dag × høy VIX",
        "Før-FOMC-driften har overlevd mest i perioder med høy usikkerhet.",
        "Martello & Ribeiro", "Kalender"),
    "earn": FeatureInfo("Megacap-earnings over natten",
        "Stor selskapsnyhet i indeksen; påvirker hvordan gapet oppfører seg.",
        "Earnings-dager", "Kalender"),
}
FEATURE_COLS = list(FEATURES)


# ---------------------------------------------------------------------------
# Hjelpere
# ---------------------------------------------------------------------------
def _at(d, t: time) -> pd.Timestamp:
    return pd.Timestamp(datetime.combine(d, t), tz=C.NY)


def _log(a, b) -> float:
    if a is None or b is None or not np.isfinite(a) or not np.isfinite(b) or a <= 0 or b <= 0:
        return np.nan
    return float(np.log(a / b))


def rth_daily_table(rth: pd.DataFrame) -> pd.DataFrame:
    """Én rad per handelsdag fra QQQ-timebarer (kun ordinær handel)."""
    rows = []
    for d, g in rth.groupby(rth.index.date):
        g = g.sort_index()
        first = g[g.index.time == C.OPEN_ET]
        if first.empty:
            continue
        # Første time er bare ferdig når neste bar (10:30) har startet. Ellers er
        # 09:30-baren fortsatt i gang, og prisen er ikke fasit ennå.
        fh_done = bool((g.index.time >= C.FIRST_HOUR_END_ET).any())
        rows.append({
            "date": d,
            "open": float(first["Open"].iloc[0]),
            "close": float(g["Close"].iloc[-1]),
            "p1030": price_asof(g, _at(d, C.FIRST_HOUR_END_ET)) if fh_done else np.nan,
            "p1530": price_asof(g, _at(d, time(15, 30))),
            "last_ts": g.index[-1],
        })
    df = pd.DataFrame(rows).set_index("date").sort_index()
    df["ret_cc"] = np.log(df["close"] / df["close"].shift(1))
    df["sigma"] = df["ret_cc"].rolling(20, min_periods=15).std()
    df["fh_ret"] = np.log(df["p1030"] / df["open"])
    return df


def _sigma_24h(df: pd.DataFrame | None, dates: list) -> pd.Series:
    """20-dagers std av døgnavkastning målt 16:00→16:00 ET for 24-timers markeder."""
    if df is None or df.empty:
        return pd.Series(np.nan, index=dates)
    closes = pd.Series([price_asof(df, _at(d, C.CLOSE_ET)) for d in dates], index=dates)
    r = np.log(closes / closes.shift(1))
    return r.rolling(20, min_periods=15).std()


def _turn_of_month(d, trading_days: list) -> int:
    """1 hvis d er siste handelsdag i måneden eller en av de tre første."""
    idx = trading_days.index(d) if d in trading_days else None
    if idx is None:
        return 0
    month_days = [x for x in trading_days if (x.year, x.month) == (d.year, d.month)]
    pos = month_days.index(d)
    if pos < 3:
        return 1
    # siste handelsdag: neste dag i lista er i ny måned (eller vi vet ikke ennå)
    nxt = trading_days[idx + 1] if idx + 1 < len(trading_days) else None
    if nxt is not None:
        return int(nxt.month != d.month)
    # live: anta siste handelsdag hvis ingen hverdag gjenstår i måneden
    probe = d + timedelta(days=1)
    while probe.month == d.month:
        if probe.weekday() < 5:
            return 0
        probe += timedelta(days=1)
    return 1


def _is_opex(d) -> int:
    if d.weekday() != 4:
        return 0
    return int(15 <= d.day <= 21)


def _fred_asof(fred: pd.DataFrame, col: str, d, lag_days: int = 1) -> tuple[float, float]:
    """Verdi og 5-observasjoners endring, kun data datert <= d - lag (unngår at
    FRED publiserer tall i etterkant)."""
    if fred is None or fred.empty or col not in fred:
        return np.nan, np.nan
    s = fred[col].dropna()
    s = s[s.index <= pd.Timestamp(d) - pd.Timedelta(days=lag_days)]
    if len(s) < 6:
        return np.nan, np.nan
    return float(s.iloc[-1]), float(s.iloc[-1] - s.iloc[-6])


# ---------------------------------------------------------------------------
# Hovedfunksjon
# ---------------------------------------------------------------------------
def build_features(bundle: dict, target_dates: list | None = None, live_cutoff: pd.Timestamp | None = None,
                   strict: bool = False) -> pd.DataFrame:
    """Returnerer DataFrame med én rad per dag: FEATURE_COLS + mål + råverdier.

    bundle: dict fra terminal.load_bundle()
    target_dates: hvilke dager som skal bygges (default: alle med historikk)
    live_cutoff: hvis satt, bygges KUN dagen i live_cutoff, med ferskeste priser
                 opp til live_cutoff (brukes i sanntid før åpning).
    strict: bruk bare ferdige barer også i live-modus (for avspilling av en
            tidligere dag, så en timebar som startet før cutoff ikke lekker).
    """
    rth = bundle["rth"]["QQQ"]
    pp = bundle["pp"]
    h24 = bundle["h24"]
    daily = bundle["daily"]
    fred = bundle.get("fred", pd.DataFrame())
    earnings = bundle.get("earnings", {})

    table = rth_daily_table(rth)
    trading_days = list(table.index)

    vix = daily.get("^VIX", pd.DataFrame()).get("Close", pd.Series(dtype=float))
    vix3m = daily.get("^VIX3M", pd.DataFrame()).get("Close", pd.Series(dtype=float))
    vix_med = vix.rolling(252, min_periods=120).median()
    vix_mean = vix.rolling(252, min_periods=120).mean()
    vix_std = vix.rolling(252, min_periods=120).std()

    sig = {t: _sigma_24h(h24.get(t), trading_days) for t in ("ZN=F", "DX-Y.NYB", "JPY=X", "BTC-USD")}

    earn_times = sorted(ts for lst in earnings.values() for ts in lst)
    fomc = set(C.FOMC_DECISION_DATES)

    if live_cutoff is not None:
        day = live_cutoff.date()
        if day in trading_days:   # skal ikke skje før åpning, men vær robust
            trading_days = [d for d in trading_days if d < day]
        days = [day]
        all_days = trading_days + [day]
        if live_cutoff < _at(day, C.OPEN_ET) and not strict:
            px = lambda df, ts, ms=pd.Timedelta(days=4): live_price(df, ts, ms)   # ferskeste pris før åpning
        else:
            px = lambda df, ts, ms=pd.Timedelta(days=4): price_asof(df, ts, ms)   # etter åpning: kun ferdige barer før 09:30
    else:
        all_days = trading_days
        days = target_dates or trading_days[1:]
        px = lambda df, ts, ms=pd.Timedelta(days=4): price_asof(df, ts, ms)

    rows = []
    for d in days:
        i = all_days.index(d)
        if i == 0:
            continue
        p = all_days[i - 1]                       # forrige handelsdag
        if p not in table.index:
            continue
        prev = table.loc[p]
        sigma = prev["sigma"]
        if not np.isfinite(sigma) or sigma <= 0:
            continue
        t_prev_close = _at(p, C.CLOSE_ET)
        cutoff = live_cutoff if live_cutoff is not None else _at(d, C.OPEN_ET)
        cutoff = min(cutoff, _at(d, C.OPEN_ET))
        t_0800 = _at(d, time(8, 0))

        FRESH = pd.Timedelta(hours=2)   # prisen ved cutoff må være fersk (ikke gårsdagens)

        def on(t):
            """Logavkastning fra forrige handelsdags 16:00 ET til cutoff."""
            if t in pp:   # ETF: basis = forrige ordinære sluttkurs
                df = pp.get(t)
                base = prev["close"] if t == "QQQ" else price_asof(bundle["rth"].get(t), t_prev_close)
            else:
                df = h24.get(t)
                base = price_asof(df, t_prev_close)
            return _log(px(df, cutoff, FRESH), base)

        # Premarket fra ETF-ene er førstevalg (ingen kontrakt-rull). Mangler den,
        # brukes futures (NQ/ES) – de kan ha et kunstig hopp på rull-dager.
        on_qqq = on("QQQ")
        if not np.isfinite(on_qqq):
            on_qqq = on("NQ=F")
        on_spy = on("SPY")
        if not np.isfinite(on_spy):
            on_spy = on("ES=F")
        on_smh = on("SMH")
        pre_df = pp.get("QQQ") if np.isfinite(px(pp.get("QQQ"), cutoff, FRESH)) else h24.get("NQ=F")
        pre_trend = _log(px(pre_df, cutoff, FRESH), price_asof(pre_df, t_0800, FRESH))

        hist = table.loc[:p]
        fh = hist["fh_ret"].dropna()
        closes = hist["close"]

        def z24(t):
            s = sig[t].get(p, np.nan) if t in sig else np.nan
            r = on(t)
            return r / s if np.isfinite(r) and np.isfinite(s) and s > 0 else np.nan

        # VIX (forrige dags close; vi bruker aldri dagens)
        vix_p = vix[vix.index <= pd.Timestamp(p)]
        v_last = float(vix_p.iloc[-1]) if len(vix_p) else np.nan
        v_prev = float(vix_p.iloc[-2]) if len(vix_p) > 1 else np.nan
        v_med = vix_med[vix_med.index <= pd.Timestamp(p)]
        v_med = float(v_med.iloc[-1]) if len(v_med) else np.nan
        v_mu = vix_mean[vix_mean.index <= pd.Timestamp(p)]
        v_sd = vix_std[vix_std.index <= pd.Timestamp(p)]
        v_z = (v_last - float(v_mu.iloc[-1])) / float(v_sd.iloc[-1]) if len(v_mu) and len(v_sd) and float(v_sd.iloc[-1]) > 0 else np.nan
        v3 = vix3m[vix3m.index <= pd.Timestamp(p)]
        v_ts = v_last / float(v3.iloc[-1]) - 1 if len(v3) and float(v3.iloc[-1]) > 0 else np.nan
        vix_hi = float(v_last > v_med) if np.isfinite(v_last) and np.isfinite(v_med) else 0.0

        y10, y10_chg = _fred_asof(fred, "DGS10", d)
        hy, hy_chg = _fred_asof(fred, "BAMLH0A0HYM2", d)

        earn_names = []
        for t, lst in earnings.items():
            if any(t_prev_close <= ts < _at(d, C.OPEN_ET) for ts in lst):
                earn_names.append(t)

        is_fomc = int(d in fomc)
        on_z = on_qqq / sigma if np.isfinite(on_qqq) else np.nan

        row = {
            "date": d,
            "on_ret": on_z,
            "premkt_trend": pre_trend / sigma if np.isfinite(pre_trend) else np.nan,
            "prev_day": np.log(prev["close"] / prev["open"]) / sigma,
            "prev_last30": _log(prev["close"], prev["p1530"]) / sigma,
            "fh_mom5": fh.iloc[-5:].mean() / sigma if len(fh) >= 5 else np.nan,
            "fh_mom20": fh.iloc[-20:].mean() / sigma if len(fh) >= 20 else np.nan,
            "ret5": _log(closes.iloc[-1], closes.iloc[-6]) / (sigma * np.sqrt(5)) if len(closes) >= 6 else np.nan,
            "trend50": _log(closes.iloc[-1], closes.iloc[-50:].mean()) / sigma if len(closes) >= 50 else np.nan,
            "qqq_spy_rel": (on_qqq - on_spy) / sigma if np.isfinite(on_qqq) and np.isfinite(on_spy) else np.nan,
            "smh_rel": (on_smh - on_qqq) / sigma if np.isfinite(on_smh) and np.isfinite(on_qqq) else np.nan,
            "zn_on": z24("ZN=F"),
            "dxy_on": z24("DX-Y.NYB"),
            "jpy_on": z24("JPY=X"),
            "btc_on": z24("BTC-USD"),
            "y10_chg5": y10_chg,
            "hy_chg5": hy_chg,
            "vix_z": v_z,
            "vix_ts": v_ts,
            "vix_chg": _log(v_last, v_prev),
            "on_x_vix": on_z * vix_hi if np.isfinite(on_z) else np.nan,
            "monday": int(d.weekday() == 0),
            "tom": _turn_of_month(d, all_days),
            "opex": _is_opex(d),
            "fomc": is_fomc,
            "fomc_hivix": is_fomc * vix_hi,
            "earn": int(bool(earn_names)),
            # --- råverdier til visning ---
            "raw_on_pct": on_qqq * 100 if np.isfinite(on_qqq) else np.nan,
            "raw_pre_pct": pre_trend * 100 if np.isfinite(pre_trend) else np.nan,
            "raw_sigma_pct": sigma * 100,
            "raw_vix": v_last,
            "raw_vix_ts": v_ts,
            "raw_y10": y10,
            "raw_hy": hy,
            "raw_earn": ", ".join(earn_names),
            "raw_fh_abs_med_pct": fh.abs().iloc[-20:].median() * 100 if len(fh) >= 5 else np.nan,
        }
        # mål (kun historikk)
        if live_cutoff is None and d in table.index:
            fr = table.loc[d, "fh_ret"]
            row["fh_ret"] = fr
            row["y"] = float(fr > 0) if np.isfinite(fr) else np.nan
        rows.append(row)

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.set_index("date").sort_index()
