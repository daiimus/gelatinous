"""The one doing the traversal trips the trap (#2466).

Reported as an asymmetry: in the drag branch of `Exit.at_traverse`,
`check_auto_defuse` is called for the grappler **and** the victim on
adjacent lines, while `check_rigged_grenade` is called for the grappler
only. The victim moves with `move_hooks=False`, so nothing on their own
move path fires either.

**Owner ruling (2026-09-06): current behaviour is correct.** Whoever is
dragging the body does the check; the dragged body defers to them,
because they are not the one doing the traversal. So the asymmetry is
intended — defusing is something either party can notice, but tripping a
rigged exit belongs to whoever actually walked through it.

Pinned here rather than left as a comment alone, because the shape reads
as an oversight: two sibling checks four lines apart, one called twice
and one called once. The next reader will file this again otherwise.

Also removed while here: `hands = getattr(traversing_object, "hands", {})`
at two sites in the same function, assigned and never read — left behind
when the weapon lookup moved to `get_wielded_weapon`.
"""
from evennia.utils.test_resources import EvenniaTest


class TestTheRulingIsInTheCode(EvenniaTest):
    def _source(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / "typeclasses" / "exits.py").read_text(errors="ignore")

    def test_the_grappler_is_checked(self):
        self.assertIn("check_rigged_grenade(traversing_object, self)",
                      self._source())

    def test_the_victim_is_not_checked(self):
        """The ruling, as code: adding this call would reverse it."""
        self.assertNotIn("check_rigged_grenade(grappled_victim_obj",
                         self._source())

    def test_both_parties_still_get_auto_defuse(self):
        body = self._source()
        self.assertIn("check_auto_defuse(traversing_object)", body)
        self.assertIn("check_auto_defuse(grappled_victim_obj)", body)

    def test_the_asymmetry_is_explained_where_it_lives(self):
        """Without this the next audit files it again."""
        self.assertIn("owner ruling, #2466", self._source())


class TestTheDeadLocalsAreGone(EvenniaTest):
    def test_no_unread_hands_local(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        body = (root / "typeclasses" / "exits.py").read_text(errors="ignore")
        self.assertNotIn('hands = getattr(traversing_object, "hands", {})',
                         body)

    def test_the_weapon_lookup_still_happens(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        body = (root / "typeclasses" / "exits.py").read_text(errors="ignore")
        self.assertIn("get_wielded_weapon(traversing_object)", body)
