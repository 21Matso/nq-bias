# NQ første time etter London-åpning – hypotesetester

Generert 2026-11-10T13:10 UTC. Data: 2014-01-02 → 2026-11-09, **3330 dager**. Mål: NQ fra 08:00 til 09:00 London-tid (09:00–10:00 norsk tid). NQ steg 51.2 % av dagene, snitt +0.4 bp, standardavvik 24 bp.

| Variabel | n | Effekt | t | q | 2014–17 | 2018–21 | 2022–26 | Bestått |
|---|---|---|---|---|---|---|---|---|
| London første time, snitt 5 dager | 3330 | ρ -0.048 | -2.3 | 0.186 | -0.054 | -0.060 | -0.041 |  |
| Overnight-range (størrelse) | 3330 | ρ +0.030 | +2.3 | 0.186 | -0.003 | -0.038 | +0.080 |  |
| T-bond over natten (2018+) | 2020 | ρ +0.060 | +2.6 | 0.186 | – | +0.054 | +0.061 |  |
| Store overnight-bevegelser (>1σ) | 3258 | ρ -0.021 | -2.1 | 0.214 | -0.016 | -0.015 | -0.029 |  |
| US-stengning → London-åpning | 3258 | ρ -0.013 | -1.4 | 0.456 | +0.021 | -0.043 | -0.011 |  |
| Avkastning 5 dager | 3330 | ρ -0.018 | -1.6 | 0.456 | -0.007 | +0.027 | -0.065 |  |
| Gull over natten | 3329 | ρ +0.025 | +1.4 | 0.456 | +0.004 | +0.060 | +0.007 |  |
| Mandag | 667 | 53.4 % opp vs 50.7 % | +1.5 | 0.456 | 49 % | 48 % | 61 % |  |
| Torsdag/fredag | 1323 | 50.7 % opp vs 51.6 % | -1.3 | 0.456 | 46 % | 54 % | 52 % |  |
| Gårsdagens siste US-time | 3258 | ρ +0.020 | +1.2 | 0.475 | +0.035 | +0.061 | -0.021 |  |
| USD/JPY over natten | 3330 | ρ -0.036 | -1.2 | 0.475 | -0.059 | -0.053 | -0.005 |  |
| Fredag | 655 | 48.1 % opp vs 52.0 % | -1.2 | 0.475 | 48 % | 49 % | 47 % |  |
| London første time, snitt 20 dager | 3330 | ρ -0.013 | -0.9 | 0.607 | -0.025 | -0.043 | +0.002 |  |
| Gårsdagens US-dag (RTH) | 3258 | ρ -0.035 | -0.7 | 0.745 | +0.047 | -0.031 | -0.095 |  |
| Tokyo-økta (00–06 London) | 2508 | ρ +0.004 | -0.3 | 0.919 | -0.127 | +0.003 | +0.027 |  |
| Siste time før London-åpning | 3330 | ρ +0.001 | +0.4 | 0.919 | +0.072 | -0.010 | -0.038 |  |
| Gårsdagens NY første time | 3303 | ρ -0.006 | -0.1 | 0.919 | +0.068 | -0.016 | -0.051 |  |
| NQ vs ES siden US-stengning | 3258 | ρ -0.014 | -0.1 | 0.919 | -0.006 | -0.038 | +0.002 |  |
| Posisjon i overnight-range | 3323 | ρ -0.005 | -0.2 | 0.919 | +0.047 | -0.002 | -0.047 |  |
| Olje over natten | 3298 | ρ -0.018 | -0.4 | 0.919 | +0.052 | -0.042 | -0.044 |  |
| DXY over natten (2017+) | 2287 | ρ -0.021 | -0.2 | 0.919 | – | -0.043 | -0.003 |  |
| Månedsskifte | 620 | 51.5 % opp vs 51.2 % | +0.3 | 0.919 | 51 % | 54 % | 50 % |  |
| Opsjonsforfall-fredag | 150 | 54.0 % opp vs 51.1 % | +0.3 | 0.919 | 49 % | 57 % | 55 % |  |

## Ærlig walk-forward
Treff 49.7 % over 2557 dager (grunnrate 51.2 %).  
Dager med minst 6 pp: 63 dager, treff 41.3 % mot 49.3 % ved tilfeldighet, -5 ekstra treff, p = 0.9190.  
Dager med minst 10 pp: 12 dager, treff 50.0 % mot 48.9 % ved tilfeldighet, +0 ekstra treff, p = 0.5818.  
Placebo (8): treff 95-persentil 51.4 %, ekstra treff 6 pp: +0.0, 10 pp: +0.0.

| Hvor sikker | dager | treff | bp |
|---|---|---|---|
| under 3 pp | 2306 | 50.3 % | +0.2 |
| 3–6 pp | 188 | 45.2 % | -0.5 |
| 6–10 pp | 51 | 39.2 % | -4.8 |
| over 10 pp | 12 | 50.0 % | -0.3 |

Variabler valgt per år: 2017: us_rth_z; 2018: pre_ldn_z, us_rth_z; 2019: us_fh_z, thu_fri; 2020: –; 2021: –; 2022: –; 2023: –; 2024: –; 2025: –; 2026: –