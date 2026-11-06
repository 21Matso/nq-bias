"""Datainnhenting fra gratis kilder, med enkel disk-cache.

Kilder: Yahoo Finance (via yfinance), FRED (CSV), ForexFactory-kalender (JSON),
og RSS-overskrifter. Alle kall er pakket inn slik at én kilde som feiler ikke
stopper programmet – den blir bare markert som manglende i rapporten.
"""
from __future__ import annotations

import io
import json
import time as _time
import warnings
import xml.etree.ElementTree as ET
from datetime import datetime

import numpy as np
import pandas as pd
import requests

import config as C

warnings.filterwarnings("ignore", category=FutureWarning)

HEADERS = {"User-Agent": "Mozilla/5.0 (nq-bias-terminal; personal research)"}
SOURCE_ERRORS: list[str] = []   # samles opp og vises i rapporten


def _note_error(msg: str) -> None:
    if msg not in SOURCE_ERRORS:
        SOURCE_ERRORS.append(msg)


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
def _cache_path(key: str):
    C.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in key)
    return C.CACHE_DIR / f"{safe}.pkl"


def _cached(key: str, max_age_sec: float, loader):
    p = _cache_path(key)
    if p.exists() and (_time.time() - p.stat().st_mtime) < max_age_sec:
        try:
            return pd.read_pickle(p)
        except Exception:
            pass
    obj = loader()
    if obj is not None:
        try:
            pd.to_pickle(obj, p)
        except Exception:
            pass
    return obj


# ---------------------------------------------------------------------------
# Yahoo Finance
# ---------------------------------------------------------------------------
def _split_download(raw: pd.DataFrame, tickers: list[str]) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    if raw is None or raw.empty:
        return out
    if isinstance(raw.columns, pd.MultiIndex):
        lvl0 = set(raw.columns.get_level_values(0))
        for t in tickers:
            if t in lvl0:
                df = raw[t].copy()
            else:  # yfinance kan legge pris-feltet øverst i stedet
                try:
                    df = raw.xs(t, axis=1, level=1).copy()
                except KeyError:
                    continue
            df = df.dropna(how="all")
            if not df.empty:
                out[t] = df
    else:
        out[tickers[0]] = raw.dropna(how="all").copy()
    return out


def _to_ny(df: pd.DataFrame) -> pd.DataFrame:
    idx = df.index
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    df.index = idx.tz_convert(C.NY)
    return df.sort_index()


def fetch_intraday(tickers: list[str], prepost: bool, max_age_sec: float) -> dict[str, pd.DataFrame]:
    """1h-barer for siste ~730 dager. Indeks i New York-tid."""
    import yfinance as yf

    key = f"intraday_{'pp' if prepost else 'rth'}_{'_'.join(sorted(tickers))}"

    def load():
        data: dict = {}
        for attempt in range(3):          # Yahoo avviser av og til; prøv igjen litt senere
            missing = [t for t in tickers if t not in data]
            if not missing:
                break
            if attempt:
                _time.sleep(10 * attempt)
            try:
                raw = yf.download(
                    missing, period=f"{C.HISTORY_DAYS}d", interval="1h", prepost=prepost,
                    group_by="ticker", auto_adjust=False, progress=False, threads=False,
                )
                data.update(_split_download(raw, missing))
            except Exception as e:  # nettverk, rate limit o.l.
                if attempt == 2:
                    _note_error(f"Yahoo intradag ({', '.join(missing)}): {e}")
        if not data:
            return None
        return {t: _to_ny(df) for t, df in data.items()}

    data = _cached(key, max_age_sec, load) or {}
    for t in tickers:
        if t not in data:
            _note_error(f"Mangler intradagdata for {t}")
    return data


def fetch_daily(tickers: list[str], max_age_sec: float) -> dict[str, pd.DataFrame]:
    import yfinance as yf

    key = f"daily_{'_'.join(sorted(tickers))}"

    def load():
        try:
            raw = yf.download(tickers, period="10y", interval="1d", group_by="ticker",
                              auto_adjust=False, progress=False, threads=True)
        except Exception as e:
            _note_error(f"Yahoo daglig: {e}")
            return None
        data = _split_download(raw, tickers)
        for t, df in data.items():
            idx = df.index
            if getattr(idx, "tz", None) is not None:
                idx = idx.tz_localize(None)
            df.index = pd.DatetimeIndex(idx).normalize()
        return data

    data = _cached(key, max_age_sec, load) or {}
    for t in tickers:
        if t not in data:
            _note_error(f"Mangler dagsdata for {t}")
    return data


def fetch_earnings_dates(tickers: list[str], max_age_sec: float = 86400) -> dict[str, list[pd.Timestamp]]:
    """Historiske og kommende earnings-tidspunkt (New York-tid) for megacaps."""
    import yfinance as yf

    def load():
        out = {}
        for t in tickers:
            try:
                df = yf.Ticker(t).get_earnings_dates(limit=16)
                if df is None or df.empty:
                    continue
                idx = df.index
                if idx.tz is None:
                    idx = idx.tz_localize(C.NY)
                out[t] = list(idx.tz_convert(C.NY))
            except Exception:
                continue
        return out if out else None

    data = _cached("earnings_megacaps", max_age_sec, load)
    if not data:
        _note_error("Fant ingen earnings-datoer (Yahoo)")
        return {}
    return data


# ---------------------------------------------------------------------------
# FRED
# ---------------------------------------------------------------------------
def fetch_fred(series: dict[str, str], max_age_sec: float = 6 * 3600) -> pd.DataFrame:
    def load():
        frames = []
        for sid in series:
            try:
                r = requests.get(C.FRED_URL.format(sid=sid), headers=HEADERS, timeout=20)
                r.raise_for_status()
                df = pd.read_csv(io.StringIO(r.text))
                date_col = df.columns[0]
                df[date_col] = pd.to_datetime(df[date_col])
                s = pd.to_numeric(df[df.columns[1]], errors="coerce")
                s.index = df[date_col]
                s.name = sid
                frames.append(s)
            except Exception as e:
                _note_error(f"FRED {sid}: {e}")
        if not frames:
            return None
        return pd.concat(frames, axis=1).sort_index()

    df = _cached("fred_" + "_".join(series), max_age_sec, load)
    return df if df is not None else pd.DataFrame()


# ---------------------------------------------------------------------------
# Økonomisk kalender
# ---------------------------------------------------------------------------
def fetch_calendar(max_age_sec: float = 3600) -> list[dict]:
    """Ukens hendelser fra ForexFactory sin offentlige JSON-feed.
    Feeden tåler få kall, derfor cache i 1 time."""
    def load():
        try:
            r = requests.get(C.CALENDAR_URL, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            _note_error(f"Økonomisk kalender: {e}")
            return None

    events = _cached("calendar_week", max_age_sec, load) or []
    out = []
    for ev in events:
        try:
            ts = pd.Timestamp(ev.get("date")).tz_convert(C.NY)
        except Exception:
            continue
        out.append({
            "time": ts,
            "country": ev.get("country", ""),
            "title": ev.get("title", ""),
            "impact": ev.get("impact", ""),
            "forecast": ev.get("forecast", ""),
            "previous": ev.get("previous", ""),
            "actual": ev.get("actual", ""),
        })
    return out


# ---------------------------------------------------------------------------
# Overskrifter (kun kontekst)
# ---------------------------------------------------------------------------
def fetch_headlines(limit: int = 6, max_age_sec: float = 600) -> list[tuple[str, str]]:
    def load():
        items = []
        for url in C.NEWS_FEEDS:
            try:
                r = requests.get(url, headers=HEADERS, timeout=15)
                r.raise_for_status()
                root = ET.fromstring(r.content)
                for it in root.iter("item"):
                    title = (it.findtext("title") or "").strip()
                    pub = (it.findtext("pubDate") or "").strip()
                    if title:
                        items.append((pub, title))
            except Exception:
                continue
        return items or None

    items = _cached("headlines", max_age_sec, load) or []
    seen, out = set(), []
    for pub, title in items:
        if title not in seen:
            seen.add(title)
            out.append((pub, title))
    return out[:limit]


# ---------------------------------------------------------------------------
# Hjelpere for tid
# ---------------------------------------------------------------------------
def now_ny() -> pd.Timestamp:
    return pd.Timestamp(datetime.now(tz=C.NY))


def bar_ends(df: pd.DataFrame) -> pd.Series:
    """Slutt-tidspunkt for hver bar: neste bars start, men maks 1 time etter start.
    Håndterer både hele timebarer og halvtimesbarer rundt 09:00–09:30."""
    starts = pd.Series(df.index, index=df.index)
    nxt = starts.shift(-1)
    cap = starts + pd.Timedelta(hours=1)
    ends = nxt.where(nxt.notna() & (nxt < cap), cap)
    # Siste ordinære aksjebar (15:30) slutter 16:00 når det ikke finnes etterhandel
    is_1530 = (starts.dt.hour == 15) & (starts.dt.minute == 30)
    close_1600 = starts.dt.normalize() + pd.Timedelta(hours=16)
    capped = pd.concat([ends, close_1600], axis=1).min(axis=1)
    ends = ends.where(~is_1530, capped)
    return ends


_ARRAYS: dict[int, tuple] = {}   # id(df) -> (df, starts_ns, ends_ns, closes)


def _arrays(df: pd.DataFrame):
    hit = _ARRAYS.get(id(df))
    if hit is not None and hit[0] is df:
        return hit[1:]
    clean = df[df["Close"].notna()]
    starts = pd.DatetimeIndex(clean.index).as_unit("ns").asi8
    ends = pd.DatetimeIndex(bar_ends(clean)).as_unit("ns").asi8
    ends = np.maximum.accumulate(ends)            # garanter stigende rekkefølge
    closes = clean["Close"].to_numpy(dtype=float)
    _ARRAYS[id(df)] = (df, starts, ends, closes)
    return starts, ends, closes


def price_asof(df: pd.DataFrame | None, ts: pd.Timestamp, max_stale: pd.Timedelta = pd.Timedelta(days=4)) -> float:
    """Siste kjente pris ved tidspunkt ts: close på siste bar som er FERDIG <= ts.
    (Bruker aldri en bar som strekker seg forbi ts → ingen look-ahead.)"""
    if df is None or df.empty:
        return np.nan
    starts, ends, closes = _arrays(df)
    ts = pd.Timestamp(ts).as_unit("ns")
    pos = np.searchsorted(ends, ts.value, side="right") - 1
    if pos < 0:
        return np.nan
    # Ikke bruk en pris som er mer enn 4 døgn gammel (helg + helligdag)
    if ts.value - ends[pos] > max_stale.value:
        return np.nan
    return float(closes[pos])


def live_price(df: pd.DataFrame | None, ts: pd.Timestamp, max_stale: pd.Timedelta = pd.Timedelta(days=4)) -> float:
    """Ferskeste pris før ts, også fra en bar som ikke er ferdig (kun live-bruk)."""
    if df is None or df.empty:
        return np.nan
    starts, ends, closes = _arrays(df)
    ts = pd.Timestamp(ts).as_unit("ns")
    pos = np.searchsorted(starts, ts.value, side="left") - 1
    if pos < 0 or ts.value - starts[pos] > max_stale.value:
        return np.nan
    return float(closes[pos])
