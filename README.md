# stem_transcriber

Single-stem audio (one instrument MP3) → MIDI + sheet PDF + MusicXML + ASCII tab + plain-text note list + key/tempo summary.

A sibling project under `~/claude/`. Knows nothing about Suno, YouTube, or stem-extraction itself — just takes a single-instrument audio file and transcribes it.

---

## 1. User manual

Install once. On **macOS** (this Mac, set up 2026-07-16) use a dedicated Python 3.11 venv and
MuseScore 4 from Homebrew:

```bash
cd ~/claude/stem_transcriber
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python 'basic-pitch[onnx]' music21 'setuptools<81'
brew install --cask musescore          # → /Applications/MuseScore 4.app
```

(The `setuptools<81` pin is required — basic-pitch's resampy still imports the removed
`pkg_resources`. `render.py` auto-finds MuseScore 4; override with `MUSESCORE_EXE`.)

Transcribe one stem (any format basic-pitch reads — mp3/wav/flac/m4a):

```bash
PYTHONPATH=~/claude ~/claude/stem_transcriber/.venv/bin/python \
    -m stem_transcriber transcribe stems/song_guitar.wav --out transcribed
```

Outputs land in `<audio_dir>/transcribed/<stem>.{mid,musicxml,pdf,tab,_notes.tsv,_summary.json}` by default. Override with `--out DIR`. Force an instrument label with `--instrument guitar|bass|vocals|drums|...` (otherwise inferred from filename). The `.tab` ASCII tablature is only generated for guitar and bass stems.

The 80% workflow:

```bash
# transcribe every stem of fog (skip drums — basic-pitch is bad at them)
for f in /mnt/d/downloads/suno_stems/fog/fog_*.mp3; do
    case "$f" in *drums*|*percussion*) continue ;; esac
    python3 -m stem_transcriber transcribe "$f"
done
ls /mnt/d/downloads/suno_stems/fog/transcribed/
```

---

## 2. Reference

### CLI subcommands

| Subcommand | Args | Purpose |
| --- | --- | --- |
| `transcribe <audio>` | `--out DIR` `--instrument LABEL` | Full pipeline → MIDI, MusicXML, sheet PDF, .tab (guitar/bass), notes TSV, summary JSON |
| `midi <audio> --out DIR` | | Just audio → MIDI |
| `musicxml <midi> --out FILE` | | Just MIDI → MusicXML (via MuseScore) |
| `pdf <input> --out FILE` | | MIDI or MusicXML → PDF |
| `notes <midi> --out FILE` | | Just MIDI → tab-separated note list |
| `summary <midi>` | | Print key, tempo, note count to stdout |

### Public Python API

```python
from stem_transcriber import (
    transcribe_stem,       # full pipeline → dict of all output paths + summary
    mp3_to_midi,           # (audio, out_dir) -> Path to .mid
    midi_to_pdf,           # (midi, pdf) -> Path
    midi_to_musicxml,      # (midi, xml) -> Path (via MuseScore — better than music21)
    musicxml_to_pdf,       # (xml, pdf) -> Path
    midi_summary,          # (midi) -> dict (key, tempos_bpm, note_count, ...)
    midi_notes,            # (midi, out) -> Path to .tsv
    midi_to_tab,           # (midi, out, instrument='guitar'|'bass') -> Path to .tab
)
```

`transcribe_stem(audio, out_dir, instrument_hint=None)` returns:

```python
{
  "midi": "/.../fog_guitar_basic_pitch.mid",
  "musicxml": "/.../fog_guitar.musicxml",
  "pdf": "/.../fog_guitar.pdf",
  "notes_tsv": "/.../fog_guitar_notes.tsv",
  "summary_json": "/.../fog_guitar_summary.json",
  "tab": "/.../fog_guitar.tab",                 # only present for guitar/bass
  "summary": {
    "midi_path": "...", "key": "e minor", "tempos_bpm": [120],
    "note_count": 1376, "part_count": 1,
    "duration_quarter_notes": 594.0, "instrument_hint": "guitar",
  },
}
```

### Filesystem contract

- Input: any audio file basic-pitch can read (mp3, wav, flac, m4a, ogg).
- Outputs: written to `out_dir`, named after the input stem (filename minus extension).
- No state outside the output dir. No cache. No config file.

### Instrument hints

Auto-inferred from filenames matching `_<label>` (Suno's stem labels):
`vocals, backing_vocals, drums, bass, percussion, guitar, keyboard, piano, strings, brass, woodwinds, synth, fx`.

Mapped to music21 instruments — affects the staff MuseScore renders. Guitar/bass get treble clef + (eventually) a linked tab staff.

### Backends

- **basic-pitch** ([spotify/basic-pitch](https://github.com/spotify/basic-pitch)) — polyphonic pitch detection. Runs on CPU via ONNX. Bad at drums. Fine at everything else.
- **music21** ([cuthbertLab/music21](https://github.com/cuthbertLab/music21)) — MIDI ⇄ MusicXML, key analysis, tempo extraction.
- **MuseScore 3** (Windows binary via WSL interop) — MusicXML → PDF.

---

## 3. Architecture

```
~/claude/stem_transcriber/
├── README.md
├── CLAUDE.md
├── __init__.py        re-exports the public API only
├── __main__.py        thin entry into cli.main
├── cli.py             argparse + dispatch (~55 lines)
├── pipeline.py        orchestrates the leaf modules — the only thing with multi-step logic
├── transcribe.py      mp3 → MIDI (basic-pitch wrapper)
├── analyze.py         MIDI → note list + key/tempo summary (music21 wrapper)
├── render.py          MIDI/MusicXML → PDF + MIDI → MusicXML (MuseScore CLI wrapper)
└── tab.py             MIDI → ASCII guitar/bass tablature (greedy fret picker)
```

Dependency graph (bottom-up, no back-edges):

```
__main__ ──► cli ──► pipeline ──► transcribe   (basic-pitch)
                              ├─► analyze      (music21)
                              ├─► render       (MuseScore)
                              └─► tab          (music21)
```

Each leaf is one purpose, one external tool. Adding a new backend = a new leaf module. Don't put orchestration logic in leaves.

### What belongs here vs a sibling

- **In here**: anything that takes a single-instrument audio file and emits notation/MIDI/notes for that one instrument.
- **Sibling**: stem extraction (Suno's hosted job → `suno_client`; local Demucs → `audio_separator`); audio FX (`audio_fx`); mixing (`audio_mixer`); workflow recipes (`music_studio`).

### Future siblings / enhancements

| What | Sibling/module | Why |
| --- | --- | --- |
| Drum transcription | new `drums.py` leaf using ADTOF | basic-pitch is bad at drums; ADTOF wasn't on PyPI when we looked (2026-05) — clone the github repo |
| Vocal lyrics extraction | new `lyrics.py` leaf using whisper or ACE-Studio | not pitch — different problem |
| Linked tab staves in PDF | edit `render.py` to inject `<staff-details><staff-type>tablature` into MusicXML before MuseScore | current `.tab` is ASCII only; PDF has sheet only |
| Guitar Pro (.gp) export | new `gp.py` leaf via pyguitarpro | richer than ASCII for tab software users |
| Klangio API backend | new `klangio.py` leaf, swappable in `pipeline.py` | higher quality at $$ |
| MuseScore 4 support | edit `render.py` to detect 3 vs 4 | nicer rendering |
