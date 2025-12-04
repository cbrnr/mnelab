# © MNELAB developers
#
# License: BSD (3-clause)

import keyword
import subprocess
import sys
from pathlib import Path

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
    """Format Python code using Ruff (if unavailable)."""
    if getattr(sys, "frozen", False):  # running in PyInstaller bundle
        bundle_dir = Path(sys._MEIPASS)
        if sys.platform == "win32":
            ruff_cmd = str(bundle_dir / "ruff.exe")
        else:
            ruff_cmd = str(bundle_dir / "ruff")
    else:
        ruff_cmd = "ruff"

    # prevent console window on Windows
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

    try:
        # run the linter to fix import sorting and remove unused imports
        lint_result = subprocess.run(
            [ruff_cmd, "check", "--select", "I,F401", "--fix", "-"],
            input=code,
            text=True,
            capture_output=True,
            timeout=5,
            creationflags=creationflags,
        )

        code_to_format = lint_result.stdout if lint_result.returncode == 0 else code

        # format the code
        result = subprocess.run(
            [ruff_cmd, "format", "-"],
            input=code_to_format,
            text=True,
            capture_output=True,
            check=True,
            timeout=5,
            creationflags=creationflags,
        )
        return result.stdout
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        return code
