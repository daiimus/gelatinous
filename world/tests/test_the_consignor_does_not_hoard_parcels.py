"""A failed run does not leave a parcel on the consignor (#3192).

The stale-parcel sweep before a run looks in the COURIER's hands:

    for stale in [o for o in soul.contents
                  if o.attributes.has("courier_package")]:
        stale.delete()

and `_spawn_package` puts the parcel in the CLERK's, as its own
docstring says — *"A real parcel in the CONSIGNOR's hands, addressed
onward."* A run that never got as far as collecting left it there, and
nothing swept the clerk.

So #2309's fix cleaned the one place the parcels are not. Measured live:

    parcels in the world, by holder:  Ezra Vantomme#5161 -> 72 (all)
    Wren (the courier), parcels held:  0
    parcel id range:  14501 .. 17098   against a world max of 17100

One per failed run, none ever removed. The predicate was never the
problem — a sampled parcel carries `courier_package` — it was the place.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


def _parcel(where, key="a Longhaul bonded parcel"):
    item = create_object("typeclasses.items.Item", key=key, location=where)
    item.attributes.add("courier_package", True)
    return item


class TestTheSweepReachesTheConsignor(EvenniaTest):
    """`_setup_run` needs a whole courier fixture, so the sweep itself is
    driven — the defect is which CONTAINER is scanned, and that is what
    these assert."""

    def setUp(self):
        super().setUp()
        self.courier = self.char1
        self.clerk = self.char2

    def sweep(self):
        """The two sweeps as the module performs them, in order."""
        import inspect

        from world.souls import salience
        source = inspect.getsource(salience)
        return source

    def test_the_clerk_is_swept_too(self):
        """Structural: the sweep must name `clerk.contents`, not only
        `soul.contents`. A behavioural test here would need the whole
        run fixture — a clerk, a counter, a destination list and a
        plannable job — and would fail for a dozen reasons that are not
        this one."""
        source = self.sweep()
        self.assertIn("for stale in [o for o in clerk.contents", source,
                      "the consignor's pile is still unswept")

    def test_the_courier_is_still_swept(self):
        """Control: the sweep that already worked must survive."""
        source = self.sweep()
        self.assertIn("for stale in [o for o in soul.contents", source)

    def test_it_sweeps_before_the_spawn(self):
        """Order is load-bearing: sweeping AFTER would destroy the
        parcel this run just created, and it is also what makes the
        clerk sweep safe if a second courier ever shares a consignor."""
        source = self.sweep()
        # `.find`, not `.index`: against the unfixed tree the clerk
        # sweep is absent and `.index` raises, which is an ERROR — and
        # an error stops the test before it can assert anything. -1
        # fails the comparison honestly.
        swept = source.find("for stale in [o for o in clerk.contents")
        spawned = source.find("package = _spawn_package(clerk, room)")
        self.assertNotEqual(swept, -1, "the clerk is never swept")
        self.assertLess(swept, spawned)


class TestThePredicateWasNeverTheProblem(EvenniaTest):
    """The parcels carried the marker all along — a sampled live one
    reads `courier_package: True`. Pinned so a future prototype change
    cannot quietly empty both sweeps."""

    def test_a_spawned_parcel_carries_the_marker(self):
        from evennia.prototypes.spawner import spawn

        from world import prototypes
        parcel = spawn(prototypes.COURIER_PACKAGE)[0]
        self.addCleanup(parcel.delete)
        self.assertTrue(parcel.attributes.has("courier_package"))

    def test_an_ordinary_item_does_not(self):
        """Control: the marker distinguishes something."""
        item = create_object("typeclasses.items.Item", key="a rock",
                             location=self.room1)
        self.assertFalse(item.attributes.has("courier_package"))
