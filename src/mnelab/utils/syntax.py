# © MNELAB developers
#
# License: BSD (3-clause)

import ast
import keyword

import black
import isort
from PySide6.QtCore import QRect, QRegularExpression, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QWidget


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self._build_rules()
        QApplication.styleHints().colorSchemeChanged.connect(
            self._on_color_scheme_changed
        )

    def _build_rules(self):
        dark = QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
        self.rules = []

        # keywords
        f = QTextCharFormat()
        f.setFontWeight(QFont.Weight.Bold)
        f.setForeground(QColor("#569CD6") if dark else QColor("#0000FF"))
        for kw in keyword.kwlist:
            self.rules.append((QRegularExpression(rf"\b{kw}\b"), f))

        # numerals
        f = QTextCharFormat()
        f.setForeground(QColor("#B5CEA8") if dark else QColor("#098658"))
        self.rules.append((QRegularExpression("[0-9]+"), f))

        # strings
        f = QTextCharFormat()
        f.setForeground(QColor("#CE9178") if dark else QColor("#A31515"))
        self.rules.append((QRegularExpression('"[^"]*"'), f))
        self.rules.append((QRegularExpression("'[^']*'"), f))

    def _on_color_scheme_changed(self):
        self._build_rules()
        self.rehighlight()

    def highlightBlock(self, text):
        for rule in self.rules:
            matches = rule[0].globalMatch(text)
            while matches.hasNext():
                match = matches.next()
                start, length = match.capturedStart(), match.capturedLength()
                self.setFormat(start, length, rule[1])


class _LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self):
        return QSize(self._editor._line_number_area_width(), 0)

    def paintEvent(self, event):
        self._editor._paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):
    """Read-only plain-text editor with a line number gutter."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._line_number_area = _LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self._update_line_number_area_width(0)

    def _line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        char_width = self.fontMetrics().horizontalAdvance("9")
        return 8 + char_width * digits  # 4 px padding on each side

    def _update_line_number_area_width(self, _):
        self.setViewportMargins(self._line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy):
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(
                0, rect.y(), self._line_number_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self._line_number_area_width(), cr.height())
        )

    def _paint_line_numbers(self, event):
        painter = QPainter(self._line_number_area)
        painter.setPen(QColor("#808080"))
        painter.setFont(self.font())

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        width = self._line_number_area.width() - 4  # right padding

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(
                    0,
                    int(top),
                    width,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(block_number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1


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
