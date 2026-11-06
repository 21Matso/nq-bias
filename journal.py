"""Journal: logger hver dags bias og fyller inn fasit etterpå.

Dette er forward-testen: tall fra journalen er det eneste beviset som teller,
fordi modellen aldri kan ha sett disse dagene på forhånd.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config as C

COLUMNS = [
    "date", "run_time_oslo", "run_time_et", "minutes_before_open", "p_raw", "p_cal",
    "bias", "strength", "top_reasons", "nq_price",
    "fh_ret_pct", "nq_points", "outcome", "correct",
]


def load() -> pd.DataFrame:
    if not C.JOURNAL_PATH.exists():
        return pd.DataFrame(columns=COLUMNS)
    text_cols = ["date", "run_time_oslo", "run_time_et", "bias", "strength", "top_reasons", "outcome", "correct"]
    df = pd.read_csv(C.JOURNAL_PATH, dtype={c: "object" for c in text_cols})
    for c in COLUMNS:
        if c not in df:
            df[c] = pd.Series([None] * len(df), dtype="object" if c in text_cols else "float64")
    return df[COLUMNS]


def save(df: pd.DataFrame) -> None:
    C.DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(C.JOURNAL_PATH, index=False)


def log_prediction(entry: dict) -> None:
    """Én rad per dato. Kjører du flere ganger før åpning, beholdes siste kjøring
    før 09:30 ET. Kjøringer etter åpning logges ikke (de ville ikke vært ærlige)."""
    if entry.get("minutes_before_open", 0) <= 0:
        return
    df = load()
    df = df[df["date"] != entry["date"]]
    row = {c: entry.get(c, np.nan) for c in COLUMNS}
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    save(df.sort_values("date"))


def fill_outcomes(daily_table: pd.DataFrame) -> int:
    """Fyller inn faktisk første time (fra QQQ-data) for rader som mangler fasit."""
    df = load()
    if df.empty:
        return 0
    n = 0
    for i, r in df.iterrows():
        if pd.notna(r["outcome"]) and str(r["outcome"]) != "":
            continue
        d = pd.Timestamp(r["date"]).date()
        if d not in daily_table.index:
            continue
        fh = daily_table.loc[d, "fh_ret"]
        if not np.isfinite(fh):
            continue
        df.at[i, "fh_ret_pct"] = round(float(fh) * 100, 3)
        if pd.notna(r["nq_price"]):
            df.at[i, "nq_points"] = round(float(r["nq_price"]) * float(np.expm1(fh)), 1)
        up = fh > 0
        df.at[i, "outcome"] = "OPP" if up else "NED"
        if r["bias"] == "NØYTRAL":
            df.at[i, "correct"] = "nøytral"
        else:
            df.at[i, "correct"] = "ja" if (r["bias"] == "BULLISH") == up else "nei"
        n += 1
    if n:
        save(df)
    return n


def summary() -> dict:
    df = load()
    done = df[df["correct"].isin(["ja", "nei"])]
    res = {"logged": len(df), "with_outcome": int(df["outcome"].notna().sum()),
           "directional": len(done), "hits": int((done["correct"] == "ja").sum())}
    res["hit_rate"] = res["hits"] / res["directional"] if res["directional"] else float("nan")
    by = {}
    for s, g in done.groupby("strength"):
        by[s] = (len(g), float((g["correct"] == "ja").mean()))
    res["by_strength"] = by
    res["neutral_days"] = int((df["correct"] == "nøytral").sum())
    return res
