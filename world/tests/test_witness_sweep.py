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
