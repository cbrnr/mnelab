# © MNELAB developers
#
# License: BSD (3-clause)

import ast
import keyword

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


def format_code(code):
    """Format Python code.

    Parameters
    ----------
    code : str
        Python code.

    Returns
    -------
    str
        Formatted code.

    Notes
    -----
    If the code cannot be formatted (e.g., due to syntax errors), the function returns
    the original code.
    """
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

        # track import nodes for reconstruction
        import_nodes = {}  # {line_number: node}

        # collect all import statements from top-level
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                import_nodes[node.lineno] = node

        # track which imported names are used
        used_names = set()

        # check all name references in the code
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                # for attribute access like module.function, track the base
                if isinstance(node.value, ast.Name):
                    used_names.add(node.value.id)

        # reconstruct or remove import lines
        lines = code.splitlines(keepends=True)
        result_lines = []
        lines_to_modify = {}  # {line_number: new_import_statement}

        for lineno, node in import_nodes.items():
            if isinstance(node, ast.Import):
                # handle "import module" statements
                used_aliases = [
                    alias
                    for alias in node.names
                    if (alias.asname if alias.asname else alias.name) in used_names
                ]
                if used_aliases:
                    # reconstruct import statement with only used imports
                    imports_str = ", ".join(
                        f"{alias.name} as {alias.asname}"
                        if alias.asname
                        else alias.name
                        for alias in used_aliases
                    )
                    lines_to_modify[lineno] = f"import {imports_str}\n"
                else:
                    # remove entire line
                    lines_to_modify[lineno] = None

            elif isinstance(node, ast.ImportFrom):
                # handle "from module import ..." statements
                used_aliases = [
                    alias
                    for alias in node.names
                    if (alias.asname if alias.asname else alias.name) in used_names
                ]
                if used_aliases:
                    # reconstruct import statement with only used imports
                    imports_str = ", ".join(
                        f"{alias.name} as {alias.asname}"
                        if alias.asname
                        else alias.name
                        for alias in used_aliases
                    )
                    module = node.module if node.module else ""
                    level = "." * node.level
                    from_str = f"from {level}{module} import {imports_str}\n"
                    lines_to_modify[lineno] = from_str
                else:
                    # remove entire line
                    lines_to_modify[lineno] = None

        if not lines_to_modify:
            return code

        # rebuild code with modified/removed import lines
        for i, line in enumerate(lines, start=1):
            if i in lines_to_modify:
                if lines_to_modify[i] is not None:
                    result_lines.append(lines_to_modify[i])
                # else: skip this line (remove it)
            else:
                result_lines.append(line)

        return "".join(result_lines)

    except (SyntaxError, ValueError):  # if parsing fails, return original code
        return code
