"""A blood pool records WHO bled (#2420).

`sleeve_uid` is an `AttributeProperty(category="identity")`, so
`character.db.sleeve_uid` reads a different row and is always `None` on a
Character. `MedicalScript` recorded every bleeding incident through that
`.db` read — live, **326 incidents, zero with a real UID**.

The forensic source-count then fell into its legacy branch and
de-duplicated on the raw `incident['character']` key instead of the
body-identity axis, so two bleeders sharing a key read as one source.

`typeclasses/death_progression.py` already documents this exact trap in a
comment and reads the property correctly. This site did not.

**Found by the same sweep, fixed here too:** `is_holographic` is an
`AttributeProperty(category="shop")` and both readers used `.db`, so the
"holographic merchants cannot be attacked" guard has never fired. Latent
rather than live — nothing sets the flag either way — but it is the same
shadowing family.

The sweep also confirmed what is NOT a defect: `Corpse`, `SeveredHead`
and `Appendage` are not Characters, so they have no shadowing property
and `.db.sleeve_uid` / `.db.worn_items` are their correct storage.
"""
from evennia.utils.test_resources import EvenniaTest


class TestTheBleederIsRecorded(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.bleeder = self.char1
        self.bleeder.location = self.room1

    def test_the_property_and_the_db_row_are_different(self):
        """The trap itself, pinned once."""
        self.bleeder.sleeve_uid = "sleeve-real"
        self.assertIsNone(self.bleeder.db.sleeve_uid)
        self.assertEqual(self.bleeder.sleeve_uid, "sleeve-real")

    def test_the_incident_carries_the_real_uid(self):
        import inspect
        from world.medical import script
        src = inspect.getsource(script)
        code = "\n".join(l for l in src.splitlines()
                         if not l.strip().startswith("#"))
        self.assertNotIn("self.obj.db.sleeve_uid", code)

    def test_the_signature_still_carries_it_too(self):
        """The backfill depends on this: `signature[0]` is documented as
        the character's real `sleeve_uid`, read through the property."""
        from world.identity import get_identity_signature
        self.bleeder.sleeve_uid = "sleeve-real"
        self.assertEqual(get_identity_signature(self.bleeder)[0],
                         "sleeve-real")


class TestTheHolographicGuardCanFire(EvenniaTest):
    """It read `.db.is_holographic`, a row that is always None on a
    Character, so it never fired once."""

    def test_a_holographic_merchant_is_refused(self):
        merchant = self.char2
        merchant.is_holographic = True
        self.assertIsNotNone(merchant.validate_attack_target())

    def test_an_ordinary_character_is_not(self):
        self.assertIsNone(self.char2.validate_attack_target())

    def test_the_db_row_alone_does_not_protect_anyone(self):
        """Pinning the shadowing: writing the bare row must NOT read as
        holographic, or the two rows have silently merged."""
        merchant = self.char2
        merchant.attributes.add("is_holographic", True)
        self.assertIsNone(merchant.validate_attack_target())


class TestTheNonCharacterStoresAreLeftAlone(EvenniaTest):
    """`Corpse`/`SeveredHead`/`Appendage` have no shadowing property, so
    `.db` IS their storage. The sweep must not have 'fixed' those."""

    def test_a_corpse_keeps_its_db_sleeve_uid(self):
        import inspect
        from typeclasses import corpse
        self.assertIn("self.db.sleeve_uid", inspect.getsource(corpse))
