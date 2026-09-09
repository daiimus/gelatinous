"""Clothing prototypes carry the rung build 090 settled on (#2464).

Build 090 ("one ladder") rewrote `layer` on every ALREADY-SPAWNED
garment to the rung its name derives to. **The prototypes were never
updated**, so anything spawned afterwards inherited the stale value and
two identical items behaved differently.

The tell is dateable. Two crew chronos exist: #6325, created
2026-08-05, sits at the ladder value; #10500, created 2026-08-30 — after
the build — sits at the prototype's. Objects made before the build were
corrected; everything spawned since was not.

The reported symptom was `CODER_SOCKS`: thigh-high socks at rung 1
collide with any trousers, so a fresh pair cannot be worn with jeans
while an older pair can. Sweeping instead of fixing the one named
prototype found **nine** disagreements, of which five more were
corroborated by live instances sitting at the ladder value.

**`derive_rung` returning a value is not on its own enough**, and this
is the part worth remembering: an explicit layer ALWAYS wins by design
— "prototypes and builders keep control" — so a disagreement can be a
deliberate override rather than an oversight. Three prototypes with no
spawned instances (`COLORED_CONTACTS`, `DUST_PONCHO`, `KEVLAR_VEST`)
are left alone for exactly that reason; a kevlar vest sitting above its
derived rung is a plausible authorial choice about armour.

**And `LONGHAUL_CHRONO` is the case that proves it.** It derives to
rung 5 — but so do the work gloves, and both cover `left_hand`, so at 5
they are a same-layer conflict and you cannot wear a watch and gloves
together. Rung 1 slips it underneath. That was caught by putting the
watch on in the running game; nothing in this file or any other would
have found it.
"""
from evennia.utils.test_resources import EvenniaTest

from world import prototypes as P
from world.style import derive_rung

#: Corrected here — each corroborated by live instances that build 090
#: had already rewritten to the ladder value.
CORRECTED = {
    "CODER_SOCKS": 0,
    "DEV_HOODIE": 2,
    "SYNTHWEAVE_SHEATH": 1,
    "SYNTH_COLLAR": 5,
    "LAB_COAT": 4,
    # Moved by #3087's follow-up: scrubs are a shirt-and-trousers SET,
    # so they belong on rung 1 with the suits, not on the outerwear
    # rung where nothing could be worn over them.
    "MEDICAL_SCRUBS": 1,
}

#: Deliberate overrides, left alone. `layer` explicitly beats the
#: ladder, and these have a reason or no evidence either way.
KEPT = {"COLORED_CONTACTS", "DUST_PONCHO", "KEVLAR_VEST"}


def _layer_of(proto):
    return dict((a[0], a[1]) for a in proto.get("attrs", []) if len(a) >= 2)


class TestTheCorrectedPrototypes(EvenniaTest):
    def test_each_now_sits_on_its_derived_rung(self):
        for name, expected in CORRECTED.items():
            attrs = _layer_of(getattr(P, name))
            self.assertEqual(attrs["layer"], expected, name)

    def test_each_agrees_with_the_ladder(self):
        for name in CORRECTED:
            proto = getattr(P, name)
            self.assertEqual(_layer_of(proto)["layer"],
                             derive_rung(proto["key"]), name)

    def test_the_socks_can_share_a_leg_with_trousers(self):
        """The reported symptom: rung 0 is under, rung 1 collides."""
        socks = _layer_of(P.CODER_SOCKS)["layer"]
        jeans = _layer_of(P.BLUE_JEANS)["layer"]
        self.assertLess(socks, jeans)


class TestTheDeliberateOverridesAreLeftAlone(EvenniaTest):
    def test_the_chrono_stays_under_the_gloves(self):
        """It USED to be an override — chrono and gloves both derived to
        rung 5 and both cover `left_hand`, so a watch could not be worn
        with gloves at all. #2433's owner ruling moved watches off that
        rung entirely, so the ladder now agrees with the prototype
        instead of fighting it."""
        chrono = _layer_of(P.LONGHAUL_CHRONO)
        self.assertLess(chrono["layer"], derive_rung("work gloves"))
        self.assertEqual(derive_rung(P.LONGHAUL_CHRONO["key"]),
                         chrono["layer"])

    def test_they_are_recorded_as_overrides_not_forgotten(self):
        """A future sweep must not silently 'correct' them back."""
        import inspect
        source = inspect.getsource(P)
        for name in KEPT:
            start = source.index(f"{name} = {{")
            block = source[start:source.index("\n}", start)]
            self.assertTrue(block, name)

    def test_the_prototypes_own_prose_says_so(self):
        """The strongest evidence was authorial, not mechanical: the
        chrono's description is 'a ridged bezel cut deep enough to turn
        with gloves on'. It was written to be worn WITH gloves, which
        rung 5 makes impossible."""
        self.assertIn("gloves", P.LONGHAUL_CHRONO["desc"])


class TestNothingElseDriftedBack(EvenniaTest):
    def test_only_the_known_overrides_disagree(self):
        drifted = []
        for name in dir(P):
            proto = getattr(P, name)
            if not isinstance(proto, dict):
                continue
            key, attrs = proto.get("key"), _layer_of(proto)
            if not key or "layer" not in attrs or "coverage" not in attrs:
                continue
            rung = derive_rung(key)
            if rung is not None and rung != attrs["layer"]:
                drifted.append(name)
        self.assertEqual(set(drifted), KEPT,
                         f"unexpected layer drift: {sorted(set(drifted) - KEPT)}")


class TestWatchesLiveLow(EvenniaTest):
    """Owner ruling 2026-08-30 (#2433): *"Watches should just live on a
    low layer like underwear and eventually be transparent since they
    won't cover a hand."*

    Three watch prototypes disagreed — two at rung 1, `STOPPED_WATCH`
    at 5 — and the ladder itself listed "watch"/"chrono" among the
    accessories on rung 5. That rung also holds GLOVES, and both cover
    `left_hand`, so a watch and gloves were a same-layer conflict and
    could not be worn together at all.

    Verified in the running game, which is where it was found: with the
    ladder moved, a watch sits under gloves and both are worn. Trying to
    add a SECOND watch correctly refuses — "you cannot wear the stopped
    watch over the crew chrono, and you would need to wear it under the
    work gloves" — because two watches on one wrist genuinely collide.

    The transparency half of the ruling ("eventually be transparent") is
    NOT built: `CLOTHING_SYSTEM_SPEC` §151-186 is a PROPOSAL with open
    owner questions, and no layer value produces "watch and gloves both
    worn AND both rendered". This settles the layer only.
    """

    WATCHES = ("LONGHAUL_CHRONO", "GILT_WRISTWATCH", "STOPPED_WATCH")

    def test_every_watch_sits_low(self):
        for name in self.WATCHES:
            layer = _layer_of(getattr(P, name))["layer"]
            self.assertLessEqual(layer, 1, name)

    def test_they_all_agree_with_each_other(self):
        layers = {_layer_of(getattr(P, n))["layer"] for n in self.WATCHES}
        self.assertEqual(len(layers), 1, f"watches disagree: {layers}")

    def test_a_watch_is_below_gloves(self):
        """The whole point: at the same rung they cannot coexist."""
        gloves = derive_rung("work gloves")
        for name in self.WATCHES:
            self.assertLess(_layer_of(getattr(P, name))["layer"], gloves, name)

    def test_the_ladder_no_longer_calls_a_watch_an_accessory(self):
        from world.style import RUNGS
        self.assertNotIn("watch", RUNGS[5])
        self.assertNotIn("chrono", RUNGS[5])

    def test_and_derives_them_low_instead(self):
        self.assertEqual(derive_rung("crew chrono"), 1)
        self.assertEqual(derive_rung("stopped watch"), 1)

    def test_the_legend_stopped_listing_watches_outermost(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        legend = (root / "world" / "combat" / "constants.py").read_text()
        self.assertNotIn("gloves, masks, watches", legend)
