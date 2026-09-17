"""A garment worn only inside the severed cluster travels with the part,
on every door (#3577).

The travel rule (issue #245, chain #339) lived on the living-limb door
alone: ``apply_sever_to_character`` moved the garments, and neither the
living decapitation (``spawn_severed_head_for_living``, #343) nor the
corpse-side sever (``spawn_severed_part_from_corpse``) did, so a helmet
stayed on a headless body or on the corpse while the head lay beside it
bare. Owner: "Why would we ignore a living decapitation?"

Both doors now call the one travel function; a corpse, which keeps no
worn stack, derives one from its flat list (``Corpse.worn_stack``) so
the same rule and the same outermost-first ledger apply.
"""

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


def garment(key, *, coverage, layer, worn_desc, location):
    item = create_object("typeclasses.items.Item", key=key, location=location)
    item.db.coverage = list(coverage)
    item.layer = layer
    item.db.worn_desc = worn_desc
    return item


class TestTheLivingDecapitation(EvenniaTest):
    def test_the_helmet_goes_the_coat_stays(self):
        from typeclasses.items import spawn_severed_head_for_living
        char = self.char1
        helmet = garment("helmet", coverage=["head"], layer=5,
                         worn_desc="A yellow helmet sits square on {their} head",
                         location=char)
        coat = garment("coat", coverage=["chest", "left_arm", "right_arm"], layer=3,
                       worn_desc="A lab coat hangs open", location=char)
        char.worn_items = {"head": [helmet], "chest": [coat],
                           "left_arm": [coat], "right_arm": [coat]}
        head = spawn_severed_head_for_living(char, injury_type="cut")
        self.assertIsNotNone(head)
        self.assertIs(helmet.location, head)
        self.assertEqual(list(head.db.worn_items["head"]), [helmet])
        self.assertIs(coat.location, char)
        self.assertNotIn("head", dict(char.worn_items))
        self.assertIn("chest", dict(char.worn_items))
        # and the head wears it, in prose
        out = head.return_appearance(self.char2)
        self.assertIn("A yellow helmet sits square on", out)
        self.assertNotIn("You see", out)


class _Corpse(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.corpse = create_object("typeclasses.corpse.Corpse", key="human corpse",
                                    location=self.room1)
        self.corpse.db.species = "human"
        self.corpse.db.original_gender = "male"
        self.corpse.db.original_character_name = "Donor"
        self.corpse.db.longdesc_data = {"head": "{They} {hold} {their} head still.",
                                        "chest": "{Their} chest is broad.",
                                        "left_hand": "{Their} left hand is scarred."}
        self.helmet = garment("mining helmet", coverage=["head"], layer=5,
                              worn_desc="A yellow helmet sits square on {their} head",
                              location=self.corpse)
        self.coat = garment("lab coat", coverage=["chest", "left_arm", "right_arm"],
                            layer=3, worn_desc="A lab coat hangs open",
                            location=self.corpse)
        self.corpse.db.worn_at_death = [self.helmet.id, self.coat.id]


class TestTheCorpseSever(_Corpse):
    def test_the_head_takes_the_helmet_and_leaves_the_coat(self):
        from typeclasses.items import spawn_severed_part_from_corpse
        head = spawn_severed_part_from_corpse(self.corpse, "head")
        self.assertIsNotNone(head)
        self.assertIs(self.helmet.location, head)
        self.assertEqual(list(head.db.worn_items["head"]), [self.helmet])
        self.assertIs(self.coat.location, self.corpse)
        self.assertEqual([g.key for g in self.corpse.worn_garments()], ["lab coat"])
        self.assertEqual([g.key for g in head.worn_garments()], ["mining helmet"])
        self.assertIn("A yellow helmet sits square on his head.",
                      head.return_appearance(self.char1))
        # the corpse no longer covers a head it no longer has
        self.assertNotIn("head", self.corpse._build_corpse_clothing_coverage_map())

    def test_a_limb_takes_only_what_it_wholly_wore(self):
        from typeclasses.items import spawn_severed_part_from_corpse
        glove = garment("glove", coverage=["left_hand"], layer=1,
                        worn_desc="A glove", location=self.corpse)
        self.corpse.db.worn_at_death = list(self.corpse.db.worn_at_death) + [glove.id]
        arm = spawn_severed_part_from_corpse(self.corpse, "left_arm")
        self.assertIsNotNone(arm)
        self.assertIs(glove.location, arm)
        self.assertEqual(list(arm.db.worn_items["left_hand"]), [glove])
        # the coat spans the chest: it stays
        self.assertIs(self.coat.location, self.corpse)

    def test_the_travelling_ledger_is_outermost_first(self):
        from typeclasses.items import spawn_severed_part_from_corpse
        balaclava = garment("balaclava", coverage=["hair", "head"], layer=2,
                            worn_desc="A balaclava", location=self.corpse)
        self.corpse.db.worn_at_death = list(self.corpse.db.worn_at_death) + [balaclava.id]
        head = spawn_severed_part_from_corpse(self.corpse, "head")
        self.assertEqual(list(head.db.worn_items["head"]), [self.helmet, balaclava])
        self.assertEqual(list(head.db.worn_items["hair"]), [balaclava])


class TestTheCorpseStack(_Corpse):
    def test_worn_stack_orders_by_layer_and_styled_coverage(self):
        cap = garment("knit cap", coverage=["head", "left_ear", "right_ear"], layer=6,
                      worn_desc="cap", location=self.corpse)
        cap.style_configs = {"adjustable": {"rolled": {
            "desc_mod": "", "coverage_mod": ["-left_ear", "-right_ear"]}}}
        cap.style_properties = {"adjustable": "rolled"}
        self.corpse.db.worn_at_death = list(self.corpse.db.worn_at_death) + [cap.id]
        stack = self.corpse.worn_stack()
        self.assertEqual(stack["head"], [cap, self.helmet])
        self.assertNotIn("left_ear", stack)
        self.assertIs(self.corpse._build_corpse_clothing_coverage_map()["head"], cap)


class TestTheTypedSeverCommand(_Corpse):
    """The player's own door: ``sever head from corpse``. The command used
    to inline its own copy of the severance (the fourth door, found in
    review); it now goes through the one helper, so the helmet travels
    and the head lands in the cutter's hands as before."""

    def test_sever_head_from_corpse_takes_the_helmet(self):
        from unittest.mock import patch
        from commands.forensics import CmdSever
        from world.tests.test_cmd_sever import _rolls, _split, _SUCCESS
        self.corpse.db.medical_state_at_death = {
            "organs": {"brain": {"current_hp": 10, "max_hp": 10, "container": "head"}},
            "conditions": [], "blood_level": 5000, "pain_level": 0, "consciousness": False,
        }
        dagger = create_object("typeclasses.items.Item", key="dagger", location=self.char1)
        dagger.db.can_sever = True
        cmd = CmdSever(); cmd.caller = self.char1; cmd.args = "head from corpse"; cmd.switches = ()
        intel, motor = _split(_SUCCESS)
        with patch("commands.forensics.get_wielded_weapon", return_value=dagger), \
             patch("commands.forensics.roll_stat", side_effect=_rolls(intel, motor)):
            cmd._complete_sever(self.char1, self.corpse, "head")
        heads = [o for o in self.char1.contents if o.is_typeclass("typeclasses.items.SeveredHead", exact=False)]
        self.assertEqual(len(heads), 1, [o.key for o in self.char1.contents])
        head = heads[0]
        self.assertIs(self.helmet.location, head)
        self.assertEqual(list(head.db.worn_items["head"]), [self.helmet])
        self.assertIs(self.coat.location, self.corpse)
        self.assertEqual([g.key for g in self.corpse.worn_garments()], ["lab coat"])
        self.assertIn("head", list(self.corpse.db.severed_locations))
