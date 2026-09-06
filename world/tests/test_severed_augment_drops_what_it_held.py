"""A severed augmented limb drops what it was holding (#2438).

`ANATOMY_AUGMENTS_SPEC` §3.4 is marked SHIPPED and promises that "the
existing severance subtraction then handles 'severed tail drops what it
held' **with no new code**". §6's test contract restates it: "severance
removes it from `hands` **and drops held items**."

It did not. `sever_character_body` builds `hands_to_clear` from
`sever_hand_by_container` — the **static species table**, which for a
human lists only the four arm/hand entries. An installed prehensile tail
is not in it, so the set came back empty and the drop block never ran:
the weapon silently stayed in generic inventory instead of falling free.

§7 rules that static anatomy reads go through the per-character overlay.
That was applied to two of the three:

    grasping_containers      -> overlay
    severable_containers     -> overlay
    sever_hand_by_container  -> still species-static

So an augmented limb was severable but not droppable. Third-sibling
pattern: the rule was written down and applied to the siblings someone
was looking at.

The overlay now lives in one place, `Character.grasping_containers()`,
which both `hands` and severance ask. It is deliberately NOT filtered by
severance — `hands` applies that filter on top, but severance needs the
unfiltered set, because by the time it runs `sever_character_body` has
already zeroed the chain's organs and `hands` would hide the very limb
being removed.
"""
from evennia.utils.test_resources import EvenniaTest


class _TailCase(EvenniaTest):
    """A character with a grasping augment at a non-species container."""

    CONTAINER = "tail"

    def setUp(self):
        super().setUp()
        self.char = self.char1
        self.char.location = self.room1
        self.weapon = self.obj1
        self.weapon.key = "a bone-handled knife"
        self.weapon.location = self.char

    def _install_grasping_organ(self):
        # The real signature: `Organ(organ_name, organ_data=...)`, and
        # `container` / `max_hp` are read OUT of that data rather than
        # passed as kwargs.
        from world.medical.core import Organ
        state = self.char.medical_state
        organ = Organ("prehensile tail", organ_data={
            "container": self.CONTAINER,
            "max_hp": 10,
            "grasping": True,
            "severable_container": True,
        })
        state.organs["prehensile tail"] = organ
        return organ


class TestTheAugmentIsAHand(_TailCase):
    def test_its_container_counts_as_grasping(self):
        self._install_grasping_organ()
        self.assertIn(self.CONTAINER, self.char.grasping_containers())

    def test_it_shows_as_a_hand(self):
        self._install_grasping_organ()
        self.assertIn(self.CONTAINER, self.char.hands)

    def test_a_body_without_one_does_not_have_it(self):
        self.assertNotIn(self.CONTAINER, self.char.grasping_containers())

    def test_the_born_anatomy_is_still_there(self):
        """The overlay ADDS; it must not replace the species table."""
        self._install_grasping_organ()
        grasping = self.char.grasping_containers()
        self.assertTrue(
            any("hand" in g or "arm" in g for g in grasping),
            f"species hands vanished: {grasping}")


class TestSeveringItDropsTheWeapon(_TailCase):
    """`detach_items_to_appendage(character, appendage, containers)` is
    the function that owns the drop -- `sever_character_body` strips
    body state and takes no appendage."""

    def sever(self, containers=None):
        from typeclasses.items import detach_items_to_appendage
        appendage = self.obj2
        appendage.key = "a severed prehensile tail"
        return detach_items_to_appendage(
            self.char, appendage, containers or (self.CONTAINER,))

    def test_the_weapon_leaves_the_slot(self):
        self._install_grasping_organ()
        self.char.held_items = {self.CONTAINER: self.weapon}
        self.sever()
        self.assertNotIn(
            self.weapon,
            dict(self.char.held_items or {}).values(),
            "the severed tail kept holding the knife")

    def test_the_weapon_falls_to_the_room(self):
        """PR-H0: it drops free rather than travelling with the limb, so
        salvage does not require handling the severed part first."""
        self._install_grasping_organ()
        self.char.held_items = {self.CONTAINER: self.weapon}
        self.sever()
        self.assertIs(self.weapon.location, self.room1)

    def test_an_empty_augment_severs_cleanly(self):
        self._install_grasping_organ()
        self.char.held_items = {}
        self.sever()
        self.assertNotIn(self.CONTAINER,
                         dict(self.char.held_items or {}))

    def test_a_species_hand_still_drops_what_it_held(self):
        """The path that already worked must keep working."""
        self.char.held_items = {"right_hand": self.weapon}
        self.sever(containers=("right_arm",))
        self.assertNotIn(self.weapon,
                         dict(self.char.held_items or {}).values())
