"""The signal bus — WSIS P0 (#2140).

The colony's state has to be legible, because collapse is legitimate
content and nobody can act on what they cannot see. These pin decay,
zone rollup, the headline counts, and the property that observation
never breaks the thing it observes.
"""
import time

from evennia.utils.test_resources import BaseEvenniaTest

from world import wsis


class _BusTest(BaseEvenniaTest):
    def setUp(self):
        super().setUp()
        wsis._ring = []
        wsis._since_checkpoint = 0

    def _emit(self, kind, zone="Kaspar Street", ago=0.0, note=""):
        layer, weight = wsis.SIGNALS.get(kind, (None, 0.35))
        wsis._ring.append((time.time() - ago, kind, layer or "population",
                           zone, weight, note))


class TestDecay(_BusTest):
    def test_a_fresh_signal_lands_at_full_weight(self):
        self._emit("death")
        row = wsis.recent()[0]
        self.assertAlmostEqual(row[4], 1.0, places=2)

    def test_a_signal_halves_over_its_layer_halflife(self):
        self._emit("death", ago=wsis.LAYERS["security"]["halflife"])
        self.assertAlmostEqual(wsis.recent()[0][4], 0.5, places=2)

    def test_layers_decay_at_their_own_rates(self):
        """A killing stays relevant longer than a stalled walk."""
        span = 6 * 3600
        self._emit("death", ago=span)
        self._emit("post_vacant", ago=span)
        by = {row[1]: row[4] for row in wsis.recent()}
        # security halves twice in six hours; infrastructure only once
        self.assertLess(by["death"] / 1.00, by["post_vacant"] / 0.50)

    def test_the_window_excludes_the_old(self):
        self._emit("death", ago=7200)
        self.assertEqual(len(wsis.recent(seconds=3600)), 0)
        self.assertEqual(len(wsis.recent()), 1)


class TestRollup(_BusTest):
    def test_pressure_sums_a_slice(self):
        self._emit("death")
        self._emit("robbery")
        self.assertGreater(wsis.pressure(), 1.5)
        self.assertGreater(wsis.pressure(layer="security"), 1.5)
        self.assertEqual(wsis.pressure(layer="economy"), 0.0)

    def test_hot_zones_rank_by_noise(self):
        self._emit("death", zone="Pessoa Street")
        self._emit("plan_faulted", zone="Kaspar Street")
        loud = wsis.hot_zones()
        self.assertEqual(loud[0][0], "Pessoa Street")

    def test_counts_are_the_undecayed_headline(self):
        for _ in range(3):
            self._emit("death", ago=1800)
        self.assertEqual(wsis.counts("death", seconds=3600), 3)
        self.assertEqual(wsis.counts("robbery", seconds=3600), 0)

    def test_by_layer_reports_every_layer_heard_from(self):
        self._emit("death")
        self._emit("sale")
        self.assertEqual(set(wsis.by_layer()), {"security", "economy"})


class TestZoning(_BusTest):
    def test_a_room_names_its_own_zone(self):
        self.room1.key = "The Brackett Arms - Unit 3C"
        self.assertEqual(wsis.zone_of(self.room1), "The Brackett Arms")

    def test_a_thing_reports_the_room_it_is_in(self):
        self.room1.key = "Kaspar Street"
        self.char1.location = self.room1
        self.assertEqual(wsis.zone_of(self.char1), "Kaspar Street")

    def test_nowhere_is_still_somewhere(self):
        self.assertEqual(wsis.zone_of(None), "the colony")


class TestSafety(_BusTest):
    def test_observation_never_raises(self):
        """The bus is wrapped because a broken readout must never be
        able to break a death, a sale, or a shift."""
        class _Exploding:
            @property
            def location(self):
                raise RuntimeError("boom")

        wsis.emit("death", _Exploding())          # must not raise

    def test_an_unknown_signal_still_records(self):
        wsis.emit("something_nobody_declared", self.room1)
        kinds = [row[1] for row in wsis.recent()]
        self.assertIn("something_nobody_declared", kinds)

    def test_the_ring_is_bounded(self):
        for _ in range(wsis.RING + 50):
            self._emit("plan_faulted")
        wsis.emit("plan_faulted", self.room1)
        self.assertLessEqual(len(wsis._ring), wsis.RING)
