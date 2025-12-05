# © MNELAB developers
#
# License: BSD (3-clause)

import ast
import keyword
import subprocess
import sys
from pathlib import Path

import black
import isort
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
    """Format Python code using Ruff."""
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


def format_with_black(code):
    """Format Python code using Black."""
    try:
        return black.format_str(
            isort.code(_remove_unused_imports(code)), mode=black.Mode()
        )
    except black.InvalidInput:
        return code


def _remove_unused_imports(code):
    """Remove unused imports from Python code.

    Parameters
    ----------
    code : str
        Python code.

    Returns
    -------
    str
        Code with unused imports removed.
    """
    try:
        tree = ast.parse(code)

        # track imported names and their line numbers
        imports = {}  # {name: line_number}
        import_lines = set()  # line numbers containing imports

        # collect all imported names
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                import_lines.add(node.lineno)
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports[name] = node.lineno
            elif isinstance(node, ast.ImportFrom):
                import_lines.add(node.lineno)
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports[name] = node.lineno

        # track which imported names are used
        used_names = set()

        # check all name references (but skip import statements themselves)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                # check if this name reference is not in an import statement
                if not hasattr(node, "lineno") or node.lineno not in import_lines:
                    used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                # for attribute access like module.function, track the base
                if isinstance(node.value, ast.Name):
                    used_names.add(node.value.id)

        # find unused imports
        unused_imports = {
            name: line for name, line in imports.items() if name not in used_names
        }

        if not unused_imports:
            return code

        # remove unused import lines
        lines = code.splitlines(keepends=True)
        unused_lines = set(unused_imports.values())

        # rebuild code without unused import lines
        result_lines = []
        for i, line in enumerate(lines, start=1):
            if i not in unused_lines:
                result_lines.append(line)

        return "".join(result_lines)

    except (SyntaxError, ValueError):  # if parsing fails, return original code
        return code
