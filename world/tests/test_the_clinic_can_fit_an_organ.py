"""The clinic can fit a replacement organ, and a stump yields nothing
twice (#2455).

**The clinic asked the wrong thing.** `build_install_chart` read the
mount point off the ITEM — `augment_anchor` / `augment_container` — and
bailed when it found neither. A LIMB augment declares where it bolts on
(`CYBER_ARM` → `{side}_arm`), but a REPLACEMENT ORGAN does not and
never did: its mount point is wherever the organ it replaces already
sits on THIS body. That is exactly what the working door does —
`_resolve_install` looks `organ_name` up in the patient's own organ
snapshot and takes that slot's container.

So 5 of the 7 words in `CLINIC_CYBERWARE` — heart, eye, ear, kidney,
jaw — resolved to None. The NPC gave no spoken reply, no surgery was
laid out, and the request evaporated in silence, while every attempt
left a spawned cyber organ in the doctor's pockets with no cleanup
path. Only `CYBER_ARM` and `CYBERNETIC_TAIL` carry an anchor, which is
why the one test of this bridge drives "cyber arm left" and stayed
green.

**The stump yielded a second set of everything.** `sever_character_body`
leaves every organ of a departed limb in `medical_state.organs` at 0 HP
with `wound_stage="severed"`, while a copy travels in the Appendage's
own snapshot. The typed `harvest` verb refuses both cases — a severed
container and a 0-HP organ — but the operate chart's picker filtered
only `removed_organs`, so the stump offered a second, identical set of
the organs and modules that had already left with the limb. Duplicated
chrome, and chrome is what the Ripper appraisal and the parts trade are
priced on. Two doors onto one decision, and only one refused.

**Eight clinic tests had been red on master since #2474** and are
repaired here. That change made the bottomless draw a POST perk — no
post, no stock — and the fixtures never gave their doctor a post, so
every `draw_supply` returned None. Production was right; the fixtures
were stale.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world import clinic


class _ClinicCase(EvenniaTest):
    def doctor(self, key="Doc"):
        doc = create_object("typeclasses.llm_npc.LLMNpc", key=key,
                            location=self.room1)
        doc.db.soul_post = self.room1     # the draw is a post perk
        return doc

    def patient(self, key="Pat"):
        return create_object("typeclasses.characters.Character", key=key,
                             location=self.room1)


class TestReplacementOrgansCanBeFitted(_ClinicCase):
    """The five words that used to evaporate in silence."""

    def _chart(self, what):
        return clinic.build_install_chart(self.doctor(), self.patient(), what)

    def test_a_heart(self):
        self.assertIsNotNone(self._chart("a new heart"))

    def test_an_eye(self):
        self.assertIsNotNone(self._chart("right eye"))

    def test_an_ear(self):
        self.assertIsNotNone(self._chart("left ear"))

    def test_a_kidney(self):
        self.assertIsNotNone(self._chart("kidney"))

    def test_a_jaw(self):
        self.assertIsNotNone(self._chart("jaw"))

    def test_the_chart_still_reads_incise_install_suture(self):
        chart = self._chart("a new heart")
        self.assertEqual([s["verb"] for s in chart["steps"]],
                         ["incise", "install", "suture"])

    def test_it_opens_the_slot_the_organ_actually_lives_in(self):
        """Not an anchor off the item — the patient's own container."""
        chart = self._chart("a new heart")
        self.assertEqual(chart["steps"][0]["args"]["location"], "chest")


class TestTheLimbAugmentPathIsUnchanged(_ClinicCase):
    def test_a_cyber_arm_still_lays_out(self):
        chart = clinic.build_install_chart(
            self.doctor(), self.patient(), "cyber arm left")
        self.assertIsNotNone(chart)

    def test_it_still_uses_the_items_own_anchor(self):
        chart = clinic.build_install_chart(
            self.doctor(), self.patient(), "cyber arm left")
        self.assertIn("arm", chart["steps"][0]["args"]["location"])


class TestAFailedRequestLeavesNoStockBehind(_ClinicCase):
    def test_an_unknown_request_draws_nothing(self):
        doc = self.doctor()
        before = len(doc.contents)
        self.assertIsNone(
            clinic.build_install_chart(doc, self.patient(), "nanite cloud"))
        self.assertEqual(len(doc.contents), before)

    def test_a_patient_with_no_such_slot_keeps_the_doctors_pockets_empty(self):
        """A body with no heart slot cannot take a heart — and the part
        must not stay in the surgeon's coat."""
        doc = self.doctor()
        pat = self.patient()
        pat.medical_state.organs.clear()
        before = len(doc.contents)
        clinic.build_install_chart(doc, pat, "a new heart")
        self.assertLessEqual(len(doc.contents), before)


class TestAStumpYieldsNothingTwice(EvenniaTest):
    def _target(self):
        target = create_object("typeclasses.characters.Character",
                               key="Victim", location=self.room1)
        return target

    def _listed(self, target):
        from commands.CmdOperate import _list_organs
        return {name for name, _container in _list_organs(target)}

    def test_a_healthy_body_still_offers_its_organs(self):
        target = self._target()
        self.assertTrue(self._listed(target))

    def test_an_organ_in_a_severed_container_is_not_offered(self):
        target = self._target()
        listed_before = self._listed(target)
        container = None
        for name, data in (target.medical_state.organs or {}).items():
            container = getattr(data, "container", None)
            if container:
                break
        target.db.severed_locations = [container]
        gone = listed_before - self._listed(target)
        self.assertTrue(gone, f"nothing was withheld for severed {container}")

    def test_a_pulped_organ_is_not_offered(self):
        target = self._target()
        name = next(iter(target.medical_state.organs))
        target.medical_state.organs[name].current_hp = 0
        self.assertNotIn(name, self._listed(target))

    def test_the_typed_verb_and_the_chart_now_agree(self):
        """The defect in one sentence: `harvest` refused, `operate`
        allowed."""
        import inspect
        from commands import CmdOperate
        source = inspect.getsource(CmdOperate._list_organs)
        self.assertIn("severed_locations", source)
        self.assertIn("current_hp", source)
