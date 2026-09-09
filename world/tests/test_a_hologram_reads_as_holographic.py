"""The holographic flag is written where it is read (#2933 sweep).

`is_holographic` is an `AttributeProperty(category="shop")` on
`Character`, and the #2420/#2933 sweep moved the combat guard onto the
property:

    if getattr(target, "is_holographic", False):   # property, not .db

`characters.py` even records why:

    `is_holographic` is an `AttributeProperty(category="shop")`, so
    `self.db.is_holographic` read a different row and was always ...

The prototype was not moved with it. `HOLOGRAPHIC_MERCHANT` writes:

    ("is_holographic", True),

A two-tuple carries NO CATEGORY, so it lands in the uncategorised row
while the property reads the "shop" one. Measured on a freshly spawned
hologram:

    attribute, NO category : True
    attribute, 'shop'      : False
    property  is_holographic -> False
    legacy    db.is_holographic -> True

So the guard never fires and a hologram takes a swing like a real body.

LATENT, not live: there are currently zero holograms in the world, so
nothing is broken today -- it breaks the first time one is spawned,
which is exactly the sort of thing that gets found the hard way. No
migration build is needed for the same reason.

The category is part of the attribute's identity, not decoration. Two
rows named `is_holographic` can hold different values at the same time,
and did.
"""
from evennia.prototypes.spawner import spawn
from evennia.utils.test_resources import EvenniaTest

from world import prototypes as P


class TestASpawnedHologramReadsAsOne(EvenniaTest):

    def test_the_property_sees_it(self):
        holo = spawn("HOLOGRAPHIC_MERCHANT")[0]
        holo.location = self.room1
        self.assertTrue(
            holo.is_holographic,
            "the flag was written to a different row than the one the "
            "combat guard reads")

    def test_the_prototype_names_the_category(self):
        """Pinned on the prototype itself, so a future edit that drops
        the category back to a two-tuple fails here with a reason."""
        attrs = [a for a in P.HOLOGRAPHIC_MERCHANT["attrs"]
                 if a[0] == "is_holographic"]
        self.assertTrue(attrs, "the prototype stopped setting the flag")
        self.assertGreaterEqual(
            len(attrs[0]), 3,
            "a two-tuple carries no category, so it lands in a different "
            "row from the AttributeProperty that reads it")
        self.assertEqual(attrs[0][2], "shop")

    def test_a_plain_character_is_not_holographic(self):
        """Control: the flag must still mean something."""
        self.assertFalse(self.char1.is_holographic)
