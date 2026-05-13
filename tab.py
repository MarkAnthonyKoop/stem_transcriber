"""MIDI → ASCII guitar/bass tab.

Algorithm: greedy fret-picker — for each note, pick the highest available string
where the pitch is fretable in [0, max_fret]; on that string use the lowest fret
(open string preferred). Time-quantize to 16th notes; one measure per block.

This is a v1: it ignores chord shape, slides, bends, hammer-ons. Anyone reading
the tab gets correct pitches at correct times — they pick fingerings from there.
"""
from __future__ import annotations
from pathlib import Path

# Standard tunings (low → high). MIDI numbers.
GUITAR_STRINGS = [40, 45, 50, 55, 59, 64]   # E2 A2 D3 G3 B3 E4
GUITAR_NAMES   = ["E", "A", "D", "G", "B", "e"]
BASS_STRINGS   = [28, 33, 38, 43]            # E1 A1 D2 G2
BASS_NAMES     = ["E", "A", "D", "G"]

_TUNINGS = {
    "guitar": (GUITAR_STRINGS, GUITAR_NAMES),
    "bass":   (BASS_STRINGS,   BASS_NAMES),
}


def _best_position(midi_pitch: int, strings: list[int], max_fret: int = 22):
    """Return (string_idx, fret) or None if pitch is unreachable on this tuning."""
    options = [(i, midi_pitch - openp) for i, openp in enumerate(strings)
               if 0 <= midi_pitch - openp <= max_fret]
    if not options:
        return None
    # Highest string first (idx desc), then lowest fret.
    return max(options, key=lambda sf: (sf[0], -sf[1]))


def midi_to_tab(midi_path: str | Path, out_path: str | Path,
                instrument: str = "guitar",
                subdivisions_per_beat: int = 4,
                beats_per_measure: int = 4,
                max_fret: int = 22) -> Path:
    """Write a 6-line (guitar) or 4-line (bass) ASCII tab to `out_path`.

    `instrument` must be 'guitar' or 'bass'.
    """
    if instrument not in _TUNINGS:
        raise ValueError(f"unsupported instrument {instrument!r}; must be one of {list(_TUNINGS)}")
    strings, names = _TUNINGS[instrument]
    n_strings = len(strings)
    cells_per_measure = beats_per_measure * subdivisions_per_beat

    from music21 import converter
    score = converter.parse(str(midi_path))

    # Collect (cell, string_idx, fret), unreachable_count
    placed: dict[tuple[int, int, int], int] = {}   # (measure, string, pos) -> fret
    unreachable = 0
    for n in score.flatten().notes:
        pitches = [p.midi for p in (n.pitches if n.isChord else [n.pitch])]
        cell = round(float(n.offset) * subdivisions_per_beat)
        measure = cell // cells_per_measure
        pos = cell % cells_per_measure
        for mp in pitches:
            sp = _best_position(mp, strings, max_fret)
            if sp is None:
                unreachable += 1
                continue
            string_idx, fret = sp
            placed[(measure, string_idx, pos)] = fret

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    measures = sorted({m for m, _, _ in placed.keys()})
    if not measures:
        out_path.write_text(f"# (no reachable {instrument} notes)\n")
        return out_path

    lines: list[str] = []
    lines.append(f"# {instrument} tab — {Path(midi_path).stem}")
    lines.append(f"# tuning (low→high): {' '.join(names)}   max_fret={max_fret}")
    lines.append(f"# {beats_per_measure}/4, {subdivisions_per_beat} subdivisions per beat "
                 f"({cells_per_measure} cells per measure)")
    lines.append(f"# notes placed: {len(placed)}, unreachable: {unreachable}")
    lines.append("")

    for m in range(measures[0], measures[-1] + 1):
        lines.append(f"m.{m + 1}")
        # Render high string at top (convention)
        for s in range(n_strings - 1, -1, -1):
            row: list[str] = []
            for p in range(cells_per_measure):
                fret = placed.get((m, s, p))
                if fret is None:
                    row.append("--")
                else:
                    row.append(f"{fret:>2}".replace(" ", "-"))
            lines.append(f"{names[s]}|" + "-".join(row) + "|")
        lines.append("")

    out_path.write_text("\n".join(lines))
    return out_path
