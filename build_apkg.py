# Copyright (c) 2025 github.com/SKOHscripts
#
# This software is licensed under the MIT License.
"""
Build Anki .apkg from puzzle CSV files.

Usage:
    python build_apkg.py                   # requires puzzles_*.csv in current dir
    python build_apkg.py --sample          # build a minimal demo deck (CI/testing)
    python build_apkg.py --csv-dir PATH    # read CSVs from a different directory
    python build_apkg.py --output FILE     # override output filename
"""
import argparse
import csv
import hashlib
import os
import shutil
import zipfile
from pathlib import Path
from typing import List, Dict

import genanki

DECK_PARENT = "♟️ Optimized Chess Puzzles"
MODEL_NAME = "OCP Puzzle v1"

# Stable model ID derived from model name
MODEL_ID = int(hashlib.sha1(MODEL_NAME.encode()).hexdigest()[:8], 16)

NOTE_FIELDS = [
    {"name": "PuzzleID"},
    {"name": "FEN"},
    {"name": "Moves"},
    {"name": "Rating"},
    {"name": "Popularity"},
    {"name": "Themes"},
    {"name": "Opening"},
    {"name": "Display Theme"},
    {"name": "Tags"},
]

ELO_RANGES: List[tuple] = [
    ("puzzles_1000minus.csv", "01 | -1000 ELO"),
    ("puzzles_1000_1100.csv", "02 | 1000-1100 ELO"),
    ("puzzles_1100_1200.csv", "03 | 1100-1200 ELO"),
    ("puzzles_1200_1300.csv", "04 | 1200-1300 ELO"),
    ("puzzles_1300_1400.csv", "05 | 1300-1400 ELO"),
    ("puzzles_1400_1500.csv", "06 | 1400-1500 ELO"),
    ("puzzles_1500_1600.csv", "07 | 1500-1600 ELO"),
    ("puzzles_1600_1700.csv", "08 | 1600-1700 ELO"),
    ("puzzles_1700_1800.csv", "09 | 1700-1800 ELO"),
    ("puzzles_1800plus.csv",  "10 | 1800+ ELO"),
]

SAMPLE_CARDS: List[Dict[str, str]] = [
    {
        "PuzzleID": "sample_fork",
        "FEN": "r1bqkb1r/pppp1ppp/2n5/4p3/2B1P1n1/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 5",
        "Moves": "Bxf7+",
        "Rating": "1200",
        "Popularity": "90",
        "Themes": "fork sacrifice",
        "Opening": "Italian",
        "Display Theme": "theme-green",
        "Tags": "OCP::fork OCP::sacrifice OCP::Italian",
    },
    {
        "PuzzleID": "sample_pin",
        "FEN": "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQK2R w KQ - 0 7",
        "Moves": "Bg5",
        "Rating": "1400",
        "Popularity": "88",
        "Themes": "pin",
        "Opening": "Italian",
        "Display Theme": "theme-green",
        "Tags": "OCP::pin OCP::Italian",
    },
    {
        "PuzzleID": "sample_endgame",
        "FEN": "8/4k3/8/3KP3/8/8/8/8 w - - 0 1",
        "Moves": "e6",
        "Rating": "1800",
        "Popularity": "95",
        "Themes": "endgame pawnEndgame",
        "Opening": "",
        "Display Theme": "theme-green",
        "Tags": "OCP::endgame OCP::pawnEndgame",
    },
]


def _deck_id(name: str) -> int:
    return int(hashlib.sha1(name.encode()).hexdigest()[:8], 16)


def _upgrade_to_anki21(path: str) -> None:
    """Rename collection.anki2 → collection.anki21 inside the .apkg zip.

    Anki 23.10+ (Qt6) refuses to import packages that contain only
    collection.anki2 and raises error 500 "specified file not found in
    archive". Renaming the entry makes the file importable on all versions
    (Anki 2.1.28+ recognises both names).
    """
    tmp = path + ".tmp"
    with zipfile.ZipFile(path, "r") as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "collection.anki2":
                item.filename = "collection.anki21"
            zout.writestr(item, data)
    shutil.move(tmp, path)


def _load_templates() -> tuple:
    """Load front/back HTML and CSS from the templates/ directory."""
    tmpl_dir = Path("templates")
    with open(tmpl_dir / "front.html", encoding="utf-8") as f:
        front = f.read()
    with open(tmpl_dir / "back.html", encoding="utf-8") as f:
        back = f.read()
    with open(tmpl_dir / "style.css", encoding="utf-8") as f:
        css = f.read()
    return front, back, css


def _build_model(front: str, back: str, css: str) -> genanki.Model:
    return genanki.Model(
        MODEL_ID,
        MODEL_NAME,
        fields=NOTE_FIELDS,
        templates=[{"name": "OCP Card", "qfmt": front, "afmt": back}],
        css=css,
    )


def _row_to_note(row: Dict[str, str], model: genanki.Model) -> genanki.Note:
    tags = [t for t in row.get("Tags", "").split() if t]
    return genanki.Note(
        model=model,
        fields=[
            row.get("PuzzleID", ""),
            row.get("FEN", ""),
            row.get("Moves", ""),
            row.get("Rating", ""),
            row.get("Popularity", ""),
            row.get("Themes", ""),
            row.get("Opening", ""),
            row.get("Display Theme", "theme-solarized"),
            row.get("Tags", ""),
        ],
        tags=tags,
    )


def build_from_csvs(csv_dir: str, output: str) -> None:
    """Build a real .apkg from the generated puzzle CSV files."""
    front, back, css = _load_templates()
    model = _build_model(front, back, css)

    media_path = os.path.join(
        "♟️_Optimized_Chess_Puzzles", "media", "_chess_merida_unicode.ttf"
    )

    decks: List[genanki.Deck] = []
    total_notes = 0

    for csv_filename, deck_suffix in ELO_RANGES:
        csv_path = os.path.join(csv_dir, csv_filename)
        if not os.path.exists(csv_path):
            print(f"  ⚠ Skipping {csv_filename} (not found)")
            continue

        deck_name = f"{DECK_PARENT}::{deck_suffix}"
        deck = genanki.Deck(_deck_id(deck_name), deck_name)

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                deck.add_note(_row_to_note(row, model))
                count += 1

        decks.append(deck)
        total_notes += count
        print(f"  ✓ {deck_suffix}: {count} cards")

    if not decks:
        print("No CSV files found. Run lichess_optimized_puzzles_datasets.py first.")
        return

    package = genanki.Package(decks)
    if os.path.exists(media_path):
        package.media_files = [media_path]

    package.write_to_file(output)
    _upgrade_to_anki21(output)
    print(f"\n✅ Built {output} — {total_notes} cards across {len(decks)} sub-decks")


def build_sample(output: str) -> None:
    """Build a minimal demo .apkg for CI/testing without real CSV files."""
    front, back, css = _load_templates()
    model = _build_model(front, back, css)

    decks: List[genanki.Deck] = []
    for _, deck_suffix in ELO_RANGES:
        deck_name = f"{DECK_PARENT}::{deck_suffix}"
        deck = genanki.Deck(_deck_id(deck_name), deck_name)
        for card in SAMPLE_CARDS:
            deck.add_note(_row_to_note(card, model))
        decks.append(deck)

    package = genanki.Package(decks)
    package.write_to_file(output)
    _upgrade_to_anki21(output)
    print(f"✅ Built sample {output} — {len(SAMPLE_CARDS)} cards × {len(ELO_RANGES)} sub-decks")


def main() -> None:
    """Parse CLI arguments and build the Anki deck."""
    parser = argparse.ArgumentParser(description="Build Anki .apkg for Optimized Chess Puzzles")
    parser.add_argument("--csv-dir", default=".", help="Directory containing puzzles_*.csv files")
    parser.add_argument(
        "--output",
        default="♟️_Optimized_Chess_Puzzles.apkg",
        help="Output .apkg filename",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Build a minimal demo deck (no real CSVs needed)",
    )
    args = parser.parse_args()

    print(f"Building Anki deck: {args.output}")
    if args.sample:
        build_sample(args.output)
    else:
        build_from_csvs(args.csv_dir, args.output)


if __name__ == "__main__":
    main()
