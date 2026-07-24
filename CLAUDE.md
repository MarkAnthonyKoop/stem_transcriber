# CLAUDE.md — stem_transcriber

Read `README.md` first. Universal rules: `~/CLAUDE.md`. Machine notes: `~/claude/CLAUDE.md`.

## Single purpose, do not grow it

`stem_transcriber` does **one thing**: take a single-instrument audio file and emit MIDI + MusicXML + sheet PDF + note list + summary. Resist:

- Adding stem extraction → that's `suno_client.stems` (Suno-hosted) or `audio_separator` (local Demucs). New sibling.
- Adding audio FX (reverb, EQ) → `audio_fx`. New sibling.
- Adding mixing → `audio_mixer`. New sibling.
- Adding YouTube publishing of PDFs → `score_publisher` or recipe in `music_studio`.
- Adding a config file, plugin system, or any state beyond the output dir.

When you're tempted to add a backend that does something fundamentally different (e.g. a model that also does source separation), ask: *would this be useful outside transcription?* If yes, sibling.

## Each backend is its own leaf module

`transcribe.py` (basic-pitch) is one leaf. `tab.py` (ASCII tab) is another. When we add ADTOF for drums, it goes in `drums.py`, NOT inside `transcribe.py`. When we add Klangio API, it's `klangio.py`. `pipeline.py` is the only place that decides which backend to use.

Don't introduce a `backends.py` registry or a plugin loader — five modules is fine, just `if instrument == "drums": from .drums import ...`.

`tab.py` is currently routed via `pipeline.py` for `instrument_hint in ("guitar", "bass")` only. Keyboard/strings/brass/etc. can in principle have tab-like representations (e.g. piano-roll) but that's a future leaf, not an extension of `tab.py`.

## Files stay under 150 lines

Soft budget 150, hard 200. Currently every file is well under. If `pipeline.py` grows past ~120 lines because we added per-instrument routing, split into `pipeline/__init__.py` + `pipeline/routing.py` BEFORE the change.

## MuseScore backend (macOS, ported 2026-07-16)

`render.py` was rewritten from the original WSL/Windows version for **this Mac**. It now probes,
in order: `$MUSESCORE_EXE`, `/Applications/MuseScore 4.app/Contents/MacOS/mscore`, the same for
MuseScore 3, then `mscore`/`musescore` on PATH. Installed here via `brew install --cask musescore`
(MuseScore 4.7.4). On macOS the CLI reads local files directly, so the old Windows-temp-dir
shuttling is gone — `_convert` is a plain `mscore -o dst src`.

**Do NOT set `QT_QPA_PLATFORM=offscreen`.** MuseScore 4's macOS bundle ships only the `cocoa` Qt
plugin; forcing `offscreen` makes it abort with SIGABRT (rc −6). Batch export via `-o` runs
headless under `cocoa` without a visible window. This bit us once — the fix is to leave the env
alone.

The original WSL notes (MuseScore 3 at `/mnt/c/Program Files/...`, UNC-path refusal) are obsolete
here but preserved in git history if this ever runs on WSL again.

## Available state

Nothing cached. No tokens. No config. The output dir is the only state, and it's reproducible from input + the model weights basic-pitch ships with.

On macOS (2026-07-16) the deps live in a dedicated Python 3.11 venv at
`~/claude/stem_transcriber/.venv` (the workspace 3.14 is too new for some basic-pitch deps):

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python 'basic-pitch[onnx]' music21 'setuptools<81'
```

`setuptools<81` is **required, non-obvious**: basic-pitch → resampy imports `pkg_resources`, which
setuptools removed in v81. Without the pin you get `ModuleNotFoundError: No module named
'pkg_resources'` at transcription time. ONNX runtime runs the model on CPU; TensorFlow is not
needed (the `[onnx]` extra is enough — you'll see a harmless "Tensorflow is not installed" warning).

Run with `PYTHONPATH=~/claude ~/claude/stem_transcriber/.venv/bin/python -m stem_transcriber ...`.

## Drums caveat

Basic-pitch produces *garbage* on drum stems — pitched-instrument model interpreting unpitched percussion. If `transcribe_stem` is given `*_drums.mp3` or `*_percussion.mp3`, it'll still run and produce a "transcription," but it won't be useful. Future work: a `drums.py` leaf using ADTOF that produces a drum-staff MusicXML directly, plus pipeline routing on the instrument hint.

For now: skip drum stems in batch loops. The README's "for f in fog_*.mp3" example shows the pattern.

## Smoke test

```bash
# create a 1s sine-wave stem
ffmpeg -y -f lavfi -i "sine=f=440:d=1" -c:a libmp3lame /tmp/st_test.mp3 2>/dev/null
PYTHONPATH=~/claude ~/claude/stem_transcriber/.venv/bin/python \
    -m stem_transcriber transcribe /tmp/st_test.mp3 --out /tmp/st_test_out
ls /tmp/st_test_out/
# expect: st_test.musicxml, st_test.pdf, st_test_basic_pitch.mid, st_test_notes.tsv, st_test_summary.json
rm -rf /tmp/st_test.mp3 /tmp/st_test_out
```

If `pdf` is missing but `musicxml` exists, MuseScore is the broken link — check the path in `render.py`.

## Documentation contract

If you change CLI flags, update README §2. If you add a backend leaf, mention it in README §3 "Future siblings / enhancements" (move it from Future to current). If you change the dependency graph, redraw it.
