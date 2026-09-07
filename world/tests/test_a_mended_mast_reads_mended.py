"""A mended mast reads mended, and two saboteurs cannot double-fell one
(#2558, #2570, #2559).

## #2558 — the wreck prose stuck forever

`mend_structure` restored the stash only `if db.intact_sensory:`. A
structure with **no authored** `sensory_contributions` stashes `None`,
so the restore was skipped — while `wreck_structure` installs the wreck
text *unconditionally* and `db.intact` was set back to `True`.

The result is a one-way trap: intact and relaying, reading as wrecked,
and mending again does nothing because it is already "intact".

Live when found — **#5641, the AWE Sentinel-9 repeater mast**:

```
intact = True
sensory = {'visual': 'A wrecked antenna mast lists against its cut guy lines…'}
intact_sensory = (empty)
```

Gated on being **wrecked** now, and the restore is unconditional:
restoring a `None` stash is the correct outcome, because it means the
structure genuinely had none. `scripts/builds/153_…` cleared the false
line from #5641 (`repaired: 1`, `remaining: 0`) against a fresh DB
backup. It clears rather than inventing replacement prose — authoring a
branded line belongs with #2559, not a data repair.

## #2570 — check-then-act across a ninety-second channel

`CmdSabotage` verified `db.intact` before starting and `_complete()`
never re-read it. Two saboteurs on one mast both passed the guard, both
completed, and **the second wreck stashed the first wreck's prose as the
structure's authored appearance** — after which mending "restored" the
wreck text permanently. The channel is per-character; nothing locked the
structure.

`wreck_structure` and `mend_structure` refuse a second pass and report
it, and both callbacks re-read at completion so the messaging cannot
claim a felling that did not happen.

## #2559 — the wreck prose named the wrong thing

It hardcoded *"antenna mast"*, so a branded `AWE Sentinel-9 repeater
mast` and a `derelict repeater` were both described in player prose as a
generic mast. It uses the structure's own key now — what the room
already calls the thing.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from commands.CmdBreach import (WRECKED_DESC, mend_structure,
                                wreck_structure)


def wrecked_sensory_for(structure):
    """Imported lazily so this module still LOADS against the unfixed
    tree — a module-scope import of a not-yet-existing helper turns
    every test into a loader error, which proves nothing. Fifth time
    in this audit."""
    from commands.CmdBreach import wrecked_sensory_for as real
    return real(structure)


class _MastCase(EvenniaTest):
    def mast(self, key="an antenna mast", desc="A mast.", sensory=None):
        obj = create_object("typeclasses.objects.Object", key=key,
                            location=self.room1)
        obj.db.breachable = True
        obj.db.intact = True
        obj.db.desc = desc
        obj.db.sensory_contributions = sensory
        return obj

    def sensory(self, mast):
        return dict(mast.db.sensory_contributions or {})


class TestAMastWithNoAuthoredSensoryRecovers(_MastCase):
    """The live case: nothing to stash, so nothing was restored."""

    def test_wrecking_installs_the_wreck_line(self):
        mast = self.mast(sensory=None)
        wreck_structure(mast)
        self.assertIn("wrecked", self.sensory(mast).get("visual", ""))

    def test_mending_removes_it_again(self):
        mast = self.mast(sensory=None)
        wreck_structure(mast)
        mend_structure(mast)
        self.assertNotIn("wrecked", str(self.sensory(mast)))

    def test_it_ends_with_no_sensory_layer_as_it_started(self):
        mast = self.mast(sensory=None)
        wreck_structure(mast)
        mend_structure(mast)
        self.assertFalse(mast.db.sensory_contributions)

    def test_the_desc_comes_back_too(self):
        mast = self.mast(desc="A tall mast.", sensory=None)
        wreck_structure(mast)
        self.assertEqual(mast.db.desc, WRECKED_DESC)
        mend_structure(mast)
        self.assertEqual(mast.db.desc, "A tall mast.")


class TestAnAuthoredMastRoundTrips(_MastCase):
    """The case that already worked — pinned, so the fix does not trade
    one for the other."""

    def test_the_authored_layer_returns(self):
        authored = {"visual": "A guyed mast.", "auditory": "It hums."}
        mast = self.mast(sensory=dict(authored))
        wreck_structure(mast)
        mend_structure(mast)
        self.assertEqual(self.sensory(mast), authored)

    def test_the_stash_is_emptied_after_use(self):
        mast = self.mast(sensory={"visual": "A guyed mast."})
        wreck_structure(mast)
        mend_structure(mast)
        self.assertIsNone(mast.db.intact_sensory)
        self.assertIsNone(mast.db.intact_desc)


class TestNeitherFlipRunsTwice(_MastCase):
    def test_a_second_wreck_is_refused(self):
        mast = self.mast(sensory={"visual": "A guyed mast."})
        self.assertTrue(wreck_structure(mast))
        self.assertFalse(wreck_structure(mast))

    def test_and_does_not_overwrite_the_stash(self):
        """The permanent damage: the second wreck used to stash the
        FIRST WRECK's prose as the authored appearance."""
        authored = {"visual": "A guyed mast."}
        mast = self.mast(sensory=dict(authored))
        wreck_structure(mast)
        wreck_structure(mast)          # the racing saboteur
        mend_structure(mast)
        self.assertEqual(self.sensory(mast), authored)

    def test_a_second_mend_is_refused(self):
        mast = self.mast(sensory={"visual": "A guyed mast."})
        wreck_structure(mast)
        self.assertTrue(mend_structure(mast))
        self.assertFalse(mend_structure(mast))

    def test_mending_an_intact_mast_does_not_clobber_it(self):
        mast = self.mast(desc="A tall mast.",
                         sensory={"visual": "A guyed mast."})
        self.assertFalse(mend_structure(mast))
        self.assertEqual(mast.db.desc, "A tall mast.")
        self.assertEqual(self.sensory(mast), {"visual": "A guyed mast."})


class TestTheWreckNamesTheStructure(_MastCase):
    def test_a_branded_repeater_is_named(self):
        mast = self.mast(key="AWE Sentinel-9 repeater mast")
        wreck_structure(mast)
        self.assertIn("AWE Sentinel-9 repeater mast",
                      self.sensory(mast).get("visual", ""))

    def test_a_derelict_repeater_is_named(self):
        mast = self.mast(key="derelict repeater")
        wreck_structure(mast)
        self.assertIn("derelict repeater",
                      self.sensory(mast).get("visual", ""))

    def test_it_no_longer_says_antenna_mast_for_everything(self):
        mast = self.mast(key="derelict repeater")
        wreck_structure(mast)
        self.assertNotIn("antenna mast",
                         self.sensory(mast).get("visual", ""))

    def test_the_helper_falls_back_for_a_nameless_thing(self):
        from types import SimpleNamespace
        line = wrecked_sensory_for(SimpleNamespace(key=None))["visual"]
        self.assertIn("antenna mast", line)
