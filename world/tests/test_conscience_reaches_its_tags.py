"""Guilt and relish must fire once, and reach the tags souls declare.

#2700 -- the once-per-deed guard compared `id(job)`, but
`soul.db.soul_job` returns a fresh `_SaverDict` on every read (verified
live: two consecutive reads give equal content and different ids). So
the marker never matched and the conscience was charged every tick
instead of once per deed.

#2708 -- five of the eight ethos tags could never reach `_conscience`.
`toil` and `solitude` are correctly ATTACHED to the duty and dwell
plans -- the author already decided those acts carry moral weight -- but
the steps those plans run never called the conscience, so the tags rode
along unread. 22 of the 24 authored stances sat on unreachable tags, and
`toil` was the single most-declared stance in the colony.

The two are ordered: wiring a per-beat step to the conscience BEFORE
fixing the guard would have charged guilt every tick.
"""
from unittest import TestCase, mock

from world.souls import jobs


class _Soul:
    def __init__(self):
        self.ndb = mock.MagicMock()
        self.ndb.conscience_charged = None
        self.db = mock.MagicMock()
        self.db.soul_job = None
        self.location = mock.MagicMock()
        self.location.key = "the yard"


class TestTheDeedIsChargedOnce(TestCase):
    def _charge(self, soul, job, times=3):
        added = []
        with mock.patch("world.souls.thoughts.add_thought",
                        side_effect=lambda *a, **k: added.append(a)), \
             mock.patch("world.souls.traits.abhors", return_value=True), \
             mock.patch("world.souls.traits.relishes", return_value=False):
            for _ in range(times):
                jobs._conscience(soul, job)
        return added

    def test_a_repeated_beat_charges_only_once(self):
        soul = _Soul()
        job = {"goal": "duty", "ethos": ("toil",)}
        self.assertEqual(len(self._charge(soul, job)), 1)

    def test_the_token_survives_a_fresh_dict_of_the_same_job(self):
        """The actual failure: every read of `db.soul_job` is a NEW
        object, so an identity-based marker never matched."""
        soul = _Soul()
        job = {"goal": "duty", "ethos": ("toil",)}
        self._charge(soul, job, times=1)
        again = dict(job)                 # what a re-read looks like
        self.assertIsNot(again, job)
        self.assertEqual(len(self._charge(soul, again, times=1)), 0,
                         "a re-read of the same job charged again")

    def test_a_genuinely_new_deed_charges_again(self):
        """The pin: the guard must not become permanent."""
        soul = _Soul()
        self._charge(soul, {"goal": "duty", "ethos": ("toil",)}, times=1)
        second = self._charge(soul, {"goal": "social", "ethos": ("revelry",)},
                              times=1)
        self.assertEqual(len(second), 1)

    def test_a_job_with_no_ethos_charges_nothing(self):
        soul = _Soul()
        self.assertEqual(self._charge(soul, {"goal": "duty"}), [])


class TestEveryAttachedTagCanReachTheConscience(TestCase):
    """A tag that is never read looks exactly like a tag whose condition
    has not come up, which is what hid this."""

    def _plans_source(self):
        import inspect

        import world.souls.actions as actions
        return inspect.getsource(actions)

    def _jobs_source(self):
        import inspect
        return inspect.getsource(jobs)

    def test_the_work_step_charges_the_conscience(self):
        """Revives `toil` — nine souls, the most-declared stance."""
        src = self._jobs_source()
        work = src[src.index('if do == "work":'):src.index('if do == "linger":')]
        self.assertIn("_conscience(soul, job)", work)

    def test_the_dwell_step_charges_the_conscience(self):
        """Revives `solitude` — five souls."""
        src = self._jobs_source()
        dwell = src[src.index('if do == "dwell":'):src.index('if do == "grapple":')]
        self.assertIn("_conscience(soul, job)", dwell)

    def test_the_paths_that_already_worked_still_do(self):
        """The pin: `rob` and `linger` were the two reachable tags."""
        src = self._jobs_source()

        def _step(name):
            """Slice one step body: from its marker to the NEXT marker,
            whatever that is. My first version hard-coded the following
            step and sliced BACKWARDS, producing an empty string that
            the assertion then failed on for the wrong reason."""
            start = src.index(f'if do == "{name}":')
            nxt = src.find('    if do == "', start + 1)
            return src[start:nxt if nxt != -1 else len(src)]

        self.assertIn("_conscience(soul, job", _step("rob"))
        self.assertIn("_conscience(soul, job)", _step("linger"))
