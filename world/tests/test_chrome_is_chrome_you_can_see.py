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


class TestEveryInorganicPrototypeClassifiesRight(EvenniaTest):
    """The whole catalogue, pinned — because the visible/hidden split is
    decided by whether a prototype bothers to set `display_location`,
    and a new implant that forgets it becomes silently invisible.

    Owner question, 2026-09-07: *"we have two kinds of cyber jaw — one
    should definitely be visible, right?"* Both are, and both show on
    the **face**: `CYBER_JAW` (the chassis) and `JAWZ` (the fang module
    that seats into it). What #2587 removed was those also chroming the
    whole HEAD.

    Measured across all 13 inorganic organ prototypes:

    ```
    VISIBLE  cybernetic jaw          head    -> face
    VISIBLE  Jawz                    head    -> face
    VISIBLE  cybernetic left/right eye, left/right ear
    VISIBLE  voice modulator         head    -> face
    VISIBLE  shotgun / integrated shotgun / targeting processor
    HIDDEN   cybernetic heart        chest   -> chest
    HIDDEN   cybernetic left/right kidney  abdomen -> abdomen
    ```
    """

    def _specs(self):
        import world.prototypes as protos
        out = {}
        for value in vars(protos).values():
            if not isinstance(value, dict):
                continue
            for attr in (value.get("attrs") or []):
                if (isinstance(attr, (list, tuple)) and len(attr) >= 2
                        and attr[0] == "organ_spec"
                        and isinstance(attr[1], dict)
                        and attr[1].get("inorganic")):
                    out[str(value.get("key"))] = attr[1]
        return out

    @staticmethod
    def _hidden(spec):
        from world.medical.diagnose import _INTERNAL_CONTAINERS
        container = spec.get("container")
        display = spec.get("display_location") or container
        return container in _INTERNAL_CONTAINERS and display == container

    def test_the_catalogue_is_the_expected_size(self):
        self.assertEqual(len(self._specs()), 13)

    def test_both_cyber_jaws_are_visible(self):
        specs = self._specs()
        for key in ("cybernetic jaw", "Jawz"):
            self.assertIn(key, specs)
            self.assertFalse(self._hidden(specs[key]), f"{key} reads hidden")

    def test_both_cyber_jaws_show_on_the_face(self):
        specs = self._specs()
        for key in ("cybernetic jaw", "Jawz"):
            self.assertEqual(specs[key].get("display_location"), "face")

    def test_eyes_ears_and_voice_are_visible(self):
        specs = self._specs()
        for key in ("cybernetic left eye", "cybernetic right eye",
                    "cybernetic left ear", "cybernetic right ear",
                    "voice modulator"):
            self.assertIn(key, specs)
            self.assertFalse(self._hidden(specs[key]), f"{key} reads hidden")

    def test_the_viscera_are_hidden(self):
        specs = self._specs()
        for key in ("cybernetic heart", "cybernetic left kidney",
                    "cybernetic right kidney"):
            self.assertIn(key, specs)
            self.assertTrue(self._hidden(specs[key]), f"{key} reads visible")

    def test_nothing_in_a_cavity_forgot_its_display_location(self):
        """The failure mode for a NEW implant: a visible one seated in
        head / chest / abdomen / back / neck that omits
        `display_location` inherits the container and vanishes."""
        from world.medical.diagnose import _INTERNAL_CONTAINERS
        suspects = []
        for key, spec in self._specs().items():
            if (spec.get("container") in _INTERNAL_CONTAINERS
                    and not spec.get("display_location")):
                suspects.append(key)
        self.assertEqual(
            sorted(suspects),
            ["cybernetic heart", "cybernetic left kidney",
             "cybernetic right kidney"],
            "a new implant in a cavity has no display_location — it will "
            "render as invisible; give it one if it should show")
