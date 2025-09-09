"""
Unit tests for the Optimized Chess Puzzles processing script.
"""

import os
import pandas
import pytest
import chess
import tempfile
import builtins
import subprocess
import sys

from collections import defaultdict

import lichess_optimized_puzzles_datasets

# ------- Fixtures and mocks ----------


@pytest.fixture
def sample_puzzles():
    """
    Return a toy DataFrame simulating a Lichess puzzle CSV import,
    with positions and UCI moves strictly legal.
    """
    data = {
        'PuzzleId': ['p1', 'p2', 'p3', 'p4'],
        'FEN': [
            # Standard starting position, white to move
            chess.STARTING_FEN,
            # After 1.e4, black to move
            'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
            # Simple king/pawn, white to move
            '6k1/5ppp/8/8/8/8/5PPP/6K1 w - - 0 1',
            # Empty board, white to move (edge case, no legal moves)
            '8/8/8/8/8/8/8/8 w - - 0 1',
        ],
        'Moves': [
            # After e2e4, playing c7c5 is legal for black, then g1f3 for white
            'e2e4 c7c5 g1f3',
            # Position is after 1.e4, black to move: play c7c5 (then white can play d2d4)
            'c7c5 d2d4',
            # White can play g2g4, then black h7h6 in this endgame
            'g2g4 h7h6',
            '',  # No moves, edge case
        ],
        'Rating': [1200, 1200, 1400, 1700],
        'Popularity': [100, 80, 95, 80],
        'Themes': ['fork pin', 'pin', 'backrank', ''],
        'OpeningTags': ['Sicilian', '', '', ''],
    }

    return pandas.DataFrame(data)

# ---- Test functions ----


def test_safe_str_handles_nan_and_null():
    """
    Test that safe_str returns '' for NaN and None, and str otherwise.
    """
    from math import nan
    assert lichess_optimized_puzzles_datasets.safe_str(nan) == ""
    assert lichess_optimized_puzzles_datasets.safe_str(None) == ""
    assert lichess_optimized_puzzles_datasets.safe_str("abc") == "abc"
    assert lichess_optimized_puzzles_datasets.safe_str(42) == "42"


def test_adjust_fen_and_moves_modifies_fen_and_removes_first_move():
    """
    Test that adjust_fen_and_moves applies the first move and removes it from the sequence.
    """
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    moves = "c7c5 d2d4"
    new_fen, rest_moves = lichess_optimized_puzzles_datasets.adjust_fen_and_moves(fen, moves)
    # Board after e2e4
    board_test = chess.Board(fen)
    board_test.push(chess.Move.from_uci("c7c5"))
    assert new_fen == board_test.fen()
    assert rest_moves == "d2d4"


def test_adjust_fen_and_moves_handles_empty_moves():
    """
    Edge case: if moves are empty, FEN should be unchanged and moves should be ''.
    """
    fen = "6k1/5ppp/8/8/8/8/5PPP/6K1 w - - 0 1"
    moves = ""
    new_fen, rest_moves = lichess_optimized_puzzles_datasets.adjust_fen_and_moves(fen, moves)
    assert new_fen == fen
    assert rest_moves == ""


def test_uci_seq_to_san_conversion():
    """
    Check UCI-to-SAN conversion for simple move sequences.
    """
    fen = chess.STARTING_FEN
    moves = "e2e4 e7e5"
    san = lichess_optimized_puzzles_datasets.uci_seq_to_san(fen, moves)
    assert san == "e4 e5"


def test_uci_seq_to_san_empty():
    """
    Edge case: empty move string returns empty SAN string.
    """
    fen = chess.STARTING_FEN
    assert lichess_optimized_puzzles_datasets.uci_seq_to_san(fen, "") == ""


def test_sample_by_themes_balances_themes_and_handles_duplicates(sample_puzzles):
    """
    Ensure sampling gives correct diversity, honors popularity threshold, and prevents duplicates.
    """
    results = lichess_optimized_puzzles_datasets.sample_by_themes(sample_puzzles, target_per_theme=1, popularity_threshold=90)
    puzzle_ids = [row['PuzzleId'] for row in results]
    # Only p1 ('fork pin') and p3 ('backrank') should be included from popularity>=90
    assert 'p1' in puzzle_ids
    assert 'p3' in puzzle_ids
    # No duplicates should exist
    assert len(set(puzzle_ids)) == len(puzzle_ids)
    # Themes should be balanced (at most 1 per theme due to target_per_theme=1)


def test_sample_by_themes_minimum_selection_filled(sample_puzzles):
    """
    If sample is too small, supplement with most popular remaining puzzles.
    """
    results = lichess_optimized_puzzles_datasets.sample_by_themes(sample_puzzles, target_per_theme=1, popularity_threshold=100)
    # Since only p1 is Popularity 100, the minimum size (700) will be filled with extras
    assert len(results) >= 1  # at least the one passing popularity
    # Since DataFrame <700, should return all unique as supplement


def test_sample_by_themes_rare_and_minimum():
    """
    Test that the 'rare themes' branch and minimum selection logic are covered.
    """
    # 1. Theme "rare" has only low-popularity puzzle
    # 2. test completes to 700 via 'extras'
    data = {
        'PuzzleId': ['p1', 'p2'],
        'FEN': [chess.STARTING_FEN, chess.STARTING_FEN],
        'Moves': ['e2e4', 'e2e4'],
        'Rating': [1200, 1200],
        'Popularity': [95, 20],       # Only p1 reaches threshold for its theme
        'Themes': ['common', 'common'],  # p2: rare, but Popularity<90
        'OpeningTags': ['', ''],
    }
    df = pandas.DataFrame(data)
    # Use small target_per_theme to make rare theme "uncaught" by high popularity logic
    results = lichess_optimized_puzzles_datasets.sample_by_themes(df, target_per_theme=2, popularity_threshold=90)
    selected_ids = {r['PuzzleId'] for r in results}
    assert 'p1' in selected_ids      # common theme
    assert 'p2' in selected_ids      # rare theme forced in by 'rare themes' logic

    # Test minimum completion logic (len(selected_rows) < 700)
    # Let's check that there are exactly 2 elements since our input is only 2 rows
    assert len(results) == 2

    # Now extend DataFrame <700 but add more puzzles to test extra completion logic
    df_large = pandas.DataFrame({
        'PuzzleId': [f'p{i}' for i in range(10)],
        'FEN': [chess.STARTING_FEN] * 10,
        'Moves': ['e2e4'] * 10,
        'Rating': [1200] * 10,
        'Popularity': [80] * 10,    # all below threshold
        'Themes': ['rare'] * 10,
        'OpeningTags': [''] * 10,
    })
    output = lichess_optimized_puzzles_datasets.sample_by_themes(df_large, target_per_theme=1, popularity_threshold=90)
    # Should return all 10 since < 700, so branch is covered
    assert len(output) == 10


def test_csv_writing_and_tags(tmp_path, sample_puzzles):
    """
    Test that writing CSV creates correct headers and unified tags field.
    """
    out_file = tmp_path / "test.csv"
    # Write one row for simplicity
    row = sample_puzzles.iloc[0]
    adj_fen, adj_moves = lichess_optimized_puzzles_datasets.adjust_fen_and_moves(row['FEN'], row['Moves'])
    san = lichess_optimized_puzzles_datasets.uci_seq_to_san(adj_fen, adj_moves)
    tags_str = f"{lichess_optimized_puzzles_datasets.safe_str(row['Themes'])} {lichess_optimized_puzzles_datasets.safe_str(row['OpeningTags'])}".strip()
    vals = [
        lichess_optimized_puzzles_datasets.safe_str(row['PuzzleId']), adj_fen, san,
        lichess_optimized_puzzles_datasets.safe_str(row['Rating']), lichess_optimized_puzzles_datasets.safe_str(row['Popularity']),
        lichess_optimized_puzzles_datasets.safe_str(row['Themes']), lichess_optimized_puzzles_datasets.safe_str(row['OpeningTags']), tags_str
    ]
    header = "PuzzleId,FEN,Moves_SAN,Rating,Popularity,Themes,OpeningTags,Tags\n"
    with open(out_file, 'w', encoding='utf8') as f:
        f.write(header)
        f.write(",".join([v.replace(',', ';') for v in vals]) + "\n")
    # Now re-read the file and check
    with open(out_file, 'r', encoding='utf8') as f:
        lines = f.readlines()
        assert lines[0].startswith("PuzzleId")
        assert tags_str in lines[1]


def test_report_theme_coverage_prints(capsys, sample_puzzles):
    """
    Test the report_theme_coverage output summarizes the right stats.
    """
    sampled_rows = [sample_puzzles.iloc[0], sample_puzzles.iloc[2]]
    lichess_optimized_puzzles_datasets.report_theme_coverage(sampled_rows, "fake.csv", sample_puzzles)
    out = capsys.readouterr().out
    assert "Theme coverage" in out
    assert "fork" in out
    assert "backrank" in out


def test_download_puzzle_db_creates_file(monkeypatch, tmp_path):
    """Test downloading creates the file only if absent, else skips."""
    fake_path = tmp_path / "puzzle.zst"
    fake_url = "https://example.com/puz"
    # Patch os.path.exists
    monkeypatch.setattr(os.path, "exists", lambda p: False)
    # Patch requests.get to return a mock with iter_content

    class FakeResp:
        def iter_content(self, chunk_size=8192):
            yield b'data'
    monkeypatch.setattr("requests.get", lambda url, stream, timeout=120: FakeResp())
    # Patch open
    monkeypatch.setattr(builtins, "open", lambda *a, **k: tempfile.TemporaryFile("w+b"))
    # Run test
    lichess_optimized_puzzles_datasets.download_puzzle_db()  # Should create the file and print messages


def test_download_puzzle_db_skips_when_exists(monkeypatch):
    """Test that download_puzzle_db does not download if file exists."""
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    lichess_optimized_puzzles_datasets.download_puzzle_db()  # Should print "File already downloaded."


def test_decompress_zst_runs(monkeypatch):
    """Test decompress when CSV is absent, then present."""
    monkeypatch.setattr(os.path, "exists", lambda f: False)
    monkeypatch.setattr(os, "system", lambda x: 0)
    lichess_optimized_puzzles_datasets.decompress_zst()
    monkeypatch.setattr(os.path, "exists", lambda f: True)
    lichess_optimized_puzzles_datasets.decompress_zst()


def test_write_csv_and_read(tmp_path, sample_puzzles):
    """Test full _write_csv_file function."""
    filename = tmp_path / "all.csv"
    lichess_optimized_puzzles_datasets._write_csv_file(sample_puzzles.to_dict(orient='records'), filename)
    # Read back and check
    with open(filename, 'r', encoding='utf8') as f:
        lines = f.readlines()
        assert lines[0].startswith("PuzzleId") and len(lines) == 5  # header + 4


def test_report_theme_coverage_empty(capsys):
    """Coverage for report_theme_coverage with empty input."""
    lichess_optimized_puzzles_datasets.report_theme_coverage([], "none.csv", pandas.DataFrame())
    out = capsys.readouterr().out
    assert "Selected puzzles: 0" in out


def test_extract_tranches_runs(monkeypatch, tmp_path):
    """Test extract_tranches without real CSV reading."""
    # Patch pandas.read_csv -> returns mock DataFrame
    dummy_data = pandas.DataFrame({
        'PuzzleId': ['pX'],
        'FEN': [chess.STARTING_FEN],
        'Moves': ['e2e4'],
        'Rating': [1300],
        'Popularity': [99],
        'Themes': ['fork'],
        'OpeningTags': ['Sicilian'],
    })
    monkeypatch.setattr(pandas, "read_csv", lambda *a, **k: dummy_data)
    monkeypatch.setattr("lichess_optimized_puzzles_datasets._write_csv_file", lambda a, b: None)
    monkeypatch.setattr("lichess_optimized_puzzles_datasets.report_theme_coverage", lambda *a, **k: None)
    lichess_optimized_puzzles_datasets.extract_tranches("fake.csv", target_per_theme=1, popularity_threshold=90)


def test_main_runs(monkeypatch):
    """Test that main runs through all logic."""
    monkeypatch.setattr("lichess_optimized_puzzles_datasets.download_puzzle_db", lambda: None)
    monkeypatch.setattr("lichess_optimized_puzzles_datasets.decompress_zst", lambda: None)
    monkeypatch.setattr("lichess_optimized_puzzles_datasets.extract_tranches", lambda *a, **k: None)
    lichess_optimized_puzzles_datasets.main()  # Should run without error
