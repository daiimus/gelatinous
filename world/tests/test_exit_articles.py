"""Exit lines agree their article (#1725).

`dest_type` is data — a room's `db.type` — so the article in front of
it cannot be hardcoded. It was, and vowel-initial types read as "There
is a interior to the elevator (in)".

The fixed-noun branches (dead-end, edge, gap, exit, intersection) are
correct as written and are pinned here so a later edit cannot quietly
break them.
"""
from evennia.utils.test_resources import EvenniaCommandTest

from world.grammar import get_article


class TestArticleAgreement(EvenniaCommandTest):
    def test_vowel_initial_room_types_take_an(self):
        for word in ("interior", "alley", "office", "atrium", "entrance",
                     "overlook", "underpass", "arcade", "elevator"):
            self.assertEqual(get_article(word), "an", f"{word!r}")

    def test_consonant_initial_room_types_take_a(self):
        for word in ("bar", "clinic", "corridor", "rooftop", "yard",
                     "constabulary", "stairwell", "lobby", "market"):
            self.assertEqual(get_article(word), "a", f"{word!r}")

    def test_the_formatter_agrees_the_article(self):
        import inspect

        from typeclasses.rooms import Room
        src = inspect.getsource(Room.format_exit_groups)
        self.assertNotIn('There is a {dest_type}', src,
                         "article is hardcoded in front of a data-driven "
                         "room type")
        self.assertIn("get_article(dest_type)", src)

    def test_fixed_noun_lines_keep_their_articles(self):
        import inspect

        from typeclasses.rooms import Room
        src = inspect.getsource(Room.format_exit_groups)
        for phrase in ("There is a dead-end", "There is an intersection",
                       "There is an edge", "There is a gap",
                       "There is an exit"):
            self.assertIn(phrase, src, f"lost: {phrase}")
