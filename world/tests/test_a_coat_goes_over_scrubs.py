"""A lab coat goes OVER scrubs, and a windbreaker does too (#3087).

The numbers are asserted next door in
`test_prototype_layers_match_the_ladder`. This asserts the BEHAVIOUR
they exist for, because the numbers were "right" twice while the
clothing was broken:

  * #3054 aligned `LAB_COAT` to its derived rung 4 -- correct by the
    ladder, and it collided with `MEDICAL_SCRUBS`, also rung 4.
  * #3087 (mine) pinned `LAB_COAT` to 5 -- which un-broke the clinic
    aide and broke the ladder test instead, because an explicit layer
    disagreeing with derivation is the exact drift #3054 removed.

Neither test could see the other's failure, and both were "green" from
where I was standing. The thing that actually matters is whether the
garments go on, so that is what this asks, through `wear_item` -- the
rule's real owner -- rather than by comparing integers.

The clinic aide's wardrobe is `MEDICAL_SCRUBS` plus EITHER `LAB_COAT`
(rung 4) or `COMPANY_WINDBREAKER` (rung 3), so both have to clear the
scrubs. The windbreaker is the case that proves scrubs were the problem
rather than the coat: at rung 4 the coat collided at the SAME layer,
but the windbreaker was refused for going UNDER -- one garment on the
wrong rung, two different refusals.
"""
from evennia.utils.test_resources import EvenniaTest
from evennia.prototypes.spawner import spawn

from world import prototypes as P
from world.style import derive_rung


class TestScrubsAreABaseGarment(EvenniaTest):

    def test_scrubs_derive_below_every_garment_worn_over_them(self):
        scrubs = derive_rung(P.MEDICAL_SCRUBS["key"])
        for over in (P.LAB_COAT, P.COMPANY_WINDBREAKER):
            self.assertLess(
                scrubs, derive_rung(over["key"]),
                f"{over['prototype_key']} cannot be worn over scrubs")

    def test_the_prototype_agrees_with_the_ladder(self):
        """No override: the LADDER was moved, not the prototype pinned."""
        for proto in (P.MEDICAL_SCRUBS, P.LAB_COAT):
            attrs = dict((a[0], a[1]) for a in proto["attrs"] if len(a) >= 2)
            self.assertEqual(attrs["layer"], derive_rung(proto["key"]),
                             proto["prototype_key"])


class TestTheAideCanActuallyGetDressed(EvenniaTest):
    """Through `wear_item`, which owns the layering rule."""

    def _dress(self, *proto_keys):
        worn = []
        for key in proto_keys:
            item = spawn(key)[0]
            item.location = self.char1
            ok, _msg = self.char1.wear_item(item)
            if ok:
                worn.append(item.key)
        return worn

    def test_a_lab_coat_goes_on_over_scrubs(self):
        worn = self._dress("MEDICAL_SCRUBS", "LAB_COAT")
        self.assertEqual(len(worn), 2,
                         f"only got {worn} on -- a garment was refused")

    def test_a_windbreaker_goes_on_over_scrubs(self):
        worn = self._dress("MEDICAL_SCRUBS", "COMPANY_WINDBREAKER")
        self.assertEqual(len(worn), 2,
                         f"only got {worn} on -- a garment was refused")

    def test_putting_the_coat_on_first_refuses_the_scrubs_by_design(self):
        """Order DOES matter, and that is the system working.

        Written the other way round first, asserting both go on in
        either order -- which failed, correctly. You cannot put a base
        layer on underneath a coat you are already wearing without
        taking the coat off, and `wear_item` says so. Kept as the
        negative case so the next person does not "fix" the refusal:
        the bug was never that an inner garment is refused under an
        outer one, it was that scrubs were classed as OUTERWEAR.
        """
        coat = spawn("LAB_COAT")[0]
        coat.location = self.char1
        self.char1.wear_item(coat)
        scrubs = spawn("MEDICAL_SCRUBS")[0]
        scrubs.location = self.char1
        ok, msg = self.char1.wear_item(scrubs)
        self.assertFalse(ok)
        self.assertIn("under", msg.lower())
