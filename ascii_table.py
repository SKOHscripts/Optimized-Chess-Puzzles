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
Module for creating ASCII tables used in opening_report.py
"""


class AsciiTable:
    """Helper class for creating perfectly aligned ASCII tables with dynamic column widths"""

    @staticmethod
    def create(data, headers, alignments=None, padding=1, border_style="none", title=None):
        """
        Create a perfectly aligned ASCII table with dynamic column widths

        Args:
            data: List of rows (each row is a list of cells)
            headers: List of header names
            alignments: List of alignments ('<', '>', '^') for each column
            padding: Number of spaces between columns
            border_style: "none", "minimal", "full"
            title: Optional table title

        Returns:
            str: Formatted table
        """
        # Déterminer la largeur maximale de chaque colonne (incluant les en-têtes)
        all_rows = [headers] + data
        col_widths = [
            max(len(str(row[i])) for row in all_rows if i < len(row))

            for i in range(max(len(row) for row in all_rows))
        ]

        # Appliquer le padding
        col_widths = [w + padding*2 for w in col_widths]

        # Définir les alignements par défaut (gauche pour le texte, droite pour les nombres)

        if not alignments:
            alignments = ['<' if i == 0 else '>' for i in range(len(col_widths))]

        # Créer les lignes du tableau
        lines = []

        # Ajouter un titre si spécifié

        if title:
            lines.append(f"{title}")
            lines.append("─" * sum(col_widths + [len(col_widths) - 1]))

        # Ligne de séparation supérieure si nécessaire

        if border_style == "full":
            top_border = '+' + '+'.join(['─' * w for w in col_widths]) + '+'
            lines.append(top_border)

        # En-têtes
        header_line = ''

        if border_style in ["minimal", "full"]:
            header_line += '|'

        for i, header in enumerate(headers):
            fmt = f"{{:{alignments[i]}{col_widths[i]}}}"
            header_line += fmt.format(header)

            if border_style in ["minimal", "full"] or i < len(headers) - 1:
                header_line += '|'
        lines.append(header_line)

        # Ligne de séparation après les en-têtes si nécessaire

        if border_style == "full":
            separator = '+' + '+'.join(['─' * w for w in col_widths]) + '+'
            lines.append(separator)
        elif border_style == "minimal":
            separator = ':' + ':'.join(['-' * w for w in col_widths]) + ':'
            lines.append(separator)

        # Données

        for row in data:
            row_line = ''

            if border_style in ["minimal", "full"]:
                row_line += '|'

            for i, cell in enumerate(row):
                if i >= len(col_widths):
                    continue
                fmt = f"{{:{alignments[i]}{col_widths[i]}}}"
                row_line += fmt.format(str(cell))

                if border_style in ["minimal", "full"] or i < len(row) - 1:
                    row_line += '|'
            lines.append(row_line)

        # Ligne de fermeture si nécessaire

        if border_style == "full":
            bottom_border = '+' + '+'.join(['─' * w for w in col_widths]) + '+'
            lines.append(bottom_border)

        return "\n".join(lines)

    @staticmethod
    def create_meter(value, width=20, symbol_filled='█', symbol_empty='░', show_value=True):
        """
        Create a visual progress meter

        Args:
            value: Value between 0 and 1
            width: Total width of the meter
            symbol_filled: Symbol for filled portion
            symbol_empty: Symbol for empty portion
            show_value: Whether to show the percentage value

        Returns:
            str: Formatted meter
        """
        level = int(value * width)
        meter = symbol_filled * level + symbol_empty * (width - level)

        if show_value:
            return f"[{meter}] {value*100:.0f}%"

        return f"[{meter}]"

    @staticmethod
    def create_balance_meter(white, black, width=20):
        """
        Create a visual balance meter for white/black distribution

        Args:
            white: Count of white positions
            black: Count of black positions
            width: Total width of the meter

        Returns:
            str: Formatted balance meter
        """
        total = white + black

        if total == 0:
            return "[          ] 0.0%"

        white_pct = white / total * 100

        white_width = int(white_pct * width / 100)
        black_width = width - white_width

        meter = "♔" * white_width + "♚" * black_width
        balance = 1.0 - abs(0.5 - white/total) * 2
        status = "(Perfect)" if balance > 0.9 else ""

        return f"[{meter}] {balance*100:.1f}% {status}"
