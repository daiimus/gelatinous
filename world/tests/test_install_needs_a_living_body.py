"""Installing an organ needs somewhere for it to live (#2507), and a
refused consumption is not a consumption (#2513).

## #2507 — the missing guard

Three of the four install resolvers refuse a target with no
`medical_state` and return WITHOUT consuming the item:

```python
state = getattr(target, "medical_state", None)
if state is None or not getattr(state, "organs", None):
    actor.msg(f"The {organ_item.key} needs a living body to reattach to.")
    return
```

`_resolve_install` — the plain-organ one — instead wrapped its install
block in `if state is not None:` and fell straight through it. Everything
after that block ran regardless: the pain seed, the success line to the
actor, the room broadcast, and `organ_item.delete()`.

Corpses and severed parts are admitted targets *by design* — the module
docstring says procedures act on "living characters, corpses, severed
heads, and severed limbs", and `_is_body_container` passes them because
they carry organ snapshots. So a surgeon could feed a harvested heart
into a corpse, be told it worked, watch the room be told it worked, and
have the heart cease to exist.

## #2513 — the refusal reported as a success

`use_item` branched only on `outcome["destroyed"]`, never on
`outcome["success"]`. A `consume_use` that declined — writing nothing —
came back as `{"success": True, "destroyed": False}` with a fabricated
uses message.

The default mismatch the issue leads with (`1` in the wrapper, `0` in
the core) was already settled in #2812: missing means ONE on both
sides. What was left is the unread flag, plus the two reads that could
drift apart again — both now go through one helper, which also survives
a stored `None` that made the bare `uses_left <= 0` raise TypeError.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class _InstallCase(EvenniaTest):
    def organ_item(self, key="a heart"):
        item = create_object("typeclasses.items.Organ", key=key,
                             location=self.char1)
        item.db.organ_name = "heart"
        item.db.condition = "pristine"
        return item

    def install(self, target, item, location="chest"):
        from world.medical.procedures import _resolve_install
        said = []
        self.char1.msg = lambda text=None, **kw: said.append(str(text))
        _resolve_install(self.char1, target, organ_item=item,
                         location=location)
        return "\n".join(said)


class TestACorpseIsNotSomewhereToInstall(_InstallCase):
    def corpse(self):
        return create_object("typeclasses.corpse.Corpse", key="a corpse",
                             location=self.room1)

    def test_the_organ_survives(self):
        item = self.organ_item()
        self.install(self.corpse(), item)
        self.assertTrue(item.pk, "the install deleted the organ")

    def test_it_stays_in_your_hands(self):
        item = self.organ_item()
        self.install(self.corpse(), item)
        self.assertEqual(item.location, self.char1)

    def test_it_does_not_claim_success(self):
        out = self.install(self.corpse(), self.organ_item())
        self.assertNotIn("You install", out)

    def test_it_says_why(self):
        out = self.install(self.corpse(), self.organ_item())
        self.assertIn("living body", out)

    def test_a_severed_limb_is_refused_too(self):
        limb = create_object("typeclasses.items.Appendage",
                             key="a severed left arm", location=self.room1)
        item = self.organ_item()
        self.install(limb, item)
        self.assertTrue(item.pk)


class TestALivingBodyStillTakesTheOrgan(_InstallCase):
    """The guard must not close the door it exists to narrow."""

    def test_a_living_target_still_installs(self):
        from unittest import mock
        item = self.organ_item()
        self.char2.location = self.room1
        # the cavity the install needs, opened directly
        self.char2.db.surgical_state = {
            "incisions": {"chest": True}, "active_procedure": None}
        with mock.patch("world.medical.procedures.roll_procedure",
                        return_value={"outcome": "success", "margin": 5}):
            out = self.install(self.char2, item)
        self.assertIn("You install", out)

    def test_and_the_organ_item_is_consumed(self):
        from unittest import mock
        item = self.organ_item()
        self.char2.location = self.room1
        self.char2.db.surgical_state = {
            "incisions": {"chest": True}, "active_procedure": None}
        with mock.patch("world.medical.procedures.roll_procedure",
                        return_value={"outcome": "success", "margin": 5}):
            self.install(self.char2, item)
        self.assertFalse(item.pk)


class TestARefusedUseIsNotAUse(EvenniaTest):
    def medical(self, key="a bandage", **attrs):
        item = create_object("typeclasses.items.Item", key=key,
                             location=self.char1)
        item.tags.add("medical_item", category="item_type")
        for name, value in attrs.items():
            item.attributes.add(name, value)
        return item

    def test_an_empty_item_is_refused(self):
        from world.medical.utils import use_item
        item = self.medical(uses_left=0, max_uses=3)
        self.assertFalse(use_item(item)["success"])

    def test_a_missing_count_still_means_one_use(self):
        """Settled in #2812 — pinned so the two sides cannot drift."""
        from world.medical.utils import can_be_used, use_item
        item = self.medical(max_uses=1)
        self.assertTrue(can_be_used(item))
        self.assertTrue(use_item(item)["success"])

    def test_a_stored_none_does_not_raise(self):
        """`None <= 0` is a TypeError, and this used to be a bare
        comparison."""
        from world.medical.utils import can_be_used, use_item
        item = self.medical(uses_left=None, max_uses=2)
        self.assertFalse(can_be_used(item))
        self.assertFalse(use_item(item)["success"])

    def test_a_real_use_still_decrements(self):
        from world.medical.utils import use_item
        item = self.medical(uses_left=3, max_uses=3)
        self.assertTrue(use_item(item)["success"])
        self.assertEqual(item.attributes.get("uses_left"), 2)

    def test_the_last_use_destroys_it(self):
        from world.medical.utils import use_item
        item = self.medical(uses_left=1, max_uses=1)
        result = use_item(item)
        self.assertTrue(result["success"])
        self.assertTrue(result["destroyed"])
        self.assertFalse(item.pk)

    def test_a_refusal_from_the_core_is_not_dressed_up_as_success(self):
        """The unread flag, driven directly: `consume_use` declines and
        writes nothing, and the wrapper used to answer
        `{"success": True}` with a uses message it made up."""
        from unittest import mock
        from world.medical.utils import use_item
        item = self.medical(uses_left=3, max_uses=3)
        with mock.patch("world.consumables.consume_use",
                        return_value={"success": False,
                                      "destroyed": False}):
            result = use_item(item)
        self.assertFalse(result["success"])
        self.assertNotIn("uses)", result["message"])
