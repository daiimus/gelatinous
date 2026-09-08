"""`medinfo organs` reports function, and a kit is drawn once
(#2533, #2474).

## #2533 — status derived from HP alone

Organ function in this engine is a **two-input** calculation — HP *and*
the conditions bound to that organ. The display read only the first:

```python
if organ.current_hp == organ.max_hp:
    status = "|gHealthy|n"
```

The only non-HP input in the whole function was `wound_stage`, consulted
only at 0 HP. So an organ the model rates **0% functional**, disabled
outright by a condition, was presented to the medic as `Healthy` — and
the summary line said `Damaged Organs: 0` about a dying patient.

`get_functionality_percentage` is the engine's own answer, and
`is_functional` is its boolean sibling. Neither had a caller outside
`core.py` and the tests. A medic reads this table to decide what to
treat.

## #2474 — a kit is a requirement, not a consumable

`incise` **checks for** a surgical kit; nothing spends it. `draw_supply`
spawns unconditionally, so every install minted a fresh one. Live when
filed — and still true when I checked: **9 kits on Jericho Black III**,
eight with consecutive object ids.

The draw now asks `find_surgical_kit`, the same predicate the procedure
gate uses, so "do I need one" and "will incise accept it" can't answer
differently.

And the bottomless draw is a **post** perk: the gate read
`post is not None and by.location != post`, which skipped the location
test entirely for anyone whose `soul_post` was None —
inverted-permissive for exactly the callers it should be strictest
about. Checked against the world before tightening: 78 objects carry a
`soul_post`, the clinic keeper among them; one (the Rook) has it set to
None and is now correctly refused.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.medical.conditions import InfectionCondition


class _OrganCase(EvenniaTest):
    def organ(self, name="heart"):
        return self.char2.medical_state.organs[name]

    def rows(self):
        """Drive the real command and return its output."""
        said = []
        self.char1.msg = lambda text=None, **kw: said.append(str(text))
        from commands.CmdMedical import CmdMedicalInfo
        cmd = CmdMedicalInfo()
        cmd.caller = self.char1
        cmd._show_organs(self.char1, self.char2, self.char2.medical_state)
        return "\n".join(said)


class TestStatusFollowsFunction(_OrganCase):
    def disable(self, organ):
        """A condition the engine rates as disabling."""
        state = self.char2.medical_state
        condition = InfectionCondition(10, organ.container)
        state.add_condition(condition)
        organ.conditions.append(condition)
        return condition

    def test_an_intact_organ_reads_healthy(self):
        self.assertIn("Healthy", self.rows())

    def test_a_condition_disabled_organ_does_not_read_healthy(self):
        organ = self.organ()
        self.disable(organ)
        if organ.is_functional():
            self.skipTest("this condition does not disable at this severity")
        out = self.rows()
        self.assertIn("Disabled", out)

    def test_the_percentage_is_shown(self):
        self.assertIn("%", self.rows())

    def test_a_damaged_organ_still_reads_damaged(self):
        organ = self.organ()
        organ.current_hp = int(organ.max_hp * 0.8)
        self.assertIn("Damaged", self.rows())

    def test_a_destroyed_organ_still_reads_destroyed(self):
        organ = self.organ()
        organ.current_hp = 0
        self.assertIn("Destroyed", self.rows())

    def test_a_severed_stump_still_reads_severed(self):
        organ = self.organ()
        organ.current_hp = 0
        organ.wound_stage = "severed"
        self.assertIn("Severed", self.rows())


class TestTheSummaryCounts(_OrganCase):
    def summary(self):
        said = []
        self.char1.msg = lambda text=None, **kw: said.append(str(text))
        from commands.CmdMedical import CmdMedicalInfo
        cmd = CmdMedicalInfo()
        cmd.caller = self.char1
        cmd._show_summary(self.char1, self.char2, self.char2.medical_state)
        return "\n".join(said)

    def test_a_healthy_body_counts_zero(self):
        out = self.summary()
        self.assertIn("Damaged Organs", out)

    def test_hp_loss_still_counts(self):
        organ = self.organ()
        organ.current_hp = organ.max_hp - 1
        self.assertNotIn("Damaged Organs |  0", self.summary())

    def test_the_count_reads_function_not_only_hp(self):
        import inspect

        from commands import CmdMedical
        body = inspect.getsource(CmdMedical.CmdMedicalInfo._show_summary)
        self.assertIn("get_functionality_percentage", body)


class TestTheKitIsDrawnOnce(EvenniaTest):
    def kit(self, holder):
        item = create_object("typeclasses.items.Item", key="a surgical kit",
                             location=holder)
        item.attributes.add("medical_type", "surgical_treatment")
        return item

    def run_builder(self, what="heart"):
        """A REAL cyberware word, so the builder gets past its first
        guard. My first version mocked `resolve_cyberware` to
        `(None, None)`, which returns immediately — so "no kit was
        drawn" was true because nothing was drawn at all."""
        from world import clinic
        with mock.patch("world.clinic._draw") as draw:
            draw.return_value = create_object(
                "typeclasses.items.Item", key="a drawn thing",
                location=self.char1)
            clinic.build_install_chart(self.char1, self.char2, what)
        return [c for c in draw.call_args_list if "SURGICAL_KIT" in str(c)]

    def test_the_builder_gets_far_enough_to_draw(self):
        """Guards the guard: with no kit carried, it must draw one."""
        self.assertEqual(len(self.run_builder()), 1)

    def test_a_surgeon_who_has_one_does_not_draw_another(self):
        from world.medical.utils import find_surgical_kit
        self.kit(self.char1)
        self.assertIsNotNone(find_surgical_kit(self.char1, self.char2))
        self.assertEqual(self.run_builder(), [])

    def test_the_builder_asks_before_drawing(self):
        import inspect

        from world import clinic
        body = inspect.getsource(clinic.build_install_chart)
        self.assertIn("find_surgical_kit", body)
        self.assertLess(body.index("find_surgical_kit"),
                        body.index('_draw(by, "SURGICAL_KIT")'))


class TestTheBottomlessDrawNeedsAPost(EvenniaTest):
    def draw(self, by):
        from world.clinic import draw_supply
        return draw_supply(by, "SURGICAL_KIT")

    def test_no_post_means_no_draw(self):
        self.char1.db.soul_post = None
        self.assertIsNone(self.draw(self.char1))

    def test_away_from_the_post_means_no_draw(self):
        self.char1.db.soul_post = self.room2
        self.char1.location = self.room1
        self.assertIsNone(self.draw(self.char1))

    def test_at_the_post_still_draws(self):
        self.char1.db.soul_post = self.room1
        self.char1.location = self.room1
        self.assertIsNotNone(self.draw(self.char1))
