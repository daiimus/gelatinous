"""A severed part's prose advances with its name (#2723).

The key carries a condition prefix recomputed as the part decays; the
`desc` was written once at sever time and never re-derived. Measured
live: 27 severed parts, **18 named "skeletal"** whose description still
read

    "A severed rat's head, the snout still twitching as if ready to
     sniff and the cut at the ne..."

A player looking at a skeletal rat head read about a twitching snout.

The two drifted because they are keyed on different scales: the NAME
advances through `_DECAY_STAGES` (fresh / early / moderate / advanced /
skeletal) and the PROSE is registered against the coarser
organ-condition scale (pristine / damaged / putrid). Nothing related
them, so only one moved.

TWO DELIBERATE LIMITS, both about not making it worse:

* Only the UNTOUCHED SEEDED prose is advanced. The refresh recomposes
  what the part's recorded `db.condition` would have produced and
  rewrites only if that is still exactly what is stored -- so a
  hand-authored description survives the decay clock. Staff prose for
  one specific severed hand is not collateral.
* A tier with no registered prose is left alone.
  `get_severed_part_description` returns "" for an unregistered
  (species, location, condition), and an empty desc reads worse than a
  stale one.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.anatomy import (
    get_severed_part_description,
    prepend_condition_to_desc,
)


class _Part(EvenniaTest):
    SPECIES = "human"
    LOCATION = "left_arm"

    def _seeded(self, condition):
        return prepend_condition_to_desc(
            condition,
            get_severed_part_description(self.SPECIES, self.LOCATION,
                                         condition),
        )

    def _part(self, *, condition="pristine"):
        part = create_object("typeclasses.items.Appendage",
                             key="human left arm", location=self.room1)
        part.db.source_species = self.SPECIES
        part.db.location_name = self.LOCATION
        part.db.condition = condition
        part.db.desc = self._seeded(condition)
        return part

    def _at_stage(self, part, stage):
        return mock.patch.object(type(part), "get_decay_stage",
                                 return_value=stage)


class TestTheProseFollowsTheDecay(_Part):

    def test_the_fixture_seeds_real_prose(self):
        """Control: if the prose table has nothing for this part, every
        assertion below passes while testing nothing."""
        self.assertTrue(self._seeded("pristine"),
                        "no registered prose for the fixture part")
        self.assertNotEqual(self._seeded("pristine"), self._seeded("putrid"))

    def test_a_fresh_part_is_unchanged(self):
        part = self._part()
        with self._at_stage(part, "fresh"):
            part._refresh_decay_desc_if_seeded()
        self.assertEqual(part.db.desc, self._seeded("pristine"))

    def test_a_skeletal_part_stops_sounding_fresh(self):
        part = self._part()
        with self._at_stage(part, "skeletal"):
            part._refresh_decay_desc_if_seeded()
        self.assertEqual(part.db.desc, self._seeded("putrid"))
        self.assertNotEqual(part.db.desc, self._seeded("pristine"))

    def test_the_recorded_condition_advances_too(self):
        """Or the next refresh would compare against a stale baseline
        and refuse to move again."""
        part = self._part()
        with self._at_stage(part, "skeletal"):
            part._refresh_decay_desc_if_seeded()
        self.assertEqual(part.db.condition, "putrid")


class TestItDoesNotClobberAuthoredProse(_Part):

    def test_an_edited_description_survives(self):
        part = self._part()
        part.db.desc = "A staff-written arm, notable for reasons."
        with self._at_stage(part, "skeletal"):
            part._refresh_decay_desc_if_seeded()
        self.assertEqual(part.db.desc,
                         "A staff-written arm, notable for reasons.")

    def test_a_part_with_no_seeded_desc_is_left_alone(self):
        part = self._part()
        part.db.desc = ""
        with self._at_stage(part, "skeletal"):
            part._refresh_decay_desc_if_seeded()
        self.assertEqual(part.db.desc, "")


class TestTheKeyRefreshDrivesIt(_Part):

    def test_refreshing_the_key_refreshes_the_prose(self):
        """The lifecycle hook the room already calls."""
        part = self._part()
        with self._at_stage(part, "skeletal"):
            part._refresh_decay_key_if_changed()
        self.assertEqual(part.db.desc, self._seeded("putrid"))
