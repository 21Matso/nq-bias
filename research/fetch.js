// Laster ned historikk fra Dukascopy (gratis) og lagrer ett år per fil.
// Fullførte år hoppes over neste gang, så nedlastingen kan fortsette over flere kjøringer.
const { getHistoricalRates } = require("dukascopy-node");
const fs = require("fs");
const path = require("path");
const zlib = require("zlib");

const OUT = path.join(__dirname, "data");
fs.mkdirSync(OUT, { recursive: true });
const NOW = new Date();
const THIS_YEAR = NOW.getUTCFullYear();
const DEADLINE = Date.now() + Number(process.env.FETCH_MINUTES || 80) * 60000;
const ONLY_PROBE = process.env.PROBE === "1";

const JOBS = [
  { inst: "usatechidxusd", tf: "m5", start: 2011 },  // Nasdaq 100
  { inst: "usa500idxusd", tf: "m5", start: 2011 },   // S&P 500
  { inst: "usdjpy", tf: "h1", start: 2011 },
  { inst: "xauusd", tf: "h1", start: 2011 },
  { inst: "lightcmdusd", tf: "h1", start: 2011 },
  { inst: "ustbondtrusd", tf: "h1", start: 2018 },   // US T-bond
  { inst: "dollaridxusd", tf: "h1", start: 2017 },   // DXY
];

async function fetchYear(job, year) {
  const from = new Date(Date.UTC(year, 0, 1));
  const to = year === THIS_YEAR ? NOW : new Date(Date.UTC(year + 1, 0, 1));
  const rows = await getHistoricalRates({
    instrument: job.inst, dates: { from, to }, timeframe: job.tf, priceType: "bid",
    volumes: false, format: "array", batchSize: 15, pauseBetweenBatchesMs: 400,
    retryCount: 3, pauseBetweenRetriesMs: 1500, retryOnEmpty: false, failAfterRetryCount: false,
  });
  return rows;
}

(async () => {
  if (process.env.RECENT_DAYS) {
    // Kun de siste dagene, til dagens live-beregning (lagres ikke i repoet)
    const from = new Date(Date.now() - Number(process.env.RECENT_DAYS) * 86400000);
    for (const job of JOBS) {
      const t0 = Date.now();
      try {
        const rows = await getHistoricalRates({
          instrument: job.inst, dates: { from, to: new Date() }, timeframe: job.tf, priceType: "bid",
          volumes: false, format: "array", batchSize: 15, pauseBetweenBatchesMs: 200,
          retryCount: 2, pauseBetweenRetriesMs: 1000, failAfterRetryCount: false,
        });
        const csv = "t,o,h,l,c\n" + rows.map(r => r.slice(0, 5).join(",")).join("\n");
        fs.writeFileSync(path.join(OUT, `${job.inst}_${job.tf}_recent.csv.gz`), zlib.gzipSync(csv));
        const last = rows.length ? new Date(rows[rows.length - 1][0]).toISOString() : "-";
        console.log(`recent ${job.inst}: ${rows.length} rader, siste ${last} (${((Date.now() - t0) / 1000).toFixed(0)} s)`);
      } catch (e) {
        console.log(`FEIL recent ${job.inst}: ${e && e.name}: ${e && e.message}`);
      }
    }
    return;
  }
  if (ONLY_PROBE) {
    const r = await getHistoricalRates({ instrument: "usatechidxusd", dates: { from: new Date("2015-03-02"), to: new Date("2015-03-04") }, timeframe: "m5", format: "array" });
    console.log("PROBE rows:", r.length, JSON.stringify(r.slice(0, 2)));
    return;
  }
  for (const job of JOBS) {
    for (let y = job.start; y <= THIS_YEAR; y++) {
      const f = path.join(OUT, `${job.inst}_${job.tf}_${y}.csv.gz`);
      if (fs.existsSync(f) && y < THIS_YEAR) continue;
      if (Date.now() > DEADLINE) { console.log("Tidsgrense nådd – fortsetter neste kjøring"); return; }
      const t0 = Date.now();
      try {
        const rows = await fetchYear(job, y);
        if (!rows.length) { console.log(`${job.inst} ${y}: 0 rader`); continue; }
        const csv = "t,o,h,l,c\n" + rows.map(r => r.slice(0, 5).join(",")).join("\n");
        fs.writeFileSync(f, zlib.gzipSync(csv));
        console.log(`${job.inst} ${job.tf} ${y}: ${rows.length} rader (${((Date.now() - t0) / 1000).toFixed(0)} s)`);
      } catch (e) {
        console.log(`FEIL ${job.inst} ${y}: ${e && e.name}: ${e && e.message}`);
        if (e && /Waf|AccessDenied/.test(e.name || "")) { console.log("Dukascopy blokkerer – stopper"); return; }
      }
    }
  }
})();
