"""An expiry of 0 must mean expired, not permanent (#2690).

`world/access.py` documents itself as fail-closed:

    Fail-closed: no sleeve, no grants, malformed entries, expired
    entries -- all read as not granted. One bad record never grants
    (or blocks) the rest.

Every other ambiguity in `is_granted` honours that. This one failed
OPEN, on the value that most obviously means "not valid", and it did so
TWICE independently -- `make_grant` coerced a falsy `until` to None on
write, and `is_granted` skipped the expiry test on any falsy value on
read. Fixing either alone leaves the other minting eternal grants.

For a module gating secured floors and leased residences, an accidental
permanent grant is the worst available failure.
"""
import time
from types import SimpleNamespace
from unittest import TestCase

from world.access import is_granted, make_grant


def _sleeve(uid):
    return SimpleNamespace(sleeve_uid=uid)


class TestZeroIsAnInstantNotASentinel(TestCase):
    def test_make_grant_keeps_a_zero_expiry(self):
        grant = make_grant(_sleeve("s1"), until=0)
        self.assertEqual(grant["until"], 0.0,
                         "a dead expiry was stored as permanent")

    def test_make_grant_still_treats_none_as_permanent(self):
        """The pin: permanent residence is the design (one credit, one
        cube, forever), so None must keep meaning never-expires."""
        self.assertIsNone(make_grant(_sleeve("s1"), until=None)["until"])

    def test_make_grant_keeps_a_real_expiry(self):
        soon = time.time() + 600
        self.assertAlmostEqual(
            make_grant(_sleeve("s1"), until=soon)["until"], soon, places=3)

    def test_a_zero_expiry_does_not_grant(self):
        grants = [make_grant(_sleeve("s1"), until=0)]
        self.assertFalse(is_granted(_sleeve("s1"), grants),
                         "an expired grant admitted the holder")

    def test_a_raw_zero_on_disk_does_not_grant(self):
        """The read side, independent of the writer -- a zero already
        stored by the old code must not read as permanent."""
        grants = [{"sleeve": "s1", "until": 0, "issued_by": None}]
        self.assertFalse(is_granted(_sleeve("s1"), grants))

    def test_a_past_expiry_still_does_not_grant(self):
        grants = [{"sleeve": "s1", "until": time.time() - 60}]
        self.assertFalse(is_granted(_sleeve("s1"), grants))

    def test_a_future_expiry_grants(self):
        grants = [{"sleeve": "s1", "until": time.time() + 600}]
        self.assertTrue(is_granted(_sleeve("s1"), grants))

    def test_a_none_expiry_grants(self):
        """The 176 live grants are all of this shape."""
        grants = [{"sleeve": "s1", "until": None}]
        self.assertTrue(is_granted(_sleeve("s1"), grants))


class TestTheRestStillFailsClosed(TestCase):
    """The surrounding contract, pinned so the polarity fix cannot
    quietly loosen anything else."""

    def test_no_sleeve_is_not_granted(self):
        self.assertFalse(is_granted(_sleeve(None),
                                    [{"sleeve": "s1", "until": None}]))

    def test_no_grants_is_not_granted(self):
        self.assertFalse(is_granted(_sleeve("s1"), []))
        self.assertFalse(is_granted(_sleeve("s1"), None))

    def test_a_different_sleeve_is_not_granted(self):
        self.assertFalse(is_granted(_sleeve("s2"),
                                    [{"sleeve": "s1", "until": None}]))

    def test_a_malformed_entry_neither_grants_nor_blocks_the_rest(self):
        grants = ["not a dict", {"sleeve": "s1", "until": None}]
        self.assertTrue(is_granted(_sleeve("s1"), grants))

    def test_an_unparseable_expiry_does_not_grant(self):
        grants = [{"sleeve": "s1", "until": "banana"}]
        self.assertFalse(is_granted(_sleeve("s1"), grants))
