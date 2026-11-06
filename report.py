"""Terminalvisning (rich)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

import config as C
from features import FEATURES

console = Console()

GREEN, RED, DIM, AMBER = "green3", "red3", "grey58", "dark_orange"
BINARY = ("monday", "tom", "opex", "fomc", "fomc_hivix", "earn")
UKEDAG = ["man", "tir", "ons", "tor", "fre", "lør", "søn"]


def bias_label(p: float) -> tuple[str, str]:
    d = p - 0.5
    if abs(d) < C.NEUTRAL_BAND:
        return "NØYTRAL", "Nøytral"
    side = "BULLISH" if d > 0 else "BEARISH"
    return side, ("Tydelig" if abs(d) >= C.STRONG_BAND else "Svak")


def _pct(x, d=2, sign=True):
    if x is None or not np.isfinite(x):
        return "–"
    return f"{x:+.{d}f} %" if sign else f"{x:.{d}f} %"


def _col(x):
    if x is None or not np.isfinite(x) or x == 0:
        return DIM
    return GREEN if x > 0 else RED


def feature_value_text(name: str, row: pd.Series) -> str:
    v = row.get(name, np.nan)
    if name == "on_ret":
        return f"{_pct(row['raw_on_pct'])} ({v:+.1f}σ)" if np.isfinite(v) else "–"
    if name == "premkt_trend":
        return f"{_pct(row['raw_pre_pct'])} ({v:+.1f}σ)" if np.isfinite(v) else "–"
    if name == "vix_z":
        return f"VIX {row['raw_vix']:.1f} (z {v:+.1f})" if np.isfinite(v) else "–"
    if name == "vix_ts":
        return f"{1 + v:.2f}" if np.isfinite(v) else "–"
    if name == "vix_chg":
        return _pct(v * 100, 1) if np.isfinite(v) else "–"
    if name == "y10_chg5":
        return f"{v * 100:+.0f} bp" if np.isfinite(v) else "–"
    if name == "hy_chg5":
        return _pct(v * 100, 2) if np.isfinite(v) else "–"
    if name == "earn":
        return row.get("raw_earn") or "Nei"
    if name in ("monday", "tom", "opex", "fomc", "fomc_hivix"):
        return "Ja" if v == 1 else "Nei"
    if not np.isfinite(v):
        return "–"
    return f"{v:+.2f}σ"


# ---------------------------------------------------------------------------
def render_live(ctx: dict) -> None:
    row = ctx["row"].iloc[0]
    pred = ctx["pred"]
    tr = ctx["trained"]
    now_et, now_oslo = ctx["now_et"], ctx["now_oslo"]
    p = pred["p_cal"]
    bias, strength = bias_label(p)

    # ---------- topp ----------
    open_et = pd.Timestamp.combine(now_et.date(), C.OPEN_ET).tz_localize(C.NY)
    mins = (open_et - now_et).total_seconds() / 60
    when = f"{mins:.0f} min til åpning" if mins > 0 else "NY har åpnet – biasen er beregnet med data fra før 09:30 ET"
    title = Text.assemble(("NQ BIAS TERMINAL", "bold"), "  ·  ",
                          (f"{UKEDAG[now_oslo.weekday()]} {now_oslo:%d.%m.%Y %H:%M} Oslo  /  {now_et:%H:%M} ET  ·  {when}", DIM))
    console.print(Panel(title, box=box.HEAVY, style="white"))

    # ---------- dom ----------
    colr = GREEN if bias == "BULLISH" else RED if bias == "BEARISH" else AMBER
    big = Text(f"  {bias}  ", style=f"bold white on {colr}")
    prob = Text.assemble(("  P(NQ opp 09:30→10:30) = ", ""), (f"{p * 100:.1f} %", f"bold {colr}"),
                         (f"   (rå modell {pred['p_raw'] * 100:.1f} %)", DIM))
    lines = [Text.assemble(big, "  ", (f"{strength}", f"bold {colr}")), prob]

    bk = tr.wf.buckets
    if bk is not None and strength in bk.index and bk.loc[strength, "n"] > 0:
        b = bk.loc[strength]
        lines.append(Text(f"  Historisk (ut-av-utvalg) i klassen «{strength}»: treff {b['hit_rate'] * 100:.0f} % "
                          f"av {int(b['n'])} dager, snitt {b['signed_bp']:+.1f} bp i biasens retning", style=DIM))
    nq = ctx.get("nq_price", np.nan)
    med = row.get("raw_fh_abs_med_pct", np.nan)
    if np.isfinite(nq) and np.isfinite(med):
        lines.append(Text(f"  Typisk bevegelse første time (median siste 20 dager): ±{nq * med / 100:.0f} NQ-poeng "
                          f"(NQ {nq:,.0f})", style=DIM))
    console.print(Panel(Group(*lines), title="Dagens bias", border_style=colr))

    # ---------- argumenter ----------
    rs = pred["reasons"].copy()
    rs = rs[~rs["missing"]]
    # Ja/nei-variabler vises bare som argument når de faktisk er aktive i dag
    inactive = [n for n in BINARY if row.get(n, 0) != 1]
    rs = rs.drop(index=[n for n in inactive if n in rs.index])
    rs = rs[rs["pp"].abs() >= 0.15].sort_values("pp")
    bull, bear = rs[rs["pp"] > 0].iloc[::-1], rs[rs["pp"] < 0]

    def arg_table(df, title, colour):
        t = Table(box=box.SIMPLE_HEAD, expand=True, title=title, title_style=f"bold {colour}", title_justify="left")
        t.add_column("Argument", ratio=3)
        t.add_column("Nå", ratio=2, justify="right")
        t.add_column("Effekt", ratio=1, justify="right")
        t.add_column("Hvorfor", ratio=6, style=DIM)
        if df.empty:
            t.add_row("–", "", "", "Ingen vesentlige argumenter")
        for name, r in df.head(7).iterrows():
            info = FEATURES[name]
            t.add_row(info.label, feature_value_text(name, row), Text(f"{r['pp']:+.1f} pp", style=colour),
                      f"{info.why} [{info.source}]")
        return t

    console.print(arg_table(bull, "▲ Argumenter for BULLISH", GREEN))
    console.print(arg_table(bear, "▼ Argumenter for BEARISH", RED))

    # ---------- markedsbilde ----------
    mk = Table(box=box.SIMPLE_HEAD, expand=True, title="Markedsbilde siden gårsdagens 16:00 ET",
               title_justify="left", title_style="bold")
    mk.add_column("Marked"); mk.add_column("Siste", justify="right"); mk.add_column("Endring", justify="right")
    for name, (last, chg) in ctx["market"].items():
        mk.add_row(name, f"{last:,.2f}" if np.isfinite(last) else "–", Text(_pct(chg), style=_col(chg)))

    rg = Table(box=box.SIMPLE_HEAD, expand=True, title="Makro-regime (FRED, siste verdi)",
               title_justify="left", title_style="bold")
    rg.add_column("Serie"); rg.add_column("Nivå", justify="right"); rg.add_column("Endring 5 obs", justify="right")
    for name, (lvl, chg) in ctx["regime"].items():
        rg.add_row(name, f"{lvl:.2f}" if np.isfinite(lvl) else "–",
                   Text(f"{chg:+.2f}" if np.isfinite(chg) else "–", style=DIM))
    vt = row.get("raw_vix_ts", np.nan)
    rg.add_row("VIX", f"{row.get('raw_vix', np.nan):.2f}", "")
    rg.add_row("VIX / VIX3M", f"{1 + vt:.2f}" if np.isfinite(vt) else "–",
               Text("backwardation (stress)" if np.isfinite(vt) and vt > 0 else "contango (normalt)", style=DIM))
    console.print(_grid(mk, rg))

    # ---------- kalender ----------
    cal = Table(box=box.SIMPLE_HEAD, expand=True, title="Dagens hendelser (USD)", title_justify="left", title_style="bold")
    cal.add_column("Oslo"); cal.add_column("ET"); cal.add_column("Hendelse", ratio=4)
    cal.add_column("Vikt."); cal.add_column("Forv."); cal.add_column("Forrige"); cal.add_column("Faktisk"); cal.add_column("Merk", ratio=3)
    if not ctx["events"]:
        cal.add_row("", "", "Ingen viktige USD-hendelser funnet (eller kalenderen var utilgjengelig)", "", "", "", "", "")
    for ev in ctx["events"]:
        t = ev["time"]
        if t.time() < C.OPEN_ET:
            note = "før åpning – allerede i prisen"
        elif t.time() <= C.FIRST_HOUR_END_ET:
            note = Text("⚠ INNE I FØRSTE TIME – øker usikkerheten", style=AMBER)
        else:
            note = "etter første time"
        imp = Text(ev["impact"], style=RED if ev["impact"] == "High" else AMBER)
        cal.add_row(f"{t.tz_convert(C.OSLO):%H:%M}", f"{t:%H:%M}", ev["title"], imp,
                    str(ev["forecast"] or ""), str(ev["previous"] or ""), str(ev["actual"] or ""), note)
    for flag in ctx["flags"]:
        cal.add_row("", "", Text(flag, style="bold"), "", "", "", "", "")
    console.print(cal)

    # ---------- overskrifter ----------
    if ctx["headlines"]:
        ht = Table(box=None, show_header=False, title="Overskrifter (kun kontekst, ikke i modellen)",
                   title_justify="left", title_style="bold")
        ht.add_column(style=DIM)
        for _, h in ctx["headlines"]:
            ht.add_row("• " + h)
        console.print(ht)

    # ---------- modellkvalitet ----------
    console.print(model_quality_panel(tr))

    # ---------- advarsler ----------
    warn = list(ctx["warnings"])
    missing = pred["reasons"][pred["reasons"]["missing"]].index.tolist()
    if missing:
        warn.append("Mangler data for: " + ", ".join(FEATURES[m].label for m in missing) + " (satt til nøytral verdi)")
    if warn:
        console.print(Panel("\n".join("• " + w for w in warn), title="Merknader", border_style=AMBER))


def _grid(a, b):
    g = Table.grid(expand=True)
    g.add_column(ratio=1); g.add_column(ratio=1)
    g.add_row(a, b)
    return g


def model_quality_panel(tr) -> Panel:
    m = tr.wf.metrics
    if not m:
        return Panel("Ingen walk-forward-resultater ennå (for lite data).", title="Modellkvalitet", border_style=DIM)
    c = m["p_cal"]
    good = c["p_value"] < 0.05 and c["brier"] < c["brier_naive"]
    meh = c["p_value"] < 0.20 and c["brier"] <= c["brier_naive"] * 1.002
    verdict = ("Modellen har slått gjetting ut-av-utvalg med statistisk dekning." if good else
               "Svakt signal: litt bedre enn gjetting, men ikke statistisk sikkert. Behandle biasen som én innsikt, ikke fasit." if meh else
               "Modellen har IKKE vist seg bedre enn gjetting ut-av-utvalg. Biasen krympes derfor nesten helt mot 50 %.")
    a, b = tr.wf.calib
    txt = (f"Walk-forward {m['start']} → {m['end']} ({m['n']} dager modellen aldri hadde sett)\n"
           f"Treffrate {c['accuracy'] * 100:.1f} %  (p = {c['p_value']:.3f})  ·  "
           f"«alltid opp» ville gitt {m['always_up_accuracy'] * 100:.1f} %\n"
           f"Brier {c['brier']:.4f} vs naiv {c['brier_naive']:.4f}  ·  AUC {c['auc']:.3f}  ·  "
           f"snitt {c['signed_bp']:+.1f} bp/dag i biasens retning\n"
           f"Tillitsfaktor (kalibrering b) = {b:.2f}  (0 = ignorer modellen, 1 = full tillit)\n"
           f"Trent {tr.trained_on} på {tr.n_train} dager\n\n{verdict}")
    return Panel(txt, title="Modellkvalitet (ærlig vurdering)", border_style=GREEN if good else AMBER if meh else RED)


# ---------------------------------------------------------------------------
def render_backtest(tr, df: pd.DataFrame) -> None:
    wf = tr.wf
    console.print(Panel(Text("WALK-FORWARD BACKTEST – NQ første time (09:30→10:30 ET)", style="bold"), box=box.HEAVY))
    console.print(model_quality_panel(tr))
    m = wf.metrics
    if not m:
        return
    t = Table(title="Rå vs kalibrert modell", box=box.SIMPLE_HEAD, title_justify="left")
    for col in ("", "Treffrate", "p-verdi", "Brier", "Brier naiv", "AUC", "bp/dag"):
        t.add_column(col, justify="right")
    for k, lbl in (("p_raw", "Rå"), ("p_cal", "Kalibrert")):
        c = m[k]
        t.add_row(lbl, f"{c['accuracy'] * 100:.1f} %", f"{c['p_value']:.3f}", f"{c['brier']:.4f}",
                  f"{c['brier_naive']:.4f}", f"{c['auc']:.3f}", f"{c['signed_bp']:+.1f}")
    console.print(t)
    console.print(f"Andel dager NQ steg i første time (grunnrate): {m['base_up'] * 100:.1f} %", style=DIM)

    bt = Table(title="Treffrate etter hvor sikker modellen var", box=box.SIMPLE_HEAD, title_justify="left")
    bt.add_column("Klasse"); bt.add_column("Dager", justify="right"); bt.add_column("Treff", justify="right")
    bt.add_column("bp i retning", justify="right")
    for k, r in wf.buckets.iterrows():
        bt.add_row(str(k), str(int(r["n"])), f"{r['hit_rate'] * 100:.1f} %" if r["n"] else "–",
                   f"{r['signed_bp']:+.1f}" if r["n"] else "–")
    console.print(bt)

    fs = wf.feature_stats.copy()
    coefs = pd.Series(tr.model.named_steps["lr"].coef_[0], index=fs.index)
    ft = Table(title="Hver variabel alene (rangkorrelasjon med første time)", box=box.SIMPLE_HEAD, title_justify="left")
    for col in ("Variabel", "ρ hele", "t", "ρ 1. halvdel", "ρ 2. halvdel", "Stabil?", "Vekt i modell"):
        ft.add_column(col, justify="right" if col != "Variabel" else "left")
    fs = fs.assign(absrho=fs["rho"].abs()).sort_values("absrho", ascending=False)
    for name, r in fs.iterrows():
        stable = (np.sign(r["rho_1"]) == np.sign(r["rho_2"])) if np.isfinite(r["rho_1"]) and np.isfinite(r["rho_2"]) else False
        sig = abs(r["t"]) >= 2 if np.isfinite(r["t"]) else False
        ft.add_row(FEATURES[name].label, f"{r['rho']:+.3f}" if np.isfinite(r["rho"]) else "–",
                   Text(f"{r['t']:+.1f}" if np.isfinite(r["t"]) else "–", style="bold" if sig else DIM),
                   f"{r['rho_1']:+.3f}" if np.isfinite(r["rho_1"]) else "–",
                   f"{r['rho_2']:+.3f}" if np.isfinite(r["rho_2"]) else "–",
                   Text("ja" if stable else "nei", style=GREEN if stable else RED),
                   f"{coefs[name]:+.3f}")
    console.print(ft)
    console.print("|t| ≥ 2 er grovt sett statistisk signifikant. «Stabil» = samme fortegn i begge halvdeler. "
                  "Med 26 variabler forventer man at ~1 er «signifikant» ved ren tilfeldighet.", style=DIM)


def render_stats(s: dict, tr) -> None:
    t = Table(title="Journal (forward-test i sanntid)", box=box.SIMPLE_HEAD, title_justify="left")
    t.add_column("Mål"); t.add_column("Verdi", justify="right")
    t.add_row("Dager logget", str(s["logged"]))
    t.add_row("Med fasit", str(s["with_outcome"]))
    t.add_row("Nøytrale dager", str(s["neutral_days"]))
    t.add_row("Dager med bias", str(s["directional"]))
    t.add_row("Treffrate", f"{s['hit_rate'] * 100:.1f} %" if s["directional"] else "–")
    for k, (n, h) in s["by_strength"].items():
        t.add_row(f"  {k}", f"{h * 100:.1f} % av {n}")
    console.print(t)
    if s["directional"] and s["directional"] < 60:
        console.print(f"Merk: {s['directional']} dager er for lite til å konkludere. Ved 60 % ekte treffrate "
                      "trengs ~100 dager før det skiller seg tydelig fra 50 %.", style=DIM)
    if tr is not None and tr.wf.metrics:
        console.print(f"Til sammenligning, backtest: {tr.wf.metrics['p_cal']['accuracy'] * 100:.1f} % "
                      f"over {tr.wf.metrics['n']} dager.", style=DIM)
