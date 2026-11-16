# NQ første time – hypotesetester

Generert 2026-11-16T22:53 UTC. Data: 2011-09-20 → 2026-11-16, **3715 handelsdager**.  
NQ steg i første time 52.6 % av dagene. Snitt +1.7 bp, standardavvik 54 bp.

**Bestått** = q < 0,10 etter korreksjon for multippel testing (Benjamini–Hochberg) OG samme fortegn i alle tre delperioder (2011–15, 2016–20, 2021–26).

## Kontinuerlige variabler

| Variabel | n | ρ | t (NW) | q | Treff regel | 2011–15 | 2016–20 | 2021–26 | Siste 2 år | Bestått |
|---|---|---|---|---|---|---|---|---|---|---|
| Første time, snitt 5 dager | 3702 | -0.060 | -3.9 | 0.001 | 48.4 % | -0.079 | -0.068 | -0.048 | -0.067 | ✅ |
| Første time, snitt 20 dager | 3700 | -0.062 | -3.9 | 0.001 | 48.4 % | -0.067 | -0.073 | -0.064 | -0.109 | ✅ |
| Overnight-gap (σ) | 3661 | -0.024 | -3.2 | 0.011 | 51.5 % | -0.055 | -0.028 | -0.010 | -0.021 | ✅ |
| NQ vs ES gap | 3661 | -0.037 | -2.9 | 0.018 | 51.7 % | -0.045 | -0.013 | -0.055 | -0.063 | ✅ |
| Asia-økt (16:00→03:00) | 3661 | -0.001 | -2.7 | 0.021 | 49.4 % | -0.058 | +0.004 | +0.021 | -0.011 |  |
| VIX/VIX3M − 1 | 3715 | +0.040 | +2.7 | 0.021 | 47.9 % | +0.038 | +0.051 | +0.036 | +0.052 | ✅ |
| Overnight-range (størrelse) | 3702 | +0.042 | +2.7 | 0.024 | 52.7 % | +0.029 | +0.062 | +0.025 | +0.083 | ✅ |
| VIX-nivå (z) | 3596 | +0.025 | +2.0 | 0.109 | 50.1 % | +0.023 | +0.066 | -0.006 | +0.045 |  |
| Siste time før åpning (08:25→09:30) | 3702 | -0.011 | -1.8 | 0.138 | 51.0 % | -0.084 | -0.007 | +0.015 | +0.004 |  |
| 10-års rente, 5 dager | 3710 | -0.030 | -1.9 | 0.138 | 50.6 % | -0.048 | +0.007 | -0.045 | -0.053 |  |
| Avkastning 5 dager | 3621 | -0.031 | -1.7 | 0.164 | 50.4 % | -0.054 | -0.036 | -0.015 | -0.053 |  |
| Gårsdagens RTH | 3661 | -0.014 | -1.7 | 0.174 | 50.8 % | -0.004 | -0.038 | -0.003 | -0.050 |  |
| Avstand til 50-dagers snitt | 2504 | -0.018 | -1.5 | 0.215 | 51.9 % | -0.033 | -0.023 | -0.018 | -0.028 |  |
| Posisjon i overnight-range (0–1) | 3685 | -0.019 | -1.3 | 0.285 | 51.2 % | -0.042 | -0.022 | +0.004 | -0.006 |  |
| Gårsdagens første time | 3702 | -0.019 | -1.1 | 0.380 | 49.8 % | -0.016 | -0.024 | -0.021 | -0.042 |  |
| Kreditt HYG/IEF, 5 dager | 3710 | -0.019 | -1.0 | 0.438 | 49.6 % | -0.010 | -0.008 | -0.039 | -0.052 |  |
| Siste halvtime før åpning | 3702 | -0.008 | -1.0 | 0.441 | 50.8 % | -0.060 | -0.016 | +0.026 | +0.032 |  |
| Olje overnight | 3410 | -0.004 | -0.9 | 0.472 | 49.3 % | +0.014 | -0.049 | +0.017 | -0.065 |  |
| VIX-endring i går | 3714 | -0.014 | +0.8 | 0.542 | 48.6 % | -0.048 | +0.004 | -0.007 | +0.009 |  |
| Gårsdagens siste time | 3661 | -0.005 | -0.6 | 0.674 | 50.3 % | -0.011 | -0.056 | +0.039 | +0.029 |  |
| Gull overnight | 3685 | +0.019 | +0.3 | 0.810 | 49.3 % | +0.050 | +0.009 | +0.003 | +0.001 |  |
| US T-bond overnight (2018+) | 1958 | -0.018 | -0.3 | 0.810 | 49.0 % | – | -0.054 | -0.009 | +0.057 |  |
| Dollarindeks overnight (2017+) | 2220 | +0.012 | +0.3 | 0.810 | 48.9 % | – | +0.068 | -0.016 | -0.046 |  |
| London-økt (03:00→08:25) | 3702 | -0.002 | -0.1 | 0.958 | 50.5 % | +0.016 | -0.026 | +0.008 | +0.001 |  |
| USD/JPY overnight | 3685 | +0.020 | +0.0 | 0.987 | 50.7 % | +0.025 | +0.005 | +0.032 | +0.025 |  |

## Ja/nei-variabler

| Variabel | dager | Opp når ja | Opp ellers | bp ja | bp ellers | t | q | Siste 2 år (ja / alle) | Bestått |
|---|---|---|---|---|---|---|---|---|---|
| Opsjonsforfall (fredag) | 172 | 39.0 % | 53.3 % | -9.1 | +2.2 | -3.1 | 0.014 | 42.9 % / 53.4 % | ✅ |
| Mandag | 697 | 57.8 % | 51.4 % | +6.7 | +0.5 | +2.8 | 0.021 | 57.7 % / 53.4 % | ✅ |
| Megacap-earnings over natten | 423 | 47.5 % | 53.3 % | -4.8 | +2.5 | -2.3 | 0.053 | 44.2 % / 53.4 % | ✅ |
| Torsdag/fredag | 1494 | 51.5 % | 53.4 % | -0.5 | +3.1 | -2.0 | 0.109 | 51.3 % / 53.4 % |  |
| 08:30-nyhetsdag (stor bevegelse 08:25–08:45) | 499 | 56.3 % | 52.0 % | +6.3 | +1.0 | +1.7 | 0.172 | 59.0 % / 53.4 % |  |
| VIX over 1-års median | 1633 | 53.8 % | 51.7 % | +3.3 | +0.4 | +1.6 | 0.202 | 55.1 % / 53.4 % |  |
| Månedsskifte | 718 | 52.9 % | 52.5 % | +3.1 | +1.3 | +0.8 | 0.558 | 65.6 % / 53.4 % |  |
| Forfallsuke | 863 | 49.8 % | 53.4 % | +2.4 | +1.5 | +0.4 | 0.787 | 45.9 % / 53.4 % |  |
| Dag før helligdag | 150 | 52.0 % | 52.6 % | +0.0 | +1.7 | -0.4 | 0.796 | 42.9 % / 53.4 % |  |
| Dag etter helligdag | 150 | 49.3 % | 52.7 % | +3.0 | +1.6 | +0.3 | 0.810 | 42.9 % / 53.4 % |  |

## Betingede hypoteser

| Hypotese | n | ρ | t (NW) | q | Treff regel | 2011–15 | 2016–20 | 2021–26 | Bestått |
|---|---|---|---|---|---|---|---|---|---|
| Gap på dager MED 08:30-nyhet | 496 | -0.174 | -4.5 | 0.000 | 45.6 % | -0.071 | -0.189 | -0.222 | ✅ |
| Store gap (|gap| > 1σ) | 369 | -0.160 | -3.8 | 0.002 | 55.3 % | -0.319 | -0.161 | -0.094 | ✅ |
| Gap utenfor gårsdagens range | 1435 | -0.060 | -3.7 | 0.002 | 51.9 % | -0.105 | -0.072 | -0.034 | ✅ |
| Gap når VIX er høy | 1619 | -0.033 | -2.9 | 0.018 | 50.6 % | -0.100 | -0.043 | +0.000 |  |
| Gap i samme retning som gårsdagen | 1881 | -0.025 | -2.9 | 0.018 | 52.2 % | -0.018 | -0.080 | +0.006 |  |
| Siste time før åpning på nyhetsdager | 499 | -0.097 | -2.7 | 0.023 | 52.3 % | -0.078 | -0.022 | -0.156 | ✅ |
| Gap torsdag/fredag | 1478 | -0.057 | -2.4 | 0.043 | 53.3 % | -0.056 | -0.081 | -0.051 | ✅ |
| Earnings-dager: gap | 414 | -0.075 | -1.6 | 0.207 | 52.4 % | -0.142 | -0.114 | -0.045 |  |
| Gap når VIX er lav | 2042 | -0.021 | -1.5 | 0.228 | 52.1 % | -0.025 | -0.014 | -0.029 |  |
| Gap på dager UTEN 08:30-nyhet | 3165 | +0.005 | -1.2 | 0.371 | 51.0 % | -0.053 | -0.002 | +0.038 |  |

## Modeller (walk-forward: trenes kun på tidligere år)

### Alle kjernevariabler

Variabler: gap_z, asia_z, pre_news_z, prev_rth_z, prev_last_z, fh_mom20_z, ret5_z, trend50_z, on_pos, rel_es_z, vix_z, vix_ts, y10_chg5, credit5, tom, monday, thu_fri, opex, pre_holiday, news_day, earn, gap_x_news, gap_x_vix  
Testperiode 2014-01-02 → 2026-11-16, 3236 dager. **Treff 52.4 %** (p = 0.003), AUC 0.535, Brier 0.2491 mot grunnrate 0.2498, +2.5 bp/dag i biasens retning. Siste 2 år: 53.6 %.

| Hvor sikker | dager | treff | bp i retning |
|---|---|---|---|
| under 3 pp | 1122 | 49.9 % | -0.3 |
| 3–6 pp | 933 | 48.8 % | -1.4 |
| 6–10 pp | 728 | 56.0 % | +6.1 |
| over 10 pp | 453 | 60.3 % | +11.3 |

Per år: 2014: 52 % · 2015: 54 % · 2016: 50 % · 2017: 49 % · 2018: 48 % · 2019: 53 % · 2020: 55 % · 2021: 54 % · 2022: 51 % · 2023: 56 % · 2024: 52 % · 2025: 52 % · 2026: 55 %


### Kun variabler som besto testene

Variabler: earn, fh_mom20_z, fh_mom5_z, gap_z, monday, on_range_z, opex, rel_es_z, vix_ts  
Testperiode 2014-01-02 → 2026-11-16, 3236 dager. **Treff 54.0 %** (p = 0.000), AUC 0.549, Brier 0.2472 mot grunnrate 0.2498, +3.9 bp/dag i biasens retning. Siste 2 år: 56.0 %.

| Hvor sikker | dager | treff | bp i retning |
|---|---|---|---|
| under 3 pp | 1182 | 50.8 % | -0.1 |
| 3–6 pp | 938 | 54.1 % | +5.7 |
| 6–10 pp | 726 | 55.1 % | +1.9 |
| over 10 pp | 390 | 61.8 % | +15.3 |

Per år: 2014: 56 % · 2015: 52 % · 2016: 53 % · 2017: 53 % · 2018: 51 % · 2019: 58 % · 2020: 55 % · 2021: 56 % · 2022: 50 % · 2023: 57 % · 2024: 50 % · 2025: 57 % · 2026: 55 %


### Kun kalender

Variabler: tom, monday, thu_fri, opex, pre_holiday  
Testperiode 2014-01-02 → 2026-11-16, 3236 dager. **Treff 52.8 %** (p = 0.001), AUC 0.518, Brier 0.2488 mot grunnrate 0.2498, +1.4 bp/dag i biasens retning. Siste 2 år: 50.2 %.

| Hvor sikker | dager | treff | bp i retning |
|---|---|---|---|
| under 3 pp | 2189 | 51.6 % | -0.3 |
| 3–6 pp | 458 | 53.9 % | +2.3 |
| 6–10 pp | 450 | 56.4 % | +6.8 |
| over 10 pp | 139 | 57.6 % | +7.8 |

Per år: 2014: 50 % · 2015: 51 % · 2016: 53 % · 2017: 55 % · 2018: 51 % · 2019: 56 % · 2020: 53 % · 2021: 56 % · 2022: 51 % · 2023: 57 % · 2024: 53 % · 2025: 50 % · 2026: 51 %


### Kun gap-familien

Variabler: gap_z, gap_x_news, gap_x_vix, pre_news_z  
Testperiode 2014-01-02 → 2026-11-16, 3236 dager. **Treff 51.9 %** (p = 0.015), AUC 0.512, Brier 0.2498 mot grunnrate 0.2498, +1.3 bp/dag i biasens retning. Siste 2 år: 53.8 %.

| Hvor sikker | dager | treff | bp i retning |
|---|---|---|---|
| under 3 pp | 1963 | 51.1 % | +0.5 |
| 3–6 pp | 908 | 52.4 % | +0.6 |
| 6–10 pp | 257 | 54.1 % | +4.2 |
| over 10 pp | 108 | 57.4 % | +16.0 |

Per år: 2014: 58 % · 2015: 52 % · 2016: 48 % · 2017: 48 % · 2018: 49 % · 2019: 54 % · 2020: 54 % · 2021: 50 % · 2022: 51 % · 2023: 52 % · 2024: 52 % · 2025: 53 % · 2026: 54 %


### Ærlig: utvalg og trening kun på fortiden

Variabler: asia_z, earn, fh_mom20_z, fh_mom5_z, gap_x_big, gap_x_earn, gap_x_news, gap_x_nonews, gap_x_outside, gap_x_thufri, gap_x_vix, gap_z, monday, on_range_z, opex, opex_week, pre_30_z, pre_news_z, rel_es_z, ret5_z, thu_fri, vix_hi, vix_ts, vix_z  
Testperiode 2014-01-02 → 2026-11-16, 3236 dager. **Treff 52.2 %** (p = 0.006), AUC 0.513, Brier 0.2498 mot grunnrate 0.2498, +1.7 bp/dag i biasens retning. Siste 2 år: 53.8 %.

| Hvor sikker | dager | treff | bp i retning |
|---|---|---|---|
| under 3 pp | 1667 | 51.3 % | +0.1 |
| 3–6 pp | 766 | 50.1 % | +0.2 |
| 6–10 pp | 562 | 55.2 % | +2.5 |
| over 10 pp | 241 | 58.5 % | +15.5 |

Per år: 2014: 55 % · 2015: 51 % · 2016: 49 % · 2017: 47 % · 2018: 53 % · 2019: 54 % · 2020: 55 % · 2021: 49 % · 2022: 49 % · 2023: 56 % · 2024: 52 % · 2025: 53 % · 2026: 55 %

Dager med minst 6 pp: 803 dager, treff 56.2 % mot 51.9 % ved tilfeldighet (samme andel bullish), +34 ekstra treff, p = 0.0090.  
Dager med minst 10 pp: 241 dager, treff 58.5 % mot 51.6 % ved tilfeldighet (samme andel bullish), +17 ekstra treff, p = 0.0184.  

## Placebo (flaksnivå)
Samme modell trent på 20 tilfeldig stokkede utfall: snitt-treff 51.0 %, 95-persentil 52.0 %, høyeste 52.2 %. En ekte modell må ligge klart over 95-persentilen for å regnes som bedre enn flaks.

**Placebo for den ærlige prosedyren** (30 stokkinger): snitt-treff 52.4 %, 95-persentil 52.9 %, høyeste 52.9 %. Ekstra treff på dager med minst 6 pp: placebo snitt -0.6, 95-persentil +1.9; minst 10 pp: snitt -0.2, 95-persentil +1.1. I den sikreste klassen (over 10 pp): snitt 43.4 %, 95-persentil 61.3 %.

## Variabler valgt hvert år (kun med fortiden)

- 2014: (ingen – brukte grunnraten)
- 2015: gap_z, fh_mom5_z, gap_x_nonews, gap_x_vix
- 2016: pre_news_z, fh_mom5_z, gap_x_vix
- 2017: asia_z, fh_mom5_z, fh_mom20_z, ret5_z, gap_x_thufri, gap_x_big, gap_x_vix
- 2018: fh_mom5_z, ret5_z
- 2019: gap_z, pre_news_z, pre_30_z, fh_mom5_z, fh_mom20_z, ret5_z, gap_x_news, gap_x_thufri, gap_x_big, gap_x_outside, gap_x_vix
- 2020: fh_mom5_z, fh_mom20_z, ret5_z, gap_x_news, gap_x_big
- 2021: pre_news_z, fh_mom5_z, fh_mom20_z, ret5_z, on_range_z, vix_z, vix_ts, gap_x_news, gap_x_thufri, gap_x_big, gap_x_vix, thu_fri, opex_week, earn, vix_hi
- 2022: gap_z, fh_mom5_z, fh_mom20_z, on_range_z, vix_z, vix_ts, gap_x_news, gap_x_thufri, gap_x_big, gap_x_outside, gap_x_earn, opex, earn, vix_hi
- 2023: gap_z, fh_mom5_z, fh_mom20_z, on_range_z, vix_ts, gap_x_news, gap_x_thufri, gap_x_big, gap_x_outside, gap_x_earn, gap_x_vix, opex
- 2024: gap_z, fh_mom5_z, fh_mom20_z, gap_x_news, gap_x_thufri, gap_x_big, gap_x_outside, gap_x_earn, opex
- 2025: fh_mom5_z, fh_mom20_z, rel_es_z, vix_ts, gap_x_news, gap_x_thufri, gap_x_earn, gap_x_vix, monday, opex
- 2026: gap_z, fh_mom5_z, fh_mom20_z, on_range_z, rel_es_z, vix_ts, gap_x_news, gap_x_thufri, gap_x_big, gap_x_outside, gap_x_earn, gap_x_vix, monday, opex, earn

## Profiler: opp-andel per kvintil (1 = laveste verdi)

| Signal | Q1 | Q2 | Q3 | Q4 | Q5 |
|---|---|---|---|---|---|
| fh_mom20_z | 58 % (+7.7 bp) | 53 % (+4.0 bp) | 51 % (+0.1 bp) | 51 % (-3.3 bp) | 51 % (-0.4 bp) |
| fh_mom5_z | 56 % (+6.8 bp) | 54 % (+3.0 bp) | 52 % (+0.4 bp) | 52 % (+0.2 bp) | 49 % (-2.3 bp) |
| gap_z | 56 % (+5.5 bp) | 55 % (+2.7 bp) | 50 % (+0.3 bp) | 49 % (-1.3 bp) | 54 % (+1.5 bp) |
| rel_es_z | 55 % (+4.6 bp) | 55 % (+1.9 bp) | 54 % (+4.0 bp) | 49 % (-1.1 bp) | 50 % (-0.8 bp) |
| vix_ts | 52 % (-0.7 bp) | 51 % (+0.4 bp) | 52 % (+0.2 bp) | 53 % (+2.1 bp) | 54 % (+6.4 bp) |
| on_range_z | 50 % (+1.1 bp) | 48 % (-3.4 bp) | 55 % (+3.4 bp) | 56 % (+4.7 bp) | 54 % (+2.4 bp) |
| gap_news | 63 % (+24.3 bp) | 63 % (+13.5 bp) | 56 % (+9.6 bp) | 51 % (-8.9 bp) | 52 % (-6.2 bp) |
| pre_news_news | 68 % (+20.8 bp) | 53 % (+3.2 bp) | 56 % (+7.8 bp) | 53 % (-4.6 bp) | 52 % (+4.2 bp) |

## Datakilde-sjekk
Dukascopy mot Yahoo NQ=F, siste 49 dager: korrelasjon i første time 1.000, samme retning 100.0 %.
