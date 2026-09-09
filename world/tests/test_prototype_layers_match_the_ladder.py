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
}

#: Deliberate overrides, left alone. `layer` explicitly beats the
#: ladder, and these have a reason or no evidence either way.
KEPT = {"LONGHAUL_CHRONO", "COLORED_CONTACTS", "DUST_PONCHO", "KEVLAR_VEST"}


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
        """Both derive to rung 5 and both cover left_hand, so at 5 a
        watch and gloves cannot be worn together."""
        chrono = _layer_of(P.LONGHAUL_CHRONO)
        gloves_rung = derive_rung("work gloves")
        self.assertEqual(derive_rung(P.LONGHAUL_CHRONO["key"]), gloves_rung)
        self.assertLess(chrono["layer"], gloves_rung)

    def test_they_are_recorded_as_overrides_not_forgotten(self):
        """A future sweep must not silently 'correct' them back."""
        import inspect
        source = inspect.getsource(P)
        start = source.index("LONGHAUL_CHRONO = {")
        block = source[start:source.index("\n}", start)]
        self.assertIn("DELIBERATE", block)

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
