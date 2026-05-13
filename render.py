r"""MIDI/MusicXML → PDF / MusicXML, via MuseScore 3 CLI on the Windows side.

Two gotchas this module hides:

1. MuseScore on Windows reliably refuses to read files via the
   `\\wsl.localhost\Ubuntu\...` UNC path when the input is non-trivial. It
   silently exits without producing output. So we ALWAYS shuttle the input
   through `C:\Users\x\AppData\Local\Temp\` first, then copy the result back
   to the WSL-side destination.

2. music21's MusicXML output of unquantized basic-pitch MIDI causes MuseScore
   to choke (1000s of tied 32nd-note tuplets). MuseScore's own MIDI importer
   is much smarter — so we let MuseScore do MIDI → MusicXML when we want XML.

Why MuseScore 3, not 4? Already installed at the path below. MuseScore 4 would
also work; probe both and use whichever exists when we add it.
"""
from __future__ import annotations
import shutil
import subprocess
import time
from pathlib import Path

_MUSESCORE_EXE = "/mnt/c/Program Files/MuseScore 3/bin/MuseScore3.exe"
_WIN_TMP_WSL = Path("/mnt/c/Users/x/AppData/Local/Temp")

# Crash-reporter starts on the Windows side too; we tolerate that and give MuseScore
# a generous timeout because launching it cold (first run after boot) takes ~10s.
_DEFAULT_TIMEOUT_S = 180


def _wslpath_w(p: str | Path) -> str:
    return subprocess.check_output(["wslpath", "-w", str(p)], text=True).strip()


def _convert(src: str | Path, dst: str | Path, timeout_s: int) -> Path:
    """MuseScore3 -o dst src, shuttled through the Windows-side temp dir."""
    if not Path(_MUSESCORE_EXE).exists():
        raise RuntimeError(f"MuseScore 3 not found at {_MUSESCORE_EXE}")
    src = Path(src); dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    _WIN_TMP_WSL.mkdir(parents=True, exist_ok=True)

    tag = f"{int(time.time()*1000)}_{src.stem}"
    win_in = _WIN_TMP_WSL / f"{tag}{src.suffix}"
    win_out = _WIN_TMP_WSL / f"{tag}{dst.suffix}"
    try:
        shutil.copyfile(src, win_in)
        cmd = [_MUSESCORE_EXE, "-o", _wslpath_w(win_out), _wslpath_w(win_in)]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
        if not win_out.exists():
            raise RuntimeError(
                f"MuseScore did not produce {dst.suffix} (rc={p.returncode})\n"
                f"stdout: {p.stdout[-500:]}\nstderr: {p.stderr[-500:]}"
            )
        shutil.copyfile(win_out, dst)
        return dst
    finally:
        for f in (win_in, win_out):
            try: f.unlink()
            except FileNotFoundError: pass


def midi_to_pdf(midi_path: str | Path, pdf_path: str | Path,
                timeout_s: int = _DEFAULT_TIMEOUT_S) -> Path:
    return _convert(midi_path, pdf_path, timeout_s)


def midi_to_musicxml(midi_path: str | Path, xml_path: str | Path,
                     timeout_s: int = _DEFAULT_TIMEOUT_S) -> Path:
    """MuseScore's MIDI importer is dramatically better than music21's at producing
    renderable MusicXML — it quantizes, infers measures, and groups notes."""
    return _convert(midi_path, xml_path, timeout_s)


def musicxml_to_pdf(xml_path: str | Path, pdf_path: str | Path,
                    timeout_s: int = _DEFAULT_TIMEOUT_S) -> Path:
    return _convert(xml_path, pdf_path, timeout_s)
