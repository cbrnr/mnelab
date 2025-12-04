# © MNELAB developers
#
# License: BSD (3-clause)

import keyword
import subprocess

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

        self.rules = []

        # keywords
        f = QTextCharFormat()
        f.setFontWeight(QFont.Bold)
        f.setForeground(Qt.darkBlue)
        for kw in keyword.kwlist:
            self.rules.append((QRegularExpression(rf"\b{kw}\b"), f))

        # numerals
        f = QTextCharFormat()
        f.setForeground(Qt.blue)
        self.rules.append((QRegularExpression("[0-9]+"), f))

        # strings
        f = QTextCharFormat()
        f.setForeground(Qt.darkCyan)
        self.rules.append((QRegularExpression('"[^"]*"'), f))
        self.rules.append((QRegularExpression("'[^']*'"), f))

    def highlightBlock(self, text):
        for rule in self.rules:
            matches = rule[0].globalMatch(text)
            while matches.hasNext():
                match = matches.next()
                start, length = match.capturedStart(), match.capturedLength()
                self.setFormat(start, length, rule[1])


def format_with_ruff(code):
    """Format and lint Python code using Ruff (fall back to original if unavailable)."""
    try:
        # run the linter to fix import sorting and remove unused imports
        lint_result = subprocess.run(
            ["ruff", "check", "--select", "I,F401", "--fix", "-"],
            input=code,
            text=True,
            capture_output=True,
            timeout=5,
        )

        code_to_format = lint_result.stdout if lint_result.returncode == 0 else code

        # format the code
        result = subprocess.run(
            ["ruff", "format", "-"],
            input=code_to_format,
            text=True,
            capture_output=True,
            check=True,
            timeout=5,
        )
        return result.stdout
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        return code
