# The Delegation Files

A 2:19 crime-documentary-style video (1920×1080, 30 fps, captions burned in) based on
Addy Osmani's essay *"Your coding agents made you a manager"*. Each anti-pattern from the essay is
a villain giving a disguised-voice interview, and each case ends with a verdict: the essay's best practice.

- `the-delegation-files.mp4`: the finished video
- `SCRIPT.md`: the full narration with timestamps (use it to record your own voice)
- `script.json`: the source of truth for every line, villain, verdict and evidence board

## Rebuild

Needs Python 3 (`pip install kokoro-onnx soundfile scipy`), ffmpeg (with rubberband), Node and Playwright.
The free Kokoro voice model files come from https://github.com/thewh1teagle/kokoro-onnx/releases (model-files-v1.0).

```bash
python3 make_audio.py <models_dir> <build_dir>   # TTS voices, original score, SFX, timeline.json
node render.mjs <build_dir> preview 20 30 40     # optional: PNG stills
node render.mjs <build_dir> video 4              # renders frames and muxes <build_dir>/the-delegation-files.mp4
```

The narrator is Kokoro `af_heart`. Villains use different Kokoro voices, pitched down and band-limited
to sound like anonymised interviews. The music and sound effects are synthesised in `make_audio.py`.
