""""sit down" sits you down (#2578).

`sit down` and `lie down` — the most natural phrasings, and the exact
words this command uses to describe itself — failed with:

```
You don't see 'down' to sit on here.
```

The lead-stripping pattern only removed `down` when a **preposition
followed it**:

```python
_LEAD = re.compile(r"^(down\\s+|back\\s+)?(on|in|at|onto|into)\\s+", re.I)
```

so `sit down` arrived as `args=" down"`, `_LEAD` did not fire, and
`down` was handed to `_find_furniture` as a furniture *name*. No seat in
the world is called "down" — measured live, **15 `Seating` objects, none
whose name begins with `down` or `back`** — so it could never match.

The irony is local: `_verb()` renders the act as *"sit down"* / *"lie
down"* in every message the command emits, and `liedown` is a registered
alias. The author models the act exactly as a player types it; only the
parse path treated the word as a target.

The preposition is optional now. With the particle stripped the argument
is empty, which already means *"the nearest free seat"* — so `sit down`
behaves as bare `sit`, which is what someone typing it means.

`\\b` matters in the pattern: without it `sit downed crate` would lose
its first word, and `the backlit bar` — a real seat in this game — would
be stripped to `lit bar`.
"""
import re

from evennia.utils.test_resources import EvenniaTest


def strip_lead(text):
    from commands.CmdFurniture import _LEAD
    return _LEAD.sub("", text).strip()


class TestTheBareParticleIsStripped(EvenniaTest):
    def test_sit_down(self):
        self.assertEqual(strip_lead("down"), "")

    def test_lie_back(self):
        self.assertEqual(strip_lead("back"), "")

    def test_down_with_trailing_space(self):
        self.assertEqual(strip_lead("down "), "")


class TestTheOldFormsStillWork(EvenniaTest):
    def test_down_on_a_named_seat(self):
        self.assertEqual(strip_lead("down on the stool"), "the stool")

    def test_a_bare_preposition(self):
        self.assertEqual(strip_lead("on the stool"), "the stool")

    def test_in(self):
        self.assertEqual(strip_lead("in the couch"), "the couch")

    def test_onto(self):
        self.assertEqual(strip_lead("onto the bench"), "the bench")

    def test_into(self):
        self.assertEqual(strip_lead("into the pod"), "the pod")

    def test_at(self):
        self.assertEqual(strip_lead("at the bar"), "the bar")

    def test_a_bare_name_is_untouched(self):
        self.assertEqual(strip_lead("stool"), "stool")

    def test_a_multi_word_name_is_untouched(self):
        self.assertEqual(strip_lead("bar stool"), "bar stool")

    def test_empty_stays_empty(self):
        self.assertEqual(strip_lead(""), "")


class TestTheWordBoundaryProtectsRealNames(EvenniaTest):
    """Without `\\b` the pattern eats the start of ordinary words."""

    def test_downed_crate_keeps_its_name(self):
        self.assertEqual(strip_lead("downed crate"), "downed crate")

    def test_the_backlit_bar_keeps_its_name(self):
        """A real seat in this game."""
        self.assertEqual(strip_lead("the backlit bar"), "the backlit bar")

    def test_backlit_without_the_article_too(self):
        self.assertEqual(strip_lead("backlit bar"), "backlit bar")


class TestNoLiveSeatBeginsWithAParticle(EvenniaTest):
    """The stripping is only safe because nothing is NAMED "down …" or
    "back …". Pinned so a future seat called "back booth" trips a test
    rather than becoming unreachable."""

    def test_the_prototypes_are_clear(self):
        import world.prototypes as protos
        offenders = []
        for value in vars(protos).values():
            if not isinstance(value, dict):
                continue
            key = str(value.get("key", ""))
            if re.match(r"^(down|back)\b", key, re.I):
                offenders.append(key)
        self.assertEqual(offenders, [])


class TestTheCommandDescribesItselfThatWay(EvenniaTest):
    """The phrasing the parser rejected is the phrasing the command
    prints — which is what makes this worth fixing rather than
    documenting around."""

    def test_the_verb_helper_says_sit_down(self):
        from commands.CmdFurniture import _verb
        self.assertEqual(_verb("sitting"), "sit down")

    def test_and_lie_down(self):
        from commands.CmdFurniture import _verb
        self.assertEqual(_verb("lying"), "lie down")

    def test_liedown_is_an_alias(self):
        from commands.CmdFurniture import CmdLie
        self.assertIn("liedown", CmdLie.aliases)
