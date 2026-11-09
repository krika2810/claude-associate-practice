"""Voices, original score, SFX and timeline for the story cut of The Delegation Files.

Usage: python3 make_story.py <models_dir> <out_dir> [--measure]
Writes <out_dir>/story_timeline.json and <out_dir>/story_soundtrack.wav (48 kHz stereo).
"""
import json, os, sys, hashlib
import numpy as np
import soundfile as sf
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS, OUT = sys.argv[1], sys.argv[2]
SR = 48000
GAP = 0.35
os.makedirs(os.path.join(OUT, "tts"), exist_ok=True)
story = json.load(open(os.path.join(HERE, "story.json")))
cast = story["cast"]
rng = np.random.default_rng(11)

_k = None
def tts(text, voice, speed):
    global _k
    key = hashlib.sha1(f"{text}|{voice}|{speed}".encode()).hexdigest()[:16]
    path = os.path.join(OUT, "tts", key + ".wav")
    if not os.path.exists(path):
        if _k is None:
            from kokoro_onnx import Kokoro
            _k = Kokoro(os.path.join(MODELS, "kokoro-v1.0.onnx"), os.path.join(MODELS, "voices-v1.0.bin"))
        s, sr = _k.create(text, voice=voice, speed=speed, lang="en-gb" if voice.startswith("b") else "en-us")
        sf.write(path, signal.resample_poly(s, SR // 1000, sr // 1000), SR)
    s, _ = sf.read(path)
    idx = np.where(np.abs(s) > 0.01)[0]
    s = s[max(0, idx[0] - 960): idx[-1] + 3840]
    return s / (np.max(np.abs(s)) or 1) * 0.9

def lp(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2)); return signal.lfilter(b, a, x)
def hp(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), "high"); return signal.lfilter(b, a, x)

def voice_fx(s):
    """Interview-mic colour: gentle high-pass, a touch of room."""
    s = hp(s, 90)
    n = int(0.18 * SR)
    ir = rng.standard_normal(n) * np.exp(-np.linspace(0, 9, n))
    room = signal.fftconvolve(s, ir)[: len(s)]
    s = s + 0.035 * room / (np.max(np.abs(room)) or 1)
    return s / (np.max(np.abs(s)) or 1) * 0.9

# ---------------------------------------------------------------- timeline
TL = {"title": story["title"], "credit": story["credit"], "cast": cast, "beats": [], "captions": [], "parts": []}
clips = []
t = 0.0
for b in story["beats"]:
    start = t
    if "part" in b:
        TL["parts"].append({"part": b["part"], "start": round(t, 3)})
    t += b.get("pre", 0.0)
    for ln in b.get("lines", []):
        c = cast[ln["who"]]
        s = voice_fx(tts(ln["text"], c["voice"], c["speed"]))
        d = len(s) / SR
        clips.append((t, s))
        hop = SR // 30
        frames = [s[k * hop:(k + 1) * hop] for k in range(int(np.ceil(len(s) / hop)))]
        rms = np.array([np.sqrt(np.mean(f ** 2)) if len(f) else 0 for f in frames])
        hpf = hp(s, 2000)
        his = np.array([np.sqrt(np.mean(hpf[k * hop:(k + 1) * hop] ** 2)) if len(frames[k]) else 0 for k in range(len(frames))])
        ref = np.percentile(rms, 95) or 1
        env = np.clip(rms / ref, 0, 1) ** 0.8
        hi = np.clip(his / (rms + 1e-6) * 2.2, 0, 1)
        TL["captions"].append({"start": round(t, 3), "end": round(t + d, 3), "who": ln["who"], "text": ln.get("caption", ln["text"]),
                               "env": [round(float(x), 2) for x in env], "hi": [round(float(x), 2) for x in hi]})
        t += d + GAP
    if b.get("lines"):
        t -= GAP
    t += b.get("post", 0.4 if b.get("lines") else 0.0)
    t = max(t, start + b.get("dur", 0.0))
    beat = {k: v for k, v in b.items() if k not in ("lines", "pre", "post", "dur")}
    beat["start"], beat["end"] = round(start, 3), round(t, 3)
    beat["speakers"] = [ln["who"] for ln in b.get("lines", [])]
    for ins in beat.get("inserts", []):
        ins["start"] = round(start + (t - start) * ins["from"], 3)
        ins["end"] = round(start + (t - start) * ins["to"], 3)
    TL["beats"].append(beat)
TOTAL = t
TL["duration"] = round(TOTAL, 3)
print(f"total duration: {TOTAL:.2f}s")
for b in TL["beats"]:
    print(f"  {b['shot']:18s} {b['start']:7.2f} -> {b['end']:7.2f}")
if "--measure" in sys.argv:
    sys.exit(0)

# ---------------------------------------------------------------- score
N = int((TOTAL + 1) * SR)
tt = np.arange(N) / SR
voice = np.zeros(N)
for at, s in clips:
    i = int(at * SR); voice[i:i + len(s)] += s

part_at = {p["part"]: p["start"] for p in TL["parts"]}
order = [p["part"] for p in TL["parts"]]
def span(name):
    i = order.index(name)
    return part_at[name], (part_at[order[i + 1]] if i + 1 < len(order) else TOTAL)
title_beat = next(b for b in TL["beats"] if b["shot"] == "title")

def env(a, b, fade_in=1.0, fade_out=1.0):
    e = np.clip((tt - a) / fade_in, 0, 1) * np.clip((b - tt) / fade_out, 0, 1)
    return e

def saw(f, x): return 2 * ((x * f) % 1) - 1
def note_hz(n): return 440 * 2 ** ((n - 69) / 12)

music = np.zeros(N)
sfx = np.zeros(N)
def add(buf, at, s, g=1.0):
    i = int(at * SR); j = min(N, i + len(s))
    if j > i: buf[i:j] += s[: j - i] * g

def pluck(freq, dur=1.6, bright=1.0):
    n = int(dur * SR); x = np.arange(n) / SR
    s = sum((1 / k) * np.sin(2 * np.pi * freq * k * x) * np.exp(-x * (2.2 + k * 1.3 / bright)) for k in range(1, 7))
    s *= np.minimum(1, x / 0.004)
    return s * 0.5

def pad(chord, a, b, gain):
    seg = slice(int(a * SR), int(b * SR))
    x = tt[seg]
    s = sum(saw(note_hz(n) * (1 + d), x) for n in chord for d in (-0.002, 0.002))
    s = lp(s, 900) * gain
    music[seg] += s * np.clip((x - a) / 1.5, 0, 1) * np.clip((b - x) / 1.5, 0, 1)

# low drone across everything, breathing
drone = (np.sin(2 * np.pi * 36.71 * tt) * 0.13 + lp(saw(73.42, tt) + saw(73.6, tt), 260) * 0.05)
drone *= 0.75 + 0.25 * np.sin(2 * np.pi * tt / 8)
music += drone * env(0, TOTAL, 2.5, 3.0)

# cold open: heartbeat + ticking tension
c0, c1 = span("cold")
beat_k = np.exp(-np.linspace(0, 28, int(0.14 * SR))) * np.sin(2 * np.pi * 52 * np.arange(int(0.14 * SR)) / SR)
x = 1.2
while x < title_beat["start"] - 0.3:
    add(music, x, beat_k, 0.35); add(music, x + 0.28, beat_k, 0.22); x += 1.05
tick = hp(rng.standard_normal(int(0.025 * SR)), 3000) * np.exp(-np.linspace(0, 10, int(0.025 * SR)))
x = 0.5
while x < title_beat["start"] - 0.5:
    add(sfx, x, tick, 0.12); x += 0.5

# phone buzz: bursts on the nightstand
def buzz(dur=0.5):
    n = int(dur * SR); x = np.arange(n) / SR
    s = np.sign(np.sin(2 * np.pi * 165 * x)) * (0.6 + 0.4 * np.sin(2 * np.pi * 31 * x))
    s = lp(s, 900, 4) + 0.3 * lp(rng.standard_normal(n), 400)
    return s * np.minimum(1, x / 0.02) * np.minimum(1, (dur - x) / 0.03) * 0.5
bed = TL["beats"][0]
ring = [bed["start"] + 0.8, bed["start"] + 1.6]
TL["ring"] = [round(r, 3) for r in ring]
for r in ring:
    add(sfx, r, buzz(0.5), 0.9)
ins = TL["beats"][1]
add(sfx, ins["start"] + 0.2, buzz(0.5), 0.7); add(sfx, ins["start"] + 1.05, buzz(0.5), 0.7)
TL["ring2"] = [round(ins["start"] + 0.2, 3), round(ins["start"] + 1.05, 3)]

# title: reverse swell into a deep hit, then a held chord with a few high notes
def swell(dur):
    n = int(dur * SR); x = np.arange(n) / SR
    s = lp(rng.standard_normal(n), 2500) * (x / dur) ** 3
    return s * 0.35
def hit():
    n = int(3.5 * SR); x = np.arange(n) / SR
    body = np.sin(2 * np.pi * (55 * np.exp(-x * 4) + 30) * x) * np.exp(-x * 1.6)
    s = lp(sum(saw(f, x) for f in (36.71, 55.0, 73.42)), 500, 4) * np.exp(-x * 1.2) * 0.5
    return np.tanh((body + s) * 1.4) * 0.7
ts = title_beat["start"]
add(sfx, ts - 1.5, swell(1.5), 0.8)
add(music, ts, hit(), 1.0)
pad([50, 57, 62, 64, 69], ts + 0.2, title_beat["end"] + 0.6, 0.04)
for i, n in enumerate([81, 76, 74]):
    add(music, ts + 0.9 + i * 0.9, pluck(note_hz(n), 2.4, 0.6), 0.10)

# rise: hopeful pulsing arpeggio that builds
def arp(a, b, prog, gain, step=0.3, bright=1.0, build=True):
    x = a; i = 0
    while x < b - 0.2:
        chord = prog[int((x - a) / (step * 8)) % len(prog)]
        n = chord[i % len(chord)]
        g = gain * (0.55 + 0.45 * ((x - a) / max(1, b - a)) if build else 1.0)
        add(music, x, pluck(note_hz(n), 1.2, bright), g * (1.0 if i % 4 == 0 else 0.72))
        x += step; i += 1

def pulse(a, b, bpm, gain):
    k = np.exp(-np.linspace(0, 22, int(0.25 * SR))) * np.sin(2 * np.pi * (48 + 40 * np.exp(-np.linspace(0, 30, int(0.25 * SR)))) * np.arange(int(0.25 * SR)) / SR)
    x = a
    while x < b - 0.2:
        add(music, x, k, gain); x += 60 / bpm

r0, r1 = span("rise")
arp(r0 + 0.3, r1, [[62, 69, 74, 77], [58, 65, 70, 74], [65, 69, 72, 77], [60, 67, 72, 76]], 0.11)
pad([38, 50, 57], r0, r1, 0.03)
pulse(r0 + 4, r1 - 0.5, 100, 0.25)
if "fall" in part_at:
    f0, f1 = span("fall")
    pad([38, 41, 45, 50], f0, f1, 0.04)
    x = f0 + 0.5
    while x < f1 - 0.5:
        add(music, x, beat_k, 0.45); add(music, x + 0.26, beat_k, 0.3); x += 0.8
    arp(f0 + 1, f1, [[62, 65, 69], [61, 65, 68]], 0.06, step=0.4, bright=0.5, build=False)
if "turn" in part_at:
    u0, u1 = span("turn")
    arp(u0 + 0.5, u1, [[65, 69, 72, 77], [60, 64, 67, 72], [62, 65, 69, 74], [58, 62, 65, 70]], 0.1, step=0.36)
    pad([41, 53, 60], u0, u1, 0.03)
if "end" in part_at:
    e0, e1 = span("end")
    pad([50, 54, 57, 62, 66], e0, TOTAL, 0.045)
    arp(e0 + 0.5, TOTAL - 4, [[74, 78, 81], [71, 74, 78], [69, 74, 78]], 0.08, step=0.5, build=False)

# part-card whooshes
def whoosh(dur=0.8):
    n = int(dur * SR); noise = rng.standard_normal(n); out = np.zeros(n); seg = 512
    for i in range(0, n - seg, seg):
        fc = 300 + 4000 * (i / n)
        bb, aa = signal.butter(2, [fc / (SR / 2), min(.99, fc * 1.6 / (SR / 2))], "band")
        out[i:i + seg] = signal.lfilter(bb, aa, noise[i:i + seg])
    return out * np.sin(np.linspace(0, np.pi, n)) ** 2 * 0.45
for b in TL["beats"]:
    if b["shot"] == "card":
        add(sfx, b["start"] - 0.5, whoosh(0.8), 0.6)
        add(music, b["start"], hit()[: int(1.5 * SR)], 0.35)

music *= env(0, TOTAL, 1.5, 2.5)
venv = np.convolve(np.abs(voice), np.ones(4800) / 4800, mode="same")
duck = 1 - 0.5 * np.clip(venv * 9, 0, 1)
mix = voice + (music * 0.85 + sfx * 0.8) * duck
st = np.stack([mix, mix + 0.015 * np.roll(music, 300)], 1)
st = st / np.max(np.abs(st)) * 0.95
sf.write(os.path.join(OUT, "story_soundtrack.wav"), st.astype(np.float32), SR)
json.dump(TL, open(os.path.join(OUT, "story_timeline.json"), "w"), indent=1)
print("wrote soundtrack + timeline")
