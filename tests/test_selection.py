import unittest

from sshtotelib.items import Item, Kind, Reason
from sshtotelib.selection import initial_selection, remember_selection
from sshtotelib.settings import Settings


def ticked(items):
    return {item.name: item.selected for item in items}


class InitialSelectionTest(unittest.TestCase):
    def test_by_default_no_variable_is_sent(self):
        items = [Item(Kind.ENV, "EDITOR", "vim"), Item(Kind.ENV, "GH_TOKEN", "t0k")]
        chosen = initial_selection(items, Settings(), set())
        self.assertEqual(ticked(chosen), {"EDITOR": False, "GH_TOKEN": False})

    def test_only_variables_listed_in_env_start_ticked(self):
        items = [
            Item(Kind.ENV, "AWS_PROFILE", "dev"),
            Item(Kind.ENV, "EDITOR", "vim"),
            Item(Kind.ENV, "GITHUB_TOKEN", "t0k"),
        ]
        chosen = initial_selection(items, Settings(env={"EDITOR", "AWS_*"}), set())
        expected = {"AWS_PROFILE": True, "EDITOR": True, "GITHUB_TOKEN": False}
        self.assertEqual(ticked(chosen), expected)
        self.assertEqual([item.reason for item in chosen], [None, None, None])

    def test_only_aliases_listed_in_aliases_start_ticked(self):
        items = [
            Item(Kind.ALIAS, "gco", "git checkout"),
            Item(Kind.ALIAS, "gs", "git status"),
            Item(Kind.ALIAS, "ll", "ls -l"),
        ]
        chosen = initial_selection(items, Settings(aliases={"g*"}), set())
        self.assertEqual(ticked(chosen), {"gco": True, "gs": True, "ll": False})
        self.assertEqual([item.reason for item in chosen], [None, None, None])

    def test_exact_entries_beat_globs_and_exceptions_beat_the_rest(self):
        items = [
            Item(Kind.ENV, "AWS_KEY", "k"),
            Item(Kind.ENV, "AWS_SECRET_1", "s1"),
            Item(Kind.ENV, "AWS_SECRET_2", "s2"),
            Item(Kind.ENV, "AWS_TOKEN", "t"),
            Item(Kind.ENV, "BOTH", "b"),
            Item(Kind.ENV, "EDITOR", "vim"),
        ]
        settings = Settings(
            env={"AWS_*", "!AWS_S*", "AWS_SECRET_2", "!AWS_TOKEN", "BOTH", "!BOTH"}
        )
        chosen = initial_selection(items, settings, set())
        expected = {
            "AWS_KEY": True,
            "AWS_SECRET_1": False,
            "AWS_SECRET_2": True,
            "AWS_TOKEN": False,
            "BOTH": False,
            "EDITOR": False,
        }
        self.assertEqual(ticked(chosen), expected)
        self.assertEqual({item.reason for item in chosen}, {None})

    def test_aliases_calling_a_local_function_are_held_back(self):
        items = [
            Item(Kind.ALIAS, "history", "omz_history -l"),
            Item(Kind.ALIAS, "gh", "omz_history"),
            Item(Kind.ALIAS, "ll", "ls -l"),
        ]
        settings = Settings(aliases={"history", "ll"})
        chosen = initial_selection(items, settings, {"omz_history"})
        self.assertEqual(ticked(chosen), {"history": False, "gh": False, "ll": True})
        reasons = [item.reason for item in chosen]
        self.assertEqual(
            reasons, [Reason.CALLS_LOCAL_FUNCTION, Reason.CALLS_LOCAL_FUNCTION, None]
        )


class RememberSelectionTest(unittest.TestCase):
    def test_choices_on_screen_replace_old_entries_and_others_are_kept(self):
        settings = Settings(
            dotfiles_dir="~/dots",
            env={"AWS_*", "PAGER", "GONE"},
            aliases={"g*", "ll"},
        )
        items = [
            Item(Kind.ENV, "EDITOR", "vim", selected=True),
            Item(Kind.ENV, "PAGER", "less", selected=False),
            Item(Kind.ALIAS, "gs", "git status", selected=True),
            Item(Kind.ALIAS, "ll", "ls -l", selected=False),
        ]
        expected = Settings(
            dotfiles_dir="~/dots",
            env={"AWS_*", "EDITOR", "GONE"},
            aliases={"g*"},
        )
        self.assertEqual(remember_selection(settings, items), expected)

    def test_unticking_a_glob_match_writes_an_exception_that_sticks(self):
        settings = Settings(env={"AWS_*"})
        captured = [Item(Kind.ENV, "AWS_KEY", "k"), Item(Kind.ENV, "AWS_SECRET", "s")]
        chosen = initial_selection(captured, settings, set())
        chosen[1].toggle()
        saved = remember_selection(settings, chosen)
        self.assertEqual(saved, Settings(env={"AWS_*", "!AWS_SECRET"}))
        next_run = initial_selection(captured, saved, set())
        self.assertEqual(ticked(next_run), {"AWS_KEY": True, "AWS_SECRET": False})

    def test_ticking_an_item_with_an_exception_removes_the_exception(self):
        settings = Settings(aliases={"g*", "!gs"})
        chosen = initial_selection([Item(Kind.ALIAS, "gs", "git")], settings, set())
        chosen[0].toggle()
        self.assertEqual(remember_selection(settings, chosen), Settings(aliases={"g*"}))

    def test_ticking_against_a_glob_exception_writes_the_exact_name(self):
        settings = Settings(env={"AWS_*", "!AWS_S*"})
        captured = [Item(Kind.ENV, "AWS_SECRET", "s")]
        chosen = initial_selection(captured, settings, set())
        chosen[0].toggle()
        saved = remember_selection(settings, chosen)
        self.assertEqual(saved, Settings(env={"AWS_*", "!AWS_S*", "AWS_SECRET"}))
        next_run = initial_selection(captured, saved, set())
        self.assertEqual(ticked(next_run), {"AWS_SECRET": True})

    def test_saving_without_changes_leaves_overlapping_entries_alone(self):
        settings = Settings(env={"E*", "EDITOR", "!EX", "!EDITOR2", "GONE"})
        captured = [
            Item(Kind.ENV, "EDITOR", "vim"),
            Item(Kind.ENV, "EDITOR2", "vi"),
            Item(Kind.ENV, "EX", "x"),
            Item(Kind.ENV, "EMACS", "e"),
        ]
        chosen = initial_selection(captured, settings, set())
        self.assertEqual(remember_selection(settings, chosen), settings)

    def test_saving_without_changes_keeps_the_config_and_ignores_hold_backs(self):
        settings = Settings(env={"EDITOR"}, aliases={"history", "ll"})
        captured = [
            Item(Kind.ENV, "EDITOR", "vim"),
            Item(Kind.ENV, "PAGER", "less"),
            Item(Kind.ALIAS, "history", "omz_history"),
            Item(Kind.ALIAS, "ll", "ls -l"),
            Item(Kind.ALIAS, "gs", "git status"),
        ]
        chosen = initial_selection(captured, settings, {"omz_history"})
        self.assertEqual(remember_selection(settings, chosen), settings)
        held_back = next(item for item in chosen if item.name == "history")
        held_back.toggle()
        self.assertEqual(remember_selection(settings, chosen), settings)
