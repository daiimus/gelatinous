"""The 3D atlas builder escapes its inline payloads like the 2D one (#2678).

`world/atlas.py` inlines JSON into a `<script>` element in two places.
`json.dumps` does not escape `</script>`, so a string containing it closes
the element early and everything after it parses as markup. The 2D builder
had hardened against this and documented why. Its twin, forty lines down,
inlined `json.dumps(...)` raw -- and again for `models.json` -- on a page
`web/website/views/atlas.py` renders with `mark_safe` and
`web/website/urls.py` serves with no authentication.

Reachability, measured rather than assumed: the public plate is built with
`account=None`, so the one player-authored string (`char.key`, via
`player_positions`) never reaches it -- that feed is a separate
`JsonResponse`, not a script context. Masts are gated on
`db.is_base_station`. Every string in the public payload is therefore
staff-authored, which makes this hardening parity rather than a live
open XSS. It is still the difference between "a builder cannot name a room
badly" and "a builder naming a room badly is inert", and the fix costs one
shared function.

`three.min.js` is deliberately NOT escaped: it is JavaScript, not JSON,
where `<` is a real operator. `test_three_js_is_not_escaped` is the control
-- it fails if someone ever "fixes" this by escaping every inlined blob.
"""
import json
import os
import tempfile

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world import atlas as atlas_mod

# Bound defensively: an absent name must report as a named failure, not an
# ImportError that takes every control in this file down with it.
_script_safe = getattr(atlas_mod, "_script_safe", None)

HOSTILE = "</script><img src=x onerror=alert(1)>"


class _StubGameDir:
    """A game_dir holding only what the builders actually open."""

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        os.makedirs(os.path.join(root, "scripts/atlas/vendor"))
        os.makedirs(os.path.join(root, "scripts/atlas/sprites"))
        self._write("scripts/atlas/vendor/three.min.js",
                    "var THREE={};if(a<b){c()}")
        self._write("scripts/atlas/sprites/models.json",
                    json.dumps({"note": HOSTILE}))
        self._write("scripts/atlas/template3d.html",
                    "<html><script>/*__THREE__*/\n"
                    "var D=/*__DATA__*/null;var M=/*__MODELS__*/null;"
                    "</script></html>")
        self._write("scripts/atlas/template.html",
                    "<html><script>var D=/*__DATA__*/null;</script></html>")
        return root

    def _write(self, rel, text):
        with open(os.path.join(self.tmp.name, rel), "w") as f:
            f.write(text)

    def __exit__(self, *exc):
        self.tmp.cleanup()
        return False


class AtlasInlinePayloadTest(EvenniaTest):
    def setUp(self):
        super().setUp()
        # A room the exporter will actually ship: `export_map` only emits
        # coord-seeded rooms, so without db.xyz this fixture would "pass"
        # by exporting nothing at all.
        self.room_evil = create_object("typeclasses.rooms.Room",
                                       key="a bar " + HOSTILE, location=None)
        self.room_evil.db.xyz = (0, 0, 0)

    def test_script_safe_exists(self):
        self.assertIsNotNone(
            _script_safe,
            "world.atlas._script_safe is missing -- the shared escaping "
            "helper the other tests in this file exercise")

    def test_script_safe_neutralises_and_preserves_json(self):
        # guarded so an absent helper reports here as a failure too,
        # rather than a TypeError that reads like a broken test
        self.assertIsNotNone(_script_safe, "world.atlas._script_safe missing")
        payload = {"name": HOSTILE, "sep": "a b"}
        out = _script_safe(json.dumps(payload))
        self.assertNotIn("</script>", out)
        self.assertNotIn(" ", out)
        # escaping must not corrupt the data the page then parses
        self.assertEqual(json.loads(out), payload)

    def test_3d_data_payload_is_escaped(self):
        with _StubGameDir() as root:
            html = atlas_mod.build_atlas3d_html(root)
        self.assertIn("a bar", html, "fixture room never reached the payload")
        self.assertNotIn(HOSTILE, html)

    def test_3d_models_payload_is_escaped(self):
        with _StubGameDir() as root:
            html = atlas_mod.build_atlas3d_html(root)
        # models.json carries HOSTILE too; if only the data payload were
        # fixed this still fails.
        self.assertEqual(html.count("</script>"), 1,
                         "exactly one real closing tag should survive")

    def test_three_js_is_not_escaped(self):
        # Control: three.min.js is JavaScript. Escaping "<" there would
        # turn a comparison into garbage. It must pass through untouched.
        with _StubGameDir() as root:
            html = atlas_mod.build_atlas3d_html(root)
        self.assertIn("if(a<b)", html)

    def test_2d_builder_still_escapes(self):
        # The branch that was already correct, guarded against the
        # refactor that made the helper shared.
        with _StubGameDir() as root:
            html = atlas_mod.build_atlas_html(root)
        self.assertIn("a bar", html)
        self.assertNotIn(HOSTILE, html)
