"""The forensic cache stores a roll, so each door asks at its own DC.

Regression pin for #2622 / #2660.  ``forensic_recognition_cache`` is
shared by two callers that roll different difficulties against it:

* ``typeclasses/identity_bearer.py`` — the look-time mixin, DC 3 at
  *moderate* decay and **DC 5** at *advanced*.
* ``commands/forensics.py`` — ``inspect`` / ``autopsy``, always
  ``AUTOPSY_DC_BASIC`` (3).

The engine used to cache ``roll >= dc`` and replay that bare verdict,
so whichever door rolled first answered for the other at its own
difficulty.  Both directions were wrong and both were permanent,
because nothing invalidates the slot:

* **Leak** — an ``inspect`` success at DC 3 replayed as recognition
  on a later look at DC 5, an identity recovered at a difficulty the
  looker never beat.
* **Lockout** — a look-time failure at DC 5 blocked the deliberate
  ``inspect`` at DC 3 that the same roll would have passed, making a
  player-initiated examination inert because of a passive roll they
  never asked for.

Caching the roll keeps the permanence the docstring argues for — one
attempt per observer per subject, no Intellect re-rolls — while
letting a harder question get a harder answer from it.
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from world.forensics import ForensicSubject, attempt_forensic_recognition


class _DB:
    pass


class _FakeOwner:
    """Cache owner — only ``db.<cache_attr>`` is touched."""

    def __init__(self) -> None:
        self.db = _DB()
        self.db.forensic_recognition_cache = None


class _FakeObserver:
    def __init__(self, *, dbref="#42") -> None:
        self.dbref = dbref


def _subject(apparent_uid="abc123"):
    return ForensicSubject(
        signature=("uid-jorge", None, None, None, ()),
        apparent_uid_at_death=apparent_uid,
        essential_item_type_ids=(),
        source_kind="corpse",
        source_ref=None,
    )


# The two DCs that actually collide in the live game.
LOOK_ADVANCED_DC = 5
AUTOPSY_DC = 3


class TestAHarderLookIsAHarderQuestion(TestCase):
    """One stored roll, judged separately by each caller's DC."""

    def _attempt(self, observer, owner, dc, roll):
        with patch("world.combat.dice.roll_stat", return_value=roll):
            return attempt_forensic_recognition(
                observer, _subject(), dc, cache_owner=owner,
            )

    # -- the lockout direction -------------------------------------

    def test_a_failed_glance_does_not_block_a_deliberate_autopsy(self):
        """Roll 4: fails the look at DC 5, must still pass inspect at 3."""
        owner, observer = _FakeOwner(), _FakeObserver()

        glance = self._attempt(observer, owner, LOOK_ADVANCED_DC, roll=4)
        self.assertFalse(glance.success)

        autopsy = self._attempt(observer, owner, AUTOPSY_DC, roll=99)
        self.assertTrue(
            autopsy.success,
            "a passive look-time failure at DC 5 permanently blocked the "
            "deliberate examination at DC 3 that the same roll passes",
        )
        self.assertTrue(autopsy.from_cache, "the roll must not be re-rolled")

    # -- the leak direction ----------------------------------------

    def test_an_easy_success_is_not_recognition_at_a_harder_dc(self):
        """Roll 4: passes inspect at DC 3, must not replay as a DC-5 look."""
        owner, observer = _FakeOwner(), _FakeObserver()

        autopsy = self._attempt(observer, owner, AUTOPSY_DC, roll=4)
        self.assertTrue(autopsy.success)

        glance = self._attempt(observer, owner, LOOK_ADVANCED_DC, roll=99)
        self.assertFalse(
            glance.success,
            "an inspect success at DC 3 replayed as recognition at DC 5 — "
            "an identity recovered at a difficulty never beaten",
        )
        self.assertTrue(glance.from_cache)

    # -- the permanence the fix must not spend ---------------------

    def test_the_second_look_never_rolls_again(self):
        """The anti-re-roll intent: one roll per observer per subject."""
        owner, observer = _FakeOwner(), _FakeObserver()
        self._attempt(observer, owner, LOOK_ADVANCED_DC, roll=4)

        with patch("world.combat.dice.roll_stat") as mocked:
            attempt_forensic_recognition(
                observer, _subject(), AUTOPSY_DC, cache_owner=owner,
            )
            mocked.assert_not_called()

    def test_a_failure_at_the_same_dc_stays_a_failure(self):
        """Control: same-DC replay is unchanged — no free re-roll."""
        owner, observer = _FakeOwner(), _FakeObserver()
        first = self._attempt(observer, owner, AUTOPSY_DC, roll=1)
        second = self._attempt(observer, owner, AUTOPSY_DC, roll=99)
        self.assertFalse(first.success)
        self.assertFalse(second.success)
        self.assertTrue(second.from_cache)

    def test_a_success_at_the_same_dc_stays_a_success(self):
        """Control the other way: the harness can report either verdict."""
        owner, observer = _FakeOwner(), _FakeObserver()
        first = self._attempt(observer, owner, AUTOPSY_DC, roll=99)
        second = self._attempt(observer, owner, AUTOPSY_DC, roll=1)
        self.assertTrue(first.success)
        self.assertTrue(second.success)

    def test_a_distinct_observer_gets_their_own_roll(self):
        """Control: the slot is per-observer, not per-subject."""
        owner = _FakeOwner()
        self._attempt(_FakeObserver(dbref="#42"), owner, AUTOPSY_DC, roll=1)
        other = self._attempt(
            _FakeObserver(dbref="#43"), owner, AUTOPSY_DC, roll=99,
        )
        self.assertTrue(other.success)
        self.assertFalse(other.from_cache)

    # -- what the live DB already holds ----------------------------

    def test_a_legacy_boolean_entry_replays_as_its_verdict(self):
        """Pre-fix slots stored the verdict; the roll behind it is gone.

        Three ``SeveredHead``s carry populated caches live.  A stored
        ``True`` must not be read as the integer 1 — ``isinstance(True,
        int)`` is True in Python, so a naive int compare would turn
        every legacy success into a failure at any DC above 1.
        """
        observer = _FakeObserver()

        for verdict in (True, False):
            with self.subTest(verdict=verdict):
                owner = _FakeOwner()
                owner.db.forensic_recognition_cache = {
                    ("#42", "abc123"): verdict,
                }
                with patch("world.combat.dice.roll_stat") as mocked:
                    result = attempt_forensic_recognition(
                        observer, _subject(), LOOK_ADVANCED_DC,
                        cache_owner=owner,
                    )
                    mocked.assert_not_called()
                self.assertIs(result.success, verdict)
                self.assertTrue(result.from_cache)

    def test_an_unreadable_slot_rolls_afresh_rather_than_answering(self):
        """A slot we cannot compare is not an answer."""
        owner, observer = _FakeOwner(), _FakeObserver()
        owner.db.forensic_recognition_cache = {("#42", "abc123"): "corrupt"}

        with patch("world.combat.dice.roll_stat", return_value=99) as mocked:
            result = attempt_forensic_recognition(
                observer, _subject(), AUTOPSY_DC, cache_owner=owner,
            )
            mocked.assert_called_once()
        self.assertTrue(result.success)
        self.assertFalse(result.from_cache)
