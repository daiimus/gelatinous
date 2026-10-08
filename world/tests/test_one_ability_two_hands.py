"""One tray of claws, two hands, one ability (#2483).

``NAILZ`` declares ``flesh_containers = ["left_hand", "right_hand"]``,
and the install loop in ``procedures.py`` seats the ability into **every
living host** in that list. So a full install genuinely produces two
organs, each carrying ``nailz``.

`find_ability` returned the first match and the toggles wrote
``state["deployed"]`` to that organ alone. Measured on a real install
before the fix:

```
organs seated:                2   (left_hand, right_hand)
hosts carrying the ability:   2
find_ability returns:         left_hand
after one toggle, deployed:   ['left_hand']
message:  "ten carbide blades slide out from beneath them..."
```

Five deployed. The second hand's claws could never be reached — the
command surface takes an ability name and has no way to address a host —
so half of whatever the surgery cost was permanently inert, and
`/system` printed one hand's state under a line reading "both hands".

**The prototype is the spec here, so this needed no ruling.** Its prose
is unambiguous that the pair is one thing: *"five per hand, both
hands"*, *"ten carbide blades"*, *"your hands are just hands again"*.
The code simply failed to honour what the content already decided.

**Severance stays per-hand, deliberately.** ``retract_all_hardware`` and
``carry_hardware_to_appendage`` walk organs themselves and clear the one
they are given, so losing a hand leaves the other one's blades out —
exactly what the install loop's own comment says should happen
(*"lose a hand and the other keeps its blades"*). Mirroring applies to
toggling, not to losing a limb.

`nailz` is the only multi-host ability in the game today, so the fix has
exactly one consumer to satisfy — but it is written at the state layer,
so a second one will work.

**2026-10-05, MULTI_WEAPON_COMBAT_SPEC:** the mirror that kept both hands'
state identical is gone. Each hand owns its claws and its own weapon
object; one `/nailz` still acts on every host, and a mixed state syncs
by retracting (owner: "Retract both to sync up makes sense.").
"""
from evennia.utils.test_resources import EvenniaTest


def _seat_nailz(char):
    """Seat the ability the way `procedures.py` does — into every living
    organ whose container is a hand."""
    from world import prototypes
    abilities = dict(prototypes.NAILZ["attrs"])["organ_spec"]["abilities"]
    state = char.medical_state
    seated = []
    for container in ("left_hand", "right_hand"):
        organ = next((o for o in state.organs.values()
                      if getattr(o, "container", None) == container
                      and o.current_hp > 0), None)
        if organ is None:
            continue
        data = dict(organ.data)
        merged = dict(data.get("abilities") or {})
        merged.update(abilities)
        data["abilities"] = merged
        organ.data = data
        seated.append(organ)
    char.medical_state = state
    return seated


class _NailzCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.seated = _seat_nailz(self.char1)

    def deployed_hands(self):
        from world.medical.augments import find_ability_hosts
        out = []
        for organ in find_ability_hosts(self.char1, "nailz"):
            store = getattr(organ, "ability_state", None) or {}
            if (store.get("nailz") or {}).get("deployed"):
                out.append(getattr(organ, "container", None))
        return sorted(out)


class TestTheInstallIsGenuinelyTwoOrgans(_NailzCase):
    """The issue flagged this as inferred-not-verified. It holds."""

    def test_two_organs_are_seated(self):
        self.assertEqual(len(self.seated), 2)

    def test_both_hands_host_the_ability(self):
        from world.medical.augments import find_ability_hosts
        hosts = find_ability_hosts(self.char1, "nailz")
        self.assertEqual(
            sorted(getattr(o, "container", None) for o in hosts),
            ["left_hand", "right_hand"])

    def test_the_prototype_declares_both(self):
        from world import prototypes
        self.assertEqual(
            set(dict(prototypes.NAILZ["attrs"])["flesh_containers"]),
            {"left_hand", "right_hand"})


class TestBothHandsDeployWithoutTheNewHelper(_NailzCase):
    """Reads the organs straight off `medical_state`, so this class
    fails against the unfixed tree for the RIGHT reason — a hand that
    never deployed — rather than on a missing import."""

    def raw_deployed(self):
        out = []
        for organ in self.char1.medical_state.organs.values():
            if getattr(organ, "container", None) not in ("left_hand",
                                                         "right_hand"):
                continue
            store = getattr(organ, "ability_state", None) or {}
            if (store.get("nailz") or {}).get("deployed"):
                out.append(organ.container)
        return sorted(out)

    def test_one_toggle_reaches_the_second_hand(self):
        from world.medical.augments import toggle_ability
        toggle_ability(self.char1, "nailz")
        self.assertEqual(self.raw_deployed(),
                         ["left_hand", "right_hand"])

    def test_the_second_hand_is_not_left_inert(self):
        from world.medical.augments import toggle_ability
        toggle_ability(self.char1, "nailz")
        self.assertIn("right_hand", self.raw_deployed(),
                      "the second hand's claws were never reachable")


class TestBothHandsDeploy(_NailzCase):
    def test_one_toggle_deploys_both(self):
        from world.medical.augments import toggle_ability
        toggle_ability(self.char1, "nailz")
        self.assertEqual(self.deployed_hands(), ["left_hand", "right_hand"])

    def test_a_second_toggle_retracts_both(self):
        from world.medical.augments import toggle_ability
        toggle_ability(self.char1, "nailz")
        toggle_ability(self.char1, "nailz")
        self.assertEqual(self.deployed_hands(), [])

    def test_it_still_toggles_rather_than_sticking(self):
        from world.medical.augments import toggle_ability
        for _ in range(3):
            toggle_ability(self.char1, "nailz")
        self.assertEqual(self.deployed_hands(), ["left_hand", "right_hand"])

    def test_each_hand_has_its_own_weapon(self):
        """One ability, one weapon item PER HAND (MULTI_WEAPON_COMBAT_SPEC
        §3): a severed hand takes exactly its own claws."""
        from world.medical.augments import (find_ability_hosts,
                                            toggle_ability)
        toggle_ability(self.char1, "nailz")
        refs = [(getattr(o, "ability_state", None) or {})
                .get("nailz", {}).get("weapon_dbref")
                for o in find_ability_hosts(self.char1, "nailz")]
        self.assertEqual(len(refs), 2)
        self.assertTrue(all(refs), refs)
        self.assertEqual(len(set(refs)), 2, f"the hands share one weapon: {refs}")

    def test_a_mixed_state_retracts_both(self):
        """Owner 2026-10-05: "Retract both to sync up makes sense." The
        FIRST host is the one put away here: a reader of the first host
        alone would deploy from this state; the any-host rule retracts."""
        from world.medical.augments import (find_ability_hosts,
                                            toggle_ability, _ability_state)
        toggle_ability(self.char1, "nailz")
        first = find_ability_hosts(self.char1, "nailz")[0]
        _ability_state(first, "nailz")["deployed"] = False     # first hand in, other out
        toggle_ability(self.char1, "nailz")
        self.assertEqual(self.deployed_hands(), [])

    def test_a_mixed_state_the_other_way_also_retracts(self):
        from world.medical.augments import (find_ability_hosts,
                                            toggle_ability, _ability_state)
        toggle_ability(self.char1, "nailz")
        last = find_ability_hosts(self.char1, "nailz")[-1]
        _ability_state(last, "nailz")["deployed"] = False
        toggle_ability(self.char1, "nailz")
        self.assertEqual(self.deployed_hands(), [])

    def test_one_hand_changing_names_the_hand(self):
        from world.medical.augments import (find_ability_hosts,
                                            toggle_ability, _ability_state)
        toggle_ability(self.char1, "nailz")
        toggle_ability(self.char1, "nailz")                     # both in
        left = next(o for o in find_ability_hosts(self.char1, "nailz")
                    if o.container == "left_hand")
        _ability_state(left, "nailz")["deployed"] = True        # one already out
        from unittest import mock
        with mock.patch("world.identity_utils.msg_room_identity") as room:
            said = toggle_ability(self.char1, "nailz")          # retracts the one
        self.assertIn("left hand", said)
        self.assertNotIn("{hand}", said)
        self.assertNotIn("your hands are just hands again", said, "the both-hands prose was used")
        self.assertTrue(room.called)
        self.assertIn("left hand", room.call_args.kwargs["template"])
        self.assertNotIn("{hand}", room.call_args.kwargs["template"])
        self.assertEqual(self.deployed_hands(), [])

    def test_the_listing_names_the_hands_only_when_they_differ(self):
        from world.medical.augments import (find_ability_hosts, list_abilities,
                                            toggle_ability, _ability_state)
        self.assertIn("/nailz — retracted", list_abilities(self.char1))
        toggle_ability(self.char1, "nailz")
        self.assertIn("/nailz — deployed", list_abilities(self.char1))
        last = find_ability_hosts(self.char1, "nailz")[-1]
        _ability_state(last, "nailz")["deployed"] = False
        out = list_abilities(self.char1)
        self.assertIn("left hand deployed", out)
        self.assertIn("right hand retracted", out)

    def test_the_director_reads_any_host(self):
        from world.director.security import _weapon_deployed
        from world.medical.augments import (find_ability_hosts, toggle_ability,
                                            _ability_state)
        self.assertFalse(_weapon_deployed(self.char1, "nailz"))
        toggle_ability(self.char1, "nailz")
        self.assertTrue(_weapon_deployed(self.char1, "nailz"))
        first = find_ability_hosts(self.char1, "nailz")[0]
        _ability_state(first, "nailz")["deployed"] = False
        self.assertTrue(_weapon_deployed(self.char1, "nailz"), "the first host alone was read")

    def test_a_shared_object_carried_off_is_not_reused(self):
        """Legacy state from before each hand owned its claws: both hosts
        point at one object, and that object lies inside a severed limb.
        Deploying must give the surviving hand its OWN claws, not a
        reference to blades on the floor (MULTI_WEAPON_COMBAT_SPEC §3)."""
        from evennia import create_object
        from world.medical.augments import (find_ability_hosts, toggle_ability,
                                            _ability_state, get_active_natural_weapons)
        limb = create_object("typeclasses.items.Appendage", key="a severed left hand", location=self.room1)
        stray = create_object("typeclasses.items.Item", key="old blades", location=limb)  # carried off
        for host in find_ability_hosts(self.char1, "nailz"):
            _ability_state(host, "nailz").update({"deployed": False, "weapon_dbref": stray.dbref})
        toggle_ability(self.char1, "nailz")
        active = get_active_natural_weapons(self.char1)
        self.assertEqual(len(active), 2)
        self.assertTrue(all(w.id != stray.id for _, w in active), "the stray object was reused")
        self.assertTrue(stray.pk, "the stray object was deleted")


class TestTheReadoutIsHonest(_NailzCase):
    def test_system_reports_deployed_when_they_are_out(self):
        from world.medical.augments import toggle_ability
        from world.medical.cyberware_status import render_system
        toggle_ability(self.char1, "nailz")
        out = str(render_system(self.char1))
        self.assertIn("DEPLOYED", out)

    def test_system_reports_retracted_when_they_are_in(self):
        from world.medical.cyberware_status import render_system
        out = str(render_system(self.char1))
        self.assertIn("retracted", out)

    def test_the_line_still_says_both_hands(self):
        from world.medical.cyberware_status import render_system
        self.assertIn("both hands",
                      str(render_system(self.char1)))

    def test_a_mixed_state_names_each_hand(self):
        from world.medical.augments import (find_ability_hosts,
                                            toggle_ability, _ability_state)
        from world.medical.cyberware_status import render_system
        toggle_ability(self.char1, "nailz")
        right = next(o for o in find_ability_hosts(self.char1, "nailz")
                     if o.container == "right_hand")
        _ability_state(right, "nailz")["deployed"] = False
        out = str(render_system(self.char1))
        self.assertIn("left hand", out)
        self.assertIn("right hand retracted", out)


class TestSingleHostAbilitiesAreUnchanged(EvenniaTest):
    """Every other ability seats into one organ; the mirror must be a
    no-op for them rather than a new code path."""

    def _seat(self, container, aname, spec):
        state = self.char1.medical_state
        organ = next((o for o in state.organs.values()
                      if getattr(o, "container", None) == container
                      and o.current_hp > 0), None)
        self.assertIsNotNone(organ, f"no living organ in {container}")
        data = dict(organ.data)
        merged = dict(data.get("abilities") or {})
        merged[aname] = spec
        data["abilities"] = merged
        organ.data = data
        self.char1.medical_state = state
        return organ

    def test_a_blindsight_toggles_normally(self):
        from world.medical.augments import toggle_ability
        organ = self._seat("head", "eyez", {"type": "blindsight"})
        toggle_ability(self.char1, "eyez")
        self.assertTrue(
            (getattr(organ, "ability_state", None) or {})
            .get("eyez", {}).get("deployed"))

    def test_it_retracts_normally(self):
        from world.medical.augments import toggle_ability
        organ = self._seat("head", "eyez", {"type": "blindsight"})
        toggle_ability(self.char1, "eyez")
        toggle_ability(self.char1, "eyez")
        self.assertFalse(
            (getattr(organ, "ability_state", None) or {})
            .get("eyez", {}).get("deployed"))

    def test_the_prose_comes_from_the_host_that_changed(self):
        """Two hosts with DIFFERENT prose (an install bakes the side into
        a sided arm's lines): the line spoken is the changed host's."""
        from world.medical.augments import toggle_ability, _ability_state
        head = self._seat("head", "eyez", {"type": "blindsight", "deploy_msg": "HEAD ON", "retract_msg": "HEAD OFF"})
        chest = self._seat("chest", "eyez", {"type": "blindsight", "deploy_msg": "CHEST ON", "retract_msg": "CHEST OFF"})
        _ability_state(chest, "eyez")["deployed"] = True        # mixed: chest out, head in
        said = toggle_ability(self.char1, "eyez")               # retracts the chest only
        self.assertEqual(said, "CHEST OFF")
        _ability_state(head, "eyez")["deployed"] = True
        said = toggle_ability(self.char1, "eyez")               # retracts the head only
        self.assertEqual(said, "HEAD OFF")

    def test_find_ability_still_returns_one_organ(self):
        from world.medical.augments import find_ability
        self._seat("head", "eyez", {"type": "blindsight"})
        organ, spec = find_ability(self.char1, "eyez")
        self.assertEqual(getattr(organ, "container", None), "head")
        self.assertEqual(spec["type"], "blindsight")


class TwoArmGunsFromTheOldModel(EvenniaTest):
    """Legacy shared state on two integrated hosts: both forearm modules
    point at one gun. A per-host deploy must not seat that one gun in the
    left hand and then move it to the right (MULTI_WEAPON_COMBAT_SPEC §3,
    §12): the hand that holds it keeps it, otherwise the first; the others
    spawn their own."""

    def setUp(self):
        super().setUp()
        from evennia import create_object
        from world.medical.core import Organ
        state = self.char1.medical_state
        self.organs = []
        for side in ("left", "right"):
            organ = Organ(f"{side}_gun_arm", organ_data={
                "container": f"{side}_arm", "max_hp": 30, "hit_weight": "common",
                "bone_type": "actuator_column", "inorganic": True, "prosthetic_frame": True,
                "abilities": {"shotgun": {"type": "integrated_weapon", "slot": f"{side}_hand",
                                          "weapon_prototype": "SHOTGUN_ARM_GUN"}},
            })
            organ.medical_state = state
            state.organs[f"{side}_gun_arm"] = organ
            self.organs.append(organ)
        self.gun = create_object("typeclasses.items.Item", key="arm shotgun", location=None)
        self.gun.db.integrated = True
        for organ in self.organs:
            organ.ability_state = {"shotgun": {"weapon_dbref": self.gun.dbref}}
        self.char1.medical_state = state
        self.char1.save_medical_state()

    def test_each_arm_ends_with_its_own_gun_in_hand(self):
        from world.medical.augments import toggle_ability
        toggle_ability(self.char1, "shotgun")
        hands = self.char1.hands
        self.assertIsNotNone(hands.get("left_hand"), hands)
        self.assertIsNotNone(hands.get("right_hand"), hands)
        self.assertNotEqual(hands["left_hand"].id, hands["right_hand"].id, "one gun hopped between the arms")
        self.assertIn(self.gun.id, {hands["left_hand"].id, hands["right_hand"].id}, "the legacy gun was abandoned")

    def test_a_gun_dropped_on_the_floor_by_a_hand_sever_is_taken_back(self):
        # Before #3697 was fixed a hand-only sever dropped the deployed
        # forearm gun to the room, locked and undroppable, and the body
        # walked on before the hand came back. The cut folds the gun back
        # now (test_a_hand_cut_folds_the_arm_gun_back); this pins the
        # safety net for a gun left on a floor by the old behaviour: the
        # next deploy takes it back from wherever it lies rather than
        # spawn a second and leave the first on a floor for good.
        from world.medical.augments import toggle_ability
        self.organs[1].ability_state = {"shotgun": {}}           # only the left arm has a gun
        self.gun.location = self.room2
        toggle_ability(self.char1, "shotgun")
        self.assertEqual(self.char1.hands["left_hand"].id, self.gun.id)
        self.assertEqual(self.gun.location, self.char1)

    def test_a_retract_folds_the_gun_out_of_the_hand_that_holds_it(self):
        # The shared gun is seated in the SECOND arm's hand (the first
        # module was dead when it deployed, then healed). The keeper is
        # the hand that holds it, not the first in order, or the retract
        # through the first host finds nothing and the gun stays seated
        # while the readout says retracted.
        from world.medical.augments import is_ability_deployed, toggle_ability
        self.gun.location = self.char1
        self.char1.hands = {"right_hand": self.gun}
        self.organs[0].ability_state = {"shotgun": {"deployed": False, "weapon_dbref": self.gun.dbref}}
        self.organs[1].ability_state = {"shotgun": {"deployed": True, "weapon_dbref": self.gun.dbref}}
        self.char1.save_medical_state()
        toggle_ability(self.char1, "shotgun")
        self.assertFalse(is_ability_deployed(self.char1, "shotgun"))
        self.assertIsNone(self.char1.hands.get("right_hand"), "the gun stayed in the hand")
        self.assertIsNone(self.gun.location, "the gun was not folded away")

    def test_a_stow_at_one_arm_leaves_the_other_arms_gun_out(self):
        # Both legacy hosts deployed on one shared gun, seated in the left
        # hand. A surgeon's stow at the RIGHT arm settles the reference
        # over every living host first, so it folds nothing out of the
        # left hand and the left module still reads deployed.
        from world.medical.augments import (find_ability_hosts, stow_abilities_at,
                                            _ability_state)
        self.gun.location = self.char1
        self.char1.hands = {"left_hand": self.gun}
        for organ in self.organs:
            organ.ability_state = {"shotgun": {"deployed": True, "weapon_dbref": self.gun.dbref}}
        self.char1.save_medical_state()
        messages = stow_abilities_at(self.char1, "right_arm")
        self.assertEqual(len(messages), 1, messages)
        self.assertEqual(self.char1.hands["left_hand"].id, self.gun.id, "the left hand's gun was folded away")
        self.assertEqual(self.gun.location, self.char1)
        states = {o.container: _ability_state(o, "shotgun")
                  for o in find_ability_hosts(self.char1, "shotgun")}
        self.assertTrue(states["left_arm"].get("deployed"))
        self.assertFalse(states["right_arm"].get("deployed"))
        self.assertNotIn("weapon_dbref", states["right_arm"], "the right arm still shares the left hand's gun")

    def test_a_stow_at_the_keeper_arm_reads_the_other_arm_retracted(self):
        # The other arm's deployed flag was the mirror's word alone (its
        # hand never held the gun). Disowned, it reads retracted, so the
        # readout, the longdesc and the director stop describing a firing
        # socket that is not there, and the next /shotgun deploys.
        from world.medical.augments import (find_ability_hosts, is_ability_deployed,
                                            stow_abilities_at, _ability_state)
        self.gun.location = self.char1
        self.char1.hands = {"left_hand": self.gun}
        for organ in self.organs:
            organ.ability_state = {"shotgun": {"deployed": True, "weapon_dbref": self.gun.dbref}}
        self.char1.save_medical_state()
        stow_abilities_at(self.char1, "left_arm")
        self.assertIsNone(self.gun.location, "the keeper's gun was not folded away")
        self.assertFalse(is_ability_deployed(self.char1, "shotgun"), "an arm reads deployed with no gun")
        states = {o.container: _ability_state(o, "shotgun")
                  for o in find_ability_hosts(self.char1, "shotgun")}
        self.assertFalse(states["right_arm"].get("deployed"))
        self.assertNotIn("weapon_dbref", states["right_arm"])

    def test_a_cut_arm_leaves_the_gun_with_the_hand_that_holds_it(self):
        # Both legacy hosts deployed on one shared gun, seated in the LEFT
        # hand. Cutting the RIGHT arm must not carry that gun off in the
        # right arm and leave the left hand gripping a ghost: the hand that
        # holds it keeps it; the limb's entry lets go.
        from typeclasses.items import apply_sever_to_character
        from world.medical.augments import find_ability_hosts, _ability_state
        self.gun.location = self.char1
        self.char1.hands = {"left_hand": self.gun}
        for organ in self.organs:
            organ.ability_state = {"shotgun": {"deployed": True, "weapon_dbref": self.gun.dbref}}
        self.char1.save_medical_state()
        apply_sever_to_character(self.char1, "right_arm")
        arm = next((o for o in self.room1.contents
                    if o.is_typeclass("typeclasses.items.Appendage", exact=False)), None)
        self.assertIsNotNone(arm, "fixture: the arm did not come off")
        self.assertEqual(self.gun.location, self.char1, "the cut arm carried off the gun the left hand holds")
        self.assertEqual(self.char1.hands.get("left_hand"), self.gun)
        (survivor,) = find_ability_hosts(self.char1, "shotgun")
        state = _ability_state(survivor, "shotgun")
        self.assertEqual(survivor.container, "left_arm")
        self.assertTrue(state.get("deployed"))
        self.assertEqual(state.get("weapon_dbref"), self.gun.dbref, "the hand that holds the gun lost its reference")
        self.assertNotIn(self.gun, arm.contents)

    def test_a_cut_arm_does_not_pull_the_gun_off_another_limb(self):
        # Master-era state: this body's first arm was cut before cuts
        # settled the share, so the gun lies on THAT limb and the other
        # arm still records it. Cutting the other arm now must not pull
        # the gun off the old limb onto the new one; the entry lets go.
        from evennia import create_object
        from typeclasses.items import apply_sever_to_character
        old_limb = create_object("typeclasses.items.Appendage", key="a severed left arm", location=self.room2)
        self.gun.location = old_limb
        self.organs[0].ability_state = {"shotgun": {"weapon_dbref": self.gun.dbref}}
        self.organs[1].ability_state = {"shotgun": {"weapon_dbref": self.gun.dbref}}
        self.char1.save_medical_state()
        apply_sever_to_character(self.char1, "right_arm")
        arm = next((o for o in self.room1.contents
                    if o.is_typeclass("typeclasses.items.Appendage", exact=False)), None)
        self.assertIsNotNone(arm, "fixture: the arm did not come off")
        self.assertEqual(self.gun.location, old_limb, "the cut pulled the gun off another limb")
        self.assertNotIn(self.gun, arm.contents)
        # the cut entry let go (the live organ; the limb's snapshot is copied
        # before the carry and reattachment reclaims only what lies on it)
        self.assertNotIn("weapon_dbref", self.organs[1].ability_state["shotgun"],
                         "the cut arm still claims a gun lying on another limb")

    def test_a_cut_arm_does_not_pull_the_gun_out_of_another_body(self):
        # The same stale reference, but the old limb has since been fitted
        # to someone else, who deployed: the gun is in their hand.
        from typeclasses.items import apply_sever_to_character
        self.gun.location = self.char2
        self.char2.hands = {"left_hand": self.gun}
        self.organs[1].ability_state = {"shotgun": {"weapon_dbref": self.gun.dbref}}
        self.char1.save_medical_state()
        apply_sever_to_character(self.char1, "right_arm")
        self.assertEqual(self.gun.location, self.char2, "the cut pulled the gun out of another body's hand")
        self.assertEqual(self.char2.hands.get("left_hand"), self.gun)


class TheStowIsAtTheCut(_NailzCase):
    """A surgeon stows the hardware AT the cut (#3360); the other hand's
    claws are not at the cut and stay out."""

    def test_stowing_one_hand_leaves_the_other_out(self):
        from world.medical.augments import stow_abilities_at, toggle_ability
        toggle_ability(self.char1, "nailz")
        messages = stow_abilities_at(self.char1, "left_hand")
        self.assertEqual(len(messages), 1)
        self.assertEqual(self.deployed_hands(), ["right_hand"])

    def test_the_stow_of_one_hand_names_that_hand(self):
        # "One of many" is judged against the living hosts, not the one
        # host the stow dispatches: the other hand's claws are still out.
        from world.medical.augments import stow_abilities_at, toggle_ability
        toggle_ability(self.char1, "nailz")
        (said,) = stow_abilities_at(self.char1, "left_hand")
        self.assertIn("left hand", said)
        self.assertNotIn("your hands are just hands again", said)

    def test_a_stow_at_the_keeper_hand_leaves_the_other_hands_legacy_claws_fighting(self):
        # Legacy shared state: both hands deployed on ONE object. The stow
        # settles the share over every living host, and the stowed hand is
        # the keeper; the other hand lets go but is deployed, so it gets
        # its own blades at once and keeps fighting, instead of reading
        # deployed with nothing behind it.
        from evennia import create_object
        from world.medical.augments import (find_ability_hosts, get_active_natural_weapons,
                                            stow_abilities_at, _ability_state)
        shared = create_object("typeclasses.items.Item", key="old blades", location=None)
        hosts = find_ability_hosts(self.char1, "nailz")
        for host in hosts:
            _ability_state(host, "nailz").update({"deployed": True, "weapon_dbref": shared.dbref})
        self.char1.save_medical_state()
        keeper, other = hosts[0], hosts[1]
        messages = stow_abilities_at(self.char1, keeper.container)
        self.assertEqual(len(messages), 1, messages)
        found = get_active_natural_weapons(self.char1)
        self.assertEqual([c for c, _ in found], [other.container], "the other hand stopped fighting")
        self.assertNotEqual(found[0][1].id, shared.id, "the other hand fights with the stowed hand's blades")
        self.assertIsNone(found[0][1].location)
        self.assertTrue(_ability_state(other, "nailz").get("deployed"))
        self.assertTrue(shared.pk, "the shared object was deleted")


class TheSurvivorSpeaksForOneHand(_NailzCase):
    """A body down to one hand has one hand's claws to move: the one-hand
    prose, naming the hand, not ten blades on five fingers (#3700)."""

    def setUp(self):
        super().setUp()
        from world.medical.augments import find_ability_hosts
        left = next(o for o in find_ability_hosts(self.char1, "nailz")
                    if getattr(o, "container", None) == "left_hand")
        left.current_hp = 0          # the way severance leaves it

    def test_the_deploy_names_the_surviving_hand(self):
        from world.medical.augments import toggle_ability
        said = toggle_ability(self.char1, "nailz")
        self.assertIn("right hand", said)
        self.assertNotIn("ten carbide blades", said)

    def test_the_retract_names_the_surviving_hand(self):
        from world.medical.augments import toggle_ability
        toggle_ability(self.char1, "nailz")
        said = toggle_ability(self.char1, "nailz")
        self.assertIn("right hand", said)
        self.assertNotIn("your hands are just hands again", said)

    def test_control_both_hands_still_speak_as_one(self):
        # the left hand restored: both move, so the both-hands line
        from world.medical.augments import toggle_ability
        for organ in self.char1.medical_state.organs.values():
            if getattr(organ, "container", None) == "left_hand":
                organ.current_hp = organ.max_hp
        said = toggle_ability(self.char1, "nailz")
        self.assertIn("ten carbide blades", said)


class TheNaturalLookupIsPerHost(_NailzCase):

    def test_every_deployed_hand_is_listed_with_its_own_item(self):
        from world.medical.augments import get_active_natural_weapons, toggle_ability
        toggle_ability(self.char1, "nailz")
        found = get_active_natural_weapons(self.char1)
        self.assertEqual(sorted(c for c, _ in found), ["left_hand", "right_hand"])
        self.assertEqual(len({w.id for _, w in found}), 2)

    def test_an_item_lying_elsewhere_is_not_a_weapon(self):
        """The stale-reference guard: an object on a severed limb (or
        anywhere but parked in the body) does not fight."""
        from world.medical.augments import get_active_natural_weapons, toggle_ability
        toggle_ability(self.char1, "nailz")
        found = get_active_natural_weapons(self.char1)
        _, item = found[0]
        item.location = self.room1
        self.assertEqual(len(get_active_natural_weapons(self.char1)), 1)


class TestSeveranceStaysPerHand(_NailzCase):
    """Losing a hand must not retract the other one's blades."""

    def test_one_hand_can_differ_after_severance(self):
        from world.medical.augments import (find_ability_hosts,
                                            toggle_ability)
        toggle_ability(self.char1, "nailz")
        hosts = find_ability_hosts(self.char1, "nailz")
        # kill the left hand's organ the way severance does
        left = next(o for o in hosts
                    if getattr(o, "container", None) == "left_hand")
        left.current_hp = 0
        still = self.deployed_hands()
        self.assertEqual(still, ["right_hand"],
                         "the surviving hand lost its blades")

    def test_a_shared_legacy_object_is_settled_at_the_cut(self):
        # Legacy shared state: both hands deployed on ONE object. The cut
        # arm takes it; the survivor must let go of it right there, or a
        # surgeon reattaching that arm to ANOTHER body leaves one object
        # claimed by two. Deployed and natural, the survivor gets its own
        # blades at once and keeps fighting.
        from evennia import create_object
        from typeclasses.items import apply_sever_to_character
        from world.medical.augments import (find_ability_hosts, get_active_natural_weapons,
                                            _ability_state)
        shared = create_object("typeclasses.items.Item", key="old blades", location=None)
        for host in find_ability_hosts(self.char1, "nailz"):
            _ability_state(host, "nailz").update({"deployed": True, "weapon_dbref": shared.dbref})
        self.char1.save_medical_state()
        apply_sever_to_character(self.char1, "left_arm")
        arm = next((o for o in self.room1.contents
                    if o.is_typeclass("typeclasses.items.Appendage", exact=False)), None)
        self.assertIsNotNone(arm, "fixture: the arm did not come off")
        self.assertEqual(shared.location, arm, "the limb did not take the shared blades")
        (survivor,) = find_ability_hosts(self.char1, "nailz")
        self.assertEqual(survivor.container, "right_hand")
        state = _ability_state(survivor, "nailz")
        self.assertTrue(state.get("deployed"), "the survivor lost its deployed flag")
        self.assertNotEqual(state.get("weapon_dbref"), shared.dbref,
                            "the survivor still points at blades lying in a severed arm")
        found = get_active_natural_weapons(self.char1)
        self.assertEqual([c for c, _ in found], ["right_hand"], "the surviving hand stopped fighting")
        self.assertNotEqual(found[0][1].id, shared.id)

    def test_the_settle_is_saved_with_the_cut(self):
        # A combat sever saves medical state BEFORE the hardware carry and
        # never again. The settle must be saved by the carry itself, or a
        # reload brings the shared reference back and orphans the
        # survivor's new blades.
        from evennia import create_object
        from typeclasses.items import apply_sever_to_character
        from world.medical.augments import find_ability_hosts, _ability_state
        shared = create_object("typeclasses.items.Item", key="old blades", location=None)
        for host in find_ability_hosts(self.char1, "nailz"):
            _ability_state(host, "nailz").update({"deployed": True, "weapon_dbref": shared.dbref})
        self.char1.save_medical_state()
        apply_sever_to_character(self.char1, "left_arm")
        (survivor,) = find_ability_hosts(self.char1, "nailz")
        own = _ability_state(survivor, "nailz").get("weapon_dbref")
        self.assertNotEqual(own, shared.dbref)
        self.char1._medical_state = None          # drop the cache: read what was SAVED
        (reloaded,) = find_ability_hosts(self.char1, "nailz")
        self.assertEqual(_ability_state(reloaded, "nailz").get("weapon_dbref"), own,
                         "the settle lived only in memory")
