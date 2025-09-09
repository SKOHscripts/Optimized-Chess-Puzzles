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
import pandas as pd
import requests
import chess
from collections import defaultdict

# Constants for database URLs and file names
PUZZLE_URL = "https://database.lichess.org/lichess_db_puzzle.csv.zst"
PUZZLE_FILE = "lichess_db_puzzle.csv.zst"
CSV_FILE = "lichess_db_puzzle.csv"


def safe_str(value):
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
    if pd.isna(value):
        return ""
    return str(value)


def adjust_fen_and_moves(fen, moves):
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

    # Apply the first move to the FEN to get the real puzzle position
    if moves_list:
        first_move = board.parse_uci(moves_list[0])
        board.push(first_move)
        new_fen = board.fen()
        # Remove the first move from the sequence
        rest_moves = " ".join(moves_list[1:])
    else:
        new_fen = fen
        rest_moves = ""

    return new_fen, rest_moves


def download_puzzle_db():
    """
    Download the Lichess puzzle database if not already present.

    Downloads the compressed puzzle database from Lichess servers.
    The file is approximately 200MB compressed.
    """
    if not os.path.exists(PUZZLE_FILE):
        print("Downloading puzzle database...")
        r = requests.get(PUZZLE_URL, stream=True)
        with open(PUZZLE_FILE, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Download completed.")
    else:
        print("File already downloaded.")


def decompress_zst():
    """
    Decompress the .zst puzzle database file to CSV format.

    Requires zstd to be installed on the system.
    The decompressed file is approximately 1GB.
    """
    if not os.path.exists(CSV_FILE):
        print("Decompressing zst file...")
        os.system(f"zstd -d {PUZZLE_FILE}")
        print("Decompression completed.")
    else:
        print("CSV file already decompressed.")


def uci_seq_to_san(fen, uci_moves):
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


def sample_by_themes(tranche, target_per_theme=30, popularity_threshold=90):
    """
    Sample puzzles using intelligent thematic diversity algorithm.

    This function implements maximum coverage sampling to ensure diverse
    representation of tactical themes while prioritizing puzzle quality.

    Parameters
    ----------
    tranche : pd.DataFrame
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
    # Group puzzles by themes for balanced sampling
    theme_dict = defaultdict(list)

    for idx, row in tranche.iterrows():
        # Split multiple themes (space-separated)
        for theme in str(row['Themes']).split():
            if row['Popularity'] >= popularity_threshold:
                theme_dict[theme].append(row)

    # Sample up to target_per_theme puzzles for each theme
    selected_ids = set()
    selected_rows = []

    for theme, puzzles in theme_dict.items():
        count = 0
        for row in puzzles:
            if row['PuzzleId'] not in selected_ids and count < target_per_theme:
                selected_ids.add(row['PuzzleId'])
                selected_rows.append(row)
                count += 1

    # For rare themes, add puzzles with lower popularity to ensure coverage
    remaining_themes = [theme for theme in theme_dict if len(theme_dict[theme]) == 0]

    for theme in remaining_themes:
        theme_puzzles = tranche[tranche['Themes'].str.contains(theme, na=False)]
        count = 0
        for idx, row in theme_puzzles.iterrows():
            if row['PuzzleId'] not in selected_ids and count < target_per_theme // 2:
                selected_ids.add(row['PuzzleId'])
                selected_rows.append(row)
                count += 1

    # Ensure minimum puzzle count for intensive training
    if len(selected_rows) < 700:
        needed = 700 - len(selected_rows)
        extras = tranche[~tranche['PuzzleId'].isin(selected_ids)].sort_values(
            'Popularity', ascending=False
        ).head(needed)
        selected_rows.extend([row for idx, row in extras.iterrows()])

    return selected_rows


def extract_tranches(csv_file, target_per_theme=30, popularity_threshold=90):
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
    # Load the complete puzzle database
    df = pd.read_csv(csv_file)
    cols = ['PuzzleId', 'FEN', 'Moves', 'Rating', 'Popularity', 'Themes', 'OpeningTags']
    df = df[cols]

    # Process beginner range: ELO < 1000
    first_tranche = df[df['Rating'] < 1000]
    sampled_rows = sample_by_themes(
        first_tranche,
        target_per_theme=target_per_theme,
        popularity_threshold=popularity_threshold
    )
    _write_csv_file(sampled_rows, "puzzles_1000minus.csv")
    report_theme_coverage(sampled_rows, "puzzles_1000minus.csv", first_tranche)

    # Process intermediate ranges: 1000-1800 ELO in 100-point increments
    for elo_start in range(1000, 1800, 100):
        elo_end = elo_start + 100
        tranche = df[(df['Rating'] >= elo_start) & (df['Rating'] < elo_end)]
        sampled_rows = sample_by_themes(
            tranche,
            target_per_theme=target_per_theme,
            popularity_threshold=popularity_threshold
        )
        out_file = f"puzzles_{elo_start}_{elo_end}.csv"
        _write_csv_file(sampled_rows, out_file)
        report_theme_coverage(sampled_rows, out_file, tranche)

    # Process advanced range: ELO >= 1800
    last_tranche = df[df['Rating'] >= 1800]
    sampled_rows = sample_by_themes(
        last_tranche,
        target_per_theme=target_per_theme,
        popularity_threshold=popularity_threshold
    )
    _write_csv_file(sampled_rows, "puzzles_1800plus.csv")
    report_theme_coverage(sampled_rows, "puzzles_1800plus.csv", last_tranche)


def _write_csv_file(sampled_rows, filename):
    """
    Write selected puzzle rows to CSV file with proper formatting.

    Parameters
    ----------
    sampled_rows : list
        List of puzzle rows to write
    filename : str
        Output CSV filename
    """
    with open(filename, "w", encoding="utf-8") as f:
        # Write CSV header
        f.write("PuzzleId,FEN,Moves_SAN,Rating,Popularity,Themes,OpeningTags,Tags\n")

        for row in sampled_rows:
            # Adjust FEN position and convert moves to SAN notation
            adj_fen, adj_moves = adjust_fen_and_moves(row['FEN'], row['Moves'])
            san_moves = uci_seq_to_san(adj_fen, adj_moves)

            # Clean theme and opening data
            themes = safe_str(row['Themes'])
            opening = safe_str(row['OpeningTags'])

            # Create unified tags column for easy filtering
            tags_str = f"{themes} {opening}".strip(" ")

            # Prepare row values
            vals = [
                safe_str(row['PuzzleId']),
                adj_fen,
                san_moves,
                safe_str(row['Rating']),
                safe_str(row['Popularity']),
                themes,
                opening,
                tags_str
            ]

            # Write row, replacing commas to avoid CSV conflicts
            f.write(",".join([v.replace(',', ';') for v in vals]) + "\n")


def report_theme_coverage(sampled_rows, out_file, tranche):
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
    tranche : pd.DataFrame
        Original tranche data for comparison
    """
    # Analyze themes present in the final selection
    selected_themes = set()
    theme_freq = {}

    for row in sampled_rows:
        for theme in str(row['Themes']).split():
            selected_themes.add(theme)
            theme_freq[theme] = theme_freq.get(theme, 0) + 1

    # Analyze all themes available in the tranche (no threshold filtering)
    tranche_themes = set()
    for idx, row in tranche.iterrows():
        for theme in str(row['Themes']).split():
            tranche_themes.add(theme)

    # Calculate coverage percentage
    percentage_coverage = len(selected_themes) / max(len(tranche_themes), 1) * 100

    # Sort themes by frequency for reporting
    sorted_freq = sorted(theme_freq.items(), key=lambda x: -x[1])
    first_themes = sorted_freq[:5]  # Most represented themes
    last_themes = sorted_freq[-5:] if len(sorted_freq) >= 5 else sorted_freq  # Least represented

    # Display coverage report
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


def main():
    """
    Main execution function.

    Downloads the Lichess puzzle database, processes it through intelligent
    thematic sampling, and generates optimized puzzle sets for different
    ELO ranges suitable for Woodpecker method and spaced repetition training.
    """
    # Download and prepare the puzzle database
    download_puzzle_db()
    decompress_zst()

    # Process and extract puzzle tranches with optimized parameters
    # Adjust target_per_theme for more/fewer puzzles per theme
    extract_tranches(CSV_FILE, target_per_theme=20, popularity_threshold=90)


if __name__ == "__main__":
    main()
