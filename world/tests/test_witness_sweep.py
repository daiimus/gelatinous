"""A witness stranded by a reload (#2367).

The flash-temp contract is "exists for the report, lingers briefly, and
despawns". The last part rides `delay(90s, despawn_witness)` — a Twisted
callback, which does NOT survive a reload. A reload inside that window
loses it and the witness stands in the street forever, wearing the
crowd's clothes and carrying a walkie. Two were found months later.
"""
import time
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaTest

from world.director import witness as wit


class TestTheStrandedSweep(BaseEvenniaTest):
    def _witness(self, age_seconds):
        w = create_object("typeclasses.characters.Character",
                          key="a wide-eyed off-shift tenant",
                          location=self.room1)
        w.db.is_witness = True
        # `spawn_witness` also tags them: the attribute is the marker,
        # the tag is how the 45s sweep FINDS them without walking the
        # whole object table (#2759).
        w.tags.add(wit.WITNESS_TAG[0], category=wit.WITNESS_TAG[1])
        return w, time.time() + age_seconds

    def test_a_fresh_witness_is_left_alone(self):
        """Their own despawn is still pending — sweeping now would
        delete them mid-report."""
        w, _ = self._witness(0)
        wit.sweep_stranded(now=time.time())
        self.assertTrue(w.pk)

    def test_a_stranded_witness_is_swept(self):
        w, now = self._witness(0)
        swept = wit.sweep_stranded(now=now + wit.WITNESS_MAX_AGE + 1)
        self.assertEqual(swept, 1)
        self.assertIsNone(w.pk)

    def test_it_leaves_everyone_else_standing(self):
        """The marker is the whole qualification — an ordinary NPC that
        happens to be old is not a stranded witness."""
        bystander = create_object("typeclasses.characters.Character",
                                  key="Aiko", location=self.room1)
        wit.sweep_stranded(now=time.time() + wit.WITNESS_MAX_AGE + 1)
        self.assertTrue(bystander.pk)

    def test_a_dead_witness_belongs_to_the_corpse_pipeline(self):
        w, now = self._witness(0)
        with mock.patch.object(type(w), "is_dead", return_value=True):
            wit.sweep_stranded(now=now + wit.WITNESS_MAX_AGE + 1)
        self.assertTrue(w.pk)


class TestTheSweepDoesNotWalkTheWholeTable(BaseEvenniaTest):
    """Finding witnesses must not cost the whole object table (#2759).

    The sweep runs on the 45s director heartbeat and used to iterate
    `ObjectDB.objects.all()`, instantiating every row through the
    typeclass system to find objects that a tag returns in one indexed
    hit — Law 8 ("the reactor is the budget") with the fix named by
    Law 3 ("tags for lookup, never attribute-key queries on a hot path").
    """

    def test_it_looks_up_by_tag_not_by_scanning(self):
        with mock.patch("evennia.objects.models.ObjectDB.objects") as objects:
            wit.sweep_stranded(now=time.time())
            objects.all.assert_not_called()

    def test_an_untagged_object_carrying_the_flag_is_not_found(self):
        """The tag is the index; something never spawned as a witness is
        simply not in it."""
        stray = create_object("typeclasses.characters.Character",
                              key="a stray", location=self.room1)
        stray.db.is_witness = True          # marker, but no tag
        wit.sweep_stranded(now=time.time() + wit.WITNESS_MAX_AGE + 1)
        self.assertTrue(stray.pk)


class TestTheSweepCountsWhatItRemoved(BaseEvenniaTest):
    """A dead witness must not be reported swept forever (#2759).

    `despawn_witness` declines the dead — the corpse pipeline owns that
    body — but the count incremented on the CALL, so a witness who died
    while stranded was re-selected every heartbeat and logged as
    "1 stranded despawned" permanently, for a body never removed.
    """

    def _witness(self, room):
        w = create_object("typeclasses.characters.Character",
                          key="a wide-eyed off-shift tenant", location=room)
        w.db.is_witness = True
        w.tags.add(wit.WITNESS_TAG[0], category=wit.WITNESS_TAG[1])
        return w

    def test_a_dead_witness_is_not_counted(self):
        w = self._witness(self.room1)
        with mock.patch.object(type(w), "is_dead", return_value=True):
            swept = wit.sweep_stranded(
                now=time.time() + wit.WITNESS_MAX_AGE + 1)
        self.assertEqual(swept, 0, "counted a body it did not remove")
        self.assertTrue(w.pk)
