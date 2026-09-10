"""An order cue proves intent, not which drink (#2689).

`resolve_order` treated an order cue as decisive on its own, so any line
carrying one served whatever board keyword it happened to contain:

    "I'll take your word for it"   ->  the last word

"i'll take" is exactly how people order, and "word" is exactly what that
drink is called. The container is a till: the patron is charged.

MOST OF THIS ISSUE WAS ALREADY FIXED. It reports thirteen phrases across
three boards, and measured through `match_recipe` — the raw matcher —
all thirteen still reproduce. Measured through `resolve_order`, the door
players actually use, twelve are already refused by #2779's intent gate:

    'cheap talk, that'            -> None      (was: mug of rotgut)
    'the old man sent me'         -> None      (was: Old Fashioned)
    "it's been a long shift"      -> None      (was: pint of shift's end)
    "I'll take your word for it"  -> the last word     <- the survivor

The survivor is a different defect from the twelve. Those were keyword
collisions; this one clears the gate because of the CUE.

The cue still settles intent — a question mark no longer refuses it,
which is the whole point of #2779's carve-out for "can I get a rotgut?"
— but what remains after the cue is stripped must still be the drink and
filler, the same test a bare order already passed.
"""
from evennia.utils.test_resources import EvenniaTest

from world.bar import resolve_order

#: The chain-hoist board, live keywords and all.
BOARD = [
    {"name": "pint of shift's end",
     "order_keywords": ["shift", "pint", "stout", "dark", "beer"]},
    {"name": "boilermaker",
     "order_keywords": ["boilermaker", "boiler", "shot", "drop"]},
    {"name": "glass of harness oil",
     "order_keywords": ["harness", "oil", "dark", "sweet", "rum"]},
    {"name": "the last word",
     "order_keywords": ["last", "word", "green", "herbal"]},
]


class _Bar:
    """A post whose only relevant surface is its board."""
    class _DB:
        def __init__(self, menu):
            self.menu = menu
            self.snacks = []
    def __init__(self, menu):
        self.db = self._DB(menu)


class _Board(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.bar = _Bar(BOARD)

    def order(self, line, addressed=True):
        got = resolve_order(self.bar, line, addressed=addressed)
        return (got or {}).get("name")


class TestARealOrderIsStillServed(_Board):
    """Controls. Every one of these is how somebody actually orders, and
    a fix that refused them would be worse than the defect."""

    def test_a_bare_name(self):
        self.assertEqual(self.order("boilermaker"), "boilermaker")

    def test_a_bare_name_with_manners(self):
        self.assertEqual(self.order("boilermaker, thanks"), "boilermaker")

    def test_every_cue_shape(self):
        for line in ("i'll have a boilermaker",
                     "pour me a boilermaker",
                     "gimme another round of boilermaker",
                     "hit me with a boilermaker",
                     "let me get a boilermaker",
                     "i'd like a boilermaker please"):
            self.assertEqual(self.order(line), "boilermaker", line)

    def test_a_cue_still_beats_a_question_mark(self):
        """#2779's carve-out: "can I get a rotgut?" is how people order,
        and this must not have quietly undone it."""
        self.assertEqual(self.order("can i get a boilermaker?"),
                         "boilermaker")

    def test_a_multi_word_drink_with_a_cue(self):
        self.assertEqual(self.order("let me get the last word"),
                         "the last word")


class TestConversationIsNotAnOrder(_Board):

    def test_the_survivor(self):
        """The one line in this issue that still reached the till."""
        self.assertIsNone(self.order("I'll take your word for it"),
                          "an idiom carrying a cue poured a drink")

    def test_the_twelve_that_were_already_refused(self):
        """Pinned so #2779's gate cannot regress unnoticed — they are
        the reason this issue is mostly closed already."""
        for line in ("cheap talk, that", "I'm stiff from the walk",
                     "she's the strong type", "the fog is bad tonight",
                     "the old man sent me", "it's been a long shift",
                     "that's a dark thing to say", "you seen my last crew?",
                     "got a shot at fixing it", "keep it green out there",
                     "he works the oil line"):
            self.assertIsNone(self.order(line), line)

    def test_a_question_without_a_cue_is_a_question(self):
        self.assertIsNone(self.order("what's in a boilermaker?"))

    def test_an_overheard_remark_with_a_cue_is_also_held_to_it(self):
        """Both branches take the same test — overhearing is the more
        conservative door, so it must not be the looser one."""
        self.assertIsNone(
            self.order("I'll take your word for it", addressed=False))
        self.assertEqual(
            self.order("i'll have a boilermaker", addressed=False),
            "boilermaker")
