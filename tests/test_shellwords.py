import unittest

from sshtotelib.shellwords import split_words


class SplitWordsTest(unittest.TestCase):
    def test_plain_words(self):
        self.assertEqual(split_words("a  b\tc\nd"), ["a", "b", "c", "d"])

    def test_single_quotes_are_literal(self):
        self.assertEqual(split_words(r"'$HOME \n'"), [r"$HOME \n"])

    def test_double_quotes_allow_escaped_quote(self):
        self.assertEqual(split_words(r'"say \"hi\""'), ['say "hi"'])

    def test_ansi_c_quotes_decode_escapes(self):
        self.assertEqual(split_words(r"$'a\nb\t\'c\x41\101'"), ["a\nb\t'cAA"])

    def test_adjacent_quoted_parts_form_one_word(self):
        self.assertEqual(split_words("x='it'\\''s'"), ["x=it's"])

    def test_quoted_newline_stays_inside_the_word(self):
        self.assertEqual(split_words("'one\ntwo' three"), ["one\ntwo", "three"])

    def test_backslash_newline_is_a_line_continuation(self):
        self.assertEqual(split_words("ab\\\ncd"), ["abcd"])

    def test_trailing_backslash_is_kept(self):
        self.assertEqual(split_words("ab\\"), ["ab\\"])
