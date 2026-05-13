"""mp3 → MIDI via Spotify's Basic Pitch (polyphonic, instrument-agnostic).

Drum stems should NOT use this — basic-pitch is bad at drums. Route drums to
a future `drums.py` (ADTOF wrapper) instead.
"""
from __future__ import annotations
import os
from pathlib import Path


def mp3_to_midi(audio_path: str | Path, out_dir: str | Path) -> Path:
    """Run basic-pitch on `audio_path`, write `<stem>_basic_pitch.mid` to `out_dir`.

    Returns the path to the produced MIDI file.
    """
    from basic_pitch.inference import predict_and_save
    from basic_pitch import ICASSP_2022_MODEL_PATH

    audio_path = Path(audio_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    midi = out_dir / f"{audio_path.stem}_basic_pitch.mid"
    if midi.exists():
        midi.unlink()

    predict_and_save(
        [str(audio_path)], str(out_dir),
        save_midi=True, sonify_midi=False,
        save_model_outputs=False, save_notes=False,
        model_or_model_path=ICASSP_2022_MODEL_PATH,
    )

    if not midi.exists():
        raise RuntimeError(f"basic-pitch did not produce {midi}")
    return midi
