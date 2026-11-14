"""`forget <name>` on an absent person clears the voice too.

The history below names `forget_voice` and a sleeve-wide scope. Both are
gone since #3825: forgetting is `world.identity.erase_look`, and the
voice half is `world.voice.erase_voices_named`. The defect this module
pins is unchanged: forget somebody who has walked out, and their voice
must not go on naming them.

Regression pin for #2652.  ``CmdForget`` had two doors:

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

Scope, since #3825: **by name**. This used to be sleeve-wide, every
named voice of the same true body whatever the observer had called it.
The owner ruled that forgetting clears what the observer connected and
nothing because the game knows two things are one body. A voice is
given a name in one place only, ``remember <somebody in front of
you>``, so a voice under the forgotten name is the observer's own
connection, and a voice of the same body under another name is not.
The voice ENTRY goes, as the face entry does.
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

    def test_the_absent_door_forgets_the_voice(self):
        """The defect of #2652: face forgotten, voice still names them
        on the radio. The face fixture is named "Big J"."""
        caller = _observer(_voice_memory(("voice-jorge", "Big J", SLEEVE)))

        _forget_by_name(caller)

        self.assertNotIn(FACE_UID, caller.recognition_memory,
                         "fixture check: the face must be forgotten")
        self.assertNotIn(
            "voice-jorge", caller.voice_memory,
            "the voice survived the forget, so the forgotten person was "
            "still named over the radio",
        )

    def test_a_voice_of_that_body_under_another_name_stays(self):
        """It used to be cleared: "natural and modulated voices are one
        person". The observer never said so (#3825)."""
        caller = _observer(_voice_memory(
            ("voice-natural", "Big J", SLEEVE),
            ("voice-modulated", "the buzzing one", SLEEVE),
        ))

        _forget_by_name(caller)

        self.assertNotIn("voice-natural", caller.voice_memory)
        self.assertEqual(
            caller.voice_memory["voice-modulated"]["assigned_name"],
            "the buzzing one")

    def test_a_stranger_is_untouched(self):
        """The negative control. Forget is scoped to one name."""
        caller = _observer(_voice_memory(
            ("voice-jorge", "Big J", SLEEVE),
            ("voice-other", "Wren", "sleeve-someone-else"),
        ))

        _forget_by_name(caller)

        self.assertNotIn("voice-jorge", caller.voice_memory)
        self.assertEqual(
            caller.voice_memory["voice-other"]["assigned_name"], "Wren",
            "forgetting one person cleared an unrelated voice",
        )

    def test_an_entry_with_no_sleeve_recorded_is_forgotten_the_same(self):
        """Nothing here is done by sleeve any more."""
        memory = _seed_memory_with_sleeve(uid=FACE_UID, real_sleeve_uid=SLEEVE)
        memory[FACE_UID]["real_sleeve_uid"] = None
        caller = _observer(
            _voice_memory(("voice-jorge", "Big J", None)), memory=memory,
        )

        _forget_by_name(caller)

        self.assertNotIn("voice-jorge", caller.voice_memory)

    def test_an_empty_voice_memory_is_not_an_error(self):
        """The overwhelmingly common case today: no voice ever named."""
        caller = _observer({})
        _forget_by_name(caller)
        self.assertNotIn(FACE_UID, caller.recognition_memory)

    def test_the_by_name_helper_exists_and_reports_what_it_erased(self):
        """Bound off the module so this file still LOADS unfixed."""
        helper = getattr(voice_mod, "erase_voices_named", None)
        self.assertIsNotNone(
            helper, "world.voice.erase_voices_named is missing",
        )
        caller = _observer(_voice_memory(
            ("voice-a", "Big J", SLEEVE),
            ("voice-b", "", SLEEVE),          # never named: nothing to erase
            ("voice-c", "Wren", "sleeve-other"),
        ))
        self.assertEqual(helper(caller, "Big J"), 0,
                         "a voice of a known body is not matched by name "
                         "alone")
        self.assertEqual(helper(caller, "Big J", real_sleeve_uid=SLEEVE), 1)
        self.assertEqual(helper(caller, None), 0)
