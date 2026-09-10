"""A single-use auto-injector must be injectable.

Regression pin for #3207.  `STIMPAK`'s desc calls it a "single-use
auto-injector", one of its aliases is "healing injection", and
`world/clinic.py`'s `CLINIC_SUPPLIES` dispatches both "stim" and
"stimpak" with the verb `inject`.  The prototype carried no
`delivery_method` tag, and its `medical_type` (`healing_acceleration`)
was absent from `LEGACY_MEDICAL_TYPE_DELIVERIES`, so `supports_delivery`
answered False for **every** verb — inject, apply, eat, drink, bandage,
inhale, smoke.  The item was dead in the hand while two shops sold it
for 150 and 350 credits.

Fixed in two places on purpose, because they reach different
populations:

* the prototype declares the tag — correct for everything spawned from
  now on;
* the legacy map gains the `medical_type` — which is what reaches the
  three copies ALREADY in the world, since a prototype fix reaches
  nothing already spawned.
"""

from __future__ import annotations

from unittest import TestCase

from world import consumables
from world.consumables import (
    DELIVERY_METHOD_CATEGORY,
    LEGACY_MEDICAL_TYPE_DELIVERIES,
    supports_delivery,
)
from world.prototypes import STIMPAK, STIMPAK_INHALER

ALL_VERBS = ("inject", "apply", "eat", "drink", "bandage", "inhale", "smoke")


class _Tags:
    """Minimal Evennia tag-handler surface."""

    def __init__(self, pairs=()):
        self._pairs = set(pairs)

    def has(self, key, category=None):
        return (key, category) in self._pairs

    def add(self, key, category=None):
        self._pairs.add((key, category))


class _Attrs:
    def __init__(self, values):
        self._values = dict(values)

    def get(self, key, default=None):
        return self._values.get(key, default)


class _Item:
    """A spawned item: tags plus attributes, nothing else."""

    def __init__(self, *, tags=(), medical_type=None):
        self.tags = _Tags(tags)
        self.attributes = _Attrs({"medical_type": medical_type})


def _proto_delivery(proto):
    return {t[0] for t in proto.get("tags", ()) if len(t) > 1
            and t[1] == "delivery_method"}


def _proto_attr(proto, name):
    return next((a[1] for a in proto.get("attrs", ()) if a[0] == name), None)


class TestAStimpakIsAnInjector(TestCase):

    # -- the prototype, for everything spawned from now on ----------

    def test_the_prototype_declares_inject(self):
        self.assertIn(
            "inject", _proto_delivery(STIMPAK),
            "a single-use auto-injector must declare the inject delivery",
        )

    def test_the_inhaler_sibling_is_unchanged(self):
        """Control: the correctly-tagged sibling stays as it was."""
        self.assertEqual(_proto_delivery(STIMPAK_INHALER), {"inhale"})

    def test_a_freshly_spawned_stimpak_can_be_injected(self):
        fresh = _Item(
            tags=[(t[0], t[1]) for t in STIMPAK["tags"]],
            medical_type=_proto_attr(STIMPAK, "medical_type"),
        )
        self.assertTrue(supports_delivery(fresh, "inject"))

    # -- the legacy map, for the copies already in the world --------

    def test_an_already_spawned_stimpak_self_heals(self):
        """The three live copies carry NO delivery tag at all.

        A prototype fix reaches nothing already spawned; the legacy map
        is what migrates them, on first use, as its docstring promises.
        """
        banked = _Item(
            tags=[("medical_item", "item_type")],
            medical_type="healing_acceleration",
        )
        self.assertTrue(
            supports_delivery(banked, "inject"),
            "a stimpak already in the world stayed unusable",
        )
        # And the migration is written back, not recomputed every call.
        self.assertTrue(banked.tags.has("inject", DELIVERY_METHOD_CATEGORY))

    def test_the_legacy_map_covers_the_declared_medical_type(self):
        self.assertEqual(
            LEGACY_MEDICAL_TYPE_DELIVERIES.get("healing_acceleration"),
            ("inject",),
        )

    # -- controls: the gate must still refuse -----------------------

    def test_a_stimpak_is_not_edible_or_applicable(self):
        """The negative control. One verb, not a free pass to all."""
        fresh = _Item(
            tags=[(t[0], t[1]) for t in STIMPAK["tags"]],
            medical_type=_proto_attr(STIMPAK, "medical_type"),
        )
        for verb in ALL_VERBS:
            with self.subTest(verb):
                self.assertIs(
                    supports_delivery(fresh, verb), verb == "inject",
                )

    def test_an_unknown_medical_type_still_supports_nothing(self):
        """The map must not have become a blanket fallback."""
        odd = _Item(tags=[("medical_item", "item_type")],
                    medical_type="not_a_real_type")
        for verb in ALL_VERBS:
            with self.subTest(verb):
                self.assertFalse(supports_delivery(odd, verb))

    def test_the_surgical_kit_stays_unreachable_by_a_delivery_verb(self):
        """A tool is not a consumable — the sweep's other near-miss."""
        kit = _Item(tags=[("medical_item", "item_type")],
                    medical_type="surgical_treatment")
        for verb in ALL_VERBS:
            with self.subTest(verb):
                self.assertFalse(supports_delivery(kit, verb))
