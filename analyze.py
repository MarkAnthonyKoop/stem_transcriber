"""MIDI → note list + key/tempo summary, via music21.

We deliberately do NOT use music21 for MIDI → MusicXML conversion: its output
on basic-pitch's unquantized MIDI is too dense for MuseScore to render. The
musicxml conversion lives in render.py (delegated to MuseScore's MIDI importer).
"""
from __future__ import annotations
from pathlib import Path
from typing import Any


def midi_summary(midi_path: str | Path) -> dict[str, Any]:
    """Return key, tempo(s), note count, duration."""
    from music21 import converter, tempo
    score = converter.parse(str(midi_path))
    flat = score.flatten()
    notes = list(flat.notes)
    tempos = [t.number for t in flat.getElementsByClass(tempo.MetronomeMark)]
    return {
        "midi_path": str(midi_path),
        "key": str(score.analyze("key")),
        "tempos_bpm": tempos,
        "note_count": len(notes),
        "part_count": len(score.parts),
        "duration_quarter_notes": float(score.duration.quarterLength),
    }


def midi_notes(midi_path: str | Path, out_path: str | Path) -> Path:
    """Write a tab-separated note list: onset_q, dur_q, pitch, midi_no, vel."""
    from music21 import converter
    score = converter.parse(str(midi_path))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows = ["onset_q\tdur_q\tpitch\tmidi_no\tvel"]
    for n in score.flatten().notes:
        if n.isChord:
            for p in n.pitches:
                rows.append(f"{float(n.offset):.4f}\t{float(n.quarterLength):.4f}\t"
                            f"{p.nameWithOctave}\t{p.midi}\t{n.volume.velocity or 0}")
        else:
            p = n.pitch
            rows.append(f"{float(n.offset):.4f}\t{float(n.quarterLength):.4f}\t"
                        f"{p.nameWithOctave}\t{p.midi}\t{n.volume.velocity or 0}")
    out_path.write_text("\n".join(rows) + "\n")
    return out_path
