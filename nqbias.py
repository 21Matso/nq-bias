#!/usr/bin/env python3
"""NQ Bias Terminal – sannsynlig retning for NQ i første time etter NY-åpning.

Bruk:
    python nqbias.py              dagens bias (kjør 15:00–15:29 norsk tid)
    python nqbias.py backtest     walk-forward-test av modellen + variabelanalyse
    python nqbias.py update       fyll inn fasit i journalen
    python nqbias.py stats        treffrate i journalen (forward-test)

Valg:
    --retrain                     tren modellen på nytt nå
    --asof "2026-11-04 09:20"     spill av en tidligere dag (tid i New York)
    --no-news                     hopp over overskrifter
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, time, timedelta

import numpy as np
import pandas as pd

import config as C
import data as D
import journal as J
import report as R
from features import FEATURES, build_features, rth_daily_table
from model import load_trained, predict_with_reasons, train_and_save

ETF_PP = list(C.INTRADAY_ETFS)
H24 = list(C.INTRADAY_24H)


# ---------------------------------------------------------------------------
def load_bundle(max_age_sec: float) -> dict:
    with R.console.status("Henter markedsdata (Yahoo, FRED)…"):
        bundle = {
            "rth": D.fetch_intraday(ETF_PP, prepost=False, max_age_sec=max_age_sec),
            "pp": D.fetch_intraday(ETF_PP, prepost=True, max_age_sec=max_age_sec),
            "h24": D.fetch_intraday(H24, prepost=False, max_age_sec=max_age_sec),
            "daily": D.fetch_daily(list(C.DAILY_TICKERS), max_age_sec=max(max_age_sec, 1800)),
            "fred": D.fetch_fred(C.FRED_SERIES),
        }
    with R.console.status("Henter earnings-datoer for megacaps…"):
        bundle["earnings"] = D.fetch_earnings_dates(C.MEGACAPS)
    if "QQQ" not in bundle["rth"]:
        R.console.print("[red]Fikk ikke QQQ-data fra Yahoo. Sjekk nettforbindelsen og prøv igjen om litt.[/red]")
        for e in D.SOURCE_ERRORS:
            R.console.print(f"  • {e}")
        sys.exit(1)
    return bundle


def get_model(bundle: dict, retrain: bool):
    tr = load_trained()
    today = datetime.now(tz=C.OSLO).strftime("%Y-%m-%d")
    if tr is not None and not retrain and tr.trained_on.startswith(today):
        return tr
    with R.console.status("Bygger historiske variabler…"):
        hist = build_features(bundle)
    n = int(hist["y"].notna().sum()) if "y" in hist else 0
    if n < 120:
        R.console.print(f"[red]For lite historikk til å trene ({n} dager).[/red]")
        sys.exit(1)
    R.console.print(f"Trener modell og kjører walk-forward på {n} dager (tar typisk 30–90 sek, én gang per dag)…")
    with R.console.status("Walk-forward…") as st:
        tr = train_and_save(hist, progress=lambda k, m: st.update(f"Walk-forward {k}/{m}…"))
    tr._hist = hist  # type: ignore[attr-defined]
    return tr


# ---------------------------------------------------------------------------
def market_snapshot(bundle: dict, now_et: pd.Timestamp, prev_day, strict: bool) -> dict:
    t_prev = pd.Timestamp(datetime.combine(prev_day, C.CLOSE_ET), tz=C.NY)
    px = D.price_asof if strict else D.live_price
    rows = {}
    order = [("NQ=F", "h24"), ("ES=F", "h24"), ("QQQ", "pp"), ("SPY", "pp"), ("SMH", "pp"),
             ("ZN=F", "h24"), ("DX-Y.NYB", "h24"), ("JPY=X", "h24"), ("BTC-USD", "h24"),
             ("CL=F", "h24"), ("GC=F", "h24"), ("^STOXX50E", "h24")]
    for t, kind in order:
        df = bundle[kind].get(t)
        name = C.INTRADAY_ETFS.get(t) or C.INTRADAY_24H.get(t, t)
        if kind == "pp":
            name += " premarket"
            base = D.price_asof(bundle["rth"].get(t), t_prev)
        else:
            base = D.price_asof(df, t_prev)
        last = px(df, now_et)
        chg = (last / base - 1) * 100 if np.isfinite(last) and np.isfinite(base) and base > 0 else np.nan
        rows[name] = (last, chg)
    return rows


def regime_snapshot(fred: pd.DataFrame) -> dict:
    out = {}
    for sid, name in C.FRED_SERIES.items():
        if fred is None or fred.empty or sid not in fred:
            out[name] = (np.nan, np.nan)
            continue
        s = fred[sid].dropna()
        out[name] = (float(s.iloc[-1]), float(s.iloc[-1] - s.iloc[-6])) if len(s) > 6 else (np.nan, np.nan)
    return out


def todays_events(day) -> list[dict]:
    evs = [e for e in D.fetch_calendar()
           if e["country"] == "USD" and e["impact"] in ("High", "Medium") and e["time"].date() == day]
    return sorted(evs, key=lambda e: e["time"])


def flags_for(day, row: pd.Series, earnings: dict) -> list[str]:
    flags = []
    if day in set(C.FOMC_DECISION_DATES):
        t = pd.Timestamp(datetime.combine(day, time(14, 0)), tz=C.NY).tz_convert(C.OSLO)
        flags.append(f"FOMC-rentebeslutning i dag kl. {t:%H:%M} norsk tid (14:00 ET), etter første time")
    if row.get("opex", 0) == 1:
        flags.append("Månedlig opsjonsforfall (OPEX) i dag")
    if row.get("raw_earn"):
        flags.append(f"Megacap-earnings siden i går kveld: {row['raw_earn']}")
    later = [t for t, lst in earnings.items() for ts in lst if ts.date() == day and ts.time() >= C.CLOSE_ET]
    if later:
        flags.append(f"Earnings etter stengning i dag: {', '.join(sorted(set(later)))}")
    if row.get("tom", 0) == 1:
        flags.append("Månedsskifte-vindu (siste/første handelsdager)")
    return flags


# ---------------------------------------------------------------------------
def compute_live(args, quiet_weekend: bool = False) -> dict | None:
    """Beregner dagens bias og alt som vises rundt den. Returnerer ctx eller None."""
    real_now = D.now_ny()
    replay = args.asof is not None
    now_et = pd.Timestamp(args.asof, tz=C.NY) if replay else real_now
    day = now_et.date()
    if now_et.weekday() >= 5:
        if not quiet_weekend:
            R.console.print("[yellow]Det er helg – NY-markedet er stengt. Kjør programmet en handelsdag "
                            "10–2 minutter før NY åpner.[/yellow]")
        return None

    bundle = load_bundle(max_age_sec=60 if not replay else 6 * 3600)
    table = rth_daily_table(bundle["rth"]["QQQ"])
    if not replay:
        filled = J.fill_outcomes(table)
        if filled:
            R.console.print(f"[grey58]Journal: fylte inn fasit for {filled} dag(er).[/grey58]")

    tr = get_model(bundle, args.retrain)

    open_et = pd.Timestamp(datetime.combine(day, C.OPEN_ET), tz=C.NY)
    strict = replay or now_et >= open_et
    row = build_features(bundle, live_cutoff=now_et, strict=strict)
    if row.empty:
        R.console.print("[red]Klarte ikke å bygge dagens variabler (mangler forrige handelsdag eller data).[/red]")
        return None
    pred = predict_with_reasons(tr, row)

    prev_days = [d for d in table.index if d < day]
    prev_day = prev_days[-1]
    nq_df = bundle["h24"].get("NQ=F")
    nq_price = (D.price_asof if strict else D.live_price)(nq_df, min(now_et, open_et))

    warnings = []
    if replay:
        warnings.append(f"AVSPILLING av {day}: modellen er trent på data som kan inkludere denne dagen (ikke en ærlig test).")
    elif now_et >= open_et:
        warnings.append("Kjørt etter åpning: biasen bruker kun data fra før 09:30 ET og logges ikke i journalen.")
    elif now_et.time() < C.IDEAL_RUN_START_ET:
        o = open_et.tz_convert(C.OSLO)
        warnings.append(f"Kjørt tidlig: premarket-variablene endrer seg frem mot åpning. Beste tidspunkt i dag er "
                        f"{(o - pd.Timedelta(minutes=10)):%H:%M}–{(o - pd.Timedelta(minutes=1)):%H:%M} norsk tid.")
    if day != real_now.date() and not replay:
        warnings.append("Datoen stemmer ikke med dagens dato.")
    if not np.isfinite(row.iloc[0].get("on_ret", np.nan)):
        warnings.insert(0, "VIKTIG: fikk ikke fersk premarket-pris for NQ. Biasen mangler sin viktigste variabel og er mer usikker enn vanlig.")
    warnings += D.SOURCE_ERRORS

    return {
        "day": day, "replay": replay, "open_et": open_et,
        "row": row, "pred": pred, "trained": tr,
        "now_et": now_et, "now_oslo": now_et.tz_convert(C.OSLO),
        "nq_price": nq_price,
        "market": market_snapshot(bundle, now_et, prev_day, strict),
        "regime": regime_snapshot(bundle["fred"]),
        "events": todays_events(day) if not replay else [],
        "flags": flags_for(day, row.iloc[0], bundle["earnings"]),
        "headlines": [] if (args.no_news or replay) else D.fetch_headlines(),
        "warnings": warnings,
        "bundle": bundle,
    }


def log_live(ctx: dict) -> None:
    if ctx["replay"]:
        return
    pred, now_et, open_et = ctx["pred"], ctx["now_et"], ctx["open_et"]
    bias, strength = R.bias_label(pred["p_cal"])
    rs = pred["reasons"].assign(a=lambda x: x["pp"].abs()).sort_values("a", ascending=False)
    top = "; ".join(f"{FEATURES[n].label} {r['pp']:+.1f}pp" for n, r in rs.head(4).iterrows())
    nq_price = ctx["nq_price"]
    J.log_prediction({
        "date": str(ctx["day"]), "run_time_oslo": f"{now_et.tz_convert(C.OSLO):%H:%M}", "run_time_et": f"{now_et:%H:%M}",
        "minutes_before_open": round((open_et - now_et).total_seconds() / 60, 1),
        "p_raw": round(pred["p_raw"], 4), "p_cal": round(pred["p_cal"], 4),
        "bias": bias, "strength": strength, "top_reasons": top,
        "nq_price": round(nq_price, 2) if np.isfinite(nq_price) else np.nan,
    })


def cmd_run(args) -> None:
    ctx = compute_live(args)
    if ctx is None:
        return
    R.render_live(ctx)
    log_live(ctx)


def cmd_backtest(args) -> None:
    bundle = load_bundle(max_age_sec=6 * 3600)
    tr = get_model(bundle, retrain=True)
    hist = getattr(tr, "_hist", None)
    R.render_backtest(tr, hist)
    out = C.DATA_DIR / "backtest_predictions.csv"
    tr.wf.preds.to_csv(out)
    R.console.print(f"\nAlle ut-av-utvalg-prediksjoner lagret i {out}", style="grey58")


def cmd_update(args) -> None:
    bundle_rth = D.fetch_intraday(["QQQ"], prepost=False, max_age_sec=60)
    if "QQQ" not in bundle_rth:
        R.console.print("[red]Fikk ikke QQQ-data.[/red]")
        return
    n = J.fill_outcomes(rth_daily_table(bundle_rth["QQQ"]))
    R.console.print(f"Fylte inn fasit for {n} dag(er). Journal: {C.JOURNAL_PATH}")


def cmd_stats(args) -> None:
    cmd_update(args)
    R.render_stats(J.summary(), load_trained())


def cmd_web(args) -> None:
    import web
    web.run(args, sys.modules[__name__])


COMMANDS = {"run": cmd_run, "backtest": cmd_backtest, "update": cmd_update, "stats": cmd_stats, "web": cmd_web}


def _ns(command="run", asof=None, retrain=False, no_news=False):
    return argparse.Namespace(command=command, asof=asof, retrain=retrain, no_news=no_news)


def menu() -> None:
    """Enkel meny for dobbeltklikk-bruk. En feil i ett valg lukker ikke vinduet."""
    from rich.panel import Panel

    while True:
        now = D.now_ny()
        d = now.date()
        while d.weekday() >= 5 or (d == now.date() and now.time() >= C.OPEN_ET):
            d += timedelta(days=1)
        o = pd.Timestamp(datetime.combine(d, C.OPEN_ET), tz=C.NY).tz_convert(C.OSLO)
        dag = "i dag" if d == now.date() else f"{R.UKEDAG[d.weekday()]} {d:%d.%m}"
        R.console.clear()
        R.console.print(Panel(
            f"[bold]NQ BIAS TERMINAL[/bold]\n\n"
            f"Neste NY-åpning: [bold]{dag} kl. {o:%H:%M}[/bold] norsk tid\n"
            f"Kjør dagens bias mellom [bold]{(o - pd.Timedelta(minutes=10)):%H:%M}[/bold] og "
            f"[bold]{(o - pd.Timedelta(minutes=1)):%H:%M}[/bold]\n\n"
            "  [bold]1[/bold]  Dagens bias\n"
            "  [bold]2[/bold]  Backtest – hvor godt fungerer modellen?\n"
            "  [bold]3[/bold]  Journal – treffrate så langt\n"
            "  [bold]4[/bold]  Spill av en tidligere dag\n"
            "  [bold]0[/bold]  Avslutt",
            border_style="white", expand=False))
        try:
            choice = input("Velg (1/2/3/4/0) og trykk Enter: ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if choice in ("0", "q", ""):
            return
        try:
            if choice == "1":
                cmd_run(_ns("run"))
            elif choice == "2":
                cmd_backtest(_ns("backtest"))
            elif choice == "3":
                cmd_stats(_ns("stats"))
            elif choice == "4":
                s = input("Dato (ÅÅÅÅ-MM-DD), f.eks. 2026-11-04: ").strip()
                cmd_run(_ns("run", asof=f"{pd.Timestamp(s):%Y-%m-%d} 09:20"))
            else:
                R.console.print("Ukjent valg.")
        except SystemExit:
            pass
        except KeyboardInterrupt:
            R.console.print("\nAvbrutt.")
        except Exception as e:  # vis feilen, men behold vinduet åpent
            R.console.print(f"[red]Noe gikk galt: {e}[/red]")
            R.console.print("[grey58]Sjekk nettforbindelsen og prøv igjen. Ta gjerne skjermbilde av feilen.[/grey58]")
        D.SOURCE_ERRORS.clear()
        try:
            input("\nTrykk Enter for å gå tilbake til menyen…")
        except (EOFError, KeyboardInterrupt):
            return


def main() -> None:
    ap = argparse.ArgumentParser(description="NQ Bias Terminal")
    ap.add_argument("command", nargs="?", default="run", choices=list(COMMANDS))
    ap.add_argument("--retrain", action="store_true")
    ap.add_argument("--asof", default=None, help='Avspilling, f.eks. "2026-11-04 09:20" (New York-tid)')
    ap.add_argument("--no-news", action="store_true")
    ap.add_argument("--menu", action="store_true", help="Vis meny (brukes av startfilene)")
    ap.add_argument("--mode", default="auto", choices=["auto", "prep", "live", "followup"],
                    help="Kun for 'web': tving en fase")
    args = ap.parse_args()
    if args.menu:
        menu()
        return
    COMMANDS[args.command](args)


if __name__ == "__main__":
    main()
