"""CLI: `python3 -m stem_transcriber transcribe <stem.mp3> [--out DIR] [--instrument LABEL]`"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from .pipeline import transcribe_stem
from .transcribe import mp3_to_midi
from .analyze import midi_summary, midi_notes
from .render import midi_to_pdf, midi_to_musicxml, musicxml_to_pdf


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="stem_transcriber",
        description="Stem MP3 → MIDI / MusicXML / sheet PDF / note list.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("transcribe", help="Full pipeline on one stem.")
    t.add_argument("audio", help="path to stem MP3 (e.g. fog_guitar.mp3)")
    t.add_argument("--out", default=None, help="output dir (default: <audio dir>/transcribed)")
    t.add_argument("--instrument", default=None,
        help="hint: guitar|bass|vocals|drums|keyboard|strings|brass|woodwinds|synth|fx")

    m = sub.add_parser("midi", help="Just mp3 → MIDI.")
    m.add_argument("audio"); m.add_argument("--out", required=True)

    x = sub.add_parser("musicxml", help="Just MIDI → MusicXML (via MuseScore).")
    x.add_argument("midi"); x.add_argument("--out", required=True)

    p = sub.add_parser("pdf", help="MIDI or MusicXML → PDF.")
    p.add_argument("input"); p.add_argument("--out", required=True)

    n = sub.add_parser("notes", help="MIDI → note list TSV.")
    n.add_argument("midi"); n.add_argument("--out", required=True)

    s = sub.add_parser("summary", help="Print MIDI key/tempo/notes summary.")
    s.add_argument("midi")

    args = ap.parse_args(argv)

    if args.cmd == "transcribe":
        out = Path(args.out) if args.out else Path(args.audio).parent / "transcribed"
        result = transcribe_stem(args.audio, out, instrument_hint=args.instrument)
        json.dump({k: v for k, v in result.items() if k != "summary"}
                  | {"summary": result["summary"]}, sys.stdout, indent=2)
        sys.stdout.write("\n")
    elif args.cmd == "midi":      mp3_to_midi(args.audio, args.out)
    elif args.cmd == "musicxml":  midi_to_musicxml(args.midi, args.out)
    elif args.cmd == "pdf":
        if args.input.lower().endswith(".mid"): midi_to_pdf(args.input, args.out)
        else:                                   musicxml_to_pdf(args.input, args.out)
    elif args.cmd == "notes":     midi_notes(args.midi, args.out)
    elif args.cmd == "summary":   json.dump(midi_summary(args.midi), sys.stdout, indent=2); sys.stdout.write("\n")
    return 0
