"""The public atlas does not ship live lock state (#2682).

`export_map()` typed every door link with `{"locked": ...}` read straight
off `ex.db.door_locked`. `world/atlas.py` embeds that whole structure in
the atlas page, and `web/website/urls.py` routes `atlas/` as "the colony
atlas — public shop window" with **no authentication** on `atlas_view`.

So anyone with the URL, logged out, could read which doors in the colony
were locked right now — joined to room names and coordinates. Live when
measured: **470 doors, 324 locked**, 348 of them touching private
residences. You could see which homes were open without walking a street.

Information disclosure, not code execution — and it cost nothing to fix,
because **nothing consumed the field**. Neither `scripts/atlas/
template.html` nor `template3d.html` mentions `door` or `locked`
anywhere. It was shipped and never read.

Doors are still typed `kind: "door"`; the atlas draws ways by kind, and
`template.html` filters on `l.kind` for edges and gaps. Only the live
state is withheld. A staff map that wants lock state can read the exits
directly rather than routing it through the public payload.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.mapping import export_map


class _AtlasCase(EvenniaTest):
    def _door(self, locked):
        # `db.xyz`, not `db.coord` -- `export_map` only ships
        # coord-seeded rooms, and a room without it produces no links at
        # all, which is how my first fixture "passed" by exporting
        # nothing.
        a = create_object("typeclasses.rooms.Room", key="a street",
                          location=None)
        a.db.xyz = (0, 0, 0)
        b = create_object("typeclasses.rooms.Room", key="a cube",
                          location=None)
        b.db.xyz = (0, 1, 0)
        ex = create_object("typeclasses.exits.Exit", key="south",
                           location=a, destination=b)
        ex.attributes.add("is_door", True)
        ex.attributes.add("door_locked", locked)
        return a, b, ex

    def links_for(self, room):
        return [l for l in export_map()["links"]
                if l["from"] == f"#{room.id}"]


class TestLockStateDoesNotLeaveTheGame(_AtlasCase):
    def test_a_locked_door_ships_no_lock_field(self):
        a, _b, _ex = self._door(True)
        for link in self.links_for(a):
            self.assertNotIn("door", link)

    def test_an_unlocked_door_ships_no_lock_field_either(self):
        """Withholding only the locked ones would still disclose them by
        omission."""
        a, _b, _ex = self._door(False)
        for link in self.links_for(a):
            self.assertNotIn("door", link)

    def test_the_word_locked_appears_nowhere_in_the_payload(self):
        self._door(True)
        self.assertNotIn("locked", str(export_map()))


class TestTheAtlasStillWorks(_AtlasCase):
    def test_the_door_is_still_typed_as_a_door(self):
        """The page draws ways by `kind`; only the live state is
        withheld, not the topology."""
        a, _b, _ex = self._door(True)
        kinds = {l["kind"] for l in self.links_for(a)}
        self.assertIn("door", kinds)

    def test_the_link_still_carries_its_endpoints(self):
        a, b, _ex = self._door(True)
        link = self.links_for(a)[0]
        self.assertEqual(link["from"], f"#{a.id}")
        self.assertEqual(link["to"], f"#{b.id}")

    def test_export_is_still_deterministic(self):
        self._door(True)
        self.assertEqual(export_map(), export_map())


class TestNoTemplateWantedIt(EvenniaTest):
    """Pinned so a future template cannot quietly start depending on a
    field the payload deliberately withholds."""

    def test_neither_atlas_template_reads_the_field(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "atlas"
        for name in ("template.html", "template3d.html"):
            path = root / name
            if not path.exists():
                continue
            body = path.read_text(errors="ignore")
            self.assertNotIn("locked", body, f"{name} reads lock state")
