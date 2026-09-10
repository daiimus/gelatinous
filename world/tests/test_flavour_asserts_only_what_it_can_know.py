"""Catalogue entries do not assert context the selector cannot check
(#2733).

Two live symptoms, one class:

  * Six NPCs standing on streets were described as "lying flat on the
    floor, staring at the ceiling", "standing in the middle of the room"
    and "blocking the doorway". A `look_place` is attached to a PERSON
    and the person moves; `look_places.py`'s own docstring says so --
    "Avoid naming specific scenery the room may not have".
  * A heavyset NPC had an abdomen "concave enough to suggest several
    missed meals". Its three neighbours making the same claim are tagged
    `slight`/`lean`; this one was untagged, so `_eligible` -- which
    filters on build -- offered it to every body.

Both are entries that assert a fact about context the selector cannot
check, with the machinery to exclude them sitting right there unused.
Same shape as #2731 (sex) and, before it, #2732 (pronouns): a pool
filtered on one axis, holding entries only valid on another.

ALL FOUR CATALOGUES ARE CHECKED HERE, which #2733 flags as the reason
these got in: the existing guards only ever read the HUMAN table, so
three of four shipped unchecked. The rat catalogue named baseboards and
the robot one swept "the room"; neither had a test that could see them.

SCOPED TO SCENERY A STREET GENUINELY LACKS -- ceiling, doorway,
baseboard, "the room". Walls and floors are deliberately NOT flagged:
almost every space has something wall-shaped and something underfoot,
and a guard that fails on "leaning against the nearest wall" would be
rejecting good prose to catch a rule it cannot state precisely.
"""
import re

from evennia.utils.test_resources import EvenniaTest

from world.mob_flavor import longdescs
from world.mob_flavor.look_places import LOOK_PLACES
from world.mob_flavor.look_places_rat import LOOK_PLACES_RAT
from world.mob_flavor.look_places_robot import LOOK_PLACES_ROBOT
from world.mob_flavor.look_places_synth import LOOK_PLACES_SYNTH

CATALOGUES = {
    "human": LOOK_PLACES,
    "rat": LOOK_PLACES_RAT,
    "robot": LOOK_PLACES_ROBOT,
    "synth": LOOK_PLACES_SYNTH,
}

INTERIOR = re.compile(r"\b(ceiling|ceilings|doorway|doorways|baseboard|"
                      r"baseboards)\b|\bthe room\b", re.I)


class TestLookPlacesTravel(EvenniaTest):

    def test_every_catalogue_is_read(self):
        """Control: the guards this replaces only read the human table,
        which is why the rat and robot entries survived."""
        for species, pool in CATALOGUES.items():
            self.assertTrue(pool, f"{species} catalogue is empty")

    def test_the_pattern_catches_what_it_is_for(self):
        """Control: and that it fires on the exact reported line."""
        self.assertTrue(
            INTERIOR.search("lying flat on the floor, staring at the ceiling."))
        self.assertFalse(
            INTERIOR.search("lying flat on the ground, staring at nothing."))

    def test_no_look_place_names_indoor_scenery(self):
        offenders = [f"{species}: {line}"
                     for species, pool in CATALOGUES.items()
                     for line in pool
                     if INTERIOR.search(line)]
        self.assertEqual(
            offenders, [],
            "a look_place travels with the person who carries it — a "
            "street has no ceiling:\n" + "\n".join(offenders))


class TestBodyClaimsAreTagged(EvenniaTest):

    def test_the_concave_abdomen_line_is_tagged(self):
        entries = longdescs.LONGDESCS["abdomen"]
        for entry in entries:
            text = entry[1] if isinstance(entry, tuple) else entry
            if "concave enough to suggest several missed meals" in text:
                self.assertIsInstance(
                    entry, tuple,
                    "an untagged line claiming a starved abdomen lands in "
                    "every body's pool, including a heavyset one")
                return
        self.fail("the line this test guards is no longer in the catalogue")
