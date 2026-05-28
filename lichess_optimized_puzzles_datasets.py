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

import json
import os
import re
import subprocess
from typing import Dict, List, Set, Tuple

import chess
import pandas
import requests  # type: ignore[import-untyped]

PUZZLE_URL = "https://database.lichess.org/lichess_db_puzzle.csv.zst"
PUZZLE_FILE = "lichess_db_puzzle.csv.zst"
CSV_FILE = "lichess_db_puzzle.csv"

MIN_PUZZLES_PER_RANGE = 700
TARGET_DECK_SIZE = 1200
DOWNLOAD_TIMEOUT = 120
DOWNLOAD_CHUNK_SIZE = 8192

# Bayesian quality-score hyperparameters:
# quality = (NbPlays * p + QUALITY_WEIGHT * QUALITY_PRIOR) / (NbPlays + QUALITY_WEIGHT)
# A puzzle with few plays is pulled toward the prior, preventing a noisy 100%/3-plays
# from outranking a well-evidenced 95%/5000-plays puzzle.
QUALITY_WEIGHT: int = 30
QUALITY_PRIOR: float = 0.5

# Maximum RatingDeviation for the "calibrated" soft-preference sort key.
# Puzzles with RD above this are still selectable but ranked lower.
RD_MAX: int = 90

# Lichess Themes tags that are NOT tactical motifs — metadata tags that would
# inflate the diversity count and coverage metric without reflecting pedagogical
# content. Applied as a denylist (fail-open: new genuine motifs in the Lichess
# vocabulary are kept automatically).
THEME_DENYLIST: Set[str] = {
    # Move-count / length descriptors
    "oneMove", "short", "long", "veryLong",
    # Forced-mate labels (the motif is checkmate, which is already tactical, but
    # the sub-labels add no diversity signal — every "mateIn2" theme is the same
    # diversity unit regardless of the motif that leads to it)
    "mate", "mateIn1", "mateIn2", "mateIn3", "mateIn4", "mateIn5",
    # Evaluation buckets (outcome, not motif)
    "crushing", "advantage", "equality",
    # Game-phase tags (broad phases, not specific patterns; sub-motifs like
    # pawnEndgame, rookEndgame, etc. are kept because they are pedagogically distinct)
    "opening", "middlegame", "endgame",
    # Player-strength provenance (not a tactical pattern)
    "master", "masterVsMaster", "superGM",
}

# Additional 100-ELO sub-tranches that replace the unbounded >=1800 tail, which
# was too heterogeneous (1800–2800+) for the Woodpecker method. Each entry is
# (lower_bound, upper_bound, output_filename). The final >=2200 tranche is
# handled separately in extract_tranches.
UPPER_TRANCHE_EDGES: List[Tuple[int, int, str]] = [
    (1800, 1900, "puzzles_1800_1900.csv"),
    (1900, 2000, "puzzles_1900_2000.csv"),
    (2000, 2200, "puzzles_2000_2200.csv"),
]


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


# ---------------------------------------------------------------------------
# Sampling helpers
# ---------------------------------------------------------------------------


def _meaningful_motifs(themes_str) -> List[str]:
    """Return the tactical-motif tokens from a Themes string, excluding metadata tags."""
    return [t for t in str(themes_str).split() if t and t not in THEME_DENYLIST]


def _augment_tranche(
    tranche: pandas.DataFrame,
    popularity_threshold: int,
    min_nbplays: int,
) -> Tuple[pandas.DataFrame, set, pandas.DataFrame]:
    """
    Add computed columns to *tranche* and return (work, all_motifs, primary_pool).

    Columns added to *work*:
    - ``_quality``: Bayesian confidence-shrunk quality score in [0, 1].
    - ``_rd_ok``:   1 if RatingDeviation ≤ RD_MAX, else 0 (soft preference).
    - ``_motifs``:  List of meaningful tactical motifs (denylist applied).

    *primary_pool* is the subset of *work* satisfying both the popularity threshold
    and (when NbPlays is present) the minimum-play confidence floor.
    """
    has_nbplays = 'NbPlays' in tranche.columns
    nbplays = tranche['NbPlays'].fillna(0).astype(float) if has_nbplays else pandas.Series(0.0, index=tranche.index)
    p = (tranche['Popularity'].clip(-100, 100) + 100.0) / 200.0
    quality = (nbplays * p + QUALITY_WEIGHT * QUALITY_PRIOR) / (nbplays + QUALITY_WEIGHT)

    has_rd = 'RatingDeviation' in tranche.columns
    rd_ok = (tranche['RatingDeviation'].fillna(200) <= RD_MAX).astype(int) if has_rd else pandas.Series(1, index=tranche.index)

    work = tranche.copy()
    work['_quality'] = quality
    work['_rd_ok'] = rd_ok
    work['_motifs'] = work['Themes'].apply(_meaningful_motifs)

    all_motifs: set = {m for ml in work['_motifs'] for m in ml}

    prim_mask = work['Popularity'] >= popularity_threshold
    if has_nbplays:
        prim_mask = prim_mask & (work['NbPlays'].fillna(0) >= min_nbplays)
    return work, all_motifs, work[prim_mask]


def _fast_pass(
    primary_pool: pandas.DataFrame,
    all_motifs: set,
    target_per_theme: int,
) -> List[str]:
    """
    Vectorized first-pass selection: best puzzles per motif from the quality pool.

    Explodes the primary pool on meaningful motifs, sorts by
    (motif, rd_ok desc, quality desc, PuzzleId asc) for determinism, then
    takes the top *target_per_theme* puzzles per motif. Deduplication ensures
    each PuzzleId appears at most once in the returned list.

    Returns an ordered list of PuzzleIds.
    """
    if primary_pool.empty or not all_motifs:
        return []
    exploded = primary_pool.explode('_motifs')
    exploded = exploded[exploded['_motifs'].notna() & (exploded['_motifs'] != '')]
    exploded = exploded.sort_values(
        ['_motifs', '_rd_ok', '_quality', 'PuzzleId'],
        ascending=[True, False, False, True],
    )
    per_motif_top = exploded.groupby('_motifs').head(target_per_theme)
    seen: List[str] = []
    seen_set: set = set()
    for pid in per_motif_top['PuzzleId']:
        if pid not in seen_set:
            seen_set.add(pid)
            seen.append(pid)
    return seen


def _find_complement_pids(
    work: pandas.DataFrame,
    selected_ids: set,
    uncovered: set,
) -> List[str]:
    """
    For each motif in *uncovered*, find the single best available puzzle.

    No popularity threshold is applied so that motifs whose only representatives
    are low-popularity puzzles are still covered.  Returns a list of PuzzleIds
    (one per uncovered motif, no duplicates).
    """
    if not uncovered:
        return []
    pool = work[~work['PuzzleId'].isin(selected_ids)].explode('_motifs')
    pool = pool[pool['_motifs'].isin(uncovered)]
    pool = pool.sort_values(
        ['_motifs', '_rd_ok', '_quality', 'PuzzleId'],
        ascending=[True, False, False, True],
    )
    result: List[str] = []
    covered: set = set()
    used: set = set()
    for _, row in pool.iterrows():
        motif = row['_motifs']
        pid = row['PuzzleId']
        if motif not in covered and pid not in used:
            covered.add(motif)
            used.add(pid)
            result.append(pid)
    return result


def _quality_topup(
    work: pandas.DataFrame,
    selected_ids: set,
    motif_count: dict,
    target_per_theme: int,
    n_remaining: int,
) -> List[str]:
    """
    Fill up to *n_remaining* more puzzles from the full tranche by quality.

    Respects the true per-motif cap: a candidate is only added when at least one
    of its motifs has not yet reached *target_per_theme* (or it has no motifs,
    in which case it is motif-neutral and added unconditionally).

    Returns an ordered list of PuzzleIds.
    """
    if n_remaining <= 0:
        return []
    remaining = work[~work['PuzzleId'].isin(selected_ids)].sort_values(
        ['_rd_ok', '_quality', 'PuzzleId'], ascending=[False, False, True]
    )
    result: List[str] = []
    for _, row in remaining.iterrows():
        if len(result) >= n_remaining:
            break
        motifs = row['_motifs']
        if not motifs or any(motif_count.get(m, 0) < target_per_theme for m in motifs):
            result.append(row['PuzzleId'])
    return result


def _process_tranche(
    tranche_df: pandas.DataFrame,
    out_file: str,
    all_stats: Dict[str, Dict],
    target_per_theme: int,
    popularity_threshold: int,
    target_deck_size: int,
) -> None:
    """Sample, write, and record coverage stats for one ELO tranche."""
    sampled_rows = sample_by_themes(
        tranche_df,
        target_per_theme=target_per_theme,
        popularity_threshold=popularity_threshold,
        target_deck_size=target_deck_size,
    )
    _write_csv_file(sampled_rows, out_file)
    all_stats[out_file] = report_theme_coverage(sampled_rows, out_file, tranche_df)


# ---------------------------------------------------------------------------
# Public sampling API
# ---------------------------------------------------------------------------


def sample_by_themes(
    tranche: pandas.DataFrame,
    target_per_theme: int = 17,
    popularity_threshold: int = 90,
    target_deck_size: int = TARGET_DECK_SIZE,
    min_nbplays: int = 20,
) -> List:
    """
    Sample puzzles using intelligent thematic diversity algorithm.

    Pipeline:
    1. Augment each puzzle with a Bayesian quality score and meaningful motifs.
    2. Vectorized fast-pass: top *target_per_theme* puzzles per motif from the
       primary quality pool (Popularity ≥ threshold, NbPlays ≥ min_nbplays when
       available), ranked by (rd_ok, quality, PuzzleId).
    3. Theme-aware complement: for motifs still uncovered, force in the best
       available puzzle regardless of popularity — so even rare themes in low-
       popularity puzzles are covered.
    4. Quality top-up to *target_deck_size*, respecting the true per-motif cap
       (counted across all co-occurring motifs of each selected puzzle).
    5. Safety fill to MIN_PUZZLES_PER_RANGE if the tranche is too small to reach
       it through quality selection alone.

    Parameters
    ----------
    tranche : pandas.DataFrame
        DataFrame containing puzzles for a specific ELO range
    target_per_theme : int, default=17
        Maximum number of puzzles per tactical motif (true cap, counting
        co-occurrences across all motifs of every selected puzzle)
    popularity_threshold : int, default=90
        Minimum popularity score for the primary quality pool
    target_deck_size : int, default=TARGET_DECK_SIZE
        Desired number of cards in the output deck
    min_nbplays : int, default=20
        Minimum number of plays for the primary quality pool
        (disabled when the NbPlays column is absent)

    Returns
    -------
    list
        List of selected puzzle rows ensuring thematic diversity
    """
    if tranche.empty:
        return []

    work, all_motifs, primary_pool = _augment_tranche(tranche, popularity_threshold, min_nbplays)
    # iloc-based lookup: PuzzleId stays a regular column; work_by_pid maps it to row position.
    work_by_pid: Dict[str, int] = {str(pid): i for i, pid in enumerate(work['PuzzleId'])}

    selected_ids: set = set()
    selected_rows: List = []
    motif_count: dict = {}

    def _add(pid: str) -> None:
        if pid in selected_ids:
            return
        row = work.iloc[work_by_pid[str(pid)]]
        selected_ids.add(pid)
        selected_rows.append(row)
        for m in row['_motifs']:
            motif_count[m] = motif_count.get(m, 0) + 1

    for pid in _fast_pass(primary_pool, all_motifs, target_per_theme):
        _add(pid)

    for pid in _find_complement_pids(work, selected_ids, all_motifs - set(motif_count)):
        _add(pid)

    for pid in _quality_topup(work, selected_ids, motif_count, target_per_theme, target_deck_size - len(selected_rows)):
        _add(pid)

    if len(selected_rows) < MIN_PUZZLES_PER_RANGE:
        needed = MIN_PUZZLES_PER_RANGE - len(selected_rows)
        extras = work[~work['PuzzleId'].isin(selected_ids)].sort_values(
            ['_rd_ok', '_quality', 'PuzzleId'], ascending=[False, False, True]
        ).head(needed)
        for _, row in extras.iterrows():
            selected_rows.append(row)
            selected_ids.add(row['PuzzleId'])

    return selected_rows


def extract_tranches(
    csv_file: str,
    target_per_theme: int = 17,
    popularity_threshold: int = 90,
    target_deck_size: int = TARGET_DECK_SIZE,
) -> Dict[str, Dict]:
    """
    Extract and process puzzle tranches for different ELO ranges.

    Creates separate CSV files for each ELO range with optimally selected puzzles.
    Ranges: <1000, 1000-1100, …, 1700-1800, 1800-1900, 1900-2000, 2000-2200, ≥2200.
    Also writes puzzles_stats.json with per-tranche coverage stats consumed by
    build_apkg.py when generating deck descriptions.

    Parameters
    ----------
    csv_file : str
        Path to the decompressed puzzle database CSV file
    target_per_theme : int, default=17
        Maximum puzzles per theme for balanced sampling
    popularity_threshold : int, default=90
        Minimum popularity threshold for quality filtering
    target_deck_size : int, default=TARGET_DECK_SIZE
        Target number of puzzles per output deck
    """
    dataframe = pandas.read_csv(csv_file)
    desired = ['PuzzleId', 'FEN', 'Moves', 'Rating', 'Popularity', 'Themes',
               'OpeningTags', 'NbPlays', 'RatingDeviation']
    dataframe = dataframe[[c for c in desired if c in dataframe.columns]]
    all_stats: Dict[str, Dict] = {}

    _process_tranche(dataframe[dataframe['Rating'] < 1000], "puzzles_1000minus.csv",
                     all_stats, target_per_theme, popularity_threshold, target_deck_size)

    for elo_start in range(1000, 1800, 100):
        elo_end = elo_start + 100
        tranche = dataframe[(dataframe['Rating'] >= elo_start) & (dataframe['Rating'] < elo_end)]
        _process_tranche(tranche, f"puzzles_{elo_start}_{elo_end}.csv",
                         all_stats, target_per_theme, popularity_threshold, target_deck_size)

    for lo, hi, filename in UPPER_TRANCHE_EDGES:
        _process_tranche(
            dataframe[(dataframe['Rating'] >= lo) & (dataframe['Rating'] < hi)],
            filename, all_stats, target_per_theme, popularity_threshold, target_deck_size,
        )

    _process_tranche(dataframe[dataframe['Rating'] >= 2200], "puzzles_2200plus.csv",
                     all_stats, target_per_theme, popularity_threshold, target_deck_size)

    with open("puzzles_stats.json", "w", encoding="utf-8") as stats_file:
        json.dump(all_stats, stats_file, indent=2)
    return all_stats


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
            "PuzzleID,FEN,Moves,Rating,Popularity,Themes,Opening,Display Theme,Tags\n"
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
) -> Dict:
    """
    Generate and display theme coverage statistics for the puzzle selection.

    Reports both full-theme and motif-only (denylist-filtered) coverage so the
    deck descriptions reflect genuine tactical diversity rather than metadata
    tags inflating the denominator.

    Parameters
    ----------
    sampled_rows : list
        Selected puzzle rows for analysis
    out_file : str
        Output filename for context
    tranche : pandas.DataFrame
        Original tranche data for comparison

    Returns
    -------
    dict
        Stats dict with keys: selected, unique_themes_sample,
        unique_themes_tranche, unique_motifs_sample, unique_motifs_tranche,
        coverage_pct (motif-based), coverage_pct_all (all-theme-based).
        Consumed by build_apkg.py to populate deck descriptions.
    """
    selected_themes: set = set()
    selected_motifs: set = set()
    theme_freq: dict = {}

    for row in sampled_rows:
        for t in str(row['Themes']).split():
            selected_themes.add(t)
            theme_freq[t] = theme_freq.get(t, 0) + 1
        for m in _meaningful_motifs(str(row['Themes'])):
            selected_motifs.add(m)

    tranche_themes = {
        t
        for ts in (tranche['Themes'].fillna('').astype(str) if 'Themes' in tranche.columns else [])
        for t in ts.split()
        if t
    }
    tranche_motifs = {
        m
        for ts in (tranche['Themes'].fillna('').astype(str) if 'Themes' in tranche.columns else [])
        for m in _meaningful_motifs(ts)
    }

    pct_all = len(selected_themes) / max(len(tranche_themes), 1) * 100
    pct_motifs = len(selected_motifs) / max(len(tranche_motifs), 1) * 100

    sorted_freq = sorted(theme_freq.items(), key=lambda x: -x[1])
    first_themes = sorted_freq[:5]
    last_themes = sorted_freq[-5:] if len(sorted_freq) >= 5 else sorted_freq

    print(f"\n📊 Theme coverage for {out_file}:")
    print(f"- Selected puzzles: {len(sampled_rows)}")
    print(f"- Unique themes covered: {len(selected_themes)} (motifs: {len(selected_motifs)})")
    print(f"- Distinct themes in tranche: {len(tranche_themes)} (motifs: {len(tranche_motifs)})")
    print(f"- Motif coverage: {pct_motifs:.1f}%  (all-theme coverage: {pct_all:.1f}%)")

    for theme, freq in first_themes:
        print(f"  • {theme}: {freq} puzzles")
    print("  • …")

    for theme, freq in last_themes:
        print(f"  • {theme}: {freq} puzzles")
    print("—" * 35)

    return {
        "selected": len(sampled_rows),
        "unique_themes_sample": len(selected_themes),
        "unique_themes_tranche": len(tranche_themes),
        "unique_motifs_sample": len(selected_motifs),
        "unique_motifs_tranche": len(tranche_motifs),
        "coverage_pct": round(pct_motifs, 1),
        "coverage_pct_all": round(pct_all, 1),
    }


def main() -> None:
    """
    Main execution function.

    Downloads the Lichess puzzle database, processes it through intelligent
    thematic sampling, and generates optimized puzzle sets for different
    ELO ranges suitable for Woodpecker method and spaced repetition training.
    """
    download_puzzle_db()
    decompress_zst()
    extract_tranches(CSV_FILE, target_per_theme=17, popularity_threshold=90,
                     target_deck_size=TARGET_DECK_SIZE)


if __name__ == "__main__":
    main()
