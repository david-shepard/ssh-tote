"""Splitting shell output into words.

shlex can't read zsh's $'...' quoting, which `alias -L` uses for values
containing newlines or quotes, so this handles '...', "...", $'...' and
backslash escapes itself.
"""

import re
import sys

WHITESPACE = frozenset(" \t\n")
ESCAPABLE_IN_DOUBLE_QUOTES = frozenset('$`"\\\n')
# fmt: off
SIMPLE_ESCAPES = {
    "n": "\n", "t": "\t", "r": "\r", "a": "\a", "b": "\b", "e": "\x1b",
    "E": "\x1b", "f": "\f", "v": "\v", "\\": "\\", "'": "'", '"': '"', "?": "?",
}
# fmt: on
HEX_ESCAPE_DIGITS = {"x": 2, "u": 4, "U": 8}
OCTAL_ESCAPE = re.compile("[0-7]{1,3}")


def split_words(text):
    return _WordSplitter(text).split()


class _WordSplitter:
    def __init__(self, text):
        self.text = text
        self.position = 0
        self.words = []
        self.word = None  # characters of the word being read; None between words
        self.readers = (
            ("$'", self._read_ansi_c_quoted),
            ("'", self._read_single_quoted),
            ('"', self._read_double_quoted),
            ("\\", self._read_backslash),
        )

    def split(self):
        while self.position < len(self.text):
            if self._peek() in WHITESPACE:
                self._finish_word()
                self.position += 1
            else:
                self._read_word_part()
        self._finish_word()
        return self.words

    def _read_word_part(self):
        if self.word is None:
            self.word = []
        for opener, read in self.readers:
            if self.text.startswith(opener, self.position):
                read()
                return
        self.word.append(self._advance())

    def _read_single_quoted(self):
        end = self.text.find("'", self.position + 1)
        if end < 0:
            end = len(self.text)
        self.word.append(self.text[self.position + 1 : end])
        self.position = end + 1

    def _read_ansi_c_quoted(self):
        self.position += len("$'")
        while self._inside_quotes("'"):
            if self._peek() == "\\" and self._peek(1):
                char, self.position = decode_ansi_c_escape(self.text, self.position + 1)
                self.word.append(char)
            else:
                self.word.append(self._advance())
        self.position += 1

    def _read_double_quoted(self):
        self.position += 1
        while self._inside_quotes('"'):
            if self._peek() == "\\" and self._peek(1) in ESCAPABLE_IN_DOUBLE_QUOTES:
                self._take_escaped_char()
            else:
                self.word.append(self._advance())
        self.position += 1

    def _read_backslash(self):
        if self._peek(1):
            self._take_escaped_char()
        else:
            self.word.append(self._advance())

    def _take_escaped_char(self):
        escaped = self._peek(1)
        is_line_continuation = escaped == "\n"
        if not is_line_continuation:
            self.word.append(escaped)
        self.position += 2

    def _inside_quotes(self, closing_quote):
        return self.position < len(self.text) and self._peek() != closing_quote

    def _peek(self, offset=0):
        index = self.position + offset
        return self.text[index] if index < len(self.text) else ""

    def _advance(self):
        char = self._peek()
        self.position += 1
        return char

    def _finish_word(self):
        if self.word is not None:
            self.words.append("".join(self.word))
            self.word = None


def decode_ansi_c_escape(text, position):
    """Decode the escape whose letter is at text[position].

    Returns the decoded text and the position just after the escape.
    """
    letter = text[position]
    if letter in SIMPLE_ESCAPES:
        return SIMPLE_ESCAPES[letter], position + 1
    decoded = _decode_hex(text, position) or _decode_octal(text, position)
    return decoded or ("\\" + letter, position + 1)


def _decode_hex(text, position):
    max_digits = HEX_ESCAPE_DIGITS.get(text[position])
    if max_digits is None:
        return None
    digits = re.compile(f"[0-9a-fA-F]{{1,{max_digits}}}")
    return _decode_number(digits.match(text, position + 1), base=16)


def _decode_octal(text, position):
    return _decode_number(OCTAL_ESCAPE.match(text, position), base=8)


def _decode_number(match, base):
    if match is None:
        return None
    code_point = int(match.group(), base)
    if code_point > sys.maxunicode:
        return None
    return chr(code_point), match.end()
