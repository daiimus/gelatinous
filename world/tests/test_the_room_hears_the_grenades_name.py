"""The room hears the grenade's name, not what the hero typed (#3354).

`jump on gren` broadcast "leaping onto gren!" and "gren explodes..." to
every observer: six room lines interpolated the parsed argument instead
of the object the search resolved. They name the object now; only the
caller-only "You don't see 'gren' here" keeps the typed text.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.combat import jump as jump_mod
from commands.combat.jump import CmdJump


class TheRoomHearsTheGrenadesNameTest(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        self.nade = create_object("typeclasses.items.Item", key="tactical grenade", location=self.room1)
        self.nade.db.is_explosive = True          # unarmed: the "wasn't even armed" path, no blast
        self.room_lines = []
        self.room1.msg_contents = lambda text=None, **kw: self.room_lines.append(str(text))

    def _jump(self, typed):
        captured = []
        def _mri(location=None, template="", **kw):
            captured.append(template)
        patches = [
            mock.patch.object(jump_mod, "msg_room_identity", side_effect=_mri),
            # the reveal is scheduled with `delay`; run it now (no reactor under test)
            mock.patch.object(jump_mod, "delay", side_effect=lambda t, cb, *a, **k: cb(*a, **k)),
        ]
        for p in patches:
            p.start(); self.addCleanup(p.stop)
        out = self.call(CmdJump(), typed, caller=self.char1)
        return out, captured + self.room_lines

    def test_an_abbreviation_never_reaches_the_room(self):
        out, lines = self._jump("on tac")
        joined = " ".join(lines)
        self.assertTrue(lines, "nothing was broadcast: %r" % out)
        self.assertNotIn("tac ", joined + " ")
        self.assertNotIn("onto tac", joined)
        self.assertIn("tactical grenade", joined)

    def test_the_sentence_starting_line_is_capitalised(self):
        out, lines = self._jump("on tac")
        armed = [l for l in lines if "wasn't even armed" in l]
        self.assertTrue(armed, lines)
        self.assertIn("The tactical grenade wasn't even armed", armed[0])

    def test_the_callers_parse_error_still_quotes_what_they_typed(self):
        out = self.call(CmdJump(), "on zzz", caller=self.char1)
        self.assertIn("You don't see 'zzz' here", out)
