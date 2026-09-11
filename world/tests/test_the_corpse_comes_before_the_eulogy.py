"""A failed death announcement must not cost the corpse.

Regression pin for #2629.  `DeathCurtain._on_animation_complete` ran the
room's death announcement FIRST and UNGUARDED -- an import, a
`get_death_cause_template` lookup, and a broadcast -- while the actual
death-state transition sat inside `except Exception`.

So the cosmetic half was guaranteed to run and could abort the method,
and the irreversible half was best-effort.  A raise anywhere in the
announcement meant `start_death_progression` was never reached.
`at_death` has already set `db.death_processed = True` by then and
returns early on it forever, so nothing retried: the body stayed
puppeted in the room with DeathCmdSet, no corpse, no archive, and
`at_post_login` auto-puppeted the player straight back into it.

`sweep_wedged_deaths` (#2932) now recovers that at the next boot, which
turns "permanent" into "wedged until the next reload".  A backstop is
not a reason to keep the order inverted -- doing the transition first
means a cosmetic failure costs a death message, not a corpse.

The guard on the transition is deliberate (#469): the animation chain
must finish either way.  The announcement now has one of its own, for
the same reason and in the other direction.
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock, patch

from typeclasses.curtain_of_death import DeathCurtain


def _curtain():
    curtain = MagicMock(spec=DeathCurtain)
    curtain.location = MagicMock()
    curtain.character = MagicMock()
    curtain.character.key = "Corpse-to-be"
    curtain.character.get_death_cause.return_value = "gunshot"
    curtain._on_animation_complete = (
        DeathCurtain._on_animation_complete.__get__(curtain, DeathCurtain)
    )
    return curtain


class TestTheCorpseComesBeforeTheEulogy(TestCase):

    # -- the defect ---------------------------------------------------

    def _run(self, curtain):
        """Drive the method, turning an ESCAPING exception into a named
        failure rather than a test error.

        The escape is the defect -- an unguarded raise in the
        announcement is exactly what stopped the transition being
        reached -- but an error reads like a broken harness. Say what
        it means instead.
        """
        try:
            curtain._on_animation_complete()
        except Exception as exc:  # noqa: BLE001 — this is the assertion
            self.fail(
                f"an exception escaped _on_animation_complete ({exc!r}); "
                f"the death transition was never reached"
            )


    def test_a_broken_announcement_still_produces_a_corpse(self):
        curtain = _curtain()
        with patch("typeclasses.death_progression.start_death_progression") as start, \
             patch("world.identity_utils.msg_room_identity",
                   side_effect=RuntimeError("broadcast exploded")), \
             patch("world.combat.debug.get_splattercast"), \
             patch("evennia.utils.logger.log_err"):
            self._run(curtain)

        start.assert_called_once_with(curtain.character)

    def test_a_broken_cause_lookup_still_produces_a_corpse(self):
        """The other unguarded call in the announcement half."""
        curtain = _curtain()
        with patch("typeclasses.death_progression.start_death_progression") as start, \
             patch("world.medical.medical_messages.get_death_cause_template",
                   side_effect=KeyError("no such cause")), \
             patch("world.combat.debug.get_splattercast"), \
             patch("evennia.utils.logger.log_err"):
            self._run(curtain)

        start.assert_called_once_with(curtain.character)

    def test_the_transition_happens_before_the_announcement(self):
        """Ordering is the fix; assert it directly, not by consequence."""
        order = []
        curtain = _curtain()
        with patch("typeclasses.death_progression.start_death_progression",
                   side_effect=lambda c: order.append("transition")), \
             patch("world.identity_utils.msg_room_identity",
                   side_effect=lambda **kw: order.append("announcement")), \
             patch("world.combat.debug.get_splattercast"):
            curtain._on_animation_complete()

        self.assertEqual(order, ["transition", "announcement"])

    # -- controls -----------------------------------------------------

    def test_the_announcement_still_happens_normally(self):
        curtain = _curtain()
        with patch("typeclasses.death_progression.start_death_progression"), \
             patch("world.identity_utils.msg_room_identity") as announce, \
             patch("world.combat.debug.get_splattercast"):
            curtain._on_animation_complete()

        announce.assert_called_once()
        self.assertIs(
            announce.call_args.kwargs["char_refs"]["actor"], curtain.character)

    def test_a_failed_transition_does_not_abort_the_chain(self):
        """The #469 guard: the animation chain finishes either way, and
        the room is still told."""
        curtain = _curtain()
        with patch("typeclasses.death_progression.start_death_progression",
                   side_effect=RuntimeError("progression exploded")), \
             patch("world.identity_utils.msg_room_identity") as announce, \
             patch("world.combat.debug.get_splattercast"), \
             patch("evennia.utils.logger.log_err") as logged:
            curtain._on_animation_complete()

        announce.assert_called_once()
        logged.assert_called()      # and it reaches the SERVER log, not
                                    # only the splattercast channel

    def test_no_location_means_no_announcement_but_still_a_corpse(self):
        curtain = _curtain()
        curtain.location = None
        with patch("typeclasses.death_progression.start_death_progression") as start, \
             patch("world.identity_utils.msg_room_identity") as announce, \
             patch("world.combat.debug.get_splattercast"):
            curtain._on_animation_complete()

        start.assert_called_once()
        announce.assert_not_called()
