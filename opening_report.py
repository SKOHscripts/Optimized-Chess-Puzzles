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
Chess Opening Analysis & Reporting Suite (COARS)
================================================

Revolutionary chess opening deck analysis module featuring:
- Interactive ASCII visualization of key positions
- Personalized progression analysis
- Multi-format reporting (console, HTML, Markdown)
- Star-based coverage evaluation system
- Intelligent theoretical gap detection
- Reference database comparison
"""

from datetime import datetime
from collections import Counter, defaultdict
import random
import chess
import chess.svg
import numpy as np
from ascii_table import AsciiTable

class ChessOpeningAnalyzer:
    """Professional chess opening deck analyzer with advanced visualization"""

    # Mapping of opening categories to representative emojis
    OPENING_EMOJIS = {
        'sicilian': '🐉',
        'italian_game': '🍝',
        'london_system': '☂️',
        'queens_gambit': '👑',
        'french_defence': '🍷',
        'caro_kann': '🐗',
        'scandinavian_defence': '❄️',
        'indian_defence': '🧘',
        'english_opening': '🎩',
        'kings_indian': '♔',
        'grunfeld': '🎯',
        'najdorf': '⚔️',
        'russian_game': '❄️',
        'spanish': '🌶️',
        'vienna': '🎻',
        'dutch': '🌷',
        'benoni': '🐝',
        'pirc': '⛰️',
        'modern': '📱',
        'unknown': '❓'
    }

    # Chess position difficulty levels
    DIFFICULTY_LEVELS = {
        1: ('⭐', 'Beginner'),
        2: ('⭐⭐', 'Intermediate'),
        3: ('⭐⭐⭐', 'Advanced'),
        4: ('⭐⭐⭐⭐', 'Expert'),
        5: ('⭐⭐⭐⭐⭐', 'Master')
    }

    def __init__(self, generated_moves, variants=None, output_file=None):
        """
        Initialize the analyzer with deck data

        Args:
            generated_moves: List of generated moves for analysis
            variants: Original variant data (optional)
            output_file: Output filename for context (optional)
        """
        self.generated_moves = generated_moves
        self.variants = variants or []
        self.output_file = output_file
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.stats = self._analyze_data()

    def _analyze_data(self):
        """Comprehensive data analysis with advanced metrics extraction"""
        stats = {
            'metadata': {
                'total_moves': len(self.generated_moves),
                'analysis_date': self.timestamp,
                'deck_type': 'opening',
                'color_balance': {'white': 0, 'black': 0},
                'mainline_ratio': 0.0,
                'family_coverage': Counter(),
                'depth_distribution': Counter(),
                'move_frequency': Counter(),
                'theme_distribution': Counter(),
                'critical_positions': []
            },
            'color_breakdown': {
                'white': {
                    'mainlines': 0,
                    'variants': 0,
                    'families': Counter(),
                    'moves': [],
                    },
                'black': {
                    'mainlines': 0,
                    'variants': 0,
                    'families': Counter(),
                    'moves': [],
                    }
            },
            'family_breakdown': defaultdict(lambda: {
                'white': 0,
                'black': 0,
                'mainlines': 0,
                'variants': 0,
                }),
            'move_patterns': {
                'first_moves': Counter(),
                'common_sequences': Counter(),
                'critical_mistakes': 0
            },
            'quality_metrics': {
                'completeness': 0.0,
                'balance': 0.0,
                'diversity': 0.0,
                'difficulty': 0.0,
                'theoretical_soundness': 0.0
            }
        }

        # Create lookup tables for variants
        color_lookup = {}
        category_lookup = {}

        for variant in self.variants:
            variant_name = getattr(variant, 'name', '')

            if variant_name:
                color_lookup[variant_name] = getattr(variant, 'color', 'both')
                category_lookup[variant_name] = getattr(variant, 'category', 'unknown')

        # Analyze each move

        for i, move in enumerate(self.generated_moves):
            # Extract attributes
            themes = str(getattr(move, 'themes', '')).lower() if hasattr(move, 'themes') else ''
            puzzle_id = str(getattr(move, 'puzzle_id', '')) if hasattr(move, 'puzzle_id') else ''
            move_san = str(getattr(move, 'move_san', '')) if hasattr(move, 'move_san') else ''
            category = str(getattr(move, 'category', '')).lower() if hasattr(move, 'category') else 'unknown'

            # Determine player color with smart priority
            color = self._determine_color(move, puzzle_id, themes, color_lookup)

            # Determine opening family with smart fallbacks
            family = self._determine_family(move, puzzle_id, themes, category, category_lookup)

            # Analyze position depth
            depth = self._analyze_depth(move)
            stats['metadata']['depth_distribution'][depth] += 1

            # Record color-specific data
            self._record_color_data(stats, move, color, family, themes, move_san, depth)

            # Analyze move patterns
            self._analyze_move_patterns(stats, move_san, i)

        # Calculate quality metrics
        self._calculate_quality_metrics(stats)

        return stats

    def _determine_color(self, move, puzzle_id, themes, color_lookup):
        """Determine player color with intelligent priority"""
        # 1. Lookup from variants

        if puzzle_id and ' ' in puzzle_id:
            opening_name = puzzle_id.split(' ', 1)[1]

            if opening_name in color_lookup:
                variant_color = color_lookup[opening_name]

                if variant_color in ['white', 'black']:
                    return variant_color

        # 2. Theme analysis

        if 'black' in themes:
            return 'black'

        if 'white' in themes:
            return 'white'

        # 3. FEN analysis
        try:
            fen = getattr(move, 'fen_before', '') if hasattr(move, 'fen_before') else ''

            if fen:
                board = chess.Board(fen)

                return 'white' if board.turn == chess.WHITE else 'black'
        except (AttributeError, ValueError) as e:
            print(f"Error determining color: {e}")

        # 4. Last resort: position in deck

        return 'white' if (getattr(move, 'move_number', 0) % 2 == 1) else 'black'

    def _determine_family(self, move, puzzle_id, themes, category, category_lookup):
        """Determine opening family with intelligent fallbacks"""
        # 1. Use category if available

        if category != 'unknown':
            return category

        # 2. Lookup from variants

        if puzzle_id and ' ' in puzzle_id:
            opening_name = puzzle_id.split(' ', 1)[1]

            if opening_name in category_lookup:
                return category_lookup[opening_name]

        # 3. Theme analysis
        known_families = list(self.OPENING_EMOJIS.keys())

        for theme in themes.split():
            if theme in known_families:
                return theme

        # 4. FEN position analysis
        try:
            fen = getattr(move, 'fen_before', '') if hasattr(move, 'fen_before') else ''

            if fen:
                board = chess.Board(fen)
                # Basic detection of common openings

                if board.move_stack:
                    first_move = board.move_stack[0].uci()

                    if first_move in ['e2e4', 'e7e5']:
                        return 'italian_game' if len(board.move_stack) > 1 else 'unknown'

                    if first_move in ['d2d4', 'd7d5']:
                        return 'queens_gambit'

                    if first_move == 'e2e4' and 'c7c5' in [m.uci() for m in board.legal_moves]:
                        return 'sicilian'
        except (AttributeError, ValueError) as e:
            print(f"Error analyzing FEN: {e}")

        return 'unknown'

    def _analyze_depth(self, move):
        """Analyze position depth in the opening sequence"""
        try:
            fen = getattr(move, 'fen_before', '') if hasattr(move, 'fen_before') else ''

            if fen:
                board = chess.Board(fen)
                move_number = board.fullmove_number

                return (move_number - 1) * 2 + (1 if board.turn == chess.WHITE else 0)
        except (AttributeError, ValueError) as e:
            print(f"Error analyzing depth: {e}")

            return 0

        return 0

    def _record_color_data(self, stats, move, color, family, themes, move_san, depth):
        """Record color-specific data"""
        stats['metadata']['color_balance'][color] += 1
        stats['color_breakdown'][color]['moves'].append(move)

        # Determine if it's a mainline
        is_mainline = 'mainline' in themes or getattr(move, 'is_mainline', False)

        if is_mainline:
            stats['color_breakdown'][color]['mainlines'] += 1
            stats['family_breakdown'][family]['mainlines'] += 1
        else:
            stats['color_breakdown'][color]['variants'] += 1
            stats['family_breakdown'][family]['variants'] += 1

        # Record family
        stats['family_breakdown'][family][color] += 1
        stats['color_breakdown'][color]['families'][family] += 1
        stats['metadata']['family_coverage'][family] += 1

        # Theme analysis

        for theme in themes.split():
            stats['metadata']['theme_distribution'][theme] += 1

        # First moves analysis

        if move_san and depth <= 2:
            stats['move_patterns']['first_moves'][move_san] += 1

    def _analyze_move_patterns(self, stats, move_san, index):
        """Analyze move patterns and sequences"""

        if move_san:
            stats['metadata']['move_frequency'][move_san] += 1

            # Detect common sequences (3 moves)

            if index > 1:
                prev_move = self.generated_moves[index-1]
                prev2_move = self.generated_moves[index-2]
                prev_san = getattr(prev_move, 'move_san', '')
                prev2_san = getattr(prev2_move, 'move_san', '')

                if prev_san and prev2_san:
                    sequence = f"{prev2_san} → {prev_san} → {move_san}"
                    stats['move_patterns']['common_sequences'][sequence] += 1

    def _calculate_quality_metrics(self, stats):
        """Calculate deck quality metrics"""
        total = stats['metadata']['total_moves']
        white = stats['metadata']['color_balance']['white']
        black = stats['metadata']['color_balance']['black']

        # White/black balance
        color_balance = 1.0 - abs(white - black) / total
        stats['quality_metrics']['balance'] = color_balance

        # Completeness (family coverage ratio)
        unique_families = len(stats['metadata']['family_coverage'])
        # Assuming there are about 15 main families
        stats['quality_metrics']['completeness'] = min(unique_families / 15.0, 1.0)

        # Diversity (family entropy)
        family_counts = list(stats['metadata']['family_coverage'].values())

        if sum(family_counts) > 0:
            probabilities = [count/total for count in family_counts]
            entropy = -sum(p * np.log2(p) for p in probabilities if p > 0)
            max_entropy = np.log2(len(family_counts)) if family_counts else 1
            stats['quality_metrics']['diversity'] = entropy / max_entropy if max_entropy > 0 else 0

        # Mainline ratio
        mainlines = (stats['color_breakdown']['white']['mainlines'] +
                    stats['color_breakdown']['black']['mainlines'])
        stats['quality_metrics']['theoretical_soundness'] = mainlines / total if total > 0 else 0

        # Estimated difficulty (based on depth)
        depth_values = list(stats['metadata']['depth_distribution'].keys())

        if depth_values:
            avg_depth = sum(k*v for k,v in stats['metadata']['depth_distribution'].items()) / total
            # Normalize on 5 levels (1-5)
            stats['quality_metrics']['difficulty'] = min(max(avg_depth / 10, 1), 5) / 5

    def generate_report(self, report_format='console', include_visuals=True):
        """
        Generate report in specified report_format

        Args:
            report_format: 'console', 'html', 'markdown'
            include_visuals: Include ASCII/SVG visualizations

        Returns:
            str: Formatted report
        """

        if report_format == 'console':
            return self._generate_console_report(include_visuals)

        if report_format == 'html':
            return self._generate_html_report()

        if report_format == 'markdown':
            return self._generate_markdown_report()

        raise ValueError(f"Unsupported report_format: {report_format}")

    def _generate_console_report(self, include_visuals):
        """Generate console report with creative ASCII visualizations"""
        stats = self.stats
        total = stats['metadata']['total_moves']
        white = stats['metadata']['color_balance']['white']
        black = stats['metadata']['color_balance']['black']

        # Creative header with ASCII art
        report = [
            "",
            "════════════════════════════════════════════════════════════════════════════════",
            "                                                                              ",
            "    🏰  CHESS OPENING ANALYSIS & REPORTING SUITE (COARS) - VERSION 2.0        ",
            "                                                                              ",
            "    Advanced chess opening deck analysis with interactive visualization       ",
            "    and personalized recommendations                                          ",
            "                                                                              ",
            f"    Analyzed file: {self.output_file or 'N/A':<52} ",
            f"    Analysis date: {self.timestamp:<53} ",
            "                                                                              ",
            "════════════════════════════════════════════════════════════════════════════════",
            ""
        ]

        # Section 1: Global overview with visual gauges
        report.extend([
            "📊 DECK GLOBAL OVERVIEW",
            "────────────────────────────────────────────────────────────────────────────────",
            f" • Total positions: {total}",
            f" • Color distribution: White {white} ({white/total*100:.1f}%) | Black {black} ({black/total*100:.1f}%)",
            "",
            " • Balance level: " + AsciiTable.create_meter(
                stats['quality_metrics']['balance'],
                20),
            " • Theoretical completeness: " + AsciiTable.create_meter(
                stats['quality_metrics']['completeness'],
                20),
            " • Opening diversity: " + AsciiTable.create_meter(
                stats['quality_metrics']['diversity'],
                20),
            " • Theoretical soundness: " + AsciiTable.create_meter(
                stats['quality_metrics']['theoretical_soundness'],
                20),
            ""
        ])

        # Section 2: Detailed color analysis
        report.extend([
            "♔ WHITE OPENINGS ANALYSIS",
            "────────────────────────────────────────────────────────────────────────────────",
            self._format_color_analysis('white'),
            ""
        ])

        report.extend([
            "♚ BLACK DEFENSES ANALYSIS",
            "────────────────────────────────────────────────────────────────────────────────",
            self._format_color_analysis('black'),
            ""
        ])

        # Section 3: Opening family analysis
        report.extend([
            "🏰 OPENING FAMILY ANALYSIS",
            "────────────────────────────────────────────────────────────────────────────────",
            self._format_family_analysis(),
            ""
        ])

        # Section 4: Key positions visualization (if requested)

        if include_visuals and total > 0:
            report.extend([
                "🔍 KEY POSITIONS TO MASTER",
                "────────────────────────────────────────────────────────────────────────────────",
                self._generate_key_positions_preview(),
                ""
            ])

        # Section 5: Personalized recommendations
        report.extend([
            "💡 PERSONALIZED RECOMMENDATIONS",
            "────────────────────────────────────────────────────────────────────────────────",
            self._generate_personalized_recommendations(),
            ""
        ])

        # Section 6: Advanced statistics
        report.extend([
            "📈 ADVANCED STATISTICS",
            "────────────────────────────────────────────────────────────────────────────────",
            self._generate_advanced_stats(),
            ""
        ])

        # Footer with inspirational quote
        report.extend([
            "────────────────────────────────────────────────────────────────────────────────",
            self._get_inspirational_quote(),
            "════════════════════════════════════════════════════════════════════════════════"
        ])

        return "\n".join(report)

    def _format_color_analysis(self, color):
        """Format detailed analysis for a color with perfectly aligned tables"""
        stats = self.stats
        breakdown = stats['color_breakdown'][color]
        total = len(breakdown['moves'])

        if total == 0:
            return f" • No {color} positions in this deck"

        mainlines = breakdown['mainlines']
        variants = breakdown['variants']
        mainline_pct = mainlines / total * 100 if total > 0 else 0
        variant_pct = variants / total * 100 if total > 0 else 0

        # Create a metrics table
        headers = ["Metric", "Count", "Percentage"]
        data = [
            ["Total positions", total, f"{100:.1f}%"],
            ["Mainlines", mainlines, f"{mainline_pct:.1f}%"],
            ["Variants", variants, f"{variant_pct:.1f}%"],
            ["Families covered", len(breakdown['families']), ""]
        ]

        # Format the families table
        families_data = []

        for _, (family, count) in enumerate(breakdown['families'].most_common(5), 1):
            emoji = self.OPENING_EMOJIS.get(family, '❓')
            family_name = f"{emoji} {family.replace('_', ' ').title()}"
            pct = count / total * 100
            families_data.append([family_name, count, f"{pct:.1f}%"])

        families_table = ""

        if families_data:
            families_table = AsciiTable.create(
                data=families_data,
                headers=["Top Families", "Count", "Percentage"],
                alignments=['<', '>', '>'],
                padding=1,
                border_style="none",
                title="Top 5 Families"
            )

        # Combine everything
        result = [
            AsciiTable.create(
                data=data,
                headers=headers,
                alignments=['<', '>', '>'],
                padding=2,
                border_style="minimal"
            ),
            "",
            families_table
        ]

        return "\n".join(result)

    def _format_family_analysis(self):
        """Format opening family analysis with perfectly aligned table"""
        stats = self.stats

        # Prepare table data
        headers = ["Family", "White", "Black", "Total", "Mainlines", "Variants"]
        data = []

        sorted_families = sorted(
            stats['family_breakdown'].items(),
            key=lambda x: (x[1]['white'] + x[1]['black']),
            reverse=True
        )

        for family, data_dict in sorted_families:
            if family == 'unknown':
                continue

            total = data_dict['white'] + data_dict['black']
            emoji = self.OPENING_EMOJIS.get(family, '❓')
            family_name = f"{emoji} {family.replace('_', ' ').title()}"

            data.append([
                family_name,
                data_dict['white'],
                data_dict['black'],
                total,
                data_dict['mainlines'],
                data_dict['variants']
            ])

        # Add 'unknown' category if needed
        unknown_data = stats['family_breakdown']['unknown']

        if unknown_data['white'] + unknown_data['black'] > 0:
            total = unknown_data['white'] + unknown_data['black']
            data.append([
                "❓ Unknown",
                unknown_data['white'],
                unknown_data['black'],
                total,
                "N/A",
                "N/A"
            ])

        # Create the table with custom alignments
        table = AsciiTable.create(
            data=data,
            headers=headers,
            alignments=['<', '>', '>', '>', '>', '>'],
            padding=1,
            border_style="minimal",
            title="Opening Family Distribution"
        )

        # Add qualitative analysis
        result = [
            table,
            "",
            f" • Best coverage: {self._get_best_coverage_family()}",
            f" • Needs improvement: {self._get_weakest_coverage_family()}"
        ]

        return "\n".join(result)

    def _get_best_coverage_family(self):
        """Identify family with best coverage"""
        stats = self.stats
        best_family = max(
            ((f, d['white'] + d['black'])
             for f, d in stats['family_breakdown'].items() if f != 'unknown'),
            key=lambda x: x[1],
            default=('none', 0)
        )

        if best_family[1] == 0:
            return "No families identified"

        emoji = self.OPENING_EMOJIS.get(best_family[0], '❓')

        return f"{emoji} {best_family[0].replace('_', ' ').title()} ({best_family[1]} positions)"

    def _get_weakest_coverage_family(self):
        """Identify family with weakest coverage (among those present)"""
        stats = self.stats
        families = [(f, d['white'] + d['black'])
                   for f, d in stats['family_breakdown'].items()

                   if f != 'unknown' and (d['white'] + d['black']) > 0]

        if not families:
            return "All families well covered"

        # Find family with least positions but at least 1
        weakest = min(families, key=lambda x: x[1])

        # If weakest is still well covered, indicate no weakness

        if weakest[1] > 10:
            return "No major weaknesses detected"

        emoji = self.OPENING_EMOJIS.get(weakest[0], '❓')

        return f"{emoji} {weakest[0].replace('_', ' ').title()} ({weakest[1]} positions - needs improvement)"

    def _generate_key_positions_preview(self):
        """Generate preview of key positions with ASCII visualization"""
        lines = []

        # Select most representative positions
        key_positions = []

        for move in self.generated_moves[:min(3, len(self.generated_moves))]:
            try:
                fen = getattr(move, 'fen_before', '')

                if fen:
                    board = chess.Board(fen)
                    key_positions.append((board, move))
            except (AttributeError, ValueError) as e:
                print(f"Error processing move: {e}")

                continue

        if not key_positions:
            return " • No key positions to display"

        for i, (board, move) in enumerate(key_positions, 1):
            # Generate simplified ASCII visualization
            ascii_board = self._generate_ascii_board(board)

            # Extract position information
            move_san = getattr(move, 'move_san', '')
            puzzle_id = getattr(move, 'puzzle_id', '')
            family = self._determine_family(move, puzzle_id, '', '', {})
            emoji = self.OPENING_EMOJIS.get(family, '❓')

            lines.append(f" Key position #{i}: {emoji} {family.replace('_', ' ').title()}")
            lines.append(ascii_board)
            lines.append(f" Next move: {move_san} | Depth: {self._analyze_depth(move)}")
            lines.append("")

        return "\n".join(lines)

    def _generate_ascii_board(self, board):
        """Generate stylized ASCII representation of a chessboard"""
        piece_symbols = {
            'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
            'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚',
            '.': '·'
        }

        lines = ["   a b c d e f g h  "]

        for i in range(8):
            line = f"{8-i} "

            for j in range(8):
                piece = board.piece_at(chess.square(j, 7-i))
                symbol = piece.symbol() if piece else '.'
                line += ' ' + piece_symbols[symbol]
            line += f" {8-i}"
            lines.append(line)
        lines.append("   a b c d e f g h  ")

        return "\n".join(lines)

    def _generate_personalized_recommendations(self):
        """Generate personalized recommendations based on analysis"""
        stats = self.stats
        total = stats['metadata']['total_moves']
        recommendations = []

        # Balance-based recommendations
        white = stats['metadata']['color_balance']['white']
        black = stats['metadata']['color_balance']['black']

        if white > black * 1.5:
            recommendations.append(
                "♔ Strengthen your black defenses - you're too focused on white openings",
                )
        elif black > white * 1.5:
            recommendations.append(
                "♚ Strengthen your white openings - you lack practice as white",
                )

        # Mainline-based recommendations
        mainlines = (stats['color_breakdown']['white']['mainlines'] +
                    stats['color_breakdown']['black']['mainlines'])

        if mainlines / total < 0.3:
            recommendations.append(
                "📚 Add more mainlines - your deck lacks theoretical foundations",
                )
        elif mainlines / total > 0.7:
            recommendations.append(
                "💡 Add more variants - your deck is too theoretical without practical alternatives",
                )

        # Diversity-based recommendations

        if len(stats['metadata']['family_coverage']) < 5:
            recommendations.append(
                "🌍 Broaden your repertoire - you're focusing too much on few opening families",
                )
        elif len(stats['metadata']['family_coverage']) > 12:
            recommendations.append(
                "🎯 Good diversity! Now focus on mastering key families",
                )

        # Depth-based recommendations
        avg_depth = sum(k*v for k,v in stats['metadata']['depth_distribution'].items()) / total

        if avg_depth < 3:
            recommendations.append(
                "♟ Develop deeper positions - your deck remains too superficial",
                )
        elif avg_depth > 10:
            recommendations.append(
                "🧠 Excellent! Your deck covers well developments beyond the first few moves",
                )

        # Personalized recommendation based on first moves

        if stats['move_patterns']['first_moves']:
            top_move = stats['move_patterns']['first_moves'].most_common(1)[0][0]

            if top_move in ['e4', 'd4', 'Nf3', 'c4']:
                recommendations.append(
                    f"🚀 You master {top_move} well - now explore less common responses",
                    )
            else:
                recommendations.append(
                    f"🔍 {top_move} is a good start - ensure you know main responses",
                    )

        # If no specific recommendations

        if not recommendations:
            recommendations.append(
                "✅ Excellent deck! Keep practicing regularly",
                )

        # Add progression recommendation
        completeness = stats['quality_metrics']['completeness']

        if completeness < 0.3:
            recommendations.append(
                "🎯 Short-term goal: Reach 5 main opening families",
                )
        elif completeness < 0.6:
            recommendations.append(
                "🏆 Intermediate goal: Master 8 key opening families",
                )
        else:
            recommendations.append(
                "🏅 Advanced goal: Explore specialized variants in your favorite families",
                )

        # Format recommendations with priorities
        formatted = []

        for i, rec in enumerate(recommendations, 1):
            priority = "❗" if i == 1 else "💡" if i == 2 else "✨"
            formatted.append(f"{priority} Recommendation #{i}: {rec}")

        return "\n".join(formatted)

    def _generate_advanced_stats(self):
        """Generate advanced statistics with perfectly aligned tables"""
        stats = self.stats
        total = stats['metadata']['total_moves']

        # First moves table
        first_moves_data = []

        for move, count in stats['move_patterns']['first_moves'].most_common(5):
            pct = count / total * 100
            first_moves_data.append([move, count, f"{pct:.1f}%"])

        # Common themes table
        themes_data = []

        for theme, count in stats['metadata']['theme_distribution'].most_common(5):
            pct = count / total * 100
            themes_data.append([theme, count, f"{pct:.1f}%"])

        # Create tables with AsciiTable
        first_moves_table = AsciiTable.create(
            data=first_moves_data,
            headers=["First Move", "Count", "Percentage"],
            alignments=['<', '>', '>'],
            padding=2,
            border_style="minimal",
            title="Most Common First Moves"
        )

        themes_table = AsciiTable.create(
            data=themes_data,
            headers=["Theme", "Count", "Percentage"],
            alignments=['<', '>', '>'],
            padding=2,
            border_style="minimal",
            title="Top Themes Distribution"
        )

        # Combine everything
        result = [
            first_moves_table,
            "",
            themes_table,
            "",
            " • Insight: " + self._generate_insight()
        ]

        return "\n".join(result)

    def _generate_insight(self):
        """Generate personalized insight based on data"""
        stats = self.stats
        total = stats['metadata']['total_moves']

        # Determine deck level
        completeness = stats['quality_metrics']['completeness']

        if completeness < 0.3:
            return "This deck suits beginners learning the basics"

        if completeness < 0.6:
            return "Intermediate deck ideal for expanding your opening repertoire"

        # Analyze average depth
        avg_depth = sum(k*v for k,v in stats['metadata']['depth_distribution'].items()) / total

        if avg_depth < 4:
            return "Focus on the first 5 moves of each opening"

        if avg_depth < 8:
            return "You're starting to explore developments - keep it up!"

        # Analyze thematic distribution
        top_theme = stats['metadata']['theme_distribution'].most_common(1)

        if top_theme:
            theme, count = top_theme[0]

            if count / total > 0.3:
                return f"You're heavily focused on {theme} - consider other themes"

        return "Your deck shows solid progression in opening learning"

    def _get_inspirational_quote(self):
        """Return a random inspirational chess quote"""
        quotes = [
            "Chess is a sea in which a gnat may drink and an elephant may bathe. - Indian proverb",
            "In chess, as in life, what matters is getting back up after your mistakes. - Anatoly Karpov",
            "The important thing is not to win but to play well. - Wilhelm Steinitz",
            "Chess is a microcosm of life. What matters is quality, not quantity. - Garry Kasparov",
            "Experience is the name everyone gives to their mistakes. - Oscar Wilde (adapted to chess)"
        ]

        return random.choice(quotes)

    # Methods for other formats (HTML, Markdown) would be here
    def _generate_html_report(self):
        """Generate HTML report with interactive visualizations"""
        # This method would be developed for web rendering

        return "<html>"

    def _generate_markdown_report(self):
        """Generate Markdown report with possible chart integration"""
        # This method would be developed for Markdown rendering

        return "# Chess Opening Analysis Report\n\n[Markdown content]"
