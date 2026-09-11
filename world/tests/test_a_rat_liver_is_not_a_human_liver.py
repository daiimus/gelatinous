"""A harvested organ only grafts into the species it came from.

Regression pin for #3070.  `_resolve_install` — the plain biological
organ path — performed **no species check of any kind**.  A rat liver
grafted into a person on any successful roll, and a human liver into a
rat.  Both directions, and the human->rat one predates the rat harvest
work entirely: a human liver carries `can_be_harvested` AND
`can_be_replaced`, and rats have a liver slot.

The gate existed everywhere else.  `_resolve_install_augment` checks,
`_resolve_install_module` checks, and `CmdOperate`'s install picker
checks when listing donors — only the flesh path did not.  The fact was
already on the item: the harvest writer stamps
`compatible_species = [source species]` on every organ it cuts out.
Nobody read it.

**A refusal is not a roll failure.**  `roll_procedure`'s failure branch
says "The graft won't take", which reads exactly like a compatibility
refusal, so a small sample of failed rolls looks like a working gate --
the reporter measured 0/11 cross-species installs before one landed and
nearly filed this as "gated, working".  Every test below forces the roll
so the dice cannot be mistaken for the gate, and the refusal message
names the species so a player can tell the two apart.

Legacy fallback mirrors the picker's convention exactly, so the two
doors cannot disagree about the same organ:

    compatible_species  ->  else [source_species]  ->  else REFUSE

An organ carrying neither field is REFUSED -- strict, matching the
cyberware gate (owner call, 2026-09-10). Measured free before
tightening: all 22 organ items in the world carry provenance, and no
prototype can spawn one without it. The middle rung is load-bearing
though -- `#2352 human liver` lives on it.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from world.medical.procedures import _resolve_install, open_incision

from world.tests.test_anatomy_augments import _patient, _surgeon


def _organ(*, key="liver", organ_name="liver", **db):
    """A harvested organ, shaped as the harvest writer leaves one."""
    item = SimpleNamespace()
    item.key = key
    item.deleted = False
    def _delete():
        item.deleted = True
    item.delete = _delete
    item.db = SimpleNamespace(
        organ_name=organ_name,
        condition="pristine",
        organ_conditions=[],
        **db,
    )
    item.get_display_name = lambda looker=None: item.key
    return item


def _install(target, item, location="abdomen", outcome="success"):
    actor = _surgeon()
    with patch("world.medical.procedures.roll_procedure",
               return_value={"outcome": outcome}):
        _resolve_install(actor, target, organ_item=item, location=location)
    return actor


def _wrecked_liver(patient):
    """A slot that WANTS a replacement, so nothing but species refuses."""
    organ = patient.medical_state.organs.get("liver")
    if organ is not None:
        organ.current_hp = 0
    open_incision(patient, "abdomen", surgeon=None)
    return patient


class TestARatLiverIsNotAHumanLiver(TestCase):

    def _said(self, actor):
        return " ".join(actor.messages)

    # -- the defect, both directions ---------------------------------

    def test_a_rat_liver_does_not_graft_into_a_person(self):
        pat = _wrecked_liver(_patient("human"))
        item = _organ(key="rat liver", compatible_species=["rat"],
                      source_species="rat")
        actor = _install(pat, item)
        self.assertIn("human", self._said(actor).lower())
        self.assertFalse(
            item.deleted,
            "the rat liver was consumed into a human abdomen",
        )

    def test_a_human_liver_does_not_graft_into_a_rat(self):
        """The direction that predates the rat harvest work."""
        pat = _wrecked_liver(_patient("rat"))
        item = _organ(key="human liver", compatible_species=["human"],
                      source_species="human")
        actor = _install(pat, item)
        self.assertIn("rat", self._said(actor).lower())
        self.assertFalse(item.deleted)

    # -- controls: the gate must not refuse what it should allow -----

    def test_a_human_liver_still_grafts_into_a_person(self):
        """The positive control. Without it a gate that refuses
        EVERYTHING would pass every test above."""
        pat = _wrecked_liver(_patient("human"))
        item = _organ(key="human liver", compatible_species=["human"],
                      source_species="human")
        actor = _install(pat, item)
        said = self._said(actor).lower()
        self.assertNotIn("isn't", said)
        self.assertIn("install", said)

    def test_a_multi_species_organ_grafts_into_either(self):
        """Cyberware declares a wider list; it must still pass."""
        for species in ("human", "rat"):
            with self.subTest(species):
                pat = _wrecked_liver(_patient(species))
                item = _organ(key="cyber liver",
                              compatible_species=["human", "rat"])
                actor = _install(pat, item)
                self.assertNotIn("isn't", self._said(actor).lower())

    # -- the legacy ladder -------------------------------------------

    def test_source_species_alone_still_gates(self):
        """An organ with provenance but no compatibility list."""
        pat = _wrecked_liver(_patient("human"))
        item = _organ(key="rat liver", source_species="rat")
        actor = _install(pat, item)
        self.assertIn("human", self._said(actor).lower())
        self.assertFalse(item.deleted)

    def test_an_organ_with_no_provenance_is_refused(self):
        """STRICT, as the cyberware gate is (owner call).

        An organ that cannot say what it came from does not go into
        anybody. Free at the time of writing: all 22 organ items in
        the world carry provenance, and no prototype can spawn one
        without it.
        """
        pat = _wrecked_liver(_patient("human"))
        item = _organ(key="old liver")
        actor = _install(pat, item)
        self.assertIn("isn't", self._said(actor).lower())
        self.assertFalse(item.deleted)

    def test_source_species_alone_is_enough_to_PASS(self):
        """The fallback rung is not decoration.

        `#2352 human liver` is live right now with
        `compatible_species = None` and `source_species = 'human'`.
        Reading only the first field would refuse a good organ sitting
        in the world.
        """
        pat = _wrecked_liver(_patient("human"))
        item = _organ(key="human liver", source_species="human")
        actor = _install(pat, item)
        self.assertNotIn("isn't", self._said(actor).lower())

    # -- the trap the issue warns about ------------------------------

    def test_a_failed_roll_is_not_a_species_refusal(self):
        """Two different outcomes must read differently.

        `roll_procedure`'s failure branch is what made this defect look
        gated for eleven attempts running.
        """
        pat = _wrecked_liver(_patient("human"))
        item = _organ(key="human liver", compatible_species=["human"])
        actor = _install(pat, item, outcome="failure")
        said = self._said(actor).lower()
        self.assertNotIn("anatomy", said,
                         "a failed roll must not claim a species mismatch")
