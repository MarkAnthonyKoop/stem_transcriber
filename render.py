r"""MIDI/MusicXML → PDF / MusicXML, via the MuseScore CLI.

macOS-native (rewritten 2026-07-16). The original targeted MuseScore 3 on the
Windows side from WSL and had to shuttle inputs through a Windows temp dir
because MuseScore refused UNC paths. On macOS MuseScore reads local files
directly, so `_convert` is a plain subprocess call.

One gotcha this module still hides:

- music21's MusicXML output of unquantized basic-pitch MIDI causes MuseScore
  to choke (1000s of tied 32nd-note tuplets). MuseScore's own MIDI importer
  is much smarter — so we let MuseScore do MIDI → MusicXML when we want XML.

We probe for MuseScore 4 first, then 3, then a bare `mscore`/`musescore` on
PATH. Set MUSESCORE_EXE to override.
"""
from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path

# Candidate MuseScore CLI binaries, most-preferred first. macOS app bundles
# expose the CLI as .../Contents/MacOS/mscore.
_CANDIDATES = [
    os.environ.get("MUSESCORE_EXE", ""),
    "/Applications/MuseScore 4.app/Contents/MacOS/mscore",
    "/Applications/MuseScore 3.app/Contents/MacOS/mscore",
    shutil.which("mscore") or "",
    shutil.which("musescore") or "",
]

# Launching MuseScore cold (first run after boot) can take ~10s; conversions of
# dense basic-pitch MIDI are heavier still.
_DEFAULT_TIMEOUT_S = 180


def _musescore_exe() -> str:
    for c in _CANDIDATES:
        if c and Path(c).exists():
            return c
    raise RuntimeError(
        "MuseScore not found. Install with `brew install --cask musescore` "
        "or set MUSESCORE_EXE to the CLI binary "
        "(…/MuseScore 4.app/Contents/MacOS/mscore)."
    )


def _convert(src: str | Path, dst: str | Path, timeout_s: int) -> Path:
    """`mscore -o dst src` — MuseScore infers both formats from the extensions."""
    exe = _musescore_exe()
    src = Path(src)
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)

    cmd = [exe, "-o", str(dst), str(src)]
    # MuseScore 4's macOS bundle ships only the "cocoa" Qt platform plugin, so we
    # do NOT force QT_QPA_PLATFORM=offscreen (that aborts with SIGABRT). Batch
    # export via -o runs fine under cocoa without a visible window.
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    if not dst.exists():
        raise RuntimeError(
            f"MuseScore did not produce {dst.suffix} (rc={p.returncode})\n"
            f"stdout: {p.stdout[-500:]}\nstderr: {p.stderr[-500:]}"
        )
    return dst


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
