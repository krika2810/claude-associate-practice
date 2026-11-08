"""Build the voiceover, original score, SFX and timeline for The Delegation Files.

Usage: python3 make_audio.py <models_dir> <out_dir>
Writes <out_dir>/timeline.json and <out_dir>/soundtrack.wav (48 kHz stereo).
"""
import json, os, sys, hashlib
import numpy as np
import soundfile as sf
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS, OUT = sys.argv[1], sys.argv[2]
SR = 48000
NARRATOR_SPEED = 1.08
VILLAIN_SPEED = 0.95
os.makedirs(os.path.join(OUT, "tts"), exist_ok=True)
script = json.load(open(os.path.join(HERE, "script.json")))
rng = np.random.default_rng(7)

# ---------------------------------------------------------------- voices
_kokoro = None
def tts(text, voice, speed):
    global _kokoro
    key = hashlib.sha1(f"{text}|{voice}|{speed}".encode()).hexdigest()[:16]
    path = os.path.join(OUT, "tts", key + ".wav")
    if not os.path.exists(path):
        if _kokoro is None:
            from kokoro_onnx import Kokoro
            _kokoro = Kokoro(os.path.join(MODELS, "kokoro-v1.0.onnx"), os.path.join(MODELS, "voices-v1.0.bin"))
        lang = "en-gb" if voice.startswith("b") else "en-us"
        s, sr = _kokoro.create(text, voice=voice, speed=speed, lang=lang)
        s = signal.resample_poly(s, SR // 1000, sr // 1000)
        sf.write(path, s, SR)
    s, _ = sf.read(path)
    return trim(s)

def trim(s, thr=0.01):
    idx = np.where(np.abs(s) > thr)[0]
    if len(idx) == 0:
        return s
    a, b = max(0, idx[0] - int(0.02 * SR)), min(len(s), idx[-1] + int(0.08 * SR))
    return s[a:b]

def norm(s, peak=0.9):
    m = np.max(np.abs(s)) or 1
    return s / m * peak

def villain_fx(s):
    """Anonymised-witness treatment: pitch down, band-limit, light grit + room."""
    out = pitch_down(s, 0.84)                       # ~3 semitones, same duration
    b, a = signal.butter(2, [180 / (SR / 2), 4200 / (SR / 2)], "band")
    out = signal.lfilter(b, a, out)
    out = np.tanh(out * 2.2) / np.tanh(2.2)
    out = out + 0.18 * reverb(out, 0.35)
    return norm(out, 0.85)

def pitch_down(s, factor):
    """Pitch-shift with ffmpeg's rubberband filter (formant-preserving off = darker)."""
    import subprocess, tempfile
    with tempfile.TemporaryDirectory() as d:
        a, b = os.path.join(d, "a.wav"), os.path.join(d, "b.wav")
        sf.write(a, s, SR)
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a, "-af",
                            f"rubberband=pitch={factor}:pitchq=quality", b])
        if r.returncode != 0:
            return wsola(signal.resample(s, int(len(s) / factor)), len(s))
        out, _ = sf.read(b)
    return out

def wsola(x, target_len, win=1024, hop=256):
    """Overlap-add time stretch of x to target_len samples (keeps pitch)."""
    ratio = len(x) / target_len
    w = np.hanning(win)
    out = np.zeros(target_len + win)
    wsum = np.zeros(target_len + win)
    prev = None
    for o in range(0, target_len, hop):
        i = int(o * ratio)
        # search small window for best alignment with previous frame tail
        best = i
        if prev is not None:
            lo, hi = max(0, i - 128), min(len(x) - win, i + 128)
            if hi > lo:
                cands = range(lo, hi, 8)
                scores = [np.dot(x[c:c + hop], prev) for c in cands]
                best = list(cands)[int(np.argmax(scores))]
        if best + win > len(x):
            break
        seg = x[best:best + win] * w
        out[o:o + win] += seg
        wsum[o:o + win] += w
        prev = x[best + hop:best + 2 * hop] if best + 2 * hop <= len(x) else None
    wsum[wsum < 1e-3] = 1
    return (out / wsum)[:target_len]

def reverb(x, seconds):
    n = int(seconds * SR)
    ir = rng.standard_normal(n) * np.exp(-np.linspace(0, 6, n))
    return signal.fftconvolve(x, ir)[: len(x)] / 30

# ---------------------------------------------------------------- timeline
lines_audio = []   # (start_sec, samples, kind)
timeline = {"scenes": [], "captions": []}
t = 0.0
GAP = 0.45

def place(line, at):
    if line["who"] == "N":
        s = norm(tts(line["text"], script["narratorVoice"], NARRATOR_SPEED), 0.95)
    else:
        s = villain_fx(tts(line["text"], line["voice"], VILLAIN_SPEED))
    lines_audio.append((at, s, line["who"]))
    d = len(s) / SR
    timeline["captions"].append({"start": round(at, 3), "end": round(at + d, 3), "who": line["who"],
                                 "text": line.get("caption", line["text"])})
    return d

for sc in script["scenes"]:
    start = t
    marks = {}
    if sc["type"] == "cold":
        t += 2.2
        for i, ln in enumerate(sc["lines"]):
            marks[f"l{i}"] = t
            t += place(ln, t) + 0.6
        t += 0.3
    elif sc["type"] == "title":
        marks["slam"] = t + 0.25
        t += 1.6
        marks["l0"] = t
        t += place(sc["lines"][0], t) + 0.8
    elif sc["type"] == "case":
        marks["stamp"] = t + 0.05
        t += 0.7
        marks["villain"] = t
        t += place(sc["lines"][0], t) + 0.35
        marks["verdict"] = t
        t += 0.25
        marks["narr"] = t
        t += place(sc["lines"][1], t) + 0.45
    elif sc["type"] == "outro":
        t += 0.8
        marks["l0"] = t
        t += place(sc["lines"][0], t) + 0.9
        marks["end"] = t
        t += 3.8
    timeline["scenes"].append({**{k: v for k, v in sc.items() if k != "lines"},
                               "start": round(start, 3), "end": round(t, 3),
                               "marks": {k: round(v, 3) for k, v in marks.items()}})

TOTAL = t
timeline["duration"] = round(TOTAL, 3)
timeline["title"] = script["title"]
timeline["credit"] = script["credit"]
print(f"total duration: {TOTAL:.2f}s")
for s in timeline["scenes"]:
    print(f"  {s['id']:6s} {s['start']:7.2f} -> {s['end']:7.2f}  ({s['end'] - s['start']:.2f}s)")
if "--measure" in sys.argv:
    sys.exit(0)

# ---------------------------------------------------------------- score
N = int((TOTAL + 1) * SR)
tt = np.arange(N) / SR
voice = np.zeros(N)
for at, s, who in lines_audio:
    i = int(at * SR)
    voice[i:i + len(s)] += s * (1.0 if who == "N" else 0.95)

def lp(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2))
    return signal.lfilter(b, a, x)

def hp(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), "high")
    return signal.lfilter(b, a, x)

def env_ar(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] *= np.linspace(1, 0, nr)
    return e

def saw(f, t):
    return 2 * ((t * f) % 1) - 1

scene_by_id = {s["id"]: s for s in timeline["scenes"]}
cold_end = scene_by_id["cold"]["end"]
outro = scene_by_id["outro"]

# drone bed: detuned saws on D (36.7 Hz root + fifth), filtered, slowly breathing
drone = sum(saw(f * (1 + d), tt) for f in (73.42, 110.0) for d in (-0.003, 0.0, 0.004))
drone = lp(drone, 380) * 0.10
drone += np.sin(2 * np.pi * 36.71 * tt) * 0.16
breathe = 0.75 + 0.25 * np.sin(2 * np.pi * tt / 7.0)
drone *= breathe
# high eerie pad (enters after cold open)
pad = sum(np.sin(2 * np.pi * f * tt + 0.3 * np.sin(2 * np.pi * 0.2 * tt)) for f in (293.66, 349.23, 440.0))
pad = pad * 0.018 * np.clip((tt - cold_end) / 6, 0, 1)
music = drone + pad
# global fade in / out
music *= np.clip(tt / 2.0, 0, 1) * np.clip((outro["end"] - tt) / 2.5, 0, 1)

# pulse: low heartbeat-like ticks through the cases (every 0.857 s = 70 bpm)
pulse = np.zeros(N)
beat = 60 / 70
k = np.exp(-np.linspace(0, 30, int(0.12 * SR))) * np.sin(2 * np.pi * 55 * np.arange(int(0.12 * SR)) / SR)
x = cold_end
while x < outro["start"]:
    i = int(x * SR)
    pulse[i:i + len(k)] += k * 0.22
    x += beat
music += pulse

sfx = np.zeros(N)
def add(at, s, g=1.0):
    i = int(at * SR)
    j = min(N, i + len(s))
    sfx[i:j] += s[: j - i] * g

# clock ticks in cold open
tick = hp(rng.standard_normal(int(0.03 * SR)), 2500) * np.exp(-np.linspace(0, 12, int(0.03 * SR)))
x = 0.3
while x < cold_end - 0.5:
    add(x, tick, 0.25)
    x += 1.0

def braam(dur=2.8):
    n = int(dur * SR)
    tl = np.arange(n) / SR
    s = sum(saw(f, tl) for f in (36.71, 36.9, 73.42, 55.0))
    s = lp(s, 600, 4) * np.exp(-tl * 1.4)
    s += np.sin(2 * np.pi * 30 * tl) * np.exp(-tl * 2) * 1.2
    return np.tanh(s * 1.5) * 0.6

def impact():
    n = int(1.2 * SR)
    tl = np.arange(n) / SR
    body = np.sin(2 * np.pi * (60 * np.exp(-tl * 6) + 32) * tl) * np.exp(-tl * 5)
    crack = hp(rng.standard_normal(n), 1500) * np.exp(-tl * 40) * 0.5
    return (body + crack) * 0.7

def whoosh(dur=0.7, rising=True):
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    seg = 512
    for i in range(0, n - seg, seg):
        p = i / n
        fc = 300 + 5000 * (p if rising else 1 - p)
        b, a = signal.butter(2, [fc / (SR / 2), min(0.99, fc * 1.6 / (SR / 2))], "band")
        out[i:i + seg] = signal.lfilter(b, a, noise[i:i + seg])
    e = np.sin(np.linspace(0, np.pi, n)) ** 2
    return out * e * 0.5

def stamp_hit():
    n = int(0.35 * SR)
    tl = np.arange(n) / SR
    thud = np.sin(2 * np.pi * 90 * tl) * np.exp(-tl * 25)
    slap = lp(rng.standard_normal(n), 2500) * np.exp(-tl * 50)
    return (thud + 0.6 * slap) * 0.8

def riser(dur=1.6):
    n = int(dur * SR)
    tl = np.arange(n) / SR
    f = 200 * (8 ** (tl / dur))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.15
    return (tone + whoosh(dur) * 0.8) * (tl / dur) ** 2

title = scene_by_id["title"]
add(title["marks"]["slam"] - 1.6, riser(1.6), 0.8)
add(title["marks"]["slam"], braam(3.5), 1.0)
add(title["marks"]["slam"], impact(), 0.8)
for s in timeline["scenes"]:
    if s["type"] == "case":
        add(s["start"] - 0.35, whoosh(0.5), 0.6)
        add(s["marks"]["stamp"], impact(), 0.55)
        add(s["marks"]["verdict"], stamp_hit(), 0.7)
        add(s["marks"]["verdict"], whoosh(0.35, False), 0.25)
# final resolve: warm major chord under the last line
oe = outro["marks"]["l0"]
n = int((outro["end"] - oe) * SR)
tl = np.arange(n) / SR
chord = sum(np.sin(2 * np.pi * f * tl) for f in (146.83, 185.0, 220.0, 293.66)) * 0.05
chord *= env_ar(n, 2.0, 2.5)
add(oe, chord)
add(outro["marks"]["end"], braam(3.0), 0.6)

# duck music+sfx under voice (simple envelope follower)
venv = np.abs(voice)
venv = signal.lfilter([1 - 0.9995], [1, -0.9995], venv)
venv = np.convolve(venv, np.ones(2400) / 2400, mode="same")
duck = 1 - 0.55 * np.clip(venv * 8, 0, 1)
bed = (music * 0.9 + sfx * 0.8) * duck

mix_l = voice + bed
mix_r = voice + bed
# subtle stereo width on the pad/sfx
mix_r = mix_r + 0.02 * np.roll(sfx, 240)
mix = np.stack([mix_l, mix_r], 1)
mix = mix / np.max(np.abs(mix)) * 0.95
sf.write(os.path.join(OUT, "soundtrack.wav"), mix.astype(np.float32), SR)
json.dump(timeline, open(os.path.join(OUT, "timeline.json"), "w"), indent=1)
print("wrote", os.path.join(OUT, "soundtrack.wav"))
