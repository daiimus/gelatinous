"""Visible chrome, and a stopword set built from words (#2587, #2583).

## #2587 — an internal implant chromed the whole region

`_location_is_inorganic` accepted a match on an organ's **container**
*or* its **display_location**. `container` is the anatomical region an
organ lives *inside*; `display_location` is the surface it renders on.
Accepting either conflated *"there is chrome visible here"* with *"there
is chrome somewhere in here."*

Measured on **Jericho Black III**, a real character, comparing the old
predicate against the new across every location on the body:

```
chest      True  -> False     (a cyber HEART, buried in it)
head       True  -> False     (a chrome JAW, which shows on the FACE)
face       True  -> True      (the jaw does show here)
right_arm  True  -> True      (chrome humerus + forearm hardpoint)
right_hand True  -> True      (chrome metacarpals)
```

Exactly the two wrong surfaces flip. Nothing that is genuinely visible
chrome stops being chrome.

**Dropping the container match alone would not have been enough.**
`display_location` **defaults to** `container` (`core.py`:
`data.get("display_location") or self.container`), so the cyber heart
reads `display_location == "chest"` and would still have chromed the
chest it is buried in.

The discriminator for that already existed —
`diagnose._is_internal_organ`: *"lives in a body cavity and has no
separate surface display"*. Reused rather than re-derived, so "is this
organ visible from outside" has one answer.

## #2583 — the pose stopword set was built from a tuple's repr

```python
_NOT_A_LEADING_VERB = frozenset((
    "the a an this ...",
    ...
).__str__().split())
```

The comma-separated literal is a **tuple**, and `__str__()` renders its
*repr* — quotes, commas and parentheses included. Splitting that gives
tokens like `('the`, `our',`, `'one`, `barely')`.

The set still had **57 entries either way**, which is exactly why it
looked right. Ten real stopwords fell out and ten pieces of junk took
their place:

```
missing: and around at barely neither one our still the under
```

Every NPC pose beginning with one of those ten got an `-s` welded on by
the conjugator — *"thes rag"*, *"stills watching him"*, *"ands turns"*.
"""
from evennia.utils.test_resources import EvenniaTest


class TestTheStopwordsAreWords(EvenniaTest):
    def _set(self):
        from typeclasses.llm_npc import LLMNpc
        return LLMNpc._NOT_A_LEADING_VERB

    def test_the_ten_that_fell_out_are_back(self):
        missing = {"and", "around", "at", "barely", "neither",
                   "one", "our", "still", "the", "under"}
        self.assertEqual(missing - set(self._set()), set())

    def test_no_entry_carries_punctuation(self):
        junk = [w for w in self._set()
                if any(ch in w for ch in "'(),")]
        self.assertEqual(junk, [])

    def test_the_count_is_unchanged(self):
        """57 either way — which is why the corruption was invisible."""
        self.assertEqual(len(self._set()), 57)

    def test_the_repr_form_really_did_corrupt_it(self):
        """Demonstrated, not described."""
        raw = ("the a an", "one both", "and then")
        broken = set(raw.__str__().split())
        correct = set(" ".join(raw).split())
        self.assertNotEqual(broken, correct)
        self.assertIn("('the", broken)
        self.assertNotIn("the", broken)

    def test_the_source_no_longer_uses_str(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        body = (root / "typeclasses" / "llm_npc.py").read_text(
            errors="ignore")
        self.assertNotIn(").__str__().split())", body)


class _ChromeCase(EvenniaTest):
    def organ(self, container, display=None, inorganic=True):
        """A stand-in shaped like a real Organ for the predicate."""
        from types import SimpleNamespace
        return SimpleNamespace(
            container=container,
            display_location=display or container,
            data={"inorganic": inorganic},
        )

    def with_organs(self, *organs):
        from unittest import mock
        state = mock.MagicMock()
        state.organs = {str(i): o for i, o in enumerate(organs)}
        return mock.patch.object(type(self.char1), "medical_state",
                                 new_callable=mock.PropertyMock,
                                 return_value=state)

    def chrome(self, location):
        return self.char1._location_is_inorganic(location)


class TestVisibleChromeStillReads(_ChromeCase):
    def test_a_chrome_jaw_shows_on_the_face(self):
        with self.with_organs(self.organ("head", "face")):
            self.assertTrue(self.chrome("face"))

    def test_a_chrome_hand_shows_on_the_hand(self):
        with self.with_organs(self.organ("right_hand")):
            self.assertTrue(self.chrome("right_hand"))

    def test_a_chrome_arm_bone_shows_on_the_arm(self):
        """`right_arm` is not an internal cavity, so a chrome humerus
        genuinely reads there."""
        with self.with_organs(self.organ("right_arm")):
            self.assertTrue(self.chrome("right_arm"))


class TestBuriedChromeDoesNot(_ChromeCase):
    def test_a_chrome_jaw_does_not_chrome_the_head(self):
        with self.with_organs(self.organ("head", "face")):
            self.assertFalse(self.chrome("head"))

    def test_a_cyber_heart_does_not_chrome_the_chest(self):
        """The case dropping the container match alone would have
        missed — `display_location` defaults to `container`."""
        with self.with_organs(self.organ("chest")):
            self.assertFalse(self.chrome("chest"))

    def test_nor_a_cyber_lung_the_abdomen(self):
        with self.with_organs(self.organ("abdomen")):
            self.assertFalse(self.chrome("abdomen"))

    def test_flesh_is_never_chrome(self):
        with self.with_organs(self.organ("right_hand", inorganic=False)):
            self.assertFalse(self.chrome("right_hand"))

    def test_an_unrelated_location_is_untouched(self):
        with self.with_organs(self.organ("right_hand")):
            self.assertFalse(self.chrome("left_hand"))


class TestItReusesTheExistingDiscriminator(EvenniaTest):
    """"Is this organ visible from outside" must have one answer."""

    def test_the_internal_test_lives_in_diagnose(self):
        from world.medical.diagnose import _is_internal_organ
        self.assertTrue(callable(_is_internal_organ))

    def test_the_renderer_imports_it(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        body = (root / "typeclasses" / "appearance_mixin.py").read_text(
            errors="ignore")
        self.assertIn("from world.medical.diagnose import _is_internal_organ",
                      body)

    def test_the_renderer_no_longer_matches_on_container(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        body = (root / "typeclasses" / "appearance_mixin.py").read_text(
            errors="ignore")
        start = body.index("def _location_is_inorganic")
        end = body.index("def _deployed_module_longdesc", start)
        self.assertNotIn('getattr(organ, "container", None),',
                         body[start:end])
