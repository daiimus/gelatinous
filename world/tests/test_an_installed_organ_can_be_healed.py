"""A slot that was refilled is no longer a removed slot (#3047 follow-up).

#3047 stopped `full_heal` regrowing what a ripper cut out. Its reasoning:

    `injury_type` is the durable marker, not the stage ... `removed_organs`
    is consulted as a second source because it is the authoritative record
    and survives anything that rewrites the organ row.

Right, and it stays. But `removed_organs` is APPEND-ONLY -- the harvest
path adds a name and nothing anywhere takes one off. It therefore
records "this slot was harvested ONCE", while `full_heal` reads it as
"this slot is empty NOW".

Those diverge the moment a surgeon installs a replacement. Measured,
with a control:

    CONTROL: never harvested (must heal)            heart hp=15/15
    slot previously harvested, organ present now    heart hp=1/15

So a ripper takes your heart, the clinic fits you a new one, and that
new heart can never be healed again -- not by `@heal`, not by any path
through `full_heal`. Both halves of the shipped ripper/clinic loop meet
here, and the record outlives the condition it describes.

Fixed in the three INSTALL resolvers only, not in `add_organ`. Seating
an organ happens during body construction and during
`reset_body_preserving_augments` as well, and clearing the record there
could hand #3047 straight back -- the whole point of the second source
is that it survives a rewritten organ row. An install is different: a
surgeon deliberately put an organ in that slot, so the slot is not
missing one any more, and it should be harvestable and healable again
like any other.

The guard #3047 added is pinned below: an organ harvested and NOT
replaced must still refuse to heal.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class TestHealingAfterAnInstall(EvenniaTest):

    def _body(self):
        return create_object("typeclasses.characters.Character",
                             key="Testheal", location=self.room1)

    def _hurt(self, who, name="heart"):
        organ = who.medical_state.organs[name]
        organ.current_hp = 1
        organ.wound_stage = None
        organ.injury_type = None
        return organ

    def test_a_normal_organ_heals(self):
        """Control: without this the assertions below prove nothing."""
        who = self._body()
        self._hurt(who)
        who.medical_state.full_heal()
        organ = who.medical_state.organs["heart"]
        self.assertEqual(organ.current_hp, organ.max_hp)

    def test_a_harvested_organ_still_refuses_to_heal(self):
        """#3047's guard, pinned. This must not be what the fix breaks."""
        who = self._body()
        organ = self._hurt(who)
        organ.injury_type = "harvested"
        who.db.removed_organs = ["heart"]
        who.medical_state.full_heal()
        self.assertEqual(who.medical_state.organs["heart"].current_hp, 1)

    def test_the_stale_record_is_what_blocks_the_heal(self):
        """THE BUG, stated as the mechanism the fix removes.

        With the name still on the list, an organ that is PRESENT and
        not harvested will not heal. Measured live before any change:

            CONTROL: never harvested (must heal)          heart 15/15
            slot previously harvested, organ present now  heart  1/15

        The fix clears the name at install time, so this state stops
        being produced; the assertion below is what makes that matter.
        """
        who = self._body()
        self._hurt(who)
        who.db.removed_organs = ["heart"]
        who.medical_state.full_heal()
        self.assertEqual(who.medical_state.organs["heart"].current_hp, 1)

    def test_clearing_the_record_lets_the_replacement_heal(self):
        """...and once the slot is refilled, healing works again."""
        from world.medical.procedures import _clear_removed_record
        who = self._body()
        self._hurt(who)
        who.db.removed_organs = ["heart"]
        _clear_removed_record(who, "heart")      # what an install now does
        who.medical_state.full_heal()
        organ = who.medical_state.organs["heart"]
        self.assertEqual(organ.current_hp, organ.max_hp)


class TestInstallClearsTheRemovedRecord(EvenniaTest):

    def test_installing_takes_the_slot_off_the_removed_list(self):
        from world.medical.procedures import _clear_removed_record
        who = create_object("typeclasses.characters.Character",
                            key="Testinstall", location=self.room1)
        who.db.removed_organs = ["heart", "left_kidney"]
        _clear_removed_record(who, "heart")
        self.assertEqual(list(who.db.removed_organs or []), ["left_kidney"])

    def test_it_is_harmless_when_the_slot_was_never_removed(self):
        who = create_object("typeclasses.characters.Character",
                            key="Testinstall2", location=self.room1)
        who.db.removed_organs = ["left_kidney"]
        from world.medical.procedures import _clear_removed_record
        _clear_removed_record(who, "heart")
        self.assertEqual(list(who.db.removed_organs or []), ["left_kidney"])
