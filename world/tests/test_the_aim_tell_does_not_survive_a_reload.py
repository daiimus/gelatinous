"""An aim tell does not outlive the aim (#2482).

Aim state lives in ``ndb`` and dies with the process. The tell it writes
— ``override_place`` — is a db attribute and does not. Every clear site
reads ``ndb.aiming_at`` first:

```python
current_target = getattr(caller.ndb, NDB_AIMING_AT, None)
if current_target:
    ...
    self._clear_aim_override_place(caller, current_target)
```

so after a reload `aim stop` and `stop aiming` both answer *"You're not
aiming at anything"* and refuse to clear a tell that is still showing.
The character stays described as taking careful aim, permanently, with
no path back.

The combat re-link sweep's own comment already named this:

    "ALL ndb state dies with the process — handler refs, melee
    proximity, aim."

It rebuilt the first two. This adds the third.

Three tells to recognise, which is why they are now named in
`world/combat/constants.py` instead of repeated as literals at seven
call sites: the person tell, the direction tell (which varies), and the
mutual-showdown tell.
"""
from evennia import create_object
from evennia.utils.test_resources import (EvenniaCommandTest,
                                          EvenniaTest)

from world.combat.constants import (AIM_TELL, SHOWDOWN_TELL,
                                    aim_direction_tell)
from world.combat.utils import sweep_stranded_aim_tells


class _SweepCase(EvenniaTest):
    def stranded(self, tell):
        """What a reload leaves: the tell written, the ndb gone."""
        self.char1.override_place = tell
        return self.char1


class TestTheSweepClearsWhatAReloadStranded(_SweepCase):
    def test_the_person_tell_is_cleared(self):
        char = self.stranded(AIM_TELL)
        self.assertEqual(sweep_stranded_aim_tells(), 1)
        self.assertEqual(char.override_place, "")

    def test_the_showdown_tell_is_cleared(self):
        char = self.stranded(SHOWDOWN_TELL)
        sweep_stranded_aim_tells()
        self.assertEqual(char.override_place, "")

    def test_the_direction_tell_is_cleared(self):
        char = self.stranded(aim_direction_tell("north"))
        sweep_stranded_aim_tells()
        self.assertEqual(char.override_place, "")

    def test_any_direction_is_recognised(self):
        for direction in ("north", "up", "the hatch", "southeast"):
            char = self.stranded(aim_direction_tell(direction))
            sweep_stranded_aim_tells()
            self.assertEqual(char.override_place, "", direction)

    def test_it_finds_the_attribute_at_all(self):
        """`override_place` is an AttributeProperty in the `description`
        CATEGORY, a different row from a bare `db.override_place` — a
        query on the key alone matches nothing and the sweep silently
        does no work."""
        self.stranded(AIM_TELL)
        self.assertEqual(sweep_stranded_aim_tells(), 1)

    def test_two_stranded_characters_are_both_cleared(self):
        self.char1.override_place = AIM_TELL
        self.char2.override_place = SHOWDOWN_TELL
        self.assertEqual(sweep_stranded_aim_tells(), 2)
        self.assertEqual(self.char1.override_place, "")
        self.assertEqual(self.char2.override_place, "")


class TestItLeavesEverythingElseAlone(_SweepCase):
    """The tell is one slot shared by several systems; a sweep that
    cleared it wholesale would strip the dead and the unconscious."""

    def test_a_death_placement_survives(self):
        self.char1.override_place = "lying motionless and deceased."
        self.assertEqual(sweep_stranded_aim_tells(), 0)
        self.assertEqual(self.char1.override_place,
                         "lying motionless and deceased.")

    def test_an_unconscious_placement_survives(self):
        self.char1.override_place = "unconscious and motionless."
        sweep_stranded_aim_tells()
        self.assertEqual(self.char1.override_place,
                         "unconscious and motionless.")

    def test_an_authored_placement_survives(self):
        self.char1.override_place = "leaning against the bar."
        sweep_stranded_aim_tells()
        self.assertEqual(self.char1.override_place,
                         "leaning against the bar.")

    def test_an_empty_placement_is_not_counted(self):
        self.char1.override_place = ""
        self.assertEqual(sweep_stranded_aim_tells(), 0)

    def test_a_live_aim_is_not_swept(self):
        """Belt-and-braces: nothing can be aiming at server start, but
        the sweep must stay correct if called on a live server."""
        from world.combat.constants import NDB_AIMING_AT
        char = self.stranded(AIM_TELL)
        setattr(char.ndb, NDB_AIMING_AT, self.char2)
        self.assertEqual(sweep_stranded_aim_tells(), 0)
        self.assertEqual(char.override_place, AIM_TELL)

    def test_a_live_direction_aim_is_not_swept(self):
        from world.combat.constants import NDB_AIMING_DIRECTION
        char = self.stranded(aim_direction_tell("north"))
        setattr(char.ndb, NDB_AIMING_DIRECTION, "north")
        self.assertEqual(sweep_stranded_aim_tells(), 0)

    def test_a_non_character_with_a_placement_is_safe(self):
        obj = create_object("typeclasses.objects.Object", key="a crate",
                            location=self.room1)
        obj.attributes.add("override_place", AIM_TELL,
                           category="description")
        sweep_stranded_aim_tells()      # must not raise


class TestTheTellsAreNamedOnce(EvenniaTest):
    """Seven call sites wrote these strings as literals. The sweep has to
    recognise a tell it did not write, so a literal that drifts in one
    place would strand exactly the case this fixes."""

    def test_the_command_modules_import_them(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        for name in ("core_actions.py", "special_actions.py"):
            body = (root / "commands" / "combat" / name).read_text(
                errors="ignore")
            self.assertNotIn('"aiming carefully at {aim_target}."', body,
                             f"{name} still writes the tell as a literal")
            self.assertNotIn('"locked in a deadly showdown."', body,
                             f"{name} still writes the tell as a literal")

    def test_the_startup_hook_runs_the_sweep(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        body = (root / "server" / "conf" / "at_server_startstop.py").read_text(
            errors="ignore")
        self.assertIn("sweep_stranded_aim_tells", body)
        start = body.index("def at_server_start(")
        stop = body.index("def at_server_stop(")
        self.assertIn("sweep_stranded_aim_tells", body[start:stop])


class TestWhyTheCommandCannotDoIt(EvenniaCommandTest):
    """The defect itself, demonstrated rather than described — and true
    both before and after the sweep, because the sweep is the fix and
    the command is not.

    `aim stop` reads `ndb.aiming_at` first and returns on the miss, so
    the one command a player would reach for cannot reach a tell whose
    ndb has been discarded. That is why this needed a startup sweep and
    not a guard.
    """

    def test_aim_stop_refuses_a_stranded_tell(self):
        from commands.combat.special_actions import CmdAim
        from world.combat.constants import MSG_STOP_NOT_AIMING
        self.char1.override_place = AIM_TELL          # ndb already gone
        out = self.call(CmdAim(), "stop", caller=self.char1)
        self.assertIn(MSG_STOP_NOT_AIMING.rstrip("."), out)

    def test_and_leaves_the_tell_showing(self):
        from commands.combat.special_actions import CmdAim
        self.char1.override_place = AIM_TELL
        self.call(CmdAim(), "stop", caller=self.char1)
        self.assertEqual(self.char1.override_place, AIM_TELL)

    def test_the_sweep_is_what_clears_it(self):
        from commands.combat.special_actions import CmdAim
        self.char1.override_place = AIM_TELL
        self.call(CmdAim(), "stop", caller=self.char1)
        self.assertEqual(sweep_stranded_aim_tells(), 1)
        self.assertEqual(self.char1.override_place, "")
