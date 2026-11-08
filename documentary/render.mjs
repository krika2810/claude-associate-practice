// Render film.html frame-by-frame with Playwright and encode with ffmpeg.
// Usage:
//   node render.mjs <build_dir> preview t1 t2 ...   -> PNG stills
//   node render.mjs <build_dir> video [workers]      -> <build_dir>/the-delegation-files.mp4
import { createRequire } from "node:module";
const { chromium } = createRequire(import.meta.url)("playwright");
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const [build, mode, ...rest] = process.argv.slice(2);
const TL = JSON.parse(fs.readFileSync(path.join(build, "timeline.json"), "utf8"));
const FPS = 30;
const END = process.env.END ? Number(process.env.END) : TL.duration;
const total = Math.round(END * FPS);
const PAGE = process.env.PAGE || "film.html";
// static server so ES modules (three.js) load
import http from "node:http";
const MIME = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".json": "application/json" };
const server = http.createServer((req, res) => {
  const f = path.join(here, decodeURIComponent(new URL(req.url, "http://x").pathname));
  if (!f.startsWith(here) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "content-type": MIME[path.extname(f)] || "application/octet-stream" });
  fs.createReadStream(f).pipe(res);
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const BASE = `http://127.0.0.1:${server.address().port}/`;

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on("pageerror", (e) => console.error("pageerror:", e.message));
  await page.goto(BASE + PAGE);
  await page.waitForFunction(() => window.renderAt && window.setTimeline, null, { timeout: 60000 });
  await page.evaluate((tl) => window.setTimeline(tl), TL);
  await page.evaluate(() => window.fontsReady());
  return page;
}

function run(cmd, args, opts = {}) {
  return new Promise((res, rej) => {
    const p = spawn(cmd, args, { stdio: ["ignore", "inherit", "inherit"], ...opts });
    p.on("exit", (c) => (c === 0 ? res() : rej(new Error(`${cmd} exited ${c}`))));
  });
}

async function renderChunk(browser, from, to, file) {
  const page = await openPage(browser);
  const ff = spawn("ffmpeg", ["-v", "error", "-y", "-f", "image2pipe", "-framerate", String(FPS), "-c:v", "mjpeg", "-i", "-",
    "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-r", String(FPS), file], { stdio: ["pipe", "inherit", "inherit"] });
  const done = new Promise((res, rej) => ff.on("exit", (c) => (c === 0 ? res() : rej(new Error("ffmpeg " + c)))));
  for (let f = from; f < to; f++) {
    await page.evaluate(([t, n]) => window.renderAt(t, n), [f / FPS, f]);
    const buf = await page.screenshot({ type: "jpeg", quality: 93 });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
    if ((f - from) % 300 === 0) console.log(`  chunk ${path.basename(file)}: ${f - from}/${to - from}`);
  }
  ff.stdin.end();
  await done;
  await page.close();
}

const browser = await chromium.launch();
if (mode === "preview") {
  const page = await openPage(browser);
  for (const t of rest.map(Number)) {
    await page.evaluate(([t, n]) => window.renderAt(t, n), [t, Math.round(t * FPS)]);
    await page.screenshot({ path: path.join(build, `still_${t.toFixed(2)}.png`) });
  }
} else {
  const workers = Number(rest[0] || 4);
  const per = Math.ceil(total / workers);
  const files = [];
  const jobs = [];
  for (let w = 0; w < workers; w++) {
    const file = path.join(build, `chunk_${w}.mp4`);
    files.push(file);
    jobs.push(renderChunk(browser, w * per, Math.min(total, (w + 1) * per), file));
  }
  await Promise.all(jobs);
  fs.writeFileSync(path.join(build, "chunks.txt"), files.map((f) => `file '${f}'`).join("\n"));
  const outFile = path.join(build, process.env.OUT || "the-delegation-files.mp4");
  await run("ffmpeg", ["-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", path.join(build, "chunks.txt"),
    "-i", path.join(build, "soundtrack.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
    "-af", `afade=t=out:st=${Math.max(0, END - .5)}:d=0.5,loudnorm=I=-14:TP=-1.5:LRA=9`, "-ar", "48000", "-c:a", "aac", "-b:a", "192k",
    "-t", String(END), "-shortest", "-movflags", "+faststart", outFile]);
  console.log("wrote", outFile);
}
await browser.close();
server.close();
