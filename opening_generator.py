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
Chess Opening Deck Generator
============================

This module creates Anki decks for chess openings by taking sequences
of moves in SAN notation and generating CSV files where each line corresponds
to a move to guess from the corresponding FEN position.

Each CSV line represents a move in the opening sequence, with the FEN
position before that move and the move in SAN notation to guess.
"""

from typing import List, Dict
from dataclasses import dataclass
import re
import io
import json
import chess
import chess.pgn
from lichess_optimized_puzzles_datasets import safe_str
import opening_report

@dataclass
class OpeningMove:
    """Represents a move in an opening with its position and metadata."""
    puzzle_id: str
    fen_before: str
    move_san: str
    rating: str
    popularity: str
    themes: str
    category: str = ""  # New field for JSON category

@dataclass
class OpeningVariant:
    """Represents an opening variant with position and moves."""
    name: str
    fen: str
    moves: str  # UCI or SAN notation
    color: str  # 'white' or 'black' - side to train
    themes: str = ""  # Tactical/positional themes
    category: str = ""  # New field for JSON category

class OpeningDeckGenerator:
    """
    Generates Anki CSV files for chess opening training.
    Creates cards showing positions where the player must find the next move
    in the opening sequence.
    """

    def __init__(self):
        self.moves: List[OpeningMove] = []
        self.variants: List[OpeningVariant] = []
        self.puzzle_counter = 1
        self.category_mapping = {}  # Store mapping from opening name to category

    def add_opening_from_pgn(self,
                             name: str,
                             pgn_moves: str,
                             rating: str = "",
                             popularity: str = "",
                             themes: str = "",
                             category: str = "") -> None:
        """
        Add an opening from PGN notation and generate all moves.

        Parameters
        ----------
        name : str
            Name of the opening/variation
        pgn_moves : str
            Moves in PGN notation (e.g., "1.e4 e5 2.Nf3 Nc6")
        rating : str
            Puzzle rating (optional)
        popularity : str
            Puzzle popularity (optional)
        themes : str
            Tactical/positional themes
        category : str
            JSON category name (family)
        """
        moves = self._parse_pgn_to_moves(pgn_moves)

        if not moves:
            print(f"Warning: No valid moves found for {name}")

            return

        # Store category mapping
        self.category_mapping[name] = category

        # Create variant for tracking
        variant = OpeningVariant(
            name=name,
            fen=chess.STARTING_FEN,
            moves=" ".join(moves),
            color="both",  # Default: all moves
            themes=themes,
            category=category
        )

        self.variants.append(variant)

        board = chess.Board()

        for move_san in moves:
            try:
                # Store FEN position BEFORE the move
                fen_before = board.fen()

                # Verify move is legal
                move = board.parse_san(move_san)

                # Create entry for this move
                opening_move = OpeningMove(
                    puzzle_id=f"opening_{self.puzzle_counter:05d} {name}",
                    fen_before=fen_before,
                    move_san=move_san,
                    rating=rating,
                    popularity=popularity,
                    themes=themes,
                    category=category
                )

                self.moves.append(opening_move)
                self.puzzle_counter += 1

                # Play the move to continue
                board.push(move)

            except (ValueError, chess.IllegalMoveError) as e:
                print(f"Error with move '{move_san}' in {name}: {e}")

                break

    def _parse_pgn_to_moves(self, pgn_moves: str) -> List[str]:
        """
        Parse a PGN string to extract the list of moves in SAN notation.

        Parameters
        ----------
        pgn_moves : str
            String of moves in PGN notation

        Returns
        -------
        List[str]
            List of moves in SAN notation
        """
        try:
            # Method 1: Use chess.pgn to parse correctly
            pgn_string = f"{pgn_moves} *"
            pgn_io = io.StringIO(pgn_string)
            game = chess.pgn.read_game(pgn_io)

            if game and game.mainline():
                moves = []
                board = chess.Board()

                for move in game.mainline_moves():
                    moves.append(board.san(move))
                    board.push(move)

                return moves

        except (ValueError, EOFError) as e:
            print(f"PGN parsing error: {e}")

        # Method 2: Fallback - manual parsing
        try:
            return self._manual_pgn_parse(pgn_moves)
        except (ValueError, chess.IllegalMoveError) as e:
            print(f"Manual parsing error: {e}")

            return []

    def _manual_pgn_parse(self, pgn_moves: str) -> List[str]:
        """
        Manual parsing of a PGN string extracting moves.

        Parameters
        ----------
        pgn_moves : str
            String of moves in PGN notation

        Returns
        -------
        List[str]
            List of moves in SAN notation
        """
        # Clean and separate moves
        clean_moves = re.sub(r'\d+\.', ' ', pgn_moves)  # Remove move numbers
        clean_moves = clean_moves.replace('...', ' ')
        clean_moves = re.sub(r'[{}\[\]()]', ' ', clean_moves)  # Remove annotations

        tokens = clean_moves.split()
        moves = []
        board = chess.Board()

        for token in tokens:
            token = token.strip()

            if not token or token == '*':
                continue

            # Ignore move numbers, comments, etc.

            if token.isdigit() or token.endswith('.'):
                continue

            try:
                move = board.parse_san(token)
                moves.append(board.san(move))
                board.push(move)
            except (ValueError, chess.IllegalMoveError):
                # Ignore invalid tokens

                continue

        return moves

    def add_from_popular_openings(self, popular_openings: Dict) -> None:
        """
        Add openings from a POPULAR_OPENINGS format dictionary.

        Parameters
        ----------
        popular_openings : Dict
            Dictionary with format: category -> list of (name, pgn, color, themes)
        """

        for category, openings in popular_openings.items():
            for opening_tuple in openings:
                if len(opening_tuple) >= 4:
                    name, pgn, color, themes = opening_tuple[:5]

                    # Use default values for rating and popularity
                    rating = ""
                    popularity = ""

                    # Store the color information in the variant for later lookup
                    moves = self._parse_pgn_to_moves(pgn)

                    if moves:
                        # Create variant with color and category information
                        variant = OpeningVariant(
                            name=name,
                            fen=chess.STARTING_FEN,
                            moves=" ".join(moves),
                            color=color,  # Store the color from input data
                            themes=themes,
                            category=category  # Store the JSON category
                        )
                        self.variants.append(variant)

                    # Add the opening with enhanced themes that include color and category
                    enhanced_themes = f"{themes} {color}" if themes else f"{color}"

                    self.add_opening_from_pgn(
                        name=name,
                        pgn_moves=pgn,
                        rating=rating,
                        popularity=popularity,
                        themes=enhanced_themes,  # Include color and category in themes
                        category=category  # Pass the category
                    )

    def generate_csv(self, output_file: str = "chess_openings.csv") -> None:
        """
        Generate CSV file for Anki import.

        Parameters
        ----------
        output_file : str
            Output filename
        """

        if not self.moves:
            print("No moves to write. Check your openings.")

            return

        def _opening_prefixed_tokens(text: str):
            # Split on whitespace and common separators, drop empties, prefix
            tokens = [t for t in re.split(r'[\s,;|]+', text.strip()) if t]

            return " ".join(f"OCP::00_Openings_Defences::{t}" for t in tokens)

        with open(output_file, "w", encoding="utf-8") as opening_file:
            # CSV header
            opening_file.write("PuzzleId,FEN,Moves_SAN,Rating,Popularity,Themes,OpeningTags,DisplayTheme,Tags\n")

            for move in self.moves:
                themes = safe_str(move.themes)
                category = safe_str(move.category)

                # ONLY tags_str is prefixed per element; original columns unchanged
                oc_themes = _opening_prefixed_tokens(themes) if themes else ""
                oc_openings = _opening_prefixed_tokens(category) if category else ""

                tags_str = " ".join(x for x in [oc_themes, oc_openings] if x).strip()

                vals = [
                    safe_str(move.puzzle_id),
                    move.fen_before,
                    move.move_san,
                    safe_str(move.rating),
                    safe_str(move.popularity),
                    safe_str(move.themes),
                    safe_str(move.category),
                    safe_str(""),  # default display theme
                    tags_str
                ]

                opening_file.write(",".join([v.replace(',', ';') for v in vals]) + "\n")

        # Importer le module contenant la nouvelle classe

        # Créer une instance de l'analyseur
        output_file='opening_report.txt'
        analyzer = opening_report.ChessOpeningAnalyzer(
            self.moves,
            self.variants,
            output_file=output_file)

        # Générer le rapport
        report = analyzer.generate_report(report_format='console', include_visuals=True)

        # Afficher le rapport (ou l'enregistrer dans un fichier)
        print(report)
        # Ou pour enregistrer dans un fichier
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)

if __name__ == "__main__":
    generator = OpeningDeckGenerator()

    with open('comprehensive_openings_repertoire.json', 'r', encoding='utf-8') as opening_json_file:
        data_dict1 = json.load(opening_json_file)

    generator.add_from_popular_openings(data_dict1)

    # Generate the complete deck
    generator.generate_csv('chess_openings.csv')
