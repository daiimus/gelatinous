"""Characterization tests for the death-progression lifecycle
(issue #477, the #469 close-out queue).

``_create_corpse_from_character`` is already covered by
``test_corpse_medical_snapshot`` / ``test_death_identity_snapshot`` /
``test_head_spawn_at_decap``.  This suite pins the previously
untested *lifecycle*: script setup, the ``at_repeat`` decision tree
(revival check → message scheduling → completion), the medical
revival path, the PC/NPC prose gate, completion orchestration, and —
critically — the deliberate failure semantics of the corpse-handoff
guard: a corpse-creation bug must be logged loudly but may never
strand the progression in a 30-second retry loop spawning corpses.

Run via::

    evennia test --settings settings.py world.tests.test_death_progression_lifecycle
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

from evennia import create_object, create_script
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character
from typeclasses.death_progression import (
    DeathProgressionScript,
    get_death_progression_status,
    start_death_progression,
)
from world.combat.constants import (
    DEATH_PROGRESSION_DURATION,
    DEATH_PROGRESSION_MESSAGE_COUNT,
)


class _LifecycleBase(EvenniaTest):
    character_typeclass = Character

    def setUp(self):
        super().setUp()
        # Touch medical state so the lazy initializer wires organs.
        _ = self.char1.medical_state
        # A dying character: total blood loss crosses the death
        # threshold, which is what holds the progression open.
        self.char1.medical_state.blood_level = 0.0
        self.script = create_script(DeathProgressionScript, obj=self.char1)

    def tearDown(self):
        if self.script and self.script.pk:
            self.script.stop()
            self.script.delete()
        super().tearDown()


class TestScriptSetup(_LifecycleBase):
    def test_creation_initializes_progression_state(self):
        self.assertEqual(self.script.db.total_duration, DEATH_PROGRESSION_DURATION)
        self.assertEqual(
            len(self.script.db.message_intervals), DEATH_PROGRESSION_MESSAGE_COUNT
        )
        spacing = DEATH_PROGRESSION_DURATION // DEATH_PROGRESSION_MESSAGE_COUNT
        self.assertEqual(self.script.db.message_intervals[0], spacing)
        self.assertEqual(self.script.db.messages_sent, [])
        self.assertTrue(self.script.db.can_be_revived)
        self.assertIsNotNone(self.script.db.start_time)

    def test_start_death_progression_reuses_existing_script(self):
        first = start_death_progression(self.char1)
        second = start_death_progression(self.char1)
        self.assertTrue(first)
        self.assertTrue(second)
        # Still exactly one progression script on the character.
        scripts = self.char1.scripts.get("death_progression")
        self.assertEqual(len(scripts), 1)

    def test_status_reports_progression(self):
        status = get_death_progression_status(self.char1)
        self.assertTrue(status["in_progression"])
        self.assertEqual(status["total_duration"], DEATH_PROGRESSION_DURATION)
        self.assertTrue(status["can_be_revived"])
        self.assertGreater(status["time_remaining"], 0)

    def test_status_without_script(self):
        npc = create_object(Character, key="statusless", location=self.room1)
        try:
            self.assertEqual(
                get_death_progression_status(npc), {"in_progression": False}
            )
        finally:
            npc.delete()


class TestRevivalCheck(_LifecycleBase):
    def test_dead_character_not_revived(self):
        self.assertFalse(
            self.script._check_medical_revival_conditions(self.char1)
        )

    def test_recovered_character_flagged_for_revival(self):
        self.char1.medical_state.blood_level = 100.0
        self.assertTrue(
            self.script._check_medical_revival_conditions(self.char1)
        )

    def test_revival_path_restores_and_cleans_up(self):
        """Medical recovery during at_repeat → revival messages, death
        state removed, script stopped and deleted."""
        self.char1.medical_state.blood_level = 100.0
        self.char1.msg = MagicMock()
        with patch.object(
            self.char1, "remove_death_state", create=True
        ) as mock_restore:
            self.script.at_repeat()
        mock_restore.assert_called_once()
        sent = " ".join(
            str(c.args[0]) for c in self.char1.msg.call_args_list if c.args
        )
        self.assertIn("medical treatment", sent.lower())
        # Script removed itself.
        self.assertFalse(self.char1.scripts.get("death_progression"))
        self.script = None  # tearDown guard


class TestProgressionMessages(_LifecycleBase):
    def test_message_sent_once_per_interval(self):
        first_interval = self.script.db.message_intervals[0]
        self.script.db.start_time = time.time() - (first_interval + 1)
        self.char1.msg = MagicMock()

        self.script.at_repeat()
        self.assertIn(first_interval, self.script.db.messages_sent)
        first_count = self.char1.msg.call_count
        self.assertGreater(first_count, 0)
        # Dying prose arrives attributed to the script.
        self.assertIs(
            self.char1.msg.call_args.kwargs.get("from_obj"), self.script
        )

        # Same elapsed window again: no duplicate message.
        self.script.at_repeat()
        self.assertEqual(self.char1.msg.call_count, first_count)

    def test_npc_skips_dying_prose(self):
        """The surreal dying monologue is PC-only (issue #356) — the
        timer still runs for NPCs, but the prose is suppressed."""
        npc = create_object(Character, key="dying rat", location=self.room1)
        _ = npc.medical_state
        npc.medical_state.blood_level = 0.0
        npc_script = create_script(DeathProgressionScript, obj=npc)
        try:
            self.assertFalse(npc_script._is_player_character())
            npc.msg = MagicMock()
            npc_script._send_initial_message()
            first = npc_script.db.message_intervals[0]
            npc_script._send_progression_message(first)
            npc.msg.assert_not_called()
        finally:
            if npc_script.pk:
                npc_script.stop()
                npc_script.delete()
            npc.delete()

    def test_pc_gate_is_account_presence(self):
        self.assertTrue(self.script._is_player_character())


class TestCompletion(_LifecycleBase):
    def test_at_repeat_triggers_completion_after_duration(self):
        self.script.db.start_time = time.time() - (
            DEATH_PROGRESSION_DURATION + 1
        )
        self.char1.msg = MagicMock()
        with patch.object(
            self.script, "_complete_death_progression"
        ) as mock_complete:
            self.script.at_repeat()
        mock_complete.assert_called_once()

    def test_completion_orchestration(self):
        """Completion: revival window closes, room is told, the corpse
        handoff runs, and the script removes itself."""
        self.char1.msg = MagicMock()
        with patch.object(
            self.script, "_handle_corpse_creation_and_transition"
        ) as mock_handoff, patch.object(
            self.char1, "apply_final_death_state", create=True
        ) as mock_final, patch(
            "world.identity_utils.msg_room_identity"
        ):
            self.script._complete_death_progression()

        self.assertFalse(self.script.db.can_be_revived if self.script.pk else False)
        mock_handoff.assert_called_once_with(self.char1)
        mock_final.assert_called_once()
        # PC got the final fade-out prose.
        self.assertTrue(self.char1.msg.called)
        # Script removed itself.
        self.assertFalse(self.char1.scripts.get("death_progression"))
        self.script = None  # tearDown guard

    def test_corpse_handoff_failure_is_contained_and_loud(self):
        """The deliberate guard: a corpse-creation bug is logged to the
        audit sink AND the server log, does not raise, and therefore
        cannot strand the progression in a 30s retry loop that spawns
        a corpse per tick."""
        router = MagicMock()
        with patch.object(
            self.script,
            "_create_corpse_from_character",
            side_effect=RuntimeError("corpse forge exploded"),
        ), patch(
            "typeclasses.death_progression.get_splattercast",
            return_value=router,
        ), patch(
            "typeclasses.death_progression.logger"
        ) as mock_logger:
            # Must not raise.
            self.script._handle_corpse_creation_and_transition(self.char1)

        audit_lines = " ".join(
            str(c.args[0]) for c in router.msg.call_args_list if c.args
        )
        self.assertIn("DEATH_COMPLETION_ERROR", audit_lines)
        # Mirrored to the server log with traceback.
        mock_logger.log_trace.assert_called_once()
