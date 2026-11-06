"""Hypotesetesting for NQ første time (09:30–10:30 ET) på ~15 år med data.

Data:
  - Dukascopy (research/data): Nasdaq 100 og S&P 500 i 5-minutters oppløsning fra 2011,
    USD/JPY, gull, olje, US T-bond og DXY i timesoppløsning.
  - Yahoo (daglig): VIX, VIX3M, 10-års rente, HYG/IEF, og QQQ for gyldige handelsdager.

Metode:
  1. Én rad per handelsdag. Alle variabler er kjent før 09:30 ET.
  2. Hver hypotese testes for seg: korrelasjon, HAC-t (Newey-West), treffrate for
     regelen, stabilitet i tre delperioder, og siste ~2 år.
  3. Korreksjon for multippel testing (Benjamini–Hochberg).
  4. Kandidatmodeller testes walk-forward (trenes bare på fortiden).
Resultat: research/RESULTS.md (lesbar rapport) og research/results.json.
"""
from __future__ import annotations

import gzip
import io
import json
import math
import os
import sys
import warnings
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
NY = ZoneInfo("America/New_York")
HERE = Path(__file__).resolve().parent
DATA = Path(os.environ.get("RESEARCH_DATA", HERE / "data"))
PERIODS = [(2011, 2015), (2016, 2020), (2021, 2026)]


# ---------------------------------------------------------------------------
# Innlesing
# ---------------------------------------------------------------------------
def load_series(inst: str, tf: str) -> pd.DataFrame:
    files = sorted(DATA.glob(f"{inst}_{tf}_*.csv.gz"))
    if not files:
        return pd.DataFrame()
    frames = [pd.read_csv(f) for f in files]
    df = pd.concat(frames, ignore_index=True).drop_duplicates("t").sort_values("t")
    df.index = pd.to_datetime(df["t"], unit="ms", utc=True).dt.tz_convert(NY)
    step = pd.Timedelta(minutes=5) if tf == "m5" else pd.Timedelta(hours=1)
    df["end"] = df.index + step
    return df[["o", "h", "l", "c", "end"]]


class Px:
    """Raske oppslag: pris ved tidspunkt (siste bar som er FERDIG <= ts)."""

    def __init__(self, df: pd.DataFrame, max_stale: pd.Timedelta):
        self.df = df
        self.ends = pd.DatetimeIndex(df["end"]).as_unit("ns").asi8 if len(df) else np.array([], dtype=np.int64)
        self.starts = pd.DatetimeIndex(df.index).as_unit("ns").asi8 if len(df) else np.array([], dtype=np.int64)
        self.c = df["c"].to_numpy(float) if len(df) else np.array([])
        self.h = df["h"].to_numpy(float) if len(df) else np.array([])
        self.l = df["l"].to_numpy(float) if len(df) else np.array([])
        self.stale = max_stale.value

    def at(self, ts: pd.Timestamp) -> float:
        if not len(self.c):
            return np.nan
        v = pd.Timestamp(ts).as_unit("ns").value
        i = np.searchsorted(self.ends, v, side="right") - 1
        if i < 0 or v - self.ends[i] > self.stale:
            return np.nan
        return self.c[i]

    def hl(self, t1: pd.Timestamp, t2: pd.Timestamp) -> tuple[float, float]:
        """Høy/lav for barer som starter i [t1, t2)."""
        a = np.searchsorted(self.starts, pd.Timestamp(t1).as_unit("ns").value, side="left")
        b = np.searchsorted(self.starts, pd.Timestamp(t2).as_unit("ns").value, side="left")
        if b <= a:
            return np.nan, np.nan
        return float(self.h[a:b].max()), float(self.l[a:b].min())


def yahoo_daily() -> dict[str, pd.Series]:
    import yfinance as yf
    tick = ["QQQ", "^VIX", "^VIX3M", "^TNX", "HYG", "IEF"]
    raw = yf.download(tick, start="2010-01-01", interval="1d", group_by="ticker", auto_adjust=True, progress=False, threads=False)
    out = {}
    for t in tick:
        try:
            s = raw[t]["Close"].dropna()
            s.index = pd.DatetimeIndex(s.index).tz_localize(None).normalize()
            out[t] = s
        except Exception:
            out[t] = pd.Series(dtype=float)
    return out


def earnings_dates() -> list[pd.Timestamp]:
    """Earnings-tidspunkt for de største Nasdaq-selskapene (så langt Yahoo går bakover)."""
    import yfinance as yf
    out = []
    for t in ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AVGO", "TSLA", "NFLX"]:
        try:
            df = yf.Ticker(t).get_earnings_dates(limit=100)
            idx = df.index if df.index.tz is not None else df.index.tz_localize(NY)
            out += list(idx.tz_convert(NY))
        except Exception:
            pass
    return sorted(out)


# ---------------------------------------------------------------------------
# Dagstabell
# ---------------------------------------------------------------------------
def at(d: date, hh: int, mm: int = 0) -> pd.Timestamp:
    return pd.Timestamp(datetime.combine(d, time(hh, mm)), tz=NY)


def logr(a, b):
    return math.log(a / b) if (a and b and np.isfinite(a) and np.isfinite(b) and a > 0 and b > 0) else np.nan


def build_days(nq: pd.DataFrame, es: pd.DataFrame, h1: dict, ydaily: dict, earn: list) -> pd.DataFrame:
    P = Px(nq, pd.Timedelta(minutes=15))
    E = Px(es, pd.Timedelta(minutes=15))
    X = {k: Px(v, pd.Timedelta(hours=3)) for k, v in h1.items()}

    qqq_days = set(ydaily["QQQ"].index.date) if len(ydaily.get("QQQ", [])) else None
    cand = sorted({ts.date() for ts in nq.index if ts.weekday() < 5})
    days = [d for d in cand if (qqq_days is None or d in qqq_days)]
    # handelsdager med komplett åpning
    days = [d for d in days if np.isfinite(P.at(at(d, 9, 30))) and np.isfinite(P.at(at(d, 10, 30)))]
    earn_ts = np.array(sorted(pd.Timestamp(e).as_unit("ns").value for e in earn), dtype=np.int64)

    rows = []
    for i, d in enumerate(days):
        if i == 0:
            continue
        p = days[i - 1]
        nxt = days[i + 1] if i + 1 < len(days) else None
        c_prev = P.at(at(p, 16, 0))
        o = P.at(at(d, 9, 30))
        r = {
            "date": d,
            "p0930": o,
            "fh": logr(P.at(at(d, 10, 30)), o),
            "fh30": logr(P.at(at(d, 10, 0)), o),
            "gap": logr(o, c_prev),
            "on_asia": logr(P.at(at(d, 3, 0)), c_prev),
            "on_london": logr(P.at(at(d, 8, 25)), P.at(at(d, 3, 0))),
            "pre_news": logr(o, P.at(at(d, 8, 25))),
            "pre_30": logr(o, P.at(at(d, 9, 0))),
            "news_move": logr(P.at(at(d, 8, 45)), P.at(at(d, 8, 25))),
            "prev_rth": logr(c_prev, P.at(at(p, 9, 30))),
            "prev_fh": logr(P.at(at(p, 10, 30)), P.at(at(p, 9, 30))),
            "prev_last": logr(c_prev, P.at(at(p, 15, 0))),
            "es_gap": logr(E.at(at(d, 9, 30)), E.at(at(p, 16, 0))),
            "es_fh": logr(E.at(at(d, 10, 30)), E.at(at(d, 9, 30))),
            "dow": d.weekday(),
            "pre_holiday": int(nxt is not None and (nxt - d).days > (3 if d.weekday() == 4 else 1)),
            "post_holiday": int((d - p).days > (3 if d.weekday() == 0 else 1)),
        }
        hi, lo = P.hl(at(p, 16, 0), at(d, 9, 30))
        r["on_pos"] = (o - lo) / (hi - lo) if np.isfinite(hi) and hi > lo else np.nan
        r["on_range"] = logr(hi, lo)
        phi, plo = P.hl(at(p, 9, 30), at(p, 16, 0))
        r["gap_vs_range"] = (1 if o > phi else -1 if o < plo else 0) if np.isfinite(phi) else np.nan
        for k in X:
            r[f"x_{k}"] = logr(X[k].at(at(d, 9, 0)), X[k].at(at(p, 16, 0)))
        a = np.searchsorted(earn_ts, at(p, 16, 0).as_unit("ns").value, side="left")
        b = np.searchsorted(earn_ts, at(d, 9, 30).as_unit("ns").value, side="left")
        r["earn"] = int(b > a)
        rows.append(r)
    df = pd.DataFrame(rows).set_index("date")

    # volatilitet og trend fra egne sluttkurser (NQ 16:00)
    close = pd.Series([P.at(at(d, 16, 0)) for d in df.index], index=df.index)
    ret = np.log(close / close.shift(1))
    df["sigma"] = ret.rolling(20, min_periods=15).std().shift(1)   # kun fortid
    df["sigma"] = df["sigma"].fillna(ret.expanding(10).std().shift(1))
    df["ret5"] = np.log(close.shift(1) / close.shift(6))
    df["trend50"] = np.log(close.shift(1) / close.shift(1).rolling(50).mean())
    df["fh_mom20"] = df["fh"].shift(1).rolling(20, min_periods=15).mean()
    df["fh_mom5"] = df["fh"].shift(1).rolling(5).mean()
    nm = df["news_move"].abs()
    df["news_z"] = nm / nm.shift(1).rolling(60, min_periods=30).median()
    df["news_day"] = (df["news_z"] > 3).astype(int)

    # kalender
    idx = pd.DatetimeIndex(df.index)
    months = pd.Series(idx.to_period("M"), index=df.index)
    pos = months.groupby(months).cumcount()
    rev = months.groupby(months).cumcount(ascending=False)
    df["tom"] = ((pos < 3) | (rev == 0)).astype(int)
    df["opex"] = [int(x.weekday() == 4 and 15 <= x.day <= 21) for x in df.index]
    df["opex_week"] = [int(15 <= (x + timedelta(days=4 - x.weekday())).day <= 21) for x in df.index]
    df["monday"] = (df["dow"] == 0).astype(int)
    df["thu_fri"] = df["dow"].isin([3, 4]).astype(int)

    # daglige Yahoo-serier (forrige dags verdi)
    def prev_val(s: pd.Series) -> pd.Series:
        if s is None or not len(s):
            return pd.Series(np.nan, index=df.index)
        s2 = s.copy()
        s2.index = s2.index.date
        out = []
        keys = np.array(sorted(s2.index))
        vals = s2.reindex(keys).to_numpy(float)
        for d in df.index:
            j = np.searchsorted(keys, d, side="left") - 1
            out.append(vals[j] if j >= 0 else np.nan)
        return pd.Series(out, index=df.index)

    vix = prev_val(ydaily.get("^VIX"))
    df["vix"] = vix
    df["vix_z"] = (vix - vix.rolling(252, min_periods=120).mean()) / vix.rolling(252, min_periods=120).std()
    df["vix_hi"] = (vix > vix.rolling(252, min_periods=120).median()).astype(float)
    df["vix_ts"] = vix / prev_val(ydaily.get("^VIX3M")) - 1
    df["vix_chg"] = np.log(vix / vix.shift(1))
    tnx = prev_val(ydaily.get("^TNX"))
    df["y10_chg5"] = tnx - tnx.shift(5)
    cr = np.log(prev_val(ydaily.get("HYG")) / prev_val(ydaily.get("IEF")))
    df["credit5"] = cr - cr.shift(5)
    df["y"] = (df["fh"] > 0).astype(float)
    df.loc[df["fh"].isna(), "y"] = np.nan
    return df


# ---------------------------------------------------------------------------
# Hypoteser
# ---------------------------------------------------------------------------
# (kolonne, navn, forventet fortegn fra litteratur/praksis, begrunnelse)
CONT = [
    ("gap_z", "Overnight-gap (σ)", -1, "Gap-reversering: Liu & Tse (2017); Yu, Rentzler & Wolf (NQ)"),
    ("asia_z", "Asia-økt (16:00→03:00)", -1, "Overnight-drift / reversering: Boyarchenko m.fl. (2023)"),
    ("london_z", "London-økt (03:00→08:25)", 0, "Europeisk prisoppdagelse"),
    ("pre_news_z", "Siste time før åpning (08:25→09:30)", 0, "Reaksjon på 08:30-tall"),
    ("pre_30_z", "Siste halvtime før åpning", 0, "Premarket-flyt"),
    ("prev_rth_z", "Gårsdagens RTH", -1, "Kortsiktig reversering"),
    ("prev_fh_z", "Gårsdagens første time", 1, "Tidsmønster gjentas: Heston, Korajczyk & Sadka (2010)"),
    ("prev_last_z", "Gårsdagens siste time", 0, "Sen flyt / gamma: Baltussen m.fl. (2021)"),
    ("fh_mom5_z", "Første time, snitt 5 dager", 1, "Heston, Korajczyk & Sadka (2010)"),
    ("fh_mom20_z", "Første time, snitt 20 dager", 1, "Heston, Korajczyk & Sadka (2010)"),
    ("ret5_z", "Avkastning 5 dager", -1, "Kortsiktig reversering"),
    ("trend50_z", "Avstand til 50-dagers snitt", 1, "Tidsserie-momentum"),
    ("on_pos", "Posisjon i overnight-range (0–1)", -1, "Praksis: åpning nær ON-high/low"),
    ("on_range_z", "Overnight-range (størrelse)", 0, "Volatilitet"),
    ("rel_es_z", "NQ vs ES gap", -1, "Relativ verdi: NQ trekkes mot ES"),
    ("x_usdjpy_z", "USD/JPY overnight", 1, "Risk-on/carry"),
    ("x_xauusd_z", "Gull overnight", -1, "Trygg havn"),
    ("x_lightcmdusd_z", "Olje overnight", 0, "Inflasjon / vekst"),
    ("x_ustbondtrusd_z", "US T-bond overnight (2018+)", 1, "Fallende renter = medvind for tech"),
    ("x_dollaridxusd_z", "Dollarindeks overnight (2017+)", -1, "Finansielle forhold"),
    ("vix_z", "VIX-nivå (z)", 1, "Høy VIX → høyere risikopremie"),
    ("vix_ts", "VIX/VIX3M − 1", 1, "Backwardation → oversolgt"),
    ("vix_chg", "VIX-endring i går", 1, "Frykt → rekyl"),
    ("y10_chg5", "10-års rente, 5 dager", -1, "Renteoppgang = motvind"),
    ("credit5", "Kreditt HYG/IEF, 5 dager", 1, "Sterk kreditt = risk-on"),
]
BIN = [
    ("monday", "Mandag", 0, "Ukedagseffekt"),
    ("thu_fri", "Torsdag/fredag", -1, "Åpningsreversering størst tor/fre: Boyarchenko m.fl."),
    ("tom", "Månedsskifte", 1, "Pengeflyt: Lakonishok & Smidt; Etula m.fl. (2020)"),
    ("opex", "Opsjonsforfall (fredag)", 0, "Gamma/forfall"),
    ("opex_week", "Forfallsuke", 0, "Gamma/forfall"),
    ("pre_holiday", "Dag før helligdag", 1, "Pre-holiday-effekt"),
    ("post_holiday", "Dag etter helligdag", 0, "Kalender"),
    ("news_day", "08:30-nyhetsdag (stor bevegelse 08:25–08:45)", 0, "Makrotall"),
    ("earn", "Megacap-earnings over natten", 0, "Selskapsnyheter"),
    ("vix_hi", "VIX over 1-års median", 0, "Regime"),
]
# Betingede hypoteser: (navn, maske-funksjon, variabel, forventet fortegn, begrunnelse)
COND = [
    ("Gap på dager UTEN 08:30-nyhet", lambda d: d["news_day"] == 0, "gap_z", -1,
     "Gap uten nyhet = likviditet → reversering"),
    ("Gap på dager MED 08:30-nyhet", lambda d: d["news_day"] == 1, "gap_z", 1,
     "Gap med nyhet = informasjon → fortsettelse"),
    ("Gap når VIX er høy", lambda d: d["vix_hi"] == 1, "gap_z", -1, "Gao m.fl. (2018): sterkere ved høy vol"),
    ("Gap når VIX er lav", lambda d: d["vix_hi"] == 0, "gap_z", -1, ""),
    ("Gap torsdag/fredag", lambda d: d["thu_fri"] == 1, "gap_z", -1, "Boyarchenko m.fl."),
    ("Store gap (|gap| > 1σ)", lambda d: d["gap_z"].abs() > 1, "gap_z", -1, "Store gap reverseres mer"),
    ("Gap i samme retning som gårsdagen", lambda d: np.sign(d["gap_z"]) == np.sign(d["prev_rth_z"]), "gap_z", -1, "Overstrekk"),
    ("Gap utenfor gårsdagens range", lambda d: d["gap_vs_range"] != 0, "gap_z", 0, "Praksis: gap utenfor value"),
    ("Siste time før åpning på nyhetsdager", lambda d: d["news_day"] == 1, "pre_news_z", 0,
     "Overreaksjon på tall?"),
    ("Earnings-dager: gap", lambda d: d["earn"] == 1, "gap_z", 0, ""),
]


def nw_t(y: np.ndarray, x: np.ndarray, lags: int = 5) -> tuple[float, float]:
    """OLS-helning og Newey-West t-verdi for y = a + b x."""
    import statsmodels.api as sm
    X = sm.add_constant(x)
    m = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(m.params[1]), float(m.tvalues[1])


def test_cont(df, col, exp):
    d = df[[col, "fh", "y"]].dropna()
    if len(d) < 150 or d[col].nunique() < 3:
        return None
    x = d[col].clip(-4, 4).to_numpy()
    yv = d["fh"].to_numpy() * 1e4
    rho, p_rho = stats.spearmanr(x, yv)
    b, t = nw_t(yv, (x - x.mean()) / x.std())
    sgn = exp if exp != 0 else (1 if rho > 0 else -1)
    pred = np.sign(x - np.median(x)) * sgn if col == "on_pos" else np.sign(x) * sgn
    ok = pred != 0
    hit = float(((pred[ok] > 0) == (d["y"].to_numpy()[ok] == 1)).mean())
    res = {"n": int(len(d)), "rho": float(rho), "t": t, "p": float(2 * stats.norm.sf(abs(t))),
           "bp_per_sd": b, "hit": hit}
    for a, z in PERIODS:
        s = d[(pd.DatetimeIndex(d.index).year >= a) & (pd.DatetimeIndex(d.index).year <= z)]
        res[f"rho_{a}"] = float(stats.spearmanr(s[col], s["fh"])[0]) if len(s) > 60 else None
    rec = d.iloc[-500:]
    res["rho_recent"] = float(stats.spearmanr(rec[col], rec["fh"])[0]) if len(rec) > 100 else None
    return res


def test_bin(df, col):
    d = df[[col, "fh", "y"]].dropna()
    a, b = d[d[col] == 1], d[d[col] == 0]
    if len(a) < 30 or len(b) < 30:
        return None
    t, p = stats.ttest_ind(a["fh"], b["fh"], equal_var=False)
    res = {"n": int(len(a)), "n0": int(len(b)), "up1": float(a["y"].mean()), "up0": float(b["y"].mean()),
           "bp1": float(a["fh"].mean() * 1e4), "bp0": float(b["fh"].mean() * 1e4), "t": float(t), "p": float(p)}
    for x, z in PERIODS:
        m = (pd.DatetimeIndex(d.index).year >= x) & (pd.DatetimeIndex(d.index).year <= z)
        s = d[m]
        res[f"up_{x}"] = float(s[s[col] == 1]["y"].mean()) if (s[col] == 1).sum() > 10 else None
        res[f"base_{x}"] = float(s["y"].mean()) if len(s) else None
    rec = d.iloc[-500:]
    res["up_recent"] = float(rec[rec[col] == 1]["y"].mean()) if (rec[col] == 1).sum() > 10 else None
    res["base_recent"] = float(rec["y"].mean())
    return res


def bh(pvals: list[float]) -> list[float]:
    p = np.array(pvals, float)
    n = len(p)
    order = np.argsort(p)
    q = np.empty(n)
    prev = 1.0
    for rank, i in reversed(list(enumerate(order, start=1))):
        prev = min(prev, p[i] * n / rank)
        q[i] = prev
    return q.tolist()


# ---------------------------------------------------------------------------
# Walk-forward modeller
# ---------------------------------------------------------------------------
def walk_forward(df: pd.DataFrame, cols: list[str], name: str, c: float = 0.05, start_years: int = 3):
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    d = df.dropna(subset=["y"]).copy()
    X = d[cols].astype(float).clip(-5, 5)
    y = d["y"].astype(int)
    years = pd.DatetimeIndex(d.index).year
    first = years.min() + start_years
    preds = pd.Series(np.nan, index=d.index)
    for yr in range(first, years.max() + 1):
        tr, te = years < yr, years == yr
        if te.sum() == 0 or y[tr].nunique() < 2:
            continue
        m = make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), StandardScaler(),
                          LogisticRegression(C=c, max_iter=2000))
        m.fit(X[tr], y[tr])
        preds[te] = m.predict_proba(X[te])[:, 1]
    p = preds.dropna()
    yy = y.loc[p.index]
    fh = d.loc[p.index, "fh"]
    base = yy.expanding().mean().shift(1).fillna(0.5)
    res = {"name": name, "features": cols, "n": int(len(p)), "start": str(p.index.min()), "end": str(p.index.max())}
    hit = ((p > 0.5).astype(int) == yy)
    res["hit"] = float(hit.mean())
    res["p_binom"] = float(stats.binomtest(int(hit.sum()), len(hit), 0.5, alternative="greater").pvalue)
    res["brier"] = float(((p - yy) ** 2).mean())
    res["brier_base"] = float(((base - yy) ** 2).mean())
    try:
        from sklearn.metrics import roc_auc_score
        res["auc"] = float(roc_auc_score(yy, p))
    except Exception:
        res["auc"] = None
    res["bp_per_day"] = float((np.sign(p - 0.5) * fh).mean() * 1e4)
    conf = (p - 0.5).abs()
    tiers = []
    for lo, hi_, lab in [(0, 0.03, "under 3 pp"), (0.03, 0.06, "3–6 pp"), (0.06, 0.10, "6–10 pp"), (0.10, 1, "over 10 pp")]:
        m = (conf >= lo) & (conf < hi_)
        if m.sum():
            tiers.append({"tier": lab, "n": int(m.sum()), "hit": float(hit[m].mean()),
                          "bp": float((np.sign(p[m] - 0.5) * fh[m]).mean() * 1e4)})
    res["tiers"] = tiers
    by_year = []
    for yr in sorted(set(pd.DatetimeIndex(p.index).year)):
        m = pd.DatetimeIndex(p.index).year == yr
        by_year.append({"year": int(yr), "n": int(m.sum()), "hit": float(hit[m].mean())})
    res["by_year"] = by_year
    rec = p.index[-500:]
    res["hit_recent"] = float(hit.loc[rec].mean())
    return res, p


# ---------------------------------------------------------------------------
def main() -> None:
    nq = load_series("usatechidxusd", "m5")
    es = load_series("usa500idxusd", "m5")
    if nq.empty:
        print("Ingen NQ-data ennå")
        sys.exit(0)
    h1 = {k: load_series(k, "h1") for k in ["usdjpy", "xauusd", "lightcmdusd", "ustbondtrusd", "dollaridxusd"]}
    h1 = {k: v for k, v in h1.items() if not v.empty}
    ydaily = yahoo_daily() if os.environ.get("NO_YAHOO") != "1" else {}
    earn = earnings_dates() if os.environ.get("NO_YAHOO") != "1" else []
    df = build_days(nq, es, h1, ydaily, earn)

    # standardisering med fortidens volatilitet
    s = df["sigma"]
    for c in ["gap", "on_asia", "on_london", "pre_news", "pre_30", "prev_rth", "prev_fh", "prev_last",
              "fh_mom5", "fh_mom20", "on_range"]:
        df[c + "_z"] = df[c] / s
    df["ret5_z"] = df["ret5"] / (s * np.sqrt(5))
    df["trend50_z"] = df["trend50"] / s
    df["rel_es_z"] = (df["gap"] - df["es_gap"]) / s
    for k in h1:
        col = f"x_{k}"
        sd = df[col].rolling(60, min_periods=30).std().shift(1)
        df[col + "_z"] = df[col] / sd
    df["vix_hi"] = df["vix_hi"].where(df["vix"].notna())

    results = {"generated": datetime.utcnow().isoformat() + "Z", "n_days": int(df["y"].notna().sum()),
               "first": str(df.index.min()), "last": str(df.index.max()),
               "base_up": float(df["y"].mean()), "mean_fh_bp": float(df["fh"].mean() * 1e4),
               "sd_fh_bp": float(df["fh"].std() * 1e4),
               "coverage": {k: int(v) for k, v in df.notna().sum().items()}}
    tests = []
    for col, name, exp, why in CONT:
        if col not in df:
            continue
        r = test_cont(df, col, exp)
        if r:
            tests.append({"kind": "cont", "col": col, "name": name, "exp": exp, "why": why, **r})
    for col, name, exp, why in BIN:
        r = test_bin(df, col)
        if r:
            tests.append({"kind": "bin", "col": col, "name": name, "exp": exp, "why": why, **r})
    for name, mask, col, exp, why in COND:
        sub = df[mask(df).fillna(False).astype(bool)]
        r = test_cont(sub, col, exp)
        if r:
            tests.append({"kind": "cond", "col": col, "name": name, "exp": exp, "why": why, **r})
    q = bh([t["p"] for t in tests])
    for t, qq in zip(tests, q):
        t["q"] = qq
        if t["kind"] == "bin":
            ups = [t.get(f"up_{a}") for a, _ in PERIODS]
            bases = [t.get(f"base_{a}") for a, _ in PERIODS]
            sgn = np.sign(t["up1"] - t["up0"])
            t["stable"] = all(u is not None and b is not None and np.sign(u - b) == sgn for u, b in zip(ups, bases))
        else:
            rhos = [t.get(f"rho_{a}") for a, _ in PERIODS]
            t["stable"] = all(r is not None and np.sign(r) == np.sign(t["rho"]) for r in rhos)
        t["passes"] = bool(t["q"] < 0.10 and t["stable"])
    results["tests"] = tests

    # modeller
    core = ["gap_z", "asia_z" if "asia_z" in df else "on_asia_z", "pre_news_z", "prev_rth_z", "prev_last_z",
            "fh_mom20_z", "ret5_z", "trend50_z", "on_pos", "rel_es_z", "vix_z", "vix_ts", "y10_chg5", "credit5",
            "tom", "monday", "thu_fri", "opex", "pre_holiday", "news_day", "earn"]
    df["asia_z"] = df["on_asia_z"]
    df["london_z"] = df["on_london_z"]
    df["gap_x_news"] = df["gap_z"] * df["news_day"]
    df["gap_x_vix"] = df["gap_z"] * df["vix_hi"].fillna(0)
    core = [c for c in core if c in df]
    passing = []
    for t in tests:
        if t["passes"]:
            passing.append(t["col"] if t["kind"] != "cond" else None)
    passing = sorted({c for c in passing if c and c in df})
    models = []
    preds = {}
    for name, cols, c in [("Alle kjernevariabler", core + ["gap_x_news", "gap_x_vix"], 0.02),
                          ("Kun variabler som besto testene", passing, 0.05),
                          ("Kun kalender", ["tom", "monday", "thu_fri", "opex", "pre_holiday"], 0.05),
                          ("Kun gap-familien", ["gap_z", "gap_x_news", "gap_x_vix", "pre_news_z"], 0.05)]:
        if not cols:
            continue
        r, pr = walk_forward(df, cols, name, c=c)
        models.append(r)
        preds[name] = pr
    results["models"] = models

    # Placebo: samme modell på tilfeldig stokkede utfall. Viser hvor høy treffrate
    # ren flaks gir med dette oppsettet, og dermed hva et ekte resultat må slå.
    rng = np.random.default_rng(42)
    perm_hits = []
    for _ in range(int(os.environ.get("N_PERM", "20"))):
        dp = df.copy()
        ok = dp["y"].notna().to_numpy()
        vals = dp.loc[ok, ["fh", "y"]].to_numpy()
        dp.loc[ok, ["fh", "y"]] = vals[rng.permutation(len(vals))]
        r, _ = walk_forward(dp, core + ["gap_x_news", "gap_x_vix"], "placebo", c=0.02)
        perm_hits.append(r["hit"])
    if perm_hits:
        results["placebo"] = {"n": len(perm_hits), "mean": float(np.mean(perm_hits)),
                              "p95": float(np.percentile(perm_hits, 95)), "max": float(np.max(perm_hits))}

    # sjekk av datakilde: Dukascopy vs Yahoo de siste 60 dagene (NQ=F 5m)
    try:
        import yfinance as yf
        y5 = yf.download("NQ=F", period="59d", interval="5m", prepost=True, progress=False, auto_adjust=False)
        y5 = y5["Close"].squeeze().dropna()
        y5.index = pd.DatetimeIndex(y5.index).tz_convert(NY)
        rows = []
        for d in df.index[-60:]:
            try:
                o, e = y5.asof(at(d, 9, 25)), y5.asof(at(d, 10, 25))
                rows.append((df.loc[d, "fh"], math.log(e / o)))
            except Exception:
                pass
        rows = [r for r in rows if np.isfinite(r[0]) and np.isfinite(r[1])]
        if len(rows) > 10:
            a = np.array(rows)
            results["source_check"] = {"n": len(a), "corr_fh": float(np.corrcoef(a[:, 0], a[:, 1])[0, 1]),
                                       "sign_agree": float((np.sign(a[:, 0]) == np.sign(a[:, 1])).mean())}
    except Exception as e:
        results["source_check"] = {"error": str(e)}

    (HERE / "results.json").write_text(json.dumps(results, indent=1, default=lambda o: None if isinstance(o, float) and not math.isfinite(o) else str(o)), encoding="utf-8")
    write_report(results)
    print(open(HERE / "RESULTS.md", encoding="utf-8").read())


def f(x, d=1, pct=False, sign=False):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "–"
    v = x * 100 if pct else x
    s = f"{v:+.{d}f}" if sign else f"{v:.{d}f}"
    return s + (" %" if pct else "")


def write_report(R: dict) -> None:
    L = []
    L.append("# NQ første time – hypotesetester\n")
    L.append(f"Generert {R['generated'][:16]} UTC. Data: {R['first']} → {R['last']}, **{R['n_days']} handelsdager**.  ")
    L.append(f"NQ steg i første time {f(R['base_up'], 1, pct=True)} av dagene. Snitt {f(R['mean_fh_bp'], 1, sign=True)} bp, "
             f"standardavvik {f(R['sd_fh_bp'], 0)} bp.\n")
    L.append("**Bestått** = q < 0,10 etter korreksjon for multippel testing (Benjamini–Hochberg) "
             "OG samme fortegn i alle tre delperioder (2011–15, 2016–20, 2021–26).\n")
    L.append("## Kontinuerlige variabler\n")
    L.append("| Variabel | n | ρ | t (NW) | q | Treff regel | 2011–15 | 2016–20 | 2021–26 | Siste 2 år | Bestått |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for t in sorted([t for t in R["tests"] if t["kind"] == "cont"], key=lambda t: t["q"]):
        L.append(f"| {t['name']} | {t['n']} | {f(t['rho'], 3, sign=True)} | {f(t['t'], 1, sign=True)} | {f(t['q'], 3)} | "
                 f"{f(t['hit'], 1, pct=True)} | {f(t.get('rho_2011'), 3, sign=True)} | {f(t.get('rho_2016'), 3, sign=True)} | "
                 f"{f(t.get('rho_2021'), 3, sign=True)} | {f(t.get('rho_recent'), 3, sign=True)} | {'✅' if t['passes'] else ''} |")
    L.append("\n## Ja/nei-variabler\n")
    L.append("| Variabel | dager | Opp når ja | Opp ellers | bp ja | bp ellers | t | q | Siste 2 år (ja / alle) | Bestått |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for t in sorted([t for t in R["tests"] if t["kind"] == "bin"], key=lambda t: t["q"]):
        L.append(f"| {t['name']} | {t['n']} | {f(t['up1'], 1, pct=True)} | {f(t['up0'], 1, pct=True)} | {f(t['bp1'], 1, sign=True)} | "
                 f"{f(t['bp0'], 1, sign=True)} | {f(t['t'], 1, sign=True)} | {f(t['q'], 3)} | "
                 f"{f(t.get('up_recent'), 1, pct=True)} / {f(t.get('base_recent'), 1, pct=True)} | {'✅' if t['passes'] else ''} |")
    L.append("\n## Betingede hypoteser\n")
    L.append("| Hypotese | n | ρ | t (NW) | q | Treff regel | 2011–15 | 2016–20 | 2021–26 | Bestått |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for t in sorted([t for t in R["tests"] if t["kind"] == "cond"], key=lambda t: t["q"]):
        L.append(f"| {t['name']} | {t['n']} | {f(t['rho'], 3, sign=True)} | {f(t['t'], 1, sign=True)} | {f(t['q'], 3)} | "
                 f"{f(t['hit'], 1, pct=True)} | {f(t.get('rho_2011'), 3, sign=True)} | {f(t.get('rho_2016'), 3, sign=True)} | "
                 f"{f(t.get('rho_2021'), 3, sign=True)} | {'✅' if t['passes'] else ''} |")
    L.append("\n## Modeller (walk-forward: trenes kun på tidligere år)\n")
    for m in R["models"]:
        L.append(f"### {m['name']}\n")
        L.append(f"Variabler: {', '.join(m['features'])}  ")
        L.append(f"Testperiode {m['start']} → {m['end']}, {m['n']} dager. **Treff {f(m['hit'], 1, pct=True)}** "
                 f"(p = {f(m['p_binom'], 3)}), AUC {f(m['auc'], 3)}, Brier {f(m['brier'], 4)} mot grunnrate {f(m['brier_base'], 4)}, "
                 f"{f(m['bp_per_day'], 1, sign=True)} bp/dag i biasens retning. Siste 2 år: {f(m['hit_recent'], 1, pct=True)}.\n")
        L.append("| Hvor sikker | dager | treff | bp i retning |")
        L.append("|---|---|---|---|")
        for t in m["tiers"]:
            L.append(f"| {t['tier']} | {t['n']} | {f(t['hit'], 1, pct=True)} | {f(t['bp'], 1, sign=True)} |")
        L.append("\nPer år: " + " · ".join(f"{y['year']}: {f(y['hit'], 0, pct=True)}" for y in m["by_year"]) + "\n")
    pl = R.get("placebo")
    if pl:
        L.append(f"## Placebo (flaksnivå)\nSamme modell trent på {pl['n']} tilfeldig stokkede utfall: snitt-treff "
                 f"{f(pl['mean'], 1, pct=True)}, 95-persentil {f(pl['p95'], 1, pct=True)}, høyeste {f(pl['max'], 1, pct=True)}. "
                 "En ekte modell må ligge klart over 95-persentilen for å regnes som bedre enn flaks.\n")
    sc = R.get("source_check", {})
    if sc and "corr_fh" in sc:
        L.append(f"## Datakilde-sjekk\nDukascopy mot Yahoo NQ=F, siste {sc['n']} dager: korrelasjon i første time "
                 f"{f(sc['corr_fh'], 3)}, samme retning {f(sc['sign_agree'], 1, pct=True)}.\n")
    (HERE / "RESULTS.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
