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
| 09:00, 09:10, 09:20, 09:25 | 15:00–15:25 | Dagens bias beregnes og publiseres. Den siste kjøringen før åpning er den som logges. |
| ca. 11:00 og etter stengning | 17:00 / 22:30 | Fasit fylles inn og journalen oppdateres |

GitHub kan starte kjøringer noen minutter forsinket, derfor gjøres det flere forsøk før åpning. Siden viser alltid når den sist ble oppdatert. I ukene der USA og Norge bytter sommertid på ulike datoer, skjer alt én time tidligere norsk tid. Siden viser riktig klokkeslett.

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

## 4. Metode

### Mål
Fortegnet på NQ fra 09:30 til 10:30 ET. Det måles på QQQ, som følger Nasdaq-100 nesten 1:1 og ikke har kontrakt-rull. Bevegelsen regnes om til NQ-poeng med NQ-prisen.

### Variabler
Alle variablene er kjent før 09:30 ET. Det er testet i koden at endring av data etter 09:30 ikke påvirker dem.

| Gruppe | Variabler | Grunnlag |
|---|---|---|
| Pris rundt åpningen | Overnight-gap, premarket-trend (siste 1,5 t), gårsdagens dag og siste halvtime, første time siste 5/20 dager, 5-dagers avkastning, avstand til 50-dagers snitt | Liu & Tse (2017): overnight-avkastning predikerer de første 30 min *negativt*. Yu, Rentzler & Wolf: i NQ-futures henger nattens bevegelse mest sammen med reversering. Gao m.fl. (2018), Baltussen m.fl. (2021): intradag-momentum, sterkere på nyhets- og høyvolatilitetsdager. Heston, Korajczyk & Sadka (2010): samme tidspunkt gjentar seg over dager. |
| Relativ styrke | NQ vs ES, halvledere vs NQ | ES har mest volum og prisoppdagelse |
| Makro (kryssmarkeder) | 10-års Treasury-future, DXY, USD/JPY og bitcoin overnight; 10-års rente og high yield-spread siste 5 dager | Rente/aksje-kobling, finansielle forhold, carry/risk-off |
| Volatilitet | VIX-nivå (z-score), VIX/VIX3M, VIX-endring, gap × høy VIX | Momentum og reversering er sterkere ved høy VIX |
| Kalender | Mandag, månedsskifte, opsjonsforfall, FOMC-dag, FOMC × høy VIX, megacap-earnings over natten | Lucca & Moench (2015), med forbehold om at før-FOMC-driften svekket seg etter 2015 (Kurov m.fl.), men har levd videre i perioder med høy VIX (Martello & Ribeiro). Turn-of-month-effekten. |

Overskrifter og økonomisk kalender vises som kontekst, men inngår ikke i modellen. Det finnes ingen gratis historikk for forventet og faktisk utfall, så de kan ikke testes.

### Modell
- Logistisk regresjon med sterk L2-krymping. Krympingen velges med tidsserie-kryssvalidering på treningsdataene.
- **Walk-forward.** Modellen trenes på dagene før og predikerer de neste 20, og så rulles vinduet videre. Alle tall i «Modellkvalitet» kommer fra dager modellen ikke hadde sett.
- **Kalibrering.** Ut-av-utvalg-prediksjonene bestemmer en tillitsfaktor. Har modellen ikke slått gjetting, går faktoren mot 0, og dagens sannsynlighet krympes mot grunnraten. Programmet kan altså ikke vise deg en sterk bias den ikke har dekning for.

## 5. Viktige begrensninger

1. **Lite historikk.** Yahoo gir bare ~2 år med timesdata gratis, altså ~500 handelsdager. Det holder til å avsløre et middels sterkt signal, men ikke et svakt et.
2. **Forvent beskjedne tall.** En ærlig treffrate for første time ligger typisk på 52–58 %. Lover noe 70 %, er det nesten alltid overtilpasset.
3. **Forsinkede data.** Yahoo sine futures-priser kan være forsinket ~10 min. Derfor bør programmet kjøres 15:20–15:29.
4. **Journalen er fasiten.** Backtesten er et estimat. Først når journalen har ~100 dager med bias, vet du om dette fungerer i praksis.
5. **Kilder kan endre seg.** Feiler en kilde, vises det under «Merknader». Variabelen settes da til nøytral verdi, og programmet kjører videre.
6. **FOMC-datoer for 2027** er foreløpige. De ligger i `config.py` og kan oppdateres der.

## 6. Filer

```
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
