"""Two dead readouts in the medical commands (#2534, #2535).

**The severity ladder was scaled to a domain the engine can't reach.**
`medinfo <target> conditions` bucketed at 20 / 10 / 5 / 1, but every
write clamps through `min(10, ...)`, so `>= 20` was unreachable and the
worst injury the game can inflict rendered as "Severe" -- one rung below
the top of its own ladder. Live confirmation before the fix: 149
conditions across 23 bodies, **maximum severity 8**, nothing above 10 in
any code path.

10 is not an invented boundary. `InfectionCondition.
disables_organ_at_severity` already calls it Critical in its own
docstring -- *"Critical infection (severity >= 10)"* -- so the ladder now
agrees with the engine instead of contradicting it. The 5 rung is
deliberately untouched: `HEALTH_AND_SUBSTANCE_SYSTEM_SPEC` pins it as
the line where a field bandage stops working and natural clotting stops
happening, so it is a real clinical boundary, not a display choice.

**And damagetest counted a key that was never emitted.**
`MedicalState.to_dict()` returns organs / conditions / blood_level /
pain_level / consciousness. It has never emitted `wounds`. The
`.get('wounds', {})` default swallowed the miss, the sum was always 0,
and the `if total_wounds > 0` guard below it could never be satisfied --
so the line never printed, no matter how much damage was applied. It
reads as working code, which is why it survived.

The replacement counts conditions, which is what damage actually
generates and what damagetest surfaces nowhere else; organ damage is
already enumerated in the block directly beneath it, so counting organs
there would only restate it.
"""
from evennia.utils.test_resources import EvenniaTest

from world.medical.conditions import BleedingCondition, PainCondition
from world.medical.core import MedicalState


class TestToDictHasNeverHadAWoundsKey(EvenniaTest):
    """The premise of the bug, pinned so the count can't silently rot
    back to reading a key that isn't there."""

    def test_the_emitted_keys_are_known(self):
        state = MedicalState(self.char1)
        self.assertEqual(
            set(state.to_dict()),
            {"organs", "conditions", "blood_level", "pain_level",
             "consciousness"},
        )

    def test_there_is_no_wounds_key(self):
        self.assertNotIn("wounds", MedicalState(self.char1).to_dict())

    def test_the_old_expression_always_summed_to_zero(self):
        """Reproduces the original read against a body that really is
        injured -- the miss was silent, not conditional on being
        healthy."""
        state = MedicalState(self.char1)
        state.conditions.append(BleedingCondition(severity=8,
                                                  location="chest"))
        old = sum(len(w) for w in state.to_dict().get("wounds", {}).values())
        self.assertEqual(old, 0)


class TestDamagetestReportsWhatDamageProduced(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.msg = lambda text=None, **kw: self.said.append(str(text))
        self.said = []

    def _run(self):
        from commands.CmdMedical import CmdDamageTest
        cmd = CmdDamageTest()
        cmd.caller = self.char1
        cmd.args = " 6 chest cut"
        cmd.func()
        return "\n".join(self.said)

    def test_an_injured_body_reports_its_conditions(self):
        out = self._run()
        self.assertIn("active", out)
        self.assertIn("condition", out)

    def test_the_count_is_not_zero(self):
        self._run()
        state = self.char1.medical_state
        self.assertGreater(len(state.conditions), 0,
                           "fixture produced no conditions -- the test "
                           "would pass vacuously")

    def test_the_line_names_the_condition_types(self):
        out = self._run()
        types = {c.type for c in self.char1.medical_state.conditions}
        for name in types:
            self.assertIn(name, out)


class TestTheLadderCoversTheEngineDomain(EvenniaTest):
    """`_show_conditions` renders the label; drive it and read the
    table rather than restating the thresholds, so a refactor of the
    branch shape can't fake a pass."""

    def _label(self, severity):
        from commands.CmdMedical import CmdMedicalInfo
        said = []
        self.char1.msg = lambda text=None, **kw: said.append(str(text))
        state = MedicalState(self.char1)
        state.conditions.append(PainCondition(severity=severity,
                                              location="chest"))
        CmdMedicalInfo()._show_conditions(self.char1, self.char1, state)
        return "\n".join(said)

    def test_the_engine_ceiling_renders_as_critical(self):
        self.assertIn("Critical", self._label(10))

    def test_the_top_rung_is_reachable_at_all(self):
        """The whole defect: no severity the engine can produce reached
        the top of the ladder."""
        reachable = [s for s in range(0, 11) if "Critical" in self._label(s)]
        self.assertTrue(reachable,
                        "no reachable severity renders as Critical")

    def test_severity_eight_the_live_maximum_is_severe(self):
        self.assertIn("Severe", self._label(8))

    def test_the_spec_pinned_five_boundary_did_not_move(self):
        """HEALTH_AND_SUBSTANCE_SYSTEM_SPEC: severity >= 5 needs a
        tourniquet and will not self-clot."""
        self.assertIn("Moderate", self._label(5))
        self.assertIn("Minor", self._label(4))

    def test_one_is_still_minor(self):
        self.assertIn("Minor", self._label(1))

    def test_zero_is_negligible(self):
        self.assertIn("Negligible", self._label(0))

    def test_every_severity_gets_a_label(self):
        for s in range(0, 11):
            out = self._label(s)
            self.assertTrue(
                any(w in out for w in
                    ("Critical", "Severe", "Moderate", "Minor",
                     "Negligible")),
                f"severity {s} rendered no label",
            )
