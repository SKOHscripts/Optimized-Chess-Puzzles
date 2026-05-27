# Copyright (c) 2025 github.com/SKOHscripts
#
# This software is licensed under the MIT License.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""
Lichess Puzzle Database Processor
=================================

This script downloads the complete Lichess puzzle database and creates curated
puzzle sets optimized for chess training using the Woodpecker method and spaced
repetition. It applies intelligent thematic sampling to maximize pattern diversity
while maintaining pedagogical quality.

The script generates CSV files for different ELO ranges with puzzles selected to
provide comprehensive coverage of tactical themes and opening patterns.
"""

import os
import re
import subprocess
from collections import defaultdict
from typing import List, Tuple

import chess
import pandas
import requests

PUZZLE_URL = "https://database.lichess.org/lichess_db_puzzle.csv.zst"
PUZZLE_FILE = "lichess_db_puzzle.csv.zst"
CSV_FILE = "lichess_db_puzzle.csv"

MIN_PUZZLES_PER_RANGE = 700
DOWNLOAD_TIMEOUT = 120
DOWNLOAD_CHUNK_SIZE = 8192


def safe_str(value) -> str:
    """
    Convert a value to string, replacing NaN or None values with empty string.

    Parameters
    ----------
    value : any
        The value to convert to string

    Returns
    -------
    str
        String representation of the value, or empty string if NaN/None
    """

    if pandas.isna(value):
        return ""

    return str(value)


def adjust_fen_and_moves(fen: str, moves: str) -> Tuple[str, str]:
    """
    Adjust FEN position and move sequence for puzzle presentation.

    Lichess puzzles show the position before the opponent's move. This function
    applies the first move to show the actual position to solve, then removes
    that move from the solution sequence.

    Parameters
    ----------
    fen : str
        Initial FEN position string
    moves : str
        Space-separated UCI move sequence

    Returns
    -------
    tuple[str, str]
        Adjusted FEN position and remaining moves sequence
    """
    board = chess.Board(fen)
    moves_list = moves.strip().split()

    if moves_list:
        first_move = board.parse_uci(moves_list[0])
        board.push(first_move)
        new_fen = board.fen()
        rest_moves = " ".join(moves_list[1:])
    else:
        new_fen = fen
        rest_moves = ""

    return new_fen, rest_moves


def download_puzzle_db() -> None:
    """
    Download the Lichess puzzle database if not already present.

    Downloads the compressed puzzle database from Lichess servers.
    The file is approximately 200MB compressed.
    """

    if not os.path.exists(PUZZLE_FILE):
        print("Downloading puzzle database...")
        request = requests.get(PUZZLE_URL, stream=True, timeout=DOWNLOAD_TIMEOUT)
        with open(PUZZLE_FILE, "wb") as puzzle_file:
            for chunk in request.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                puzzle_file.write(chunk)
        print("Download completed.")
    else:
        print("File already downloaded.")


def decompress_zst() -> None:
    """
    Decompress the .zst puzzle database file to CSV format.

    Requires zstd to be installed on the system.
    The decompressed file is approximately 1GB.
    """

    if not os.path.exists(CSV_FILE):
        print("Decompressing zst file...")
        subprocess.run(["zstd", "-d", PUZZLE_FILE], check=True)
        print("Decompression completed.")
    else:
        print("CSV file already decompressed.")


def uci_seq_to_san(fen: str, uci_moves: str) -> str:
    """
    Convert UCI move sequence to Standard Algebraic Notation (SAN).

    Parameters
    ----------
    fen : str
        Starting position in FEN notation
    uci_moves : str
        Space-separated UCI moves (e.g., "e2e4 e7e5")

    Returns
    -------
    str
        Space-separated SAN moves (e.g., "e4 e5")
    """
    board = chess.Board(fen)
    san_moves = []

    for move_uci in uci_moves.strip().split():
        move = board.parse_uci(move_uci)
        san_moves.append(board.san(move))
        board.push(move)

    return " ".join(san_moves)


def sample_by_themes(
    tranche: pandas.DataFrame,
    target_per_theme: int = 30,
    popularity_threshold: int = 90,
) -> List:
    """
    Sample puzzles using intelligent thematic diversity algorithm.

    This function implements maximum coverage sampling to ensure diverse
    representation of tactical themes while prioritizing puzzle quality.

    Parameters
    ----------
    tranche : pandas.DataFrame
        DataFrame containing puzzles for a specific ELO range
    target_per_theme : int, default=30
        Maximum number of puzzles to select per theme
    popularity_threshold : int, default=90
        Minimum popularity score for initial selection

    Returns
    -------
    list
        List of selected puzzle rows ensuring thematic diversity
    """
    theme_dict: defaultdict = defaultdict(list)

    for _, row in tranche.iterrows():
        if row['Popularity'] >= popularity_threshold:
            for theme in str(row['Themes']).split():
                theme_dict[theme].append(row)

    selected_ids: set = set()
    selected_rows: List = []

    for puzzles in theme_dict.values():
        count = 0
        for row in puzzles:
            if row['PuzzleId'] not in selected_ids and count < target_per_theme:
                selected_ids.add(row['PuzzleId'])
                selected_rows.append(row)
                count += 1

    if len(selected_rows) < MIN_PUZZLES_PER_RANGE:
        needed = MIN_PUZZLES_PER_RANGE - len(selected_rows)
        extras = tranche[~tranche['PuzzleId'].isin(selected_ids)].sort_values(
            'Popularity', ascending=False
        ).head(needed)
        selected_rows.extend(row for _, row in extras.iterrows())

    return selected_rows


def extract_tranches(
    csv_file: str,
    target_per_theme: int = 30,
    popularity_threshold: int = 90,
) -> None:
    """
    Extract and process puzzle tranches for different ELO ranges.

    Creates separate CSV files for each ELO range with optimally selected puzzles.
    Ranges include: <1000, 1000-1100, 1100-1200, ..., 1700-1800, 1800+

    Parameters
    ----------
    csv_file : str
        Path to the decompressed puzzle database CSV file
    target_per_theme : int, default=30
        Maximum puzzles per theme for balanced sampling
    popularity_threshold : int, default=90
        Minimum popularity threshold for quality filtering
    """
    dataframe = pandas.read_csv(csv_file)
    cols = ['PuzzleId', 'FEN', 'Moves', 'Rating', 'Popularity', 'Themes', 'OpeningTags']
    dataframe = dataframe[cols]

    first_tranche = dataframe[dataframe['Rating'] < 1000]
    sampled_rows = sample_by_themes(
        first_tranche,
        target_per_theme=target_per_theme,
        popularity_threshold=popularity_threshold
    )
    _write_csv_file(sampled_rows, "puzzles_1000minus.csv")
    report_theme_coverage(sampled_rows, "puzzles_1000minus.csv", first_tranche)

    for elo_start in range(1000, 1800, 100):
        elo_end = elo_start + 100
        tranche = dataframe[(dataframe['Rating'] >= elo_start) & (dataframe['Rating'] < elo_end)]
        sampled_rows = sample_by_themes(
            tranche,
            target_per_theme=target_per_theme,
            popularity_threshold=popularity_threshold
        )
        out_file = f"puzzles_{elo_start}_{elo_end}.csv"
        _write_csv_file(sampled_rows, out_file)
        report_theme_coverage(sampled_rows, out_file, tranche)

    last_tranche = dataframe[dataframe['Rating'] >= 1800]
    sampled_rows = sample_by_themes(
        last_tranche,
        target_per_theme=target_per_theme,
        popularity_threshold=popularity_threshold
    )
    _write_csv_file(sampled_rows, "puzzles_1800plus.csv")
    report_theme_coverage(sampled_rows, "puzzles_1800plus.csv", last_tranche)


def _write_csv_file(sampled_rows: List, filename) -> None:
    """
    Write selected puzzle rows to CSV file with proper formatting.
    Parameters
    ----------
    sampled_rows : list
        List of puzzle rows to write
    filename : str
        Output CSV filename
    """
    def _ocp_prefixed_tokens(text: str) -> str:
        tokens = [t for t in re.split(r'[\s,;|]+', text.strip()) if t]
        return " ".join(f"OCP::{t}" for t in tokens)

    with open(filename, "w", encoding="utf-8") as puzzle_file:
        puzzle_file.write(
            "PuzzleId,FEN,Moves_SAN,Rating,Popularity,Themes,OpeningTags,DisplayTheme,Tags\n"
        )

        for row in sampled_rows:
            adj_fen, adj_moves = adjust_fen_and_moves(row['FEN'], row['Moves'])
            san_moves = uci_seq_to_san(adj_fen, adj_moves)

            themes = safe_str(row['Themes'])
            opening = safe_str(row['OpeningTags'])

            oc_themes = _ocp_prefixed_tokens(themes) if themes else ""
            oc_openings = _ocp_prefixed_tokens(opening) if opening else ""
            tags_str = " ".join(x for x in [oc_themes, oc_openings] if x).strip()

            vals = [
                safe_str(row['PuzzleId']),
                adj_fen,
                san_moves,
                safe_str(row['Rating']),
                safe_str(row['Popularity']),
                themes,
                opening,
                safe_str("theme-solarized"),
                tags_str
            ]
            puzzle_file.write(",".join([v.replace(',', ';') for v in vals]) + "\n")


def report_theme_coverage(
    sampled_rows: List,
    out_file: str,
    tranche: pandas.DataFrame,
) -> None:
    """
    Generate and display theme coverage statistics for the puzzle selection.

    Provides transparency about the thematic diversity achieved in each
    puzzle set, showing coverage percentage and theme distribution.

    Parameters
    ----------
    sampled_rows : list
        Selected puzzle rows for analysis
    out_file : str
        Output filename for context
    tranche : pandas.DataFrame
        Original tranche data for comparison
    """
    selected_themes: set = set()
    theme_freq = {}

    for row in sampled_rows:
        for theme in str(row['Themes']).split():
            selected_themes.add(theme)
            theme_freq[theme] = theme_freq.get(theme, 0) + 1

    tranche_themes = {
        theme
        for themes_str in (tranche['Themes'].fillna('').astype(str) if 'Themes' in tranche.columns else [])
        for theme in themes_str.split()
        if theme
    }

    percentage_coverage = len(selected_themes) / max(len(tranche_themes), 1) * 100

    sorted_freq = sorted(theme_freq.items(), key=lambda x: -x[1])
    first_themes = sorted_freq[:5]
    last_themes = sorted_freq[-5:] if len(sorted_freq) >= 5 else sorted_freq

    print(f"\n📊 Theme coverage for {out_file}:")
    print(f"- Selected puzzles: {len(sampled_rows)}")
    print(f"- Unique themes covered: {len(selected_themes)}")
    print(f"- Distinct themes in tranche (all puzzles): {len(tranche_themes)}")
    print(f"- Real thematic coverage percentage: {percentage_coverage:.1f}%")

    for theme, freq in first_themes:
        print(f"  • {theme}: {freq} puzzles")
    print("  • …")

    for theme, freq in last_themes:
        print(f"  • {theme}: {freq} puzzles")
    print("—" * 35)


def main() -> None:
    """
    Main execution function.

    Downloads the Lichess puzzle database, processes it through intelligent
    thematic sampling, and generates optimized puzzle sets for different
    ELO ranges suitable for Woodpecker method and spaced repetition training.
    """
    download_puzzle_db()
    decompress_zst()
    extract_tranches(CSV_FILE, target_per_theme=20, popularity_threshold=90)


if __name__ == "__main__":
    main()
