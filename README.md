# NQ Bias

Et program som før NY-åpning gir en sannsynlig retning for **NQ i første time** (09:30–10:30 ET = 15:30–16:30 norsk tid), med argumentene bak, og som måler seg selv ærlig.

Det svarer på ett spørsmål: *Er NQ høyere kl. 10:30 ET enn kl. 09:30 ET i dag?* Svaret er en sannsynlighet og en av tre merkelapper: BULLISH, BEARISH eller NØYTRAL.

---

## 1. Nettsiden (hovedbruken)

**Adresse:** https://21matso.github.io/nq-bias/

Legg den til på hjemskjermen på telefonen. På iPhone: åpne siden i Safari → Del-knappen → *Legg til på Hjem-skjerm*. På Android: Chrome → ⋮ → *Legg til på startskjermen*.

Siden oppdaterer seg selv. Du trenger ikke kjøre noe, og ingen PC må stå på. GitHub kjører programmet automatisk hver handelsdag:

| Tid (New York) | Vanligvis norsk tid | Hva skjer |
|---|---|---|
| ca. 08:20 | 14:20 | Modellen trenes på nytt med gårsdagens data |
| 09:00, 09:12, 09:22 | 15:00, 15:12, 15:22 | Dagens bias beregnes og publiseres. Den siste kjøringen før åpning er den som logges. |
| ca. 11:00 og etter stengning | 17:00 / 22:30 | Fasit fylles inn og journalen oppdateres |

GitHub sin timeplan er upresis og hopper iblant over kjøringer. Derfor starter én kjøring ca. 08:40 ET og venter selv til hvert klokkeslett, med reservekjøringer hvis den ikke starter. Siden viser alltid når den sist ble oppdatert. I ukene der USA og Norge bytter sommertid på ulike datoer, skjer alt én time tidligere norsk tid. Siden viser riktig klokkeslett.

**Hvis noe feiler**, står det øverst på siden, og GitHub sender deg en e-post. Du ser alle kjøringene under fanen *Actions* i repoet. Der kan du også starte en kjøring manuelt: *NQ Bias* → *Run workflow*.

**Journalen** ligger i `data/journal.csv` i repoet. Hver bias lagres som en commit med tidsstempel *før* åpning. Git-historikken er dermed et bevis på at biasen faktisk ble satt på forhånd.

## 2. Lokalt på egen PC (valgfritt)

1. Last ned repoet (grønn *Code*-knapp → *Download ZIP*) og pakk det ut.
2. Dobbeltklikk på startfilen:
   - **Windows:** `START NQ BIAS (Windows).bat`. Hvis Windows viser «Windows beskyttet PC-en», trykk *Mer informasjon* → *Kjør likevel*.
   - **Mac:** `START NQ BIAS (Mac).command`. Første gang: høyreklikk → *Åpne* → *Åpne*.
3. Har du ikke Python, åpner startfilen python.org. Installer derfra (Windows: huk av for **«Add python.exe to PATH»**) og dobbeltklikk igjen. Resten installeres automatisk, og så kommer en meny med *Dagens bias*, *Backtest*, *Journal* og *Spill av en tidligere dag*.

Den lokale versjonen har sin egen journal på PC-en, adskilt fra nettsidens.

**For de som vil bruke terminalen direkte** (Mac: `.venv/bin/python` i stedet for `python`):

| Kommando | Hva den gjør |
|---|---|
| `python nqbias.py` | Dagens bias |
| `python nqbias.py backtest` | Full walk-forward-test og analyse av hver variabel |
| `python nqbias.py stats` | Treffrate i journalen (sanntidstesten) |
| `python nqbias.py update` | Fyll inn fasit i journalen manuelt |
| `python nqbias.py web` | Det GitHub kjører: oppdaterer `docs/data.json` for nettsiden |
| `python nqbias.py --asof "2026-11-04 09:20"` | Spill av en tidligere dag (New York-tid) |
| `--retrain` | Tving ny trening |
| `--no-news` | Hopp over overskrifter |

## 3. Slik leser du skjermen

- **Dagens bias.** Sannsynligheten for at NQ er opp etter første time. Under står det hvor ofte modellen historisk har truffet når den var like sikker som i dag. Det er det tallet du skal stole på, ikke selve prosenten.
- **Klasser.** Nøytral betyr under 3 prosentpoeng fra 50 %. Svak er 3–8 pp. Tydelig er over 8 pp.
- **Argumenter for BULLISH / BEARISH.** Hver variabel og hvor mange prosentpoeng den flytter sannsynligheten i dag, med begrunnelse og forskningskilde.
- **Markedsbilde.** Hvordan NQ, ES, renter, dollar, yen, bitcoin, olje, gull og Europa har beveget seg siden gårsdagens stengning.
- **Makro-regime.** Rentenivå, rentekurve, realrente, kredittspread, Fed funds og finansielle forhold fra FRED, pluss VIX og terminstrukturen.
- **Dagens hendelser.** Viktige USD-tall i dag. Tall som kommer *inne i* første time (typisk 10:00 ET, for eksempel ISM) markeres, fordi de kan snu alt.
- **Modellkvalitet.** En ærlig vurdering av om modellen har slått gjetting på dager den aldri har sett.

## 4. Metode (nettsiden, modell v2)

### Mål
Fortegnet på NQ fra 09:30 til 10:30 ET: er NQ høyere etter første time enn ved åpning?

### Data
- **Dukascopy**, gratis: Nasdaq 100 og S&P 500 i 5-minutters oppløsning fra september 2011, rundt 3700 handelsdager, og USD/JPY, gull, olje, US T-bond og DXY i timesoppløsning. Lastes ned av `research/fetch.js`. Ferske data hentes før hver kjøring; Dukascopy ligger bare noen minutter bak.
- **Yahoo**, daglig: VIX, VIX3M, renter og HYG/IEF. Også earnings-datoer, markedsbildet på siden og fasiten i journalen.
- Sjekket mot Yahoo NQ=F: korrelasjonen i første time er 1,000.

### Hypoteser (research/analyze.py)
Over 40 hypoteser fra forskning og praksis er testet hver for seg: gap og overnight-økter, 08:30-reaksjon, gårsdagen, tidsmønstre, NQ mot ES, kryssmarkeder, VIX, renter, kreditt, kalender, og betingede varianter som gap på nyhetsdager, store gap og gap torsdag/fredag. For hver hypotese beregnes:
- korrelasjon og Newey-West-t
- treffrate
- stabilitet i 2011–15, 2016–20 og 2021–26
- korreksjon for multippel testing (Benjamini–Hochberg)

Resultatene står i `research/RESULTS.md` og oppdateres hver kveld.

### Modell
- Variablene velges med en fast regel: q under 0,10 og samme fortegn i alle tre deler av perioden. Utvalget gir logistisk regresjon med krymping.
- **Ærlig test:** walk-forward der både variabelutvalget og treningen for hvert år bare bruker årene før. Treffraten på siden kommer derfra.
- **Placebo:** hele prosedyren kjøres på tilfeldig stokkede utfall. Det viser hvilken treffrate ren flaks gir.
- Under 6 prosentpoeng fra 50 % vises NØYTRAL. Der har modellen ikke hatt noen fordel.
- **Lignende dager:** for hver betingelse i dag vises hvor ofte NQ har steget i samme situasjon siden 2011.

Den lokale terminalversjonen (`nqbias.py run`) bruker fortsatt den første modellen (v1, 2 år Yahoo-data).

## 5. Viktige begrensninger

1. **Små marginer.** Treffraten ligger i beste fall noen prosentpoeng over 50 % i snitt, og er høyere bare på dagene modellen er mest sikker. Det er et filter, ikke en fasit.
2. **Marked endrer seg.** Effekter som var sterke i 2011–15 kan svekkes. Utvalget gjøres på nytt hver dag, og den rullerende treffraten på siden viser om fordelen holder.
3. **Kilder kan endre seg.** Dukascopy kan stramme inn tilgangen. Er dataene forsinket, brukes Yahoo for dagens rad, og det står under «Merknader».
4. **Journalen er fasiten.** Den måler modellen i sanntid, fremover i tid.

## 6. Filer

```
research/     15 års historikk, hypotesetester (RESULTS.md) og nedlasting
bias2.py      modell v2 (brukes av nettsiden)
docs/         nettsiden (index.html viser data.json)
.github/      GitHub Actions: når programmet kjører automatisk
web.py        lager data.json for nettsiden
nqbias.py     hovedprogram (kommandoer)
config.py     innstillinger, tickere, FOMC-datoer, terskler
data.py       henting fra Yahoo, FRED, kalender, RSS (med cache)
features.py   bygger variablene (uten look-ahead)
model.py      modell, walk-forward, kalibrering
report.py     visning i terminalen
journal.py    logging og forward-test
data/         cache, lagret modell, journal.csv, backtest_predictions.csv
```

Dette er et analyseverktøy, ikke finansiell rådgivning.
