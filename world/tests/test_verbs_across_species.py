"""One act, two vocabularies, one command (#2278).

`operate` works as an umbrella because the KEY commits to neither meat
nor metal while the prose underneath commits to exactly one. The other
verbs didn't have that property: `suture` is meat in the command word
itself, and a mechanic had to type it at a chassis.

`sever`/`amputate` and `inspect`/`autopsy` already had the shape --
neutral primary, flavoured alias. This finishes it everywhere, and
purely by addition: every existing key still works.
"""
from evennia.utils.test_resources import EvenniaCommandTest

from commands import CmdConsumption, CmdSurgical, forensics
from world.medical.charts import gerund_for, verb_for


class TestYouCanSayItEitherWay(EvenniaCommandTest):
    def test_every_key_still_works(self):
        """Additive means additive. Nothing that worked stops."""
        for cls, key in ((CmdSurgical.CmdIncise, "incise"),
                         (CmdSurgical.CmdHarvest, "harvest"),
                         (CmdSurgical.CmdInstall, "install"),
                         (CmdSurgical.CmdSuture, "suture"),
                         (forensics.CmdSever, "sever"),
                         (CmdConsumption.CmdBandage, "bandage")):
            with self.subTest(key=key):
                self.assertEqual(cls.key, key)

    def test_the_machine_words_are_there(self):
        for cls, word in ((CmdSurgical.CmdIncise, "cut"),
                          (CmdSurgical.CmdHarvest, "extract"),
                          (CmdSurgical.CmdInstall, "fit"),
                          (CmdSurgical.CmdSuture, "seal"),
                          (forensics.CmdSever, "shear"),
                          (CmdConsumption.CmdBandage, "patch")):
            with self.subTest(word=word):
                self.assertIn(word, cls.aliases)

    def test_the_organic_words_survived(self):
        self.assertIn("stitch", CmdSurgical.CmdSuture.aliases)
        self.assertIn("amputate", forensics.CmdSever.aliases)
        self.assertIn("wrap", CmdConsumption.CmdBandage.aliases)

    def test_no_two_commands_claim_the_same_word(self):
        """A duplicate key silently shadows one command. Cheap to
        check, miserable to debug."""
        import ast, pathlib, re
        seen = {}
        for f in sorted(pathlib.Path("commands").glob("*.py")):
            src = f.read_text()
            for m in re.finditer(r'^class (Cmd\w+)\(.*?\):(.*?)(?=^class |\Z)',
                                 src, re.S | re.M):
                body = m.group(2)
                words = []
                k = re.search(r'^\s{4}key\s*=\s*["\']([^"\']+)', body, re.M)
                if k:
                    words.append(k.group(1))
                a = re.search(r'^\s{4}aliases\s*=\s*(\[[^\]]*\]|\([^)]*\))',
                              body, re.M)
                if a:
                    try:
                        words += list(ast.literal_eval(a.group(1)) or [])
                    except Exception:
                        pass
                for w in words:
                    seen.setdefault(w, []).append(m.group(1))
        for word in ("cut", "extract", "fit", "graft", "seal", "shear",
                     "patch"):
            with self.subTest(word=word):
                self.assertEqual(len(seen.get(word, [])), 1,
                                 f"{word!r} claimed by {seen.get(word)}")


class TestTheProseFollowsTheBody(EvenniaCommandTest):
    def test_a_person_is_sutured(self):
        self.assertEqual(gerund_for("suture", "human"), "suturing")

    def test_a_chassis_is_sealed(self):
        self.assertEqual(gerund_for("suture", "robot"), "sealing")

    def test_the_chart_and_the_command_agree(self):
        """Two routes into one act must not describe it differently.
        The chart says 'seal'; the command must not say 'suture'."""
        self.assertEqual(verb_for("suture", "robot"), "seal")
        self.assertTrue(gerund_for("suture", "robot").startswith("seal"))

    def test_cutting_into_reads_for_both(self):
        """Already true by accident before this change; locked in now
        so nobody 'fixes' it into 'incising'."""
        self.assertEqual(gerund_for("incise", "human"), "cutting into")
        self.assertEqual(gerund_for("incise", "robot"), "cutting into")

    def test_an_unknown_species_reads_organically(self):
        self.assertEqual(gerund_for("suture", "rat"), "suturing")
        self.assertEqual(gerund_for("suture", None), "suturing")


class TestInstrumentsAreSpeciesSpecific(EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        from evennia.prototypes.spawner import spawn
        from world import prototypes
        self.kit = spawn(prototypes.SURGICAL_KIT)[0]
        self.roll = spawn(prototypes.TOOL_ROLL)[0]
        self.bot = self.char2
        self.bot.db.species = "robot"
        self.char1.db.species = "human"

    def test_a_surgical_kit_no_longer_opens_a_chassis(self):
        self.kit.move_to(self.char1, quiet=True, move_hooks=False)
        self.assertIsNone(CmdSurgical._find_surgical_kit(self.char1, self.bot))

    def test_the_tool_roll_does(self):
        self.roll.move_to(self.char1, quiet=True, move_hooks=False)
        self.assertIs(CmdSurgical._find_surgical_kit(self.char1, self.bot),
                      self.roll)

    def test_and_the_tool_roll_does_not_open_a_person(self):
        self.roll.move_to(self.char1, quiet=True, move_hooks=False)
        self.assertIsNone(
            CmdSurgical._find_surgical_kit(self.char1, self.char1))

    def test_the_refusal_names_what_to_fetch(self):
        """'You need a surgical kit' while holding a surgical kit is
        the least useful refusal we could write."""
        self.assertEqual(CmdSurgical._instruments_wanted(self.bot),
                         "a tool roll")
        self.assertEqual(CmdSurgical._instruments_wanted(self.char1),
                         "a surgical kit")

    def test_no_target_keeps_the_old_behaviour(self):
        """Any caller not yet updated is unchanged, not broken."""
        self.kit.move_to(self.char1, quiet=True, move_hooks=False)
        self.assertIs(CmdSurgical._find_surgical_kit(self.char1), self.kit)
