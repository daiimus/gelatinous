"""Supplies know whose body they are for (#2262).

Nothing gated a medical item by species, and robots carry human-shaped
medical state — so a secbot could be bandaged with sterile gauze, given
a painkiller for pain it cannot feel, and transfused with donor blood.
All of it worked.

Refusing is the interesting half. If a first aid kit fixes a secbot,
the service bench and the three people standing shifts at it have no
reason to exist.

The safety property that lets this ship without breaking the world:
an item declaring NEITHER `serves` nor `not_for` still works on
everyone. Only the refusals are new.
"""
from evennia.utils.test_resources import EvenniaCommandTest
from evennia.prototypes.spawner import spawn

from world import prototypes
from world.medical.utils import serves_species


def _spawn(proto):
    return spawn(getattr(prototypes, proto))[0]


class TestTheGate(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.bot, self.person = self.char1, self.char2
        self.bot.db.species = "robot"
        self.person.db.species = "human"

    def test_a_chassis_refuses_a_painkiller(self):
        ok, why = serves_species(_spawn("PAINKILLER"), self.bot)
        self.assertFalse(ok)
        self.assertIn("living tissue", why)

    def test_a_chassis_refuses_sterile_gauze(self):
        """The translated articles step aside too — a dressing on a
        hydraulic leak is exactly the costume the bench exists to
        make impossible."""
        self.assertFalse(serves_species(_spawn("GAUZE_BANDAGES"), self.bot)[0])

    def test_a_person_refuses_machine_stock(self):
        ok, why = serves_species(_spawn("SEALANT_PATCH"), self.person)
        self.assertFalse(ok)
        self.assertIn("machine stock", why)

    def test_the_machine_kit_serves_machines(self):
        for proto in ("SEALANT_PATCH", "CONFORMAL_COATING",
                      "STRUT_BRACE", "HYDRAULIC_CHARGE"):
            with self.subTest(proto=proto):
                self.assertTrue(serves_species(_spawn(proto), self.bot)[0])

    def test_the_organic_kit_still_serves_people(self):
        for proto in ("GAUZE_BANDAGES", "PAINKILLER", "BLOOD_BAG", "SPLINT"):
            with self.subTest(proto=proto):
                self.assertTrue(serves_species(_spawn(proto), self.person)[0])

    def test_the_tourniquet_serves_both(self):
        """One article, both bodies: clamping a line stops amber
        hydraulic fluid as well as it stops blood. It declares nothing
        precisely so it is refused by nobody."""
        tq = _spawn("TOURNIQUET")
        self.assertTrue(serves_species(tq, self.bot)[0])
        self.assertTrue(serves_species(tq, self.person)[0])
        self.assertIsNone(tq.attributes.get("serves", None))
        self.assertIsNone(tq.attributes.get("not_for", None))

    def test_an_undeclared_item_works_on_everyone(self):
        """The safety property. Anything not reviewed keeps its old
        behaviour, so this change can only ever ADD refusals."""
        kit = _spawn("SURGICAL_KIT")
        self.assertTrue(serves_species(kit, self.bot)[0])
        self.assertTrue(serves_species(kit, self.person)[0])

    def test_a_synthetic_takes_the_human_kit(self):
        """Organic-presenting and people-shaped, so the organic kit is
        coarse rather than wrong. Its own tier comes later (§8.3)."""
        self.person.db.species = "synthetic_humanoid"
        self.assertTrue(serves_species(_spawn("GAUZE_BANDAGES"), self.person)[0])
        self.assertFalse(serves_species(_spawn("SEALANT_PATCH"), self.person)[0])

    def test_a_missing_species_is_treated_as_a_person(self):
        self.person.attributes.remove("species")
        self.assertTrue(serves_species(_spawn("PAINKILLER"), self.person)[0])


class TestTheBenchStocksItsOwn(EvenniaCommandTest):
    def test_the_par_is_the_machine_kit(self):
        from world.director.medical import MECHANIC_PAR
        for proto in MECHANIC_PAR:
            with self.subTest(proto=proto):
                item = _spawn(proto)
                self.assertTrue(
                    serves_species(item, self._robot())[0],
                    f"{proto} is stocked at the bench but bounces off a unit")

    def _robot(self):
        self.char1.db.species = "robot"
        return self.char1

    def test_the_mechanic_stocks_nothing_organic(self):
        from world.director.medical import MECHANIC_PAR
        person = self.char2
        person.db.species = "human"
        useful_to_people = [p for p in MECHANIC_PAR
                            if p != "TOURNIQUET"
                            and serves_species(_spawn(p), person)[0]]
        self.assertEqual(useful_to_people, [])


class TestAtTheSurface(EvenniaCommandTest):
    """The helper agreeing with itself proves nothing. These drive the
    command a mechanic actually types, because that is where a gate
    either fires or silently doesn't."""

    def setUp(self):
        super().setUp()
        from commands import CmdConsumption
        self.cmds = CmdConsumption
        self.bot = self.char2
        self.bot.db.species = "robot"
        # trust, so the refusal we see is the SPECIES gate and not the
        # consent gate standing in front of it
        from world.consent import grant_trust
        try:
            grant_trust(self.bot, self.char1)
        except Exception:
            self.bot.db.trusted = [self.char1]

    def test_bandaging_a_secbot_is_refused_in_words(self):
        gauze = _spawn("GAUZE_BANDAGES")
        gauze.move_to(self.char1, quiet=True, move_hooks=False)
        out = self.call(self.cmds.CmdBandage(),
                        f"{self.bot.key}'s chest with gauze")
        self.assertIn("living tissue", out)

    def test_every_treatment_verb_shares_the_one_gate(self):
        """inject / apply / bandage / eat / drink / inhale all route
        through `check_medical_requirements`, so the gate cannot be
        live on one verb and absent on another."""
        import inspect
        src = inspect.getsource(self.cmds)
        self.assertEqual(src.count("check_medical_requirements(item"), 6)
        self.assertEqual(src.count("serves_species(item"), 1)

    def test_the_sealant_patch_is_not_refused(self):
        """The other half: the machine article must actually get
        through the same gate, or the mechanic has no way in at all."""
        patch = _spawn("SEALANT_PATCH")
        patch.move_to(self.char1, quiet=True, move_hooks=False)
        out = self.call(self.cmds.CmdBandage(),
                        f"{self.bot.key}'s chest with patches")
        self.assertNotIn("living tissue", out)
        self.assertNotIn("machine stock", out)
