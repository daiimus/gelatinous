"""Death prose says how you died (#2778).

`get_death_cause()` could return six strings -- five capacity failures
plus "unknown causes". The death-prose matcher looked for nine keywords,
and only two of them ("blood loss", "heart failure") appeared in
anything the engine could emit. So the authored lines for a head wound,
a stab and a slash existed in every species table and no player had ever
seen one; four of the six real causes collapsed into one generic line.
Someone killed with a knife -- the most ordinary death in this game --
got "draws their final breath and grows still."

The producer described WHICH CAPACITY hit zero; the tables were authored
against WHAT DID THE DAMAGE. Two questions, and nothing recorded the
second. Now `take_damage` records the killing blow at the one place
both halves are in scope, `get_death_cause` composes it into the cause
("blood loss from a stab wound to the chest"), and the four capacity
causes that had no prose get a line per species.

Priority is deliberate: the physiology keywords keep the top of the
order, so a stab that bleeds out still reads as bleeding out -- specific
prose, not generic -- and a blow only decides the line when the
physiology phrase had none of its own.

Also: the personal bleeding line told a robot it was bleeding BLOOD, in
amber, while the room prose four lines up said hydraulic fluid. The noun
now follows the species like the colour already did.

`poison` and `fire` remain unreachable: nothing in the game deals either
as an injury type. That is the game's vocabulary, not a bug here; the
prose stays for when it does.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.anatomy import SPECIES_DEFINITIONS
from world.medical.medical_messages import (_GENERIC_DEATH_BY_SPECIES,
                                            get_death_cause_template)

CAPACITY_CAUSES = ("blood loss", "heart failure", "respiratory failure",
                   "organ failure", "critical injuries")


def _generic(species):
    return _GENERIC_DEATH_BY_SPECIES.get(species) or _GENERIC_DEATH_BY_SPECIES["human"]


class TestEveryRealCauseHasItsOwnLine(EvenniaTest):
    def test_no_capacity_cause_falls_to_generic_on_any_species(self):
        collapsed = []
        for species in SPECIES_DEFINITIONS:
            for cause in CAPACITY_CAUSES:
                if get_death_cause_template(cause, species) == _generic(species):
                    collapsed.append(f"{species}/{cause}")
        self.assertEqual(collapsed, [])

    def test_unknown_causes_is_still_generic(self):
        """The one cause that should stay generic."""
        self.assertEqual(get_death_cause_template("unknown causes", "human"),
                         _generic("human"))

    def test_the_lines_differ_across_causes(self):
        """Distinct causes must not just share one new line."""
        lines = {get_death_cause_template(c, "human") for c in CAPACITY_CAUSES}
        self.assertEqual(len(lines), len(CAPACITY_CAUSES))


class TestTheBlowReachesTheProse(EvenniaTest):
    def test_a_stab_that_did_not_bleed_out_reads_as_a_stab(self):
        cause = "critical injuries from a stab wound to the chest"
        self.assertEqual(get_death_cause_template(cause, "human"),
                         get_death_cause_template("stab", "human"))

    def test_a_blow_to_the_head_reads_as_a_head_wound(self):
        cause = "critical injuries from blunt trauma to the head"
        self.assertEqual(get_death_cause_template(cause, "human"),
                         get_death_cause_template("head", "human"))

    def test_bleeding_out_from_a_stab_still_reads_as_bleeding_out(self):
        """Physiology keeps precedence: specific prose either way, and
        the knife does not override the pooling blood."""
        cause = "blood loss from a stab wound to the chest"
        self.assertEqual(get_death_cause_template(cause, "human"),
                         get_death_cause_template("blood loss", "human"))


class TestTheKillingBlowIsRecorded(EvenniaTest):
    def _body(self):
        b = create_object("typeclasses.characters.Character", key="a victim",
                          location=self.room1)
        b.msg = lambda text=None, **kw: None
        return b

    def test_a_fatal_stab_is_remembered(self):
        b = self._body()
        b.take_damage(500, "chest", "stab")
        self.assertEqual(dict(b.db.death_blow),
                         {"injury_type": "stab", "location": "chest"})

    def test_and_composed_into_the_cause(self):
        b = self._body()
        b.take_damage(500, "chest", "stab")
        self.assertTrue(b.medical_state.is_dead())
        cause = b.get_death_cause()
        self.assertIn("stab wound", cause)
        self.assertIn("chest", cause)

    def test_a_cut_reads_as_a_slash(self):
        """Chest, not head: head damage lands as unconsciousness, not
        death (`_compute_is_dead`'s own docstring), so a head cut alone
        does not kill and `get_death_cause` returns None for the living."""
        b = self._body()
        b.take_damage(500, "chest", "cut")
        cause = b.get_death_cause()
        self.assertIn("slash", cause)
        self.assertIn("chest", cause)

    def test_the_first_fatal_blow_wins(self):
        b = self._body()
        b.take_damage(500, "chest", "stab")
        b.take_damage(500, "head", "blunt")
        self.assertEqual(b.db.death_blow["injury_type"], "stab")

    def test_a_non_fatal_hit_records_nothing(self):
        b = self._body()
        b.take_damage(1, "left_hand", "cut")
        self.assertFalse(b.db.death_blow)

    def test_no_blow_means_the_plain_cause(self):
        """Bleeding out over time, no recorded blow: the old string."""
        b = self._body()
        state = b.medical_state
        state.blood_level = 0.0
        b.medical_state = state
        b.save_medical_state()
        self.assertEqual(b.get_death_cause(), "blood loss")


class TestTheBleedingNounFollowsTheSpecies(EvenniaTest):
    def _bleeder(self, species):
        from world.medical.conditions import BleedingCondition
        from world.medical.script import start_medical_script
        b = create_object("typeclasses.characters.Character", key="a bleeder",
                          location=self.room1)
        b.db.species = species
        heard = []
        b.msg = lambda text=None, **kw: heard.append(str(text))
        # personal prose only reaches a body with an account
        b.account = self.account
        state = b.medical_state
        state.conditions.append(BleedingCondition(severity=6, location="chest"))
        b.medical_state = state
        b.save_medical_state()
        script = start_medical_script(b)
        self.addCleanup(lambda: script._stop_task())
        return b, script, heard

    def _personal(self, species):
        b, script, heard = self._bleeder(species)
        script._send_medical_messages(6, 0, 0)
        return "\n".join(heard).lower()

    def test_a_robot_is_told_about_fluid_not_blood(self):
        out = self._personal("robot")
        self.assertTrue(out, "no personal line reached the body")
        self.assertIn("hydraulic fluid", out)
        self.assertNotIn("blood", out)

    def test_a_human_is_still_told_about_blood(self):
        out = self._personal("human")
        self.assertTrue(out)
        self.assertIn("blood", out)
        self.assertNotIn("hydraulic", out)
