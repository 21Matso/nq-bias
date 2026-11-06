"""Innstillinger for NQ Bias Terminal.

Alt som er "tall man kan skru på" ligger her, så resten av koden kan stå i fred.
"""
from datetime import date, time
from pathlib import Path
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
OSLO = ZoneInfo("Europe/Oslo")

# NY-åpning og målvindu (første time)
OPEN_ET = time(9, 30)
FIRST_HOUR_END_ET = time(10, 30)
CLOSE_ET = time(16, 0)

# Mapper for cache, modell og journal (ligger ved siden av programmet)
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
MODEL_PATH = DATA_DIR / "model.joblib"
JOURNAL_PATH = DATA_DIR / "journal.csv"

# ---------------------------------------------------------------------------
# Tickere (alle gratis via Yahoo Finance / yfinance)
# ---------------------------------------------------------------------------
# Målet måles på QQQ (følger Nasdaq-100 nesten 1:1 og har ingen kontrakt-rull),
# og omregnes til NQ-poeng med NQ=F-prisen.
TARGET_TICKER = "QQQ"
NQ_TICKER = "NQ=F"

# Hentes som 1h-barer med pre/post-market (prepost=True)
INTRADAY_ETFS = {
    "QQQ": "Nasdaq-100 (QQQ)",
    "SPY": "S&P 500 (SPY)",
    "SMH": "Halvledere (SMH)",
}
# 24-timers markeder, 1h-barer
INTRADAY_24H = {
    "ZN=F": "10-års Treasury future",
    "DX-Y.NYB": "Dollarindeks (DXY)",
    "JPY=X": "USD/JPY",
    "BTC-USD": "Bitcoin",
    "NQ=F": "NQ future",
    "ES=F": "ES future",
    "CL=F": "Råolje (WTI)",
    "GC=F": "Gull",
    "^STOXX50E": "Euro Stoxx 50",
}
# Daglige serier
DAILY_TICKERS = {
    "^VIX": "VIX",
    "^VIX3M": "VIX 3 mnd",
    "QQQ": "QQQ",
}

# FRED-serier (gratis CSV uten API-nøkkel)
FRED_SERIES = {
    "DGS10": "10-års rente (%)",
    "DGS2": "2-års rente (%)",
    "T10Y2Y": "Rentekurve 10y-2y (pp)",
    "DFII10": "10-års realrente (%)",
    "BAMLH0A0HYM2": "High yield-spread (pp)",
    "DFF": "Fed funds (%)",
    "NFCI": "Chicago Fed finansielle forhold",
}
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"

# Økonomisk kalender (ForexFactory sin offentlige ukesfeed)
CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

# Overskrifter (kun til visning, inngår ikke i modellen)
NEWS_FEEDS = [
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://feeds.content.dowjones.io/public/rss/mw_topstories",
]

# Megacaps i Nasdaq-100 (earnings fra disse flytter NQ)
MEGACAPS = ["NVDA", "MSFT", "AAPL", "AMZN", "GOOGL", "META", "AVGO", "TSLA", "NFLX", "COST"]

# ---------------------------------------------------------------------------
# FOMC-rentebeslutninger (dag 2 = annonseringsdag, 14:00 ET).
# Kilde: federalreserve.gov/monetarypolicy/fomccalendars.htm
# 2027 er foreløpig (Fed bekrefter hvert møte på møtet før). Oppdater ved behov.
# ---------------------------------------------------------------------------
FOMC_DECISION_DATES = [
    date(2024, 1, 31), date(2024, 3, 20), date(2024, 5, 1), date(2024, 6, 12),
    date(2024, 7, 31), date(2024, 9, 18), date(2024, 11, 7), date(2024, 12, 18),
    date(2025, 1, 29), date(2025, 3, 19), date(2025, 5, 7), date(2025, 6, 18),
    date(2025, 7, 30), date(2025, 9, 17), date(2025, 10, 29), date(2025, 12, 10),
    date(2026, 1, 28), date(2026, 3, 18), date(2026, 4, 29), date(2026, 6, 17),
    date(2026, 7, 29), date(2026, 9, 16), date(2026, 10, 28), date(2026, 12, 9),
    date(2027, 1, 27), date(2027, 3, 17), date(2027, 4, 28), date(2027, 6, 9),
    date(2027, 7, 28), date(2027, 9, 15), date(2027, 10, 27), date(2027, 12, 8),
]

# ---------------------------------------------------------------------------
# Modell
# ---------------------------------------------------------------------------
HISTORY_DAYS = 729            # yfinance tillater maks 730 dager med 1h-data
MIN_TRAIN_DAYS = 200          # første walk-forward-trening
REFIT_EVERY = 20              # refit hver ~måned i backtest
C_GRID = [0.003, 0.01, 0.03, 0.1, 0.3]   # L2-styrke (lav C = sterk krymping mot 50 %)
Z_CLIP = 4.0                  # klipp ekstreme z-verdier (beskytter mot rull-hopp o.l.)

# Hvor langt fra 50 % før vi kaller det en bias
NEUTRAL_BAND = 0.03           # |p - 0.5| < 3 pp  -> NØYTRAL
STRONG_BAND = 0.08            # |p - 0.5| >= 8 pp -> "tydelig"

# Programmet er laget for å kjøres rett før 09:30 ET (vanligvis 15:20–15:29 norsk tid)
IDEAL_RUN_START_ET = time(9, 0)
