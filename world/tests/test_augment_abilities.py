"""Phase 1 test contract for AUGMENT_ABILITIES_SPEC (issue #516).

Pins the toggled-cyberware ability layer:

* ability lookup reads organs (severed organs drop out);
* integrated_weapon deploy fills the hand slot with the weapon item
  (held-is-wielded: combat resolution follows for free) and
  auto-drops whatever the hand held;
* retract restores the empty hand and parks the weapon off-grid;
* ability_state round-trips with the organ;
* severance carries retracted hardware onto the appendage.

Run via::

    evennia test --settings settings.py world.tests.test_augment_abilities
"""

from __future__ import annotations

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character
from world.medical.augments import (
    CYBERWARE_COMMAND_PREFIX,
    carry_hardware_to_appendage,
    find_ability,
    list_abilities,
    toggle_ability,
)
from world.medical.core import Organ


def _gun_arm_organ(state, deployed_weapon_dbref=None):
    """A cybernetic arm organ carrying the shotgun ability — the
    spec shape the SHOTGUN_ARM item will declare.  Built with a
    bespoke organ_data copy (never mutate species-table specs)."""
    organ = Organ("cybernetic_humerus", organ_data={
        "container": "right_arm", "max_hp": 30, "hit_weight": "common",
        "bone_type": "actuator_column",
        "abilities": {
            "shotgun": {
                "type": "integrated_weapon",
                "slot": "right_hand",
                "weapon_prototype": "SHOTGUN_ARM_GUN",
            },
        },
    })
    organ.medical_state = state
    state.organs["cybernetic_humerus"] = organ
    if deployed_weapon_dbref:
        organ.ability_state = {
            "shotgun": {"weapon_dbref": deployed_weapon_dbref},
        }
    return organ


class TestAbilityLayer(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char = create_object(Character, key="Chrome", location=self.room1)
        self.organ = _gun_arm_organ(self.char.medical_state)
        # Pre-seed the integrated weapon so tests don't depend on the
        # Phase 2 prototype.
        self.gun = create_object(
            "typeclasses.items.Item", key="arm shotgun", location=None,
        )
        self.gun.db.integrated = True
        self.gun.locks.add("get:false();drop:false();give:false()")
        self.organ.ability_state = {
            "shotgun": {"weapon_dbref": self.gun.dbref},
        }

    def test_find_ability_reads_organs(self):
        organ, spec = find_ability(self.char, "shotgun")
        self.assertIs(organ, self.organ)
        self.assertEqual(spec["slot"], "right_hand")

    def test_severed_organ_loses_the_ability(self):
        self.organ.wound_stage = "severed"
        self.organ.current_hp = 0
        organ, spec = find_ability(self.char, "shotgun")
        self.assertIsNone(organ)
        self.assertIn("no cyberware", toggle_ability(self.char, "shotgun"))

    def test_dead_organ_powers_nothing(self):
        """Abilities require a FUNCTIONAL organ (#526 playtest fix):
        a harvested-out or destroyed slot at 0 HP is a tombstone, not
        a power source — /shotgun on it must find nothing."""
        self.organ.current_hp = 0  # destroyed in place / harvested out
        organ, spec = find_ability(self.char, "shotgun")
        self.assertIsNone(organ)

    def test_unknown_ability_lists_what_you_have(self):
        msg = toggle_ability(self.char, "lasereyes")
        self.assertIn(f"{CYBERWARE_COMMAND_PREFIX}shotgun", msg)

    def test_deploy_fills_the_slot(self):
        toggle_ability(self.char, "shotgun")
        self.assertIs(self.char.hands["right_hand"], self.gun)
        self.assertIs(self.gun.location, self.char)
        self.assertTrue(
            self.organ.ability_state["shotgun"]["deployed"]
        )
        # Held-is-wielded: combat resolves the deployed gun.
        from world.combat.utils import get_wielded_weapon
        self.assertIs(get_wielded_weapon(self.char), self.gun)

    def test_deploy_auto_drops_held_item(self):
        knife = create_object(
            "typeclasses.items.Item", key="knife", location=self.char,
        )
        self.char.hands = {"right_hand": knife}
        toggle_ability(self.char, "shotgun")
        self.assertIs(knife.location, self.room1)
        self.assertIs(self.char.hands["right_hand"], self.gun)

    def test_retract_restores_the_hand(self):
        toggle_ability(self.char, "shotgun")
        toggle_ability(self.char, "shotgun")
        self.assertIsNone(self.char.hands["right_hand"])
        self.assertIsNone(self.gun.location)
        self.assertFalse(
            self.organ.ability_state["shotgun"]["deployed"]
        )

    def test_listing_shows_state(self):
        self.assertIn("retracted", list_abilities(self.char))
        toggle_ability(self.char, "shotgun")
        self.assertIn("deployed", list_abilities(self.char))

    def test_ability_state_round_trips(self):
        toggle_ability(self.char, "shotgun")
        restored = Organ.from_dict(self.organ.to_dict())
        self.assertTrue(restored.ability_state["shotgun"]["deployed"])
        self.assertEqual(
            restored.ability_state["shotgun"]["weapon_dbref"],
            self.gun.dbref,
        )
        self.assertIn("abilities", restored.data)

    def test_severance_carries_retracted_hardware(self):
        """Retracted = folded inside the arm; the severed arm takes
        it (spec decision 7)."""
        appendage = create_object(
            "typeclasses.items.Item", key="severed arm", location=self.room1,
        )
        carry_hardware_to_appendage(
            self.char, ("right_arm", "right_hand"), appendage,
        )
        self.assertIs(self.gun.location, appendage)
        self.assertFalse(
            self.organ.ability_state["shotgun"].get("deployed", False)
        )

    def test_natural_weapon_toggle_and_precedence(self):
        """#526 M4: claws never touch the hand slots, and active
        claws beat anything held (settled decision 2026-06-12)."""
        from world.combat.utils import get_wielded_weapon

        claws_organ = Organ("left_metacarpals_clawed", organ_data={
            "container": "left_hand", "max_hp": 15,
            "abilities": {
                "nailz": {
                    "type": "natural_weapon",
                    "weapon_prototype": "NAILZ_CLAWS",
                },
            },
        })
        claws_organ.medical_state = self.char.medical_state
        self.char.medical_state.organs["left_metacarpals_clawed"] = claws_organ
        claws = create_object(
            "typeclasses.items.Item", key="monofilament claws",
            location=None,
        )
        claws.db.integrated = True
        claws_organ.ability_state = {
            "nailz": {"weapon_dbref": claws.dbref},
        }
        # A held, weapon-tagged knife to lose the precedence fight.
        knife = create_object(
            "typeclasses.items.Item", key="knife", location=self.char,
        )
        knife.tags.add("weapon", category="type")
        self.char.hands = {"left_hand": knife}

        toggle_ability(self.char, "nailz")
        # Claws deployed: never in hands, still off-grid, but they
        # ARE the combat weapon.
        self.assertIsNone(claws.location)
        self.assertNotIn(claws, self.char.hands.values())
        self.assertIs(get_wielded_weapon(self.char), claws)

        toggle_ability(self.char, "nailz")
        # Retracted: the held knife serves again.
        self.assertIs(get_wielded_weapon(self.char), knife)

    def test_resetmedical_preserves_chrome(self):
        """#526 review: @resetmedical rebuilds flesh from the current
        species table but carries installed augments over instead of
        erasing them."""
        from commands.CmdAdmin import _reset_medical_preserving_augments

        # The gun-arm organ from setUp is an augment (abilities).
        # Wound the flesh heart so we can see it factory-reset.
        self.char.medical_state.organs["heart"].current_hp = 3
        preserved = _reset_medical_preserving_augments(self.char)
        self.assertGreaterEqual(preserved, 1)
        state = self.char.medical_state
        self.assertIn("cybernetic_humerus", state.organs)
        self.assertIn(
            "shotgun",
            state.organs["cybernetic_humerus"].data.get("abilities", {}),
        )
        # Flesh rebuilt at factory.
        self.assertEqual(
            state.organs["heart"].current_hp,
            state.organs["heart"].max_hp,
        )

    def test_no_inline_weapon_picks_outside_the_resolver(self):
        """Doctrine pin (#516 playtest): combat code must resolve
        weapons through get_wielded_weapon, never the inline
        first-held-item idiom — that idiom is how the engagement
        message brandished a zippo while the hit fired the arm-gun.
        """
        import pathlib

        root = pathlib.Path(__file__).resolve().parents[2]
        idiom = "next((item for hand, item in"
        offenders = []
        for sub in ("commands", "world", "typeclasses"):
            for path in (root / sub).rglob("*.py"):
                if "tests" in path.parts:
                    continue
                if idiom in path.read_text(encoding="utf-8"):
                    offenders.append(str(path.relative_to(root)))
        self.assertEqual(
            offenders, [],
            "inline weapon picks found — use get_wielded_weapon: "
            f"{offenders}",
        )

    def test_integrated_weapon_refuses_drop(self):
        toggle_ability(self.char, "shotgun")
        self.assertFalse(self.gun.access(self.char, "drop"))
        self.assertFalse(self.gun.access(self.char, "get"))

    def test_unwield_refuses_integrated(self):
        """The freehands bug: unwield and freehands both route
        through unwield_item — the deployed gun is not held, it IS
        the hand."""
        toggle_ability(self.char, "shotgun")
        result = self.char.unwield_item("right_hand")
        self.assertIn("retract it instead", result)
        # Still seated.
        self.assertIs(self.char.hands["right_hand"], self.gun)

    def test_wield_refuses_integrated(self):
        """A freed integrated weapon must never be wieldable into an
        arbitrary hand — that's how the gun ended up in the wrong
        slot."""
        self.gun.location = self.char  # simulate the freed state
        result = self.char.wield_item(self.gun, "left_hand")
        self.assertIn("doesn't wield", result)
        self.assertIsNone(self.char.hands["left_hand"])

    def test_retract_clears_the_actual_slot(self):
        """Legacy desync (the Laszlo state): gun displaced into the
        WRONG slot — retract scans for where it really is instead of
        trusting the spec slot."""
        self.gun.location = self.char
        self.char.held_items = {"left_hand": self.gun}
        self.organ.ability_state["shotgun"]["deployed"] = True
        toggle_ability(self.char, "shotgun")  # retract
        self.assertIsNone(self.char.hands["left_hand"])
        self.assertIsNone(self.char.hands["right_hand"])
        self.assertIsNone(self.gun.location)

    def test_deploy_reseats_from_wrong_slot(self):
        """Deploying over the same legacy desync clears the stale
        reference and seats the gun in its spec slot — exactly one
        place, the right one."""
        self.gun.location = self.char
        self.char.held_items = {"left_hand": self.gun}
        toggle_ability(self.char, "shotgun")  # deploy
        self.assertIs(self.char.hands["right_hand"], self.gun)
        self.assertIsNone(self.char.hands["left_hand"])
        # And the desync auto-drop guard: the gun itself was never
        # "dropped" to the room.
        self.assertIs(self.gun.location, self.char)

    def test_deployed_gun_beats_offhand_junk(self):
        """The Laszlo bug: combat must resolve the deployed shotgun,
        not the cigarette in the other hand — weapons (weapon_type)
        take priority over other held items regardless of hand
        order."""
        from world.combat.utils import get_wielded_weapon

        self.gun.db.weapon_type = "cybernetic_shotgun"
        # The real discriminator: every Item defaults weapon_type to
        # "melee" (the cigarette included), so weapons are known by
        # the ("weapon", "type") tag the base prototypes carry.
        self.gun.tags.add("weapon", category="type")
        cigarette = create_object(
            "typeclasses.items.Item", key="cigarette", location=self.char,
        )
        self.char.hands = {"left_hand": cigarette}
        toggle_ability(self.char, "shotgun")
        self.assertIs(get_wielded_weapon(self.char), self.gun)
        # Retracted, the cigarette is all that's held — brawl-with-
        # whatever behavior is preserved.
        toggle_ability(self.char, "shotgun")
        self.assertIs(get_wielded_weapon(self.char), cigarette)


class TestSeveranceDropsHeldItems(EvenniaTest):
    """Production-path regression (#533 follow-on): a limb severed
    mid-grip drops the held item to the room.  The shorthand stubs
    in test_living_sever never caught the canonical-key /
    functional-anatomy-gate interaction — this uses a real
    Character."""

    def test_severed_arm_drops_its_weapon_to_the_room(self):
        from typeclasses.items import apply_sever_to_character

        char = create_object(Character, key="Armless", location=self.room1)
        knife = create_object(
            "typeclasses.items.Item", key="kitchen knife", location=char,
        )
        result = char.wield_item(knife, "right_hand")
        self.assertIn("wield", result.lower())
        self.assertIs(char.hands["right_hand"], knife)

        # Pulp the right-arm bones so the chain is severable.
        for name in ("right_humerus", "right_metacarpals"):
            char.medical_state.organs[name].current_hp = 0

        apply_sever_to_character(char, "right_arm", injury_type="cut")

        # The knife fell free — in the room, not orphaned in the
        # backing store, not on the appendage.
        self.assertIs(knife.location, self.room1)
        self.assertNotIn(knife, (char.held_items or {}).values())
        # And the drop was recorded for the severance prose.
        # (ndb is cleared by apply_sever after emitting the beat.)

    def test_empty_hand_severance_drops_nothing(self):
        from typeclasses.items import apply_sever_to_character

        char = create_object(Character, key="Emptyhand", location=self.room1)
        for name in ("left_humerus", "left_metacarpals"):
            char.medical_state.organs[name].current_hp = 0
        # Should not raise and should record no dropped items.
        apply_sever_to_character(char, "left_arm", injury_type="cut")
        self.assertIsNone(
            getattr(char.ndb, "_sever_dropped_items", None)
        )


class TestDeployedWeaponDisplay(EvenniaTest):
    """#516 review (items 1+4): a deployed cyber weapon is not 'held'
    — it reads as part of the hand in self-inventory, is excluded
    from the look-at-others held list, and dominates the sdesc."""

    def setUp(self):
        super().setUp()
        self.char = create_object(Character, key="Chrome", location=self.room1)
        # Give them an sdesc so get_distinguishing_feature engages.
        self.char.db.height = "average"
        self.char.db.build = "wiry"
        organ = Organ("cybernetic_humerus", organ_data={
            "container": "right_arm", "max_hp": 30,
            "abilities": {"shotgun": {
                "type": "integrated_weapon", "slot": "right_hand",
                "weapon_prototype": "SHOTGUN_ARM_GUN",
            }},
        })
        organ.medical_state = self.char.medical_state
        self.char.medical_state.organs["cybernetic_humerus"] = organ
        self.organ = organ
        self.gun = create_object(
            "typeclasses.items.Item", key="shotgun module", location=None,
        )
        self.gun.db.integrated = True
        self.gun.tags.add("weapon", category="type")
        organ.ability_state = {"shotgun": {"weapon_dbref": self.gun.dbref}}

    def test_self_inventory_says_is_your_hand(self):
        from commands.CmdInventory import CmdInventory

        toggle_ability(self.char, "shotgun")
        captured = []
        self.char.msg = lambda text=None, **kw: captured.append(text or "")
        cmd = CmdInventory()
        cmd.caller = self.char
        cmd.args = ""
        cmd.obj = self.char
        cmd.func()
        output = "\n".join(captured).lower()
        self.assertIn("shotgun module is your", output)
        self.assertNotIn("shotgun module is held in", output)

    def test_look_excludes_integrated_from_held(self):
        toggle_ability(self.char, "shotgun")
        looker = create_object(Character, key="Witness", location=self.room1)
        appearance = self.char.return_appearance(looker)
        self.assertNotIn("holding a shotgun module", appearance)
        self.assertNotIn("holding nothing", appearance)

    def test_look_shows_integrated_as_hand(self):
        """An onlooker sees the deployed weapon AS the hand — the
        third-person mirror of the ``inv`` "is your right hand" line."""
        toggle_ability(self.char, "shotgun")
        looker = create_object(Character, key="Witness", location=self.room1)
        appearance = self.char.return_appearance(looker).lower()
        self.assertIn("shotgun module is", appearance)
        self.assertIn("right hand", appearance)

    def test_integrated_dominates_sdesc(self):
        toggle_ability(self.char, "shotgun")
        feature = self.char.get_distinguishing_feature()
        self.assertIn("shotgun module", feature)

    def test_natural_weapon_leaves_hands_empty(self):
        """Claws live off-grid: they don't fill a hand, so empty hands
        still read "holding nothing" while the claws are out (the sdesc
        carries the armed signal)."""
        claws_organ = Organ("left_metacarpals", organ_data={
            "container": "left_hand", "max_hp": 15,
            "abilities": {"nailz": {
                "type": "natural_weapon", "weapon_prototype": "NAILZ_CLAWS",
            }},
        })
        claws_organ.medical_state = self.char.medical_state
        self.char.medical_state.organs["left_metacarpals"] = claws_organ
        claws = create_object(
            "typeclasses.items.Item", key="monofilament claws", location=None,
        )
        claws.db.integrated = True
        claws_organ.ability_state = {"nailz": {"weapon_dbref": claws.dbref}}
        toggle_ability(self.char, "nailz")
        looker = create_object(Character, key="Witness", location=self.room1)
        appearance = self.char.return_appearance(looker).lower()
        self.assertIn("holding nothing", appearance)

    def test_natural_weapon_dominates_sdesc(self):
        claws_organ = Organ("left_metacarpals", organ_data={
            "container": "left_hand", "max_hp": 15,
            "abilities": {"nailz": {
                "type": "natural_weapon", "weapon_prototype": "NAILZ_CLAWS",
            }},
        })
        claws_organ.medical_state = self.char.medical_state
        self.char.medical_state.organs["left_metacarpals"] = claws_organ
        claws = create_object(
            "typeclasses.items.Item", key="monofilament claws", location=None,
        )
        claws.db.integrated = True
        claws_organ.ability_state = {"nailz": {"weapon_dbref": claws.dbref}}
        toggle_ability(self.char, "nailz")
        feature = self.char.get_distinguishing_feature()
        self.assertIn("claws", feature.lower())


class TestChromeLongdesc(EvenniaTest):
    """#516 review (item 2 + item 4-longdesc): chrome renders gunmetal
    (not skintone), and a deployed module expands the limb's longdesc."""

    def setUp(self):
        super().setUp()
        self.char = create_object(Character, key="Chrome", location=self.room1)
        self.char.db.skintone = "tan"
        organ = Organ("cybernetic_humerus", organ_data={
            "container": "left_arm", "max_hp": 30, "inorganic": True,
            "abilities": {"shotgun": {
                "type": "integrated_weapon", "slot": "left_hand",
                "weapon_prototype": "X",
                "deployed_longdesc": "A stub shotgun barrel juts where the hand should be.",
            }},
        })
        organ.medical_state = self.char.medical_state
        self.char.medical_state.organs["cybernetic_humerus"] = organ
        self.organ = organ
        ld = dict(self.char.longdesc or {})
        ld["left_arm"] = "A full cybernetic left arm."
        self.char.longdesc = ld

    def test_inorganic_location_detected(self):
        self.assertTrue(self.char._location_is_inorganic("left_arm"))
        self.assertFalse(self.char._location_is_inorganic("chest"))

    def test_chrome_renders_gunmetal_not_skintone(self):
        from world.combat.constants import (
            CHROME_DEFAULT_COLOR, SKINTONE_PALETTE,
        )
        rendered = self.char._render_body_longdesc(
            "left_arm", self.char.longdesc["left_arm"], self.char,
        )
        self.assertIn(CHROME_DEFAULT_COLOR, rendered)
        self.assertNotIn(SKINTONE_PALETTE["tan"], rendered)

    def test_flesh_still_skintoned(self):
        from world.combat.constants import SKINTONE_PALETTE
        rendered = self.char._render_body_longdesc(
            "chest", "A broad chest.", self.char,
        )
        self.assertIn(SKINTONE_PALETTE["tan"], rendered)

    def test_deployed_module_expands_longdesc(self):
        self.organ.ability_state = {
            "shotgun": {"deployed": True, "weapon_dbref": "#1"},
        }
        rendered = self.char._render_body_longdesc(
            "left_arm", self.char.longdesc["left_arm"], self.char,
        )
        self.assertIn("shotgun barrel juts", rendered)

    def test_retracted_module_does_not_expand(self):
        self.organ.ability_state = {"shotgun": {"deployed": False}}
        rendered = self.char._render_body_longdesc(
            "left_arm", self.char.longdesc["left_arm"], self.char,
        )
        self.assertNotIn("shotgun barrel juts", rendered)

    def _add_chrome_hand(self):
        hand = Organ("cybernetic_metacarpals", organ_data={
            "container": "left_hand", "max_hp": 18, "inorganic": True,
        })
        hand.medical_state = self.char.medical_state
        self.char.medical_state.organs["cybernetic_metacarpals"] = hand
        ld = dict(self.char.longdesc or {})
        ld["left_hand"] = (
            "An articulated alloy left hand, five-fingered and precise."
        )
        self.char.longdesc = ld
        self.organ.data["abilities"]["shotgun"]["deployed_longdesc_slot"] = (
            "Where the left hand should be, the wrist tapers into a "
            "seamless firing socket."
        )

    def test_deployed_weapon_replaces_the_hand_longdesc(self):
        """The /shotgun follow-up: deploying folds the hand away, so
        the hand's longdesc is REPLACED (not appended) by the slot
        prose."""
        self._add_chrome_hand()
        self.organ.ability_state = {
            "shotgun": {"deployed": True, "weapon_dbref": "#1"},
        }
        rendered = self.char._render_body_longdesc(
            "left_hand", self.char.longdesc["left_hand"], self.char,
        )
        self.assertIn("firing socket", rendered)
        self.assertNotIn("five-fingered", rendered)  # baseline replaced

    def test_retracted_weapon_restores_the_hand_longdesc(self):
        self._add_chrome_hand()
        self.organ.ability_state = {"shotgun": {"deployed": False}}
        rendered = self.char._render_body_longdesc(
            "left_hand", self.char.longdesc["left_hand"], self.char,
        )
        self.assertIn("five-fingered", rendered)
        self.assertNotIn("firing socket", rendered)
