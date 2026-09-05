"""A gap is not an edge in the map export (#2789).

`_link_kind` tested `is_edge` before `is_gap`, and every one of the
colony's 90 gaps also carries `is_edge` -- 100% overlap, measured -- so
the `gap` branch was reached by exactly zero exits. Not dead code:
shadowed live code, which is why the fix is ordering rather than
deletion.

The distinction is real to a player. An edge is a ledge you can fall
off; a gap is a space you jump across, and the colony's first
inter-building parkour crossing is a gap. Anything reading the export
saw all 90 jumps as ledges, and nothing surfaced it because "edge" is a
plausible answer and the classifier never errors.
"""
from types import SimpleNamespace
from unittest import TestCase

from world.mapping import _link_kind


def _exit(**flags):
    db = SimpleNamespace(is_door=None, is_edge=None, is_gap=None)
    for k, v in flags.items():
        setattr(db, k, v)
    return SimpleNamespace(db=db, key=flags.pop("key", "north"))


def _room(sky=False):
    return SimpleNamespace(db=SimpleNamespace(is_sky_room=sky or None))


class TestMostSpecificClaimWins(TestCase):
    def test_a_gap_that_is_also_an_edge_reads_as_a_gap(self):
        """The live shape: all 90 carry both flags."""
        self.assertEqual(
            _link_kind(_exit(is_gap=True, is_edge=True), _room()), "gap")

    def test_a_plain_edge_still_reads_as_an_edge(self):
        """The pin: 13 exits are edges and not gaps, and must stay so."""
        self.assertEqual(_link_kind(_exit(is_edge=True), _room()), "edge")

    def test_a_plain_gap_reads_as_a_gap(self):
        self.assertEqual(_link_kind(_exit(is_gap=True), _room()), "gap")

    def test_a_door_still_outranks_both(self):
        """Door is the most specific of all and keeps precedence — 0 of
        the 90 gaps are doors, but the ordering must not drift."""
        self.assertEqual(
            _link_kind(_exit(is_door=True, is_gap=True, is_edge=True),
                       _room()), "door")

    def test_a_sky_room_down_exit_is_a_fall(self):
        self.assertEqual(_link_kind(_exit(key="down"), _room(sky=True)),
                         "fall")

    def test_an_ordinary_exit_is_a_walk(self):
        self.assertEqual(_link_kind(_exit(), _room()), "walk")

    def test_only_a_literal_true_counts(self):
        """The flags are read with `is True`, so a truthy non-True value
        must not classify."""
        self.assertEqual(_link_kind(_exit(is_gap=1), _room()), "walk")
