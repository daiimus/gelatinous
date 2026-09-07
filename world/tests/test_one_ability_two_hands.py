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

    def test_both_hands_point_at_the_same_weapon(self):
        """One ability, one weapon item — not one per hand."""
        from world.medical.augments import (find_ability_hosts,
                                            toggle_ability)
        toggle_ability(self.char1, "nailz")
        refs = {(getattr(o, "ability_state", None) or {})
                .get("nailz", {}).get("weapon_dbref")
                for o in find_ability_hosts(self.char1, "nailz")}
        self.assertEqual(len(refs), 1, f"hands disagree about the weapon: {refs}")


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

    def test_find_ability_still_returns_one_organ(self):
        from world.medical.augments import find_ability
        self._seat("head", "eyez", {"type": "blindsight"})
        organ, spec = find_ability(self.char1, "eyez")
        self.assertEqual(getattr(organ, "container", None), "head")
        self.assertEqual(spec["type"], "blindsight")


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
