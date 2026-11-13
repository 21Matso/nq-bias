# NQ første time – hypotesetester

Generert 2026-11-13T22:51 UTC. Data: 2011-09-20 → 2026-11-13, **3714 handelsdager**.  
NQ steg i første time 52.6 % av dagene. Snitt +1.7 bp, standardavvik 54 bp.

**Bestått** = q < 0,10 etter korreksjon for multippel testing (Benjamini–Hochberg) OG samme fortegn i alle tre delperioder (2011–15, 2016–20, 2021–26).

## Kontinuerlige variabler

| Variabel | n | ρ | t (NW) | q | Treff regel | 2011–15 | 2016–20 | 2021–26 | Siste 2 år | Bestått |
|---|---|---|---|---|---|---|---|---|---|---|
| Første time, snitt 5 dager | 3701 | -0.060 | -3.9 | 0.001 | 48.4 % | -0.079 | -0.068 | -0.048 | -0.061 | ✅ |
| Første time, snitt 20 dager | 3699 | -0.062 | -3.9 | 0.001 | 48.4 % | -0.067 | -0.073 | -0.064 | -0.112 | ✅ |
| Overnight-gap (σ) | 3660 | -0.025 | -3.2 | 0.010 | 51.5 % | -0.055 | -0.028 | -0.011 | -0.025 | ✅ |
| NQ vs ES gap | 3660 | -0.038 | -3.0 | 0.016 | 51.7 % | -0.045 | -0.013 | -0.057 | -0.067 | ✅ |
| Asia-økt (16:00→03:00) | 3660 | -0.001 | -2.8 | 0.020 | 49.4 % | -0.058 | +0.004 | +0.019 | -0.016 |  |
| VIX/VIX3M − 1 | 3714 | +0.041 | +2.8 | 0.020 | 47.9 % | +0.038 | +0.051 | +0.037 | +0.056 | ✅ |
| Overnight-range (størrelse) | 3701 | +0.042 | +2.7 | 0.023 | 52.7 % | +0.029 | +0.062 | +0.026 | +0.083 | ✅ |
| VIX-nivå (z) | 3595 | +0.025 | +2.0 | 0.103 | 50.2 % | +0.023 | +0.066 | -0.005 | +0.048 |  |
| Siste time før åpning (08:25→09:30) | 3701 | -0.010 | -1.8 | 0.148 | 51.0 % | -0.084 | -0.007 | +0.016 | +0.010 |  |
| 10-års rente, 5 dager | 3709 | -0.029 | -1.8 | 0.152 | 50.5 % | -0.048 | +0.007 | -0.043 | -0.051 |  |
| Gårsdagens RTH | 3660 | -0.014 | -1.7 | 0.168 | 50.8 % | -0.004 | -0.038 | -0.004 | -0.054 |  |
| Avkastning 5 dager | 3620 | -0.031 | -1.7 | 0.168 | 50.4 % | -0.054 | -0.036 | -0.014 | -0.055 |  |
| Avstand til 50-dagers snitt | 2503 | -0.018 | -1.6 | 0.200 | 51.9 % | -0.033 | -0.023 | -0.019 | -0.033 |  |
| Posisjon i overnight-range (0–1) | 3684 | -0.019 | -1.4 | 0.265 | 51.2 % | -0.042 | -0.022 | +0.003 | -0.005 |  |
| Gårsdagens første time | 3701 | -0.020 | -1.2 | 0.343 | 49.8 % | -0.016 | -0.024 | -0.022 | -0.046 |  |
| Siste halvtime før åpning | 3701 | -0.008 | -1.0 | 0.447 | 50.8 % | -0.060 | -0.016 | +0.027 | +0.038 |  |
| Kreditt HYG/IEF, 5 dager | 3709 | -0.018 | -1.0 | 0.447 | 49.6 % | -0.010 | -0.008 | -0.037 | -0.048 |  |
| Olje overnight | 3409 | -0.004 | -0.9 | 0.461 | 49.3 % | +0.014 | -0.049 | +0.016 | -0.066 |  |
| VIX-endring i går | 3713 | -0.013 | +0.8 | 0.535 | 48.6 % | -0.048 | +0.004 | -0.006 | +0.009 |  |
| Gårsdagens siste time | 3660 | -0.005 | -0.6 | 0.674 | 50.3 % | -0.011 | -0.056 | +0.039 | +0.030 |  |
| Gull overnight | 3684 | +0.018 | +0.3 | 0.814 | 49.3 % | +0.050 | +0.009 | +0.003 | +0.000 |  |
| US T-bond overnight (2018+) | 1957 | -0.018 | -0.3 | 0.814 | 49.0 % | – | -0.054 | -0.008 | +0.060 |  |
| Dollarindeks overnight (2017+) | 2219 | +0.012 | +0.3 | 0.814 | 48.9 % | – | +0.068 | -0.015 | -0.041 |  |
| London-økt (03:00→08:25) | 3701 | -0.003 | -0.1 | 0.938 | 50.5 % | +0.016 | -0.026 | +0.007 | -0.001 |  |
| USD/JPY overnight | 3684 | +0.020 | +0.0 | 0.992 | 50.7 % | +0.025 | +0.005 | +0.032 | +0.027 |  |

## Ja/nei-variabler

| Variabel | dager | Opp når ja | Opp ellers | bp ja | bp ellers | t | q | Siste 2 år (ja / alle) | Bestått |
|---|---|---|---|---|---|---|---|---|---|
| Opsjonsforfall (fredag) | 172 | 39.0 % | 53.3 % | -9.1 | +2.2 | -3.1 | 0.014 | 40.9 % / 53.4 % | ✅ |
| Mandag | 696 | 57.9 % | 51.4 % | +6.9 | +0.5 | +2.9 | 0.018 | 58.3 % / 53.4 % | ✅ |
| Megacap-earnings over natten | 423 | 47.5 % | 53.3 % | -4.8 | +2.5 | -2.3 | 0.051 | 44.2 % / 53.4 % | ✅ |
| Torsdag/fredag | 1494 | 51.5 % | 53.4 % | -0.5 | +3.2 | -2.0 | 0.103 | 51.0 % / 53.4 % |  |
| 08:30-nyhetsdag (stor bevegelse 08:25–08:45) | 499 | 56.3 % | 52.0 % | +6.3 | +1.0 | +1.7 | 0.168 | 59.0 % / 53.4 % |  |
| VIX over 1-års median | 1632 | 53.8 % | 51.7 % | +3.4 | +0.4 | +1.6 | 0.188 | 55.1 % / 53.4 % |  |
| Månedsskifte | 718 | 52.9 % | 52.5 % | +3.1 | +1.4 | +0.7 | 0.569 | 65.6 % / 53.4 % |  |
| Forfallsuke | 862 | 49.9 % | 53.4 % | +2.5 | +1.5 | +0.5 | 0.735 | 45.9 % / 53.4 % |  |
| Dag før helligdag | 150 | 52.0 % | 52.6 % | +0.0 | +1.8 | -0.4 | 0.790 | 42.9 % / 53.4 % |  |
| Dag etter helligdag | 150 | 49.3 % | 52.7 % | +3.0 | +1.7 | +0.3 | 0.814 | 42.9 % / 53.4 % |  |

## Betingede hypoteser

| Hypotese | n | ρ | t (NW) | q | Treff regel | 2011–15 | 2016–20 | 2021–26 | Bestått |
|---|---|---|---|---|---|---|---|---|---|
| Gap på dager MED 08:30-nyhet | 496 | -0.174 | -4.5 | 0.000 | 45.6 % | -0.071 | -0.189 | -0.222 | ✅ |
| Store gap (|gap| > 1σ) | 369 | -0.160 | -3.8 | 0.002 | 55.3 % | -0.319 | -0.161 | -0.094 | ✅ |
| Gap utenfor gårsdagens range | 1434 | -0.061 | -3.7 | 0.002 | 52.0 % | -0.105 | -0.072 | -0.036 | ✅ |
| Gap i samme retning som gårsdagen | 1880 | -0.026 | -2.9 | 0.016 | 52.2 % | -0.018 | -0.080 | +0.004 |  |
| Gap når VIX er høy | 1618 | -0.034 | -2.9 | 0.016 | 50.7 % | -0.100 | -0.043 | -0.003 | ✅ |
| Siste time før åpning på nyhetsdager | 499 | -0.097 | -2.7 | 0.023 | 52.3 % | -0.078 | -0.022 | -0.156 | ✅ |
| Gap torsdag/fredag | 1478 | -0.057 | -2.4 | 0.043 | 53.3 % | -0.056 | -0.081 | -0.051 | ✅ |
| Earnings-dager: gap | 414 | -0.075 | -1.6 | 0.200 | 52.4 % | -0.142 | -0.114 | -0.045 |  |
| Gap når VIX er lav | 2042 | -0.021 | -1.5 | 0.228 | 52.1 % | -0.025 | -0.014 | -0.029 |  |
| Gap på dager UTEN 08:30-nyhet | 3164 | +0.004 | -1.2 | 0.343 | 51.0 % | -0.053 | -0.002 | +0.037 |  |

## Modeller (walk-forward: trenes kun på tidligere år)

### Alle kjernevariabler

Variabler: gap_z, asia_z, pre_news_z, prev_rth_z, prev_last_z, fh_mom20_z, ret5_z, trend50_z, on_pos, rel_es_z, vix_z, vix_ts, y10_chg5, credit5, tom, monday, thu_fri, opex, pre_holiday, news_day, earn, gap_x_news, gap_x_vix  
Testperiode 2014-01-02 → 2026-11-13, 3235 dager. **Treff 52.4 %** (p = 0.003), AUC 0.535, Brier 0.2491 mot grunnrate 0.2498, +2.5 bp/dag i biasens retning. Siste 2 år: 53.8 %.

| Hvor sikker | dager | treff | bp i retning |
|---|---|---|---|
| under 3 pp | 1122 | 49.9 % | -0.3 |
| 3–6 pp | 932 | 48.8 % | -1.2 |
| 6–10 pp | 728 | 56.0 % | +6.1 |
| over 10 pp | 453 | 60.3 % | +11.3 |

Per år: 2014: 52 % · 2015: 54 % · 2016: 50 % · 2017: 49 % · 2018: 48 % · 2019: 53 % · 2020: 55 % · 2021: 54 % · 2022: 51 % · 2023: 56 % · 2024: 52 % · 2025: 52 % · 2026: 56 %


### Kun variabler som besto testene

Variabler: earn, fh_mom20_z, fh_mom5_z, gap_z, monday, on_range_z, opex, rel_es_z, vix_ts  
Testperiode 2014-01-02 → 2026-11-13, 3235 dager. **Treff 54.0 %** (p = 0.000), AUC 0.550, Brier 0.2472 mot grunnrate 0.2498, +3.9 bp/dag i biasens retning. Siste 2 år: 56.2 %.

| Hvor sikker | dager | treff | bp i retning |
|---|---|---|---|
| under 3 pp | 1182 | 50.8 % | -0.1 |
| 3–6 pp | 938 | 54.1 % | +5.7 |
| 6–10 pp | 725 | 55.2 % | +2.0 |
| over 10 pp | 390 | 61.8 % | +15.3 |

Per år: 2014: 56 % · 2015: 52 % · 2016: 53 % · 2017: 53 % · 2018: 51 % · 2019: 58 % · 2020: 55 % · 2021: 56 % · 2022: 50 % · 2023: 57 % · 2024: 50 % · 2025: 57 % · 2026: 55 %


### Kun kalender

Variabler: tom, monday, thu_fri, opex, pre_holiday  
Testperiode 2014-01-02 → 2026-11-13, 3235 dager. **Treff 52.9 %** (p = 0.001), AUC 0.519, Brier 0.2488 mot grunnrate 0.2498, +1.5 bp/dag i biasens retning. Siste 2 år: 50.4 %.

| Hvor sikker | dager | treff | bp i retning |
|---|---|---|---|
| under 3 pp | 2189 | 51.6 % | -0.3 |
| 3–6 pp | 458 | 53.9 % | +2.3 |
| 6–10 pp | 449 | 56.6 % | +7.1 |
| over 10 pp | 139 | 57.6 % | +7.8 |

Per år: 2014: 50 % · 2015: 51 % · 2016: 53 % · 2017: 55 % · 2018: 51 % · 2019: 56 % · 2020: 53 % · 2021: 56 % · 2022: 51 % · 2023: 57 % · 2024: 53 % · 2025: 50 % · 2026: 51 %


### Kun gap-familien

Variabler: gap_z, gap_x_news, gap_x_vix, pre_news_z  
Testperiode 2014-01-02 → 2026-11-13, 3235 dager. **Treff 51.9 %** (p = 0.015), AUC 0.512, Brier 0.2498 mot grunnrate 0.2498, +1.4 bp/dag i biasens retning. Siste 2 år: 53.8 %.

| Hvor sikker | dager | treff | bp i retning |
|---|---|---|---|
| under 3 pp | 1962 | 51.1 % | +0.6 |
| 3–6 pp | 908 | 52.4 % | +0.6 |
| 6–10 pp | 257 | 54.1 % | +4.2 |
| over 10 pp | 108 | 57.4 % | +16.0 |

Per år: 2014: 58 % · 2015: 52 % · 2016: 48 % · 2017: 48 % · 2018: 49 % · 2019: 54 % · 2020: 54 % · 2021: 50 % · 2022: 51 % · 2023: 52 % · 2024: 52 % · 2025: 53 % · 2026: 54 %


### Ærlig: utvalg og trening kun på fortiden

Variabler: asia_z, earn, fh_mom20_z, fh_mom5_z, gap_x_big, gap_x_earn, gap_x_news, gap_x_nonews, gap_x_outside, gap_x_thufri, gap_x_vix, gap_z, monday, on_range_z, opex, opex_week, pre_30_z, pre_news_z, rel_es_z, ret5_z, thu_fri, vix_hi, vix_ts, vix_z  
Testperiode 2014-01-02 → 2026-11-13, 3235 dager. **Treff 52.2 %** (p = 0.006), AUC 0.513, Brier 0.2498 mot grunnrate 0.2498, +1.7 bp/dag i biasens retning. Siste 2 år: 54.0 %.

| Hvor sikker | dager | treff | bp i retning |
|---|---|---|---|
| under 3 pp | 1667 | 51.3 % | +0.1 |
| 3–6 pp | 766 | 50.1 % | +0.2 |
| 6–10 pp | 561 | 55.3 % | +2.7 |
| over 10 pp | 241 | 58.5 % | +15.5 |

Per år: 2014: 55 % · 2015: 51 % · 2016: 49 % · 2017: 47 % · 2018: 53 % · 2019: 54 % · 2020: 55 % · 2021: 49 % · 2022: 49 % · 2023: 56 % · 2024: 52 % · 2025: 53 % · 2026: 56 %

Dager med minst 6 pp: 802 dager, treff 56.2 % mot 51.9 % ved tilfeldighet (samme andel bullish), +34 ekstra treff, p = 0.0082.  
Dager med minst 10 pp: 241 dager, treff 58.5 % mot 51.6 % ved tilfeldighet (samme andel bullish), +17 ekstra treff, p = 0.0186.  

## Placebo (flaksnivå)
Samme modell trent på 20 tilfeldig stokkede utfall: snitt-treff 51.1 %, 95-persentil 52.1 %, høyeste 52.2 %. En ekte modell må ligge klart over 95-persentilen for å regnes som bedre enn flaks.

**Placebo for den ærlige prosedyren** (30 stokkinger): snitt-treff 52.5 %, 95-persentil 52.9 %, høyeste 53.0 %. Ekstra treff på dager med minst 6 pp: placebo snitt -1.2, 95-persentil +0.7; minst 10 pp: snitt -0.5, 95-persentil +1.3. I den sikreste klassen (over 10 pp): snitt 46.3 %, 95-persentil 57.2 %.

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
| fh_mom20_z | 58 % (+7.7 bp) | 53 % (+4.0 bp) | 51 % (+0.2 bp) | 51 % (-3.3 bp) | 51 % (-0.4 bp) |
| fh_mom5_z | 56 % (+6.8 bp) | 54 % (+3.0 bp) | 52 % (+0.4 bp) | 52 % (+0.5 bp) | 49 % (-2.4 bp) |
| gap_z | 56 % (+5.7 bp) | 55 % (+2.7 bp) | 50 % (+0.3 bp) | 49 % (-1.3 bp) | 54 % (+1.5 bp) |
| rel_es_z | 55 % (+4.8 bp) | 55 % (+1.9 bp) | 54 % (+4.0 bp) | 49 % (-1.1 bp) | 50 % (-0.8 bp) |
| vix_ts | 52 % (-0.7 bp) | 51 % (+0.4 bp) | 52 % (+0.1 bp) | 53 % (+2.3 bp) | 54 % (+6.4 bp) |
| on_range_z | 50 % (+1.1 bp) | 48 % (-3.4 bp) | 55 % (+3.4 bp) | 56 % (+4.8 bp) | 54 % (+2.5 bp) |
| gap_news | 63 % (+24.3 bp) | 63 % (+13.5 bp) | 56 % (+9.6 bp) | 51 % (-8.9 bp) | 52 % (-6.2 bp) |
| pre_news_news | 68 % (+20.8 bp) | 53 % (+3.2 bp) | 56 % (+7.8 bp) | 53 % (-4.6 bp) | 52 % (+4.2 bp) |

## Datakilde-sjekk
Dukascopy mot Yahoo NQ=F, siste 49 dager: korrelasjon i første time 1.000, samme retning 98.0 %.
