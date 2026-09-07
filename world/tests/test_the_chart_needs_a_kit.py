"""No instruments, no surgery — through either door (#2545).

Seven standalone surgical dispatch sites in `CmdSurgical` gate on a
surgical kit in inventory. The `operate` chart door reached the same
resolvers and checked **nothing**. A character carrying nothing at all
could chart `incise chest` → `harvest heart` → Commence and extract an
organ bare-handed, or chart `amputate left arm` and shear a limb off a
living person. `operate` is `locks = "cmd:all()"` and registered
unconditionally.

`HEALTH_AND_SUBSTANCE_SYSTEM_SPEC` states it without qualification —
*"Four verbs, all gated on a surgical kit in inventory"* — and records
that the kit was deliberately repurposed into a tool prerequisite. This
is the constraint, not a side effect.

## Two pieces of evidence that the check was meant to exist

`_resolve_amputate`'s docstring skips its own weapon check because *"the
chart runner already requires the surgical kit at chart-author time via
the procedure-verb infrastructure"*. It does not.

And `commence_chart` already has the handler for it:

```python
except Exception as exc:
    # Dispatch failure (e.g. surgeon dropped their kit between
    # chart authoring and commence).  Mark the step failed and
    # advance to the next so a recoverable later step still gets a shot.
```

That block was written for a raise that nothing performed.

## Gated at the funnel

`start_procedure` is the single entry — eight callers, seven of which
already check and so never reach it. Putting the guard there closes the
chart door and any future one, and produces exactly the failure
`commence_chart` was already written to absorb.

Also moved: `find_surgical_kit` / `instruments_wanted` from
`commands/CmdSurgical.py` to `world/medical/utils.py`. `world` importing
`commands` would be a layering inversion; the command keeps thin aliases
so its seven call sites and their better-worded refusals are unchanged.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class _SurgeryCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.surgeon = self.char1
        self.patient = self.char2
        for c in (self.surgeon, self.patient):
            c.location = self.room1

    def give_kit(self, to=None, species_ok=True):
        kit = create_object("typeclasses.items.Item", key="a surgical kit",
                            location=to or self.surgeon)
        kit.attributes.add("medical_type", "surgical_treatment")
        if species_ok:
            kit.attributes.add("target_species", ["human"])
        return kit

    def begin(self, verb="incise"):
        from world.medical import procedures
        return procedures.start_procedure(
            self.patient, verb=verb, actor=self.surgeon, location="chest")


class TestBareHandedSurgeryIsRefused(_SurgeryCase):
    def test_starting_without_a_kit_raises(self):
        from world.medical.procedures import SurgicalKitRequired
        with self.assertRaises(SurgicalKitRequired):
            self.begin()

    def test_the_refusal_names_the_instrument(self):
        from world.medical.procedures import SurgicalKitRequired
        with self.assertRaises(SurgicalKitRequired) as caught:
            self.begin()
        self.assertIn("surgical kit", str(caught.exception))

    def test_no_procedure_is_staged(self):
        """The important part: it must refuse BEFORE writing state."""
        from world.medical import procedures
        from world.medical.procedures import SurgicalKitRequired
        with self.assertRaises(SurgicalKitRequired):
            self.begin()
        self.assertFalse(procedures.is_procedure_active(self.patient))

    def test_amputation_is_refused_too(self):
        """`_resolve_amputate` dropped its weapon check citing this
        gate — so this is the verb with nothing else standing behind
        it."""
        from world.medical.procedures import SurgicalKitRequired
        with self.assertRaises(SurgicalKitRequired):
            self.begin(verb="amputate")


class TestWithAKitItProceeds(_SurgeryCase):
    def test_it_starts(self):
        self.give_kit()
        self.begin()
        from world.medical import procedures
        self.assertTrue(procedures.is_procedure_active(self.patient))

    def test_a_kit_on_the_floor_does_not_count(self):
        """Inventory, per the spec — not merely present in the room."""
        from world.medical.procedures import SurgicalKitRequired
        self.give_kit(to=self.room1)
        with self.assertRaises(SurgicalKitRequired):
            self.begin()

    def test_a_kit_carried_by_the_patient_does_not_count(self):
        from world.medical.procedures import SurgicalKitRequired
        self.give_kit(to=self.patient)
        with self.assertRaises(SurgicalKitRequired):
            self.begin()


class TestTheChartDoorAbsorbsIt(_SurgeryCase):
    """`commence_chart` already had the handler; this checks it catches
    the new raise rather than propagating it to the player as a
    traceback."""

    def test_commence_marks_the_step_failed(self):
        from world.medical import charts
        chart = {"steps": [{"verb": "incise", "args": {"location": "chest"},
                            "status": "pending"}]}
        charts.save_chart(self.patient, chart)
        try:
            charts.commence_chart(self.patient, self.surgeon)
        except Exception as exc:  # noqa: BLE001
            self.fail(f"commence let the kit refusal escape: {exc!r}")

    def test_no_organ_comes_out(self):
        from world.medical import procedures
        from world.medical.procedures import SurgicalKitRequired
        with self.assertRaises(SurgicalKitRequired):
            procedures.start_procedure(
                self.patient, verb="harvest", actor=self.surgeon,
                location="chest", target_organ="heart")
        self.assertFalse(procedures.is_procedure_active(self.patient))


class TestTheHelpersMovedButBehaveTheSame(_SurgeryCase):
    def test_the_command_alias_still_finds_a_kit(self):
        from commands.CmdSurgical import _find_surgical_kit
        kit = self.give_kit()
        self.assertIs(_find_surgical_kit(self.surgeon, self.patient), kit)

    def test_the_command_alias_returns_none_without_one(self):
        from commands.CmdSurgical import _find_surgical_kit
        self.assertIsNone(_find_surgical_kit(self.surgeon, self.patient))

    def test_the_wording_helper_still_works(self):
        from commands.CmdSurgical import _instruments_wanted
        self.assertEqual(_instruments_wanted(self.patient), "a surgical kit")

    def test_a_robot_wants_a_tool_roll(self):
        from world.medical.utils import instruments_wanted
        self.patient.db.species = "robot"
        self.assertEqual(instruments_wanted(self.patient), "a tool roll")

    def test_world_does_not_import_commands(self):
        """The reason the helpers moved."""
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        for name in ("procedures.py", "charts.py", "utils.py"):
            body = (root / "world" / "medical" / name).read_text(
                errors="ignore")
            self.assertNotIn("from commands.", body, f"{name} imports commands")


class TestBareHandedSurgeryStagesNothing(_SurgeryCase):
    """Stated without naming the new exception, so it fails as a clean
    FAILURE against the unfixed tree rather than erroring on a missing
    symbol — unfixed, the procedure is staged and this catches it."""

    def try_begin(self, verb="incise"):
        from world.medical import procedures
        try:
            procedures.start_procedure(
                self.patient, verb=verb, actor=self.surgeon,
                location="chest")
        except Exception:  # noqa: BLE001 — the refusal, whatever shape
            pass
        return procedures.is_procedure_active(self.patient)

    def test_incising_with_nothing_in_hand_stages_nothing(self):
        self.assertFalse(self.try_begin(),
                         "surgery began bare-handed")

    def test_harvesting_with_nothing_in_hand_stages_nothing(self):
        self.assertFalse(self.try_begin(verb="harvest"),
                         "an organ harvest began bare-handed")

    def test_amputating_with_nothing_in_hand_stages_nothing(self):
        self.assertFalse(self.try_begin(verb="amputate"),
                         "an amputation began bare-handed")

    def test_with_a_kit_it_does_stage(self):
        """The control — the guard must refuse the empty-handed case,
        not every case."""
        self.give_kit()
        self.assertTrue(self.try_begin())
