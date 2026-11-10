"""`sabotage` and the structure branch of `repair` find their target with
the core matcher (#3783).

They used to walk the room by hand and take the first breachable thing
whose key or alias CONTAINED the typed text: "tenna" felled the antenna
mast, ordinals meant nothing, and nothing perceived or not mattered.
Now both verbs hand the breachable structures in the room to
`Character.search` as its pool, so a name means what it means in every
other command: exact key or alias first, then words that START a word of
the name, ordinals counted over that pool, and the presence gate.

Searches run as `char2`, who holds no staff permission. The channel is
captured rather than run (world/channeled.py owns timing), and its
callbacks are fired directly, as `test_breach.py` does.
"""
from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdArmor import CmdArmorRepair
from commands.CmdBreach import (CmdSabotage, breachable_here,
                                try_repair_structure, wreck_structure)

NOT_FOUND = "Sabotage what? Nothing here answers to that."


class _Breach(EvenniaCommandTest):

    def structure(self, key="antenna mast", *, aliases=None,
                  breachable=True, wrecked=False):
        obj = create_object("typeclasses.objects.Object", key=key,
                            location=self.room1, aliases=aliases or [])
        obj.db.breachable = True if breachable else None
        obj.db.intact = True
        obj.db.desc = "authored prose"
        obj.db.sensory_contributions = {"visual": "authored"}
        if wrecked:
            wreck_structure(obj)
        return obj

    def drive(self, cmd, args, cmdstring=None):
        """Drive the real command as char2; return (output, channel)."""
        channel = {}

        def begin(actor, duration, tell, on_complete, on_interrupt, key):
            channel.update(actor=actor, complete=on_complete,
                           interrupt=on_interrupt, key=key)
            return True

        with patch("world.channeled.begin_channel", side_effect=begin):
            out = self.call(cmd, args, caller=self.char2,
                            cmdstring=cmdstring) or ""
        return out, channel

    def sabotage(self, args):
        return self.drive(CmdSabotage(), args)

    def repair(self, args):
        return self.drive(CmdArmorRepair(), args, cmdstring="repair")


class SabotageFindsByTheCoreMatcher(_Breach):

    def test_an_alias_that_is_not_in_the_key_resolves(self):
        mast = self.structure(aliases=["dispatch spar"])
        _, channel = self.sabotage("dispatch spar")
        self.assertEqual(channel.get("key"), "sabotaging")
        with patch("world.director.crime.report_crime"):
            channel["complete"]()
        self.assertIs(mast.db.intact, False)

    def test_an_ordinal_picks_the_second_twin(self):
        # Created first, so an ordinal counted over the whole room would
        # make the first mast "2nd". Only breachable things are counted.
        self.structure(breachable=False)
        first = self.structure()
        second = self.structure()
        _, channel = self.sabotage("2nd antenna mast")
        with patch("world.director.crime.report_crime"):
            channel["complete"]()
        self.assertIs(second.db.intact, False)
        self.assertIs(first.db.intact, True)

    def test_a_fragment_from_inside_a_word_is_refused(self):
        mast = self.structure()
        out, channel = self.sabotage("tenna")
        self.assertIn(NOT_FOUND, out)
        self.assertFalse(channel)
        self.assertIs(mast.db.intact, True)

    def test_control_a_word_start_resolves(self):
        self.structure()
        _, channel = self.sabotage("ant")
        self.assertEqual(channel.get("key"), "sabotaging")

    def test_here_and_me_name_no_structure(self):
        self.structure()
        for word in ("here", "me"):
            out, channel = self.sabotage(word)
            self.assertIn(NOT_FOUND, out)
            self.assertFalse(channel)

    def test_an_empty_name_is_refused(self):
        self.structure()
        out, channel = self.sabotage("")
        self.assertIn(NOT_FOUND, out)
        self.assertFalse(channel)

    def test_a_thing_that_is_not_breachable_is_not_found(self):
        self.structure(breachable=False)
        out, channel = self.sabotage("antenna mast")
        self.assertIn(NOT_FOUND, out)
        self.assertFalse(channel)
        self.assertEqual(breachable_here(self.char2), [])

    def test_completion_wrecks_and_commits_the_crime(self):
        mast = self.structure()
        _, channel = self.sabotage("antenna mast")
        self.assertEqual(channel["key"], "sabotaging")
        with patch("world.director.crime.report_crime") as crime:
            channel["complete"]()
        self.assertIs(mast.db.intact, False)
        crime.assert_called_once_with("sabotage", self.room1,
                                      perp=self.char2)

    def test_interruption_lands_nothing(self):
        mast = self.structure()
        _, channel = self.sabotage("antenna mast")
        channel["interrupt"](0.9)
        self.assertIs(mast.db.intact, True)
        self.assertEqual(mast.db.desc, "authored prose")

    def test_already_wrecked_refuses(self):
        self.structure(wrecked=True)
        out, channel = self.sabotage("antenna mast")
        self.assertIn("already down", out)
        self.assertFalse(channel)


class RepairFindsByTheCoreMatcher(_Breach):

    def test_an_alias_that_is_not_in_the_key_resolves(self):
        mast = self.structure(aliases=["dispatch spar"], wrecked=True)
        _, channel = self.repair("dispatch spar")
        self.assertEqual(channel.get("key"), "repairing")
        channel["complete"]()
        self.assertIs(mast.db.intact, True)
        self.assertEqual(mast.db.desc, "authored prose")

    def test_an_ordinal_picks_the_second_twin(self):
        self.structure(breachable=False)
        first = self.structure(wrecked=True)
        second = self.structure(wrecked=True)
        _, channel = self.repair("2nd antenna mast")
        channel["complete"]()
        self.assertIs(second.db.intact, True)
        self.assertIs(first.db.intact, False)

    def test_a_fragment_from_inside_a_word_falls_to_armor(self):
        mast = self.structure(wrecked=True)
        out, channel = self.repair("tenna")
        self.assertFalse(channel)
        self.assertNotIn("rigging", out)
        self.assertIs(mast.db.intact, False)
        self.assertFalse(try_repair_structure(self.char2, "tenna"))

    def test_me_and_here_fall_to_armor(self):
        self.structure(wrecked=True)
        self.assertFalse(try_repair_structure(self.char2, "me"))
        self.assertFalse(try_repair_structure(self.char2, "here"))

    def test_a_tool_clause_is_not_a_structure_name(self):
        self.structure(wrecked=True)
        self.assertFalse(
            try_repair_structure(self.char2, "mast with sewing kit"))

    def test_no_breachable_match_yields_to_armor(self):
        self.assertFalse(try_repair_structure(self.char2, "vest"))

    def test_intact_structure_reports_sound_without_channel(self):
        self.structure()
        out, channel = self.repair("antenna mast")
        self.assertIn("standing and sound", out)
        self.assertFalse(channel)
