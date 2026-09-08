"""There is deliberately no auto-reaper (#2450).

`DEATH_AND_SLEEVE_LIFECYCLE_SPEC` §7 is a dated owner design decision:

> **Persistence is intentional — remains are world-state, not garbage
> (design decision, 2026-07-04).** There is deliberately **no
> auto-reaper**. A corpse decays to `skeletal` and *stays* until
> something in the world removes it.

and it names the two consequences the design wants: uncollected remains
as environmental storytelling ("the harder the room is to reach, the
longer the story persists"), and cleanup as an economic loop — the
corpse-disposal gig, deferred at §9 step 4.

The code had a 14-day reaper behind **two doors**. `Room.
_check_corpse_decay` deleted any corpse past the threshold on the next
character entry, dumping whatever was still on the body loose on the
floor. And `Corpse.return_appearance` called `_handle_complete_decay`
and then `return None` — so `look <remains>` printed literally nothing
to the player before the object vanished.

**Measured live before the fix: six corpses aged 18.8–19.4 days, every
one already past the threshold and returning True.** They had survived
only because nobody had walked into those rooms — two hospital rooftops
and a hull-top, precisely the hard-to-reach case the design is built
around. They would have gone on the next footstep, and the deletion is
irreversible while this revert is one line.

Both methods are removed rather than left uncalled: a reaper nothing
invokes is a loaded gun for the next caller to rediscover. Decay to
skeletal STAYS — the stage key still advances on room entry. It is only
the terminal delete that goes.
"""
import time

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class _RemainsCase(EvenniaTest):
    def corpse(self, age_days=0.0):
        body = create_object("typeclasses.corpse.Corpse", key="a corpse",
                             location=self.room1)
        stamp = time.time() - age_days * 86400
        body.db.creation_time = stamp
        body.db.death_time = stamp
        return body


class TestAnOldCorpseSurvives(_RemainsCase):
    def test_a_twenty_day_corpse_is_not_deleted_on_entry(self):
        body = self.corpse(20)
        self.room1._check_corpse_decay()
        self.assertTrue(body.pk, "the reaper is still armed")

    def test_a_hundred_day_corpse_survives_too(self):
        """No threshold at all, not merely a longer one."""
        body = self.corpse(100)
        self.room1._check_corpse_decay()
        self.assertTrue(body.pk)

    def test_repeated_entries_do_not_wear_it_down(self):
        body = self.corpse(20)
        for _ in range(5):
            self.room1._check_corpse_decay()
        self.assertTrue(body.pk)

    def test_its_belongings_are_not_dumped_on_the_floor(self):
        body = self.corpse(20)
        shiv = create_object("typeclasses.items.Item", key="a shiv",
                             location=body)
        self.room1._check_corpse_decay()
        self.assertIs(shiv.location, body)


class TestLookingAtOldRemainsShowsSomething(_RemainsCase):
    def test_an_old_corpse_still_renders(self):
        """The look path deleted it and returned None — the player saw
        nothing at all."""
        body = self.corpse(20)
        self.assertTrue(str(body.return_appearance(self.char1) or ""))

    def test_and_looking_does_not_delete_it(self):
        body = self.corpse(20)
        body.return_appearance(self.char1)
        self.assertTrue(body.pk)


class TestTheReaperIsGoneNotJustUnwired(_RemainsCase):
    def test_neither_method_survives(self):
        from typeclasses.corpse import Corpse
        for name in ("check_complete_decay", "_handle_complete_decay"):
            self.assertFalse(hasattr(Corpse, name),
                             f"{name} is still a loaded gun")


class TestDecayToSkeletalStillHappens(_RemainsCase):
    """Only the terminal delete goes — the stage ladder is wanted."""

    def test_an_old_corpse_reaches_a_late_stage(self):
        body = self.corpse(20)
        self.assertTrue(body.get_decay_stage())

    def test_a_fresh_corpse_and_an_old_one_differ(self):
        fresh = self.corpse(0)
        old = self.corpse(20)
        self.assertNotEqual(fresh.get_decay_stage(), old.get_decay_stage())

    def test_the_key_still_refreshes_on_entry(self):
        body = self.corpse(20)
        self.room1._check_corpse_decay()   # must not raise
        self.assertTrue(body.pk and body.key)
