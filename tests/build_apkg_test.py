"""
Tests for build_apkg.py — stable identifiers and dynamic deck descriptions.

Key invariants:
  1. Note GUID  — keyed on Puzzle ID only (not on mutable fields)
  2. Model ID   — hardcoded constant
  3. Deck IDs   — derived from deck name via SHA1
  4. Descriptions — contain puzzle count, themes, ELO stats from the rows
"""

import sys
import os
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_apkg
from build_apkg import (
    PuzzleNote,
    MODEL_ID,
    _deck_id,
    _build_model,
    _build_description,
    _load_deck_stats,
    _row_to_note,
    build_sample,
    ALL_DECKS,
    DECK_PARENT,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_model():
    """Return a minimal model using stub templates."""
    import genanki
    return genanki.Model(
        MODEL_ID,
        "Test Model",
        fields=build_apkg.NOTE_FIELDS,
        templates=[{"name": "Card 1", "qfmt": "{{PuzzleID}}", "afmt": "{{FEN}}"}],
    )


def _make_row(puzzle_id: str, rating: str = "1200", popularity: str = "90") -> dict:
    return {
        "PuzzleID": puzzle_id,
        "FEN": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "Moves": "e4",
        "Rating": rating,
        "Popularity": popularity,
        "Themes": "fork",
        "Opening": "",
        "Display Theme": "theme-solarized",
        "Tags": "OCP::fork",
    }


# ---------------------------------------------------------------------------
# 1. Note GUID is anchored to Puzzle ID only
# ---------------------------------------------------------------------------

class TestPuzzleNoteGuid:
    def test_guid_is_stable_across_builds(self):
        """Same PuzzleID → same GUID regardless of other field values."""
        model = _make_model()
        note1 = _row_to_note(_make_row("abc123", rating="1200", popularity="90"), model)
        note2 = _row_to_note(_make_row("abc123", rating="1500", popularity="55"), model)
        assert note1.guid == note2.guid

    def test_different_puzzle_ids_give_different_guids(self):
        model = _make_model()
        note_a = _row_to_note(_make_row("puzzle_A"), model)
        note_b = _row_to_note(_make_row("puzzle_B"), model)
        assert note_a.guid != note_b.guid

    def test_guid_is_deterministic_across_instances(self):
        """Two independent PuzzleNote objects with the same ID must agree."""
        model = _make_model()
        first  = _row_to_note(_make_row("stable_id"), model)
        second = _row_to_note(_make_row("stable_id"), model)
        assert first.guid == second.guid

    def test_row_to_note_returns_puzzle_note(self):
        model = _make_model()
        note = _row_to_note(_make_row("xyz"), model)
        assert isinstance(note, PuzzleNote)


# ---------------------------------------------------------------------------
# 2. Model ID is a stable constant
# ---------------------------------------------------------------------------

class TestModelId:
    def test_model_id_is_hardcoded(self):
        assert MODEL_ID == 1757360269638

    def test_two_model_builds_share_id(self):
        """_build_model must always embed MODEL_ID."""
        import unittest.mock as mock
        with mock.patch("builtins.open", mock.mock_open(read_data="")):
            m1 = _build_model("", "", "")
            m2 = _build_model("", "", "")
        assert m1.model_id == m2.model_id == MODEL_ID


# ---------------------------------------------------------------------------
# 3. Deck IDs are derived deterministically from deck names
# ---------------------------------------------------------------------------

class TestDeckIds:
    def test_same_name_gives_same_id(self):
        assert _deck_id("foo") == _deck_id("foo")

    def test_different_names_give_different_ids(self):
        assert _deck_id("deck_A") != _deck_id("deck_B")

    def test_all_subdeck_ids_are_stable(self):
        """Each sub-deck has a reproducible ID across two calls."""
        for _, suffix in ALL_DECKS:
            name = f"{DECK_PARENT}::{suffix}"
            assert _deck_id(name) == _deck_id(name)

    def test_all_subdeck_ids_are_distinct(self):
        ids = [_deck_id(f"{DECK_PARENT}::{s}") for _, s in ALL_DECKS]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# 4. Integration: build_sample produces stable .apkg
# ---------------------------------------------------------------------------

class TestBuildSampleStability:
    def _build_and_collect(self, tmp_path):
        out = str(tmp_path / "sample.apkg")
        build_sample(out)
        return out

    def test_note_guids_are_consistent_across_two_builds(self):
        """Notes built from the same SAMPLE_CARDS have identical GUIDs."""
        model = _make_model()
        guids_first  = [_row_to_note(c, model).guid for c in build_apkg.SAMPLE_CARDS]
        guids_second = [_row_to_note(c, model).guid for c in build_apkg.SAMPLE_CARDS]
        assert guids_first == guids_second

    def test_apkg_contains_expected_entries(self, tmp_path):
        out = str(tmp_path / "sample.apkg")
        build_sample(out)
        with zipfile.ZipFile(out) as z:
            names = z.namelist()
        assert "collection.anki2" in names
        assert "collection.anki21" in names
        assert "meta" in names


# ---------------------------------------------------------------------------
# 5. Deck descriptions
# ---------------------------------------------------------------------------

def _make_themed_row(puzzle_id: str, themes: str, rating: str = "1200", popularity: str = "90") -> dict:
    return {
        "PuzzleID": puzzle_id,
        "FEN": "",
        "Moves": "",
        "Rating": rating,
        "Popularity": popularity,
        "Themes": themes,
        "Opening": "",
        "Display Theme": "theme-solarized",
        "Tags": "",
    }


class TestBuildDescription:
    def test_empty_rows_returns_empty_string(self):
        assert _build_description([]) == ""

    def test_singular_puzzle(self):
        desc = _build_description([_make_row("p1")])
        assert "1 puzzle" in desc

    def test_plural_puzzles(self):
        desc = _build_description([_make_row("p1"), _make_row("p2")])
        assert "2 puzzles" in desc

    def test_rating_range_and_average(self):
        rows = [
            _make_themed_row("p1", "fork", rating="1000"),
            _make_themed_row("p2", "pin",  rating="1200"),
        ]
        desc = _build_description(rows)
        assert "1000" in desc
        assert "1200" in desc
        assert "average 1100" in desc

    def test_popularity_average(self):
        rows = [
            _make_themed_row("p1", "fork", popularity="80"),
            _make_themed_row("p2", "fork", popularity="100"),
        ]
        desc = _build_description(rows)
        assert "average 90%" in desc

    def test_themes_listed_by_frequency(self):
        rows = [
            _make_themed_row("p1", "fork pin"),
            _make_themed_row("p2", "fork"),
            _make_themed_row("p3", "pin"),
            _make_themed_row("p4", "fork"),
        ]
        desc = _build_description(rows)
        assert "fork (3)" in desc
        assert "pin (2)" in desc
        assert desc.index("fork (3)") < desc.index("pin (2)")  # fork first (more frequent)

    def test_theme_count_in_description(self):
        rows = [_make_themed_row("p1", "fork pin skewer")]
        desc = _build_description(rows)
        assert "3 themes" in desc

    def test_singular_theme(self):
        rows = [_make_themed_row("p1", "fork")]
        desc = _build_description(rows)
        assert "1 theme" in desc
        assert "1 themes" not in desc

    def test_missing_rating_omits_rating_line(self):
        rows = [_make_themed_row("p1", "fork", rating="")]
        desc = _build_description(rows)
        assert "Rating" not in desc

    def test_missing_popularity_omits_popularity_line(self):
        rows = [_make_themed_row("p1", "fork", popularity="")]
        desc = _build_description(rows)
        assert "Popularity" not in desc

    def test_description_is_stable(self):
        rows = [_make_row("p1"), _make_row("p2")]
        assert _build_description(rows) == _build_description(rows)

    def test_sample_cards_have_description(self):
        desc = _build_description(list(build_apkg.SAMPLE_CARDS))
        assert "3 puzzles" in desc
        assert "fork" in desc

    def test_coverage_shown_when_provided(self):
        rows = [_make_themed_row("p1", "fork pin")]
        desc = _build_description(rows, coverage=74.3)
        assert "74.3%" in desc
        assert "of tranche themes" in desc

    def test_coverage_absent_when_none(self):
        rows = [_make_themed_row("p1", "fork pin")]
        desc = _build_description(rows, coverage=None)
        assert "tranche" not in desc

    def test_coverage_100_percent(self):
        rows = [_make_themed_row("p1", "fork")]
        desc = _build_description(rows, coverage=100.0)
        assert "100.0%" in desc


class TestLoadDeckStats:
    def test_returns_empty_dict_when_file_absent(self, tmp_path):
        assert _load_deck_stats(str(tmp_path)) == {}

    def test_loads_coverage_pct(self, tmp_path):
        import json
        stats = {
            "puzzles_1000minus.csv": {
                "selected": 847,
                "unique_themes_sample": 23,
                "unique_themes_tranche": 31,
                "coverage_pct": 74.2,
            }
        }
        (tmp_path / "puzzles_stats.json").write_text(json.dumps(stats))
        loaded = _load_deck_stats(str(tmp_path))
        assert loaded["puzzles_1000minus.csv"]["coverage_pct"] == 74.2
