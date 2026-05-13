"""End-to-end orchestration: stem MP3 → MIDI + MusicXML + sheet PDF + note list + summary."""
from __future__ import annotations
import json
import re
from pathlib import Path

from .transcribe import mp3_to_midi
from .analyze import midi_summary, midi_notes
from .render import midi_to_pdf, midi_to_musicxml
from .tab import midi_to_tab


def _infer_label(stem: str) -> str | None:
    """Guess Suno stem label from filename: 'fog_guitar.mp3' → 'guitar'."""
    m = re.search(r"_(vocals|backing_vocals|drums|bass|percussion|guitar|"
                  r"keyboard|piano|strings|brass|woodwinds|synth|fx)\b",
                  stem.lower())
    return m.group(1) if m else None


def transcribe_stem(audio_path: str | Path, out_dir: str | Path,
                    instrument_hint: str | None = None) -> dict:
    """Run the full pipeline on one stem.

    Outputs (in `out_dir`):
        <stem>_basic_pitch.mid   raw MIDI from basic-pitch
        <stem>.musicxml          MusicXML rendered by MuseScore (smart-quantized)
        <stem>.pdf               sheet PDF rendered by MuseScore
        <stem>_notes.tsv         tab-separated note list (raw, from basic-pitch)
        <stem>_summary.json      key, tempo, note count, etc.

    `instrument_hint` is recorded in the summary; future versions will route to
    drums.py for percussion stems and add tab-staff rendering for guitar/bass.

    Returns a dict of all output paths plus the analysis summary.
    """
    audio_path = Path(audio_path)
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    name = audio_path.stem
    hint = instrument_hint or _infer_label(name)

    midi = mp3_to_midi(audio_path, out_dir)
    pdf = midi_to_pdf(midi, out_dir / f"{name}.pdf")
    xml = midi_to_musicxml(midi, out_dir / f"{name}.musicxml")
    notes_tsv = midi_notes(midi, out_dir / f"{name}_notes.tsv")
    summary = midi_summary(midi)
    summary["instrument_hint"] = hint
    summary_json = out_dir / f"{name}_summary.json"
    summary_json.write_text(json.dumps(summary, indent=2))

    out: dict = {
        "midi": str(midi), "musicxml": str(xml), "pdf": str(pdf),
        "notes_tsv": str(notes_tsv), "summary_json": str(summary_json),
        "summary": summary,
    }

    # ASCII tab for stringed instruments
    tab_inst = "bass" if hint == "bass" else "guitar" if hint in ("guitar",) else None
    if tab_inst:
        tab_path = midi_to_tab(midi, out_dir / f"{name}.tab", instrument=tab_inst)
        out["tab"] = str(tab_path)

    return out
