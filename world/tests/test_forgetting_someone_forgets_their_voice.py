"""`forget <name>` on an absent person clears the voice too.

Regression pin for #2652.  ``CmdForget`` has two doors:

* ``_forget_visible`` — the target is in the room.  Clears the face, and
  clears the voice via ``forget_voice(caller, target)``.
* ``_forget_remembered`` — the target is absent, resolved by the name the
  observer assigned.  Cleared the face and **nothing else**.

So ``forget marcus`` for someone who had walked out half-worked, silently.
The next time they spoke where the observer could not see them — a dark
room, from behind, or **over the radio, which is voice-only** — they were
still announced by the name just deleted.  Radio makes that the common
case rather than the edge one: it is precisely the channel where voice
attribution is the whole mechanism.

The issue reported the omission as structural, on the grounds that
``forget_voice`` needs a live object to compute the current voice UID.
That was true when it was read and is not true now — #2809 gave
``forget_voice`` by-name and by-``voice_uid`` addressing, because
forgetting a voice needs nothing from the target.  What was missing was
the call.

Scope: **sleeve-wide**, matching what ``forget`` means when addressed to
a person rather than to a face in front of you, and matching the
pierce-cache clear on the same command.  The visible door stays
per-presentation — it has a presentation to scope to.
"""

from __future__ import annotations

from unittest import TestCase

from world import voice as voice_mod
from world.tests.test_identity_commands import (
    _make_character,
    _seed_memory_with_sleeve,
)

SLEEVE = "sleeve-jorge"
FACE_UID = "uid-target"


def _voice_memory(*entries):
    """Build a voice_memory dict from (voice_uid, name, sleeve) triples."""
    return {
        uid: {
            "assigned_name": name,
            "real_sleeve_uid": sleeve,
            "times_heard": 3,
        }
        for uid, name, sleeve in entries
    }


def _observer(voice_memory=None, memory=None):
    caller = _make_character(
        key="Observer",
        sleeve_uid="uid-observer",
        recognition_memory=(
            memory if memory is not None
            else _seed_memory_with_sleeve(uid=FACE_UID, real_sleeve_uid=SLEEVE)
        ),
    )
    caller.voice_memory = voice_memory if voice_memory is not None else {}
    caller.db.voice_discern_cache = None
    return caller


def _forget_by_name(caller):
    """Drive the absent door exactly as ``CmdForget.func`` does."""
    from commands.CmdCharacter import CmdForget

    cmd = CmdForget()
    cmd.caller = caller
    entry = caller.recognition_memory[FACE_UID]
    cmd._forget_remembered(caller, FACE_UID, entry)


class TestForgettingSomeoneForgetsTheirVoice(TestCase):

    def test_the_absent_door_clears_the_voice(self):
        """The defect: face forgotten, voice still names them on the radio."""
        caller = _observer(_voice_memory(("voice-jorge", "Big J", SLEEVE)))

        _forget_by_name(caller)

        self.assertEqual(
            caller.recognition_memory[FACE_UID]["assigned_name"], "",
            "fixture check — the face must be cleared either way",
        )
        self.assertEqual(
            caller.voice_memory["voice-jorge"]["assigned_name"], "",
            "the voice survived the forget, so the forgotten person was "
            "still named over the radio",
        )

    def test_every_presentation_of_that_sleeve_is_cleared(self):
        """Natural and modulated voices are one person; forget means both."""
        caller = _observer(_voice_memory(
            ("voice-natural", "Big J", SLEEVE),
            ("voice-modulated", "the buzzing one", SLEEVE),
        ))

        _forget_by_name(caller)

        for uid in ("voice-natural", "voice-modulated"):
            self.assertEqual(caller.voice_memory[uid]["assigned_name"], "")

    def test_a_stranger_sharing_no_sleeve_is_untouched(self):
        """The negative control. Forget is scoped to one person."""
        caller = _observer(_voice_memory(
            ("voice-jorge", "Big J", SLEEVE),
            ("voice-other", "Wren", "sleeve-someone-else"),
        ))

        _forget_by_name(caller)

        self.assertEqual(caller.voice_memory["voice-jorge"]["assigned_name"], "")
        self.assertEqual(
            caller.voice_memory["voice-other"]["assigned_name"], "Wren",
            "forgetting one person cleared an unrelated voice",
        )

    def test_the_entry_itself_survives(self):
        """Forget clears the name, not the history — as the face side does."""
        caller = _observer(_voice_memory(("voice-jorge", "Big J", SLEEVE)))

        _forget_by_name(caller)

        entry = caller.voice_memory["voice-jorge"]
        self.assertEqual(entry["times_heard"], 3)
        self.assertEqual(entry["real_sleeve_uid"], SLEEVE)

    def test_a_pre_schema_entry_falls_back_to_the_name(self):
        """No sleeve recorded: `remember` taught both axes one name."""
        memory = _seed_memory_with_sleeve(uid=FACE_UID, real_sleeve_uid=SLEEVE)
        memory[FACE_UID]["real_sleeve_uid"] = None
        caller = _observer(
            _voice_memory(("voice-jorge", "Big J", None)), memory=memory,
        )

        _forget_by_name(caller)

        self.assertEqual(caller.voice_memory["voice-jorge"]["assigned_name"], "")

    def test_an_empty_voice_memory_is_not_an_error(self):
        """The overwhelmingly common case today: no voice ever named."""
        caller = _observer({})
        _forget_by_name(caller)
        self.assertEqual(caller.recognition_memory[FACE_UID]["assigned_name"], "")

    def test_the_by_sleeve_helper_exists_and_reports_what_it_cleared(self):
        """Bound off the module so this file still LOADS unfixed."""
        helper = getattr(voice_mod, "forget_voices_for_sleeve", None)
        self.assertIsNotNone(
            helper, "world.voice.forget_voices_for_sleeve is missing",
        )
        caller = _observer(_voice_memory(
            ("voice-a", "Big J", SLEEVE),
            ("voice-b", "", SLEEVE),          # never named — nothing to clear
            ("voice-c", "Wren", "sleeve-other"),
        ))
        self.assertEqual(helper(caller, SLEEVE), 1)
        self.assertEqual(helper(caller, None), 0)
