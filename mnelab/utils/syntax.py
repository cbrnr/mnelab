import keyword
from qtpy.QtGui import QSyntaxHighlighter, QTextCharFormat, QFont
from qtpy.QtCore import Qt, QRegularExpression


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
        self.rules.append((QRegularExpression("\".*\""), f))
        self.rules.append((QRegularExpression("'.*'"), f))

    def highlightBlock(self, text):
        for rule in self.rules:
            matches = rule[0].globalMatch(text)
            while matches.hasNext():
                match = matches.next()
                start, length = match.capturedStart(), match.capturedLength()
                self.setFormat(start, length, rule[1])
