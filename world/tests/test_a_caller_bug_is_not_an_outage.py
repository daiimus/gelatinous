"""An exception from the success handler is not a transport failure
(#2727).

`evennia.utils.run_async` wires the pair as `deferred.addCallback(
at_return)` then `deferred.addErrback(at_err)` — sequentially, not as a
pair. So anything the success callback raises lands in the ERRBACK,
which records a transport failure against the circuit breaker, logs it
as "LLM backend call failed", and runs the failure path after the
success path already ran.

Measured in the live server log:

    1159  LLM backend call failed [AttributeError]
     146  LLM backend call failed [ReadTimeout]
      88  LLM backend call failed [ConnectionError]

83.2% of logged backend failures were the game's own code throwing.
Three consequences, none cosmetic: the breaker trips on our bugs and
stops dispatching to a backend that is answering fine; a real outage is
invisible in a log that is 83% noise; and `on_fail()` runs after
`on_turn()` already produced a reply.
"""
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest
from twisted.python.failure import Failure as _Failure

from world.llm import client as client_mod

_shielded = getattr(client_mod, "_shielded", None)


class TestTheShieldExists(EvenniaTest):

    def test_every_success_callback_is_shielded(self):
        """Structural: four `run_async` sites in this module, and a
        handler left unwrapped at any of them puts that lane's caller
        bugs back on the breaker."""
        import inspect
        source = inspect.getsource(client_mod)
        self.assertEqual(
            source.count("at_return=_shielded("),
            source.count("run_async(_thread_fn"),
            "a run_async site is dispatching an unshielded handler")


class TestACallerBugIsNotAnOutage(EvenniaTest):

    def setUp(self):
        super().setUp()
        if _shielded is None:
            self.skipTest("no shield in this tree")

    def test_a_clean_handler_is_passed_through(self):
        """Control: the shield must not change the ordinary path."""
        seen = []
        wrapped = _shielded(lambda r: seen.append(r), lambda: None, "X")
        wrapped("hello")
        self.assertEqual(seen, ["hello"])

    def test_a_raising_handler_does_not_propagate(self):
        """Which is the whole point: nothing reaches the errback, so
        nothing is counted against the breaker."""
        def boom(_r):
            raise AttributeError("'NoneType' object has no attribute 'id'")
        wrapped = _shielded(boom, lambda: None, "X")
        wrapped("hello")            # must not raise

    def test_the_failure_path_still_runs(self):
        failed = []
        def boom(_r):
            raise AttributeError("nope")
        wrapped = _shielded(boom, lambda: failed.append(1), "X")
        wrapped("hello")
        self.assertEqual(failed, [1])

    def test_it_is_logged_as_caller_side(self):
        def boom(_r):
            raise AttributeError("nope")
        with patch.object(client_mod.logger, "log_err") as log:
            _shielded(boom, lambda: None, "LLM turn")("hello")
        said = " ".join(str(c.args[0]) for c in log.call_args_list if c.args)
        self.assertIn("caller-side", said)
        self.assertNotIn("backend call failed", said)

    def test_a_failing_on_fail_does_not_escape_either(self):
        """A fallback that throws would land back in the errback and
        be counted as an outage a second time."""
        def boom(_r):
            raise AttributeError("nope")
        def worse():
            raise RuntimeError("the fallback is broken too")
        _shielded(boom, worse, "X")("hello")   # must not raise


class TestTheBreakerIsNotTouched(EvenniaTest):
    """The measurable consequence, driven through `request_turn` itself
    rather than through the helper — the seam is `run_async`, so that is
    what gets faked, with EVENNIA'S OWN CHAINING:

        deferred.addCallback(at_return)
        deferred.addErrback(at_err)

    which is sequential, not paired, so an exception from `at_return`
    reaches `at_err`. Everything else in the path is the real code, and
    this class runs identically against the unfixed tree — where it
    fails, because the transport failure IS recorded.
    """

    def drive(self, on_turn, on_fail=lambda: None):
        """Run `request_turn` with a canned successful response."""
        def fake_run_async(fn, at_return=None, at_err=None, **kw):
            try:
                at_return('{"say": "hello"}')
            except Exception as err:  # noqa: BLE001 — Twisted's behaviour
                if at_err:
                    at_err(_Failure(err))

        with patch.object(client_mod, "run_async", fake_run_async), \
                patch.object(client_mod, "note_transport_failure") as failed, \
                patch.object(client_mod, "note_transport_success") as ok, \
                patch.object(client_mod.logger, "log_err"), \
                patch.object(client_mod.logger, "log_trace"):
            client_mod.request_turn([{"role": "user", "content": "hi"}],
                                    on_turn, on_fail)
        return failed, ok

    def test_a_clean_turn_records_a_success(self):
        """Control: the fixture reaches the real callback at all."""
        seen = []
        failed, ok = self.drive(lambda raw: seen.append(raw))
        self.assertTrue(seen)
        ok.assert_called()
        failed.assert_not_called()

    def test_a_caller_bug_records_no_transport_failure(self):
        def boom(_raw):
            raise AttributeError("'NoneType' object has no attribute 'id'")
        failed, ok = self.drive(boom)
        ok.assert_called()
        failed.assert_not_called()

    def test_and_the_failure_path_still_runs_for_the_caller(self):
        fell_back = []
        def boom(_raw):
            raise AttributeError("nope")
        self.drive(boom, on_fail=lambda: fell_back.append(1))
        self.assertEqual(fell_back, [1])
