"""A model call in flight does not hold a reload (#3815).

What went wrong: model calls ran on the reactor's worker pool
(``evennia.utils.run_async``). Twisted joins that pool's threads when
the reactor shuts down, so a reload issued while a model was still
answering held the old Server, and its pid file, until the answer came.
The Portal had already started the replacement, which found the pid
file and quit.

The first class here runs that shutdown for real, in a process of its
own with a real reactor and a real POST to a socket that never answers:
once with the call on the reactor's pool (the control, which must wait)
and once on ours (which must not). The rest
pin how results come back, the ceiling on calls in flight, and that
every door of the client goes through the one seam.
"""
import ast
import json
import os
import subprocess
import sys
import time
from unittest import TestCase, mock

from world.llm import client


def _fixed(name):
    """A name the fix adds, fetched late so this module still LOADS
    against the unfixed tree: a loader error is not evidence."""
    try:
        from world.llm import detached
    except ImportError:
        raise AssertionError("world.llm.detached does not exist: "
                             "the fix is not here") from None
    return getattr(detached, name)


#: Run in a process of its own: ``python -c SCENARIO <module file> <mode>
#: <seconds>``. Loads `detached.py` by path, so nothing of the game or
#: of Django is imported, and drives it under a real reactor.
SCENARIO = r'''
import importlib.util, json, socket, sys, threading, time
import requests
from twisted.internet import reactor, threads

path, mode, seconds = sys.argv[1], sys.argv[2], float(sys.argv[3])
spec = importlib.util.spec_from_file_location("detached", path)
detached = importlib.util.module_from_spec(spec)
spec.loader.exec_module(detached)
out = {}
main = threading.main_thread()


def say(**more):
    out.update(more)
    print(json.dumps(out), flush=True)


silent = socket.socket()                   # takes the connection, never answers
silent.bind(("127.0.0.1", 0))
silent.listen(1)
URL = "http://127.0.0.1:%d/v1/chat/completions" % silent.getsockname()[1]


def shutdown_with_a_call_in_flight():
    def work():
        # What the client's thread does: a blocking POST with a timeout.
        out["call_started"] = True
        out["worker_is_daemon"] = threading.current_thread().daemon
        session = requests.Session()
        session.trust_env = False          # no proxy between us and 127.0.0.1
        session.post(URL, json={"messages": []}, timeout=seconds)
        return "too late"

    if mode == "ours":
        detached.run_detached(work, lambda result: None, lambda fail: None)
    else:                                  # what run_async does
        threads.deferToThread(work).addErrback(lambda fail: None)

    def stop():
        out["stop_asked"] = time.monotonic()
        reactor.stop()
    reactor.callLater(0.5, stop)


def deliver():
    got = {}

    def finish(gave_up=False):
        if len(got) == 3 or gave_up:
            say(**got)
            reactor.stop()

    def returned(result):
        got["returned"] = [result, threading.current_thread() is main]
        finish()

    def failed(failure):
        got["failed"] = [failure.type.__name__,
                         threading.current_thread() is main]
        finish()

    def raises_on_return(result):
        raise KeyError("the caller's own bug")

    def chained(failure):
        got["chained"] = [failure.type.__name__,
                          threading.current_thread() is main]
        finish()

    def boom():
        raise ValueError("the backend is down")

    detached.run_detached(lambda: "answer", returned, failed)
    detached.run_detached(boom, returned, failed)
    detached.run_detached(lambda: "answer", raises_on_return, chained)
    reactor.callLater(6, finish, True)     # report what came, never hang


def ceiling():
    gate = threading.Event()
    started, done = [], []
    extra = 3
    total = detached.MAX_IN_FLIGHT + extra

    def work():
        started.append(1)
        gate.wait(10)

    def finished(_):
        done.append(1)
        if len(done) == total:
            say(finished=len(done))
            reactor.stop()

    for _ in range(total):
        detached.run_detached(work, finished, finished)

    def look(waited=0.0):
        # Wait for the workers to take what they can, then a little
        # longer: time for one too many to start, if it could.
        if len(started) < detached.MAX_IN_FLIGHT and waited < 5.0:
            reactor.callLater(0.1, look, waited + 0.1)
            return
        reactor.callLater(0.7, report)

    def report():
        say(limit=detached.MAX_IN_FLIGHT, asked=total,
            in_flight_while_held=len(started))
        gate.set()
    reactor.callLater(0.1, look)
    reactor.callLater(12, reactor.stop)    # never hang the test


reactor.callWhenRunning({"ours": shutdown_with_a_call_in_flight,
                         "reactor": shutdown_with_a_call_in_flight,
                         "deliver": deliver, "ceiling": ceiling}[mode])
reactor.run()
if "stop_asked" in out:
    say(reactor_returned_after=round(time.monotonic() - out["stop_asked"], 2))
'''


def run_scenario(mode, seconds=0.0, timeout=20):
    """Run SCENARIO; return (what it reported last, wall seconds, exit code).
    A process that is still there at the timeout is the fault itself:
    something waited on a thread."""
    began = time.monotonic()
    try:
        done = subprocess.run(
            [sys.executable, "-c", SCENARIO, _fixed("__file__"), mode,
             str(seconds)],
            capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as late:
        raise AssertionError(
            f"the process had not exited after {timeout} seconds: something "
            f"was still waiting on a thread. It had said: {late.stdout!r}"
        ) from None
    wall = time.monotonic() - began
    lines = [line for line in done.stdout.splitlines() if line.startswith("{")]
    report = json.loads(lines[-1]) if lines else {}
    report["stderr"] = done.stderr[-600:]
    return report, wall, done.returncode


class TestAShutdownWithACallInFlight(TestCase):
    """The reload race, reduced to its cause: does the process get out
    while a call is still waiting on its answer?"""

    def test_control_on_the_reactors_pool_the_shutdown_waits(self):
        """What `run_async` did. The model never answers and the call
        gives up after four seconds; the reactor cannot finish stopping
        until it has."""
        report, wall, code = run_scenario("reactor", seconds=4)
        self.assertTrue(report.get("call_started"), report)
        self.assertIs(report.get("worker_is_daemon"), False, report)
        self.assertGreaterEqual(report["reactor_returned_after"], 2.0, report)
        self.assertGreaterEqual(wall, 4.0)
        self.assertEqual(code, 0, report)

    def test_on_our_pool_the_shutdown_does_not_wait(self):
        """The call would wait thirty seconds for its answer. The
        reactor stops at once and the process is gone long before."""
        report, wall, code = run_scenario("ours", seconds=30, timeout=12)
        self.assertTrue(report.get("call_started"),
                        f"the call never started, so nothing was shown: {report}")
        self.assertIs(report.get("worker_is_daemon"), True, report)
        self.assertLess(report["reactor_returned_after"], 2.0, report)
        self.assertLess(wall, 8.0, report)
        self.assertEqual(code, 0, report)


class TestWhatComesBack(TestCase):

    def test_results_and_failures_arrive_on_the_reactor(self):
        report, _wall, code = run_scenario("deliver")
        self.assertEqual(code, 0, report)
        self.assertEqual(report.get("returned"), ["answer", True], report)
        self.assertEqual(report.get("failed"), ["ValueError", True], report)

    def test_an_exception_from_the_success_callback_reaches_the_errback(self):
        """Evennia's `run_async` chained them that way, and `_shielded`
        in the client exists because of it. Kept the same on purpose:
        only the pool changed."""
        report, _wall, _code = run_scenario("deliver")
        self.assertEqual(report.get("chained"), ["KeyError", True], report)


class TestTheCeiling(TestCase):

    def test_no_more_run_at_once_than_the_reactors_pool_allowed(self):
        report, _wall, code = run_scenario("ceiling")
        self.assertEqual(code, 0, report)
        self.assertEqual(report.get("limit"), 10, report)
        self.assertEqual(report.get("asked"), 13, report)
        self.assertEqual(report.get("in_flight_while_held"), 10, report)

    def test_the_ones_that_waited_run_afterwards(self):
        """The control for the test above: the three past the ceiling
        were held back, not dropped."""
        report, _wall, _code = run_scenario("ceiling")
        self.assertEqual(report.get("finished"), 13, report)


class TestEveryDoorOfTheClient(TestCase):
    """Four functions send something to a model. Each goes through the
    one seam, with a callback and an errback."""

    DOORS = {
        "request_turn": lambda: client.request_turn(
            [{"role": "user", "content": "hi"}], print, print),
        "request_embedding": lambda: client.request_embedding(
            "a line", print, print),
        "request_civic_line": lambda: client.request_civic_line(
            "be brief", "traffic", print, print),
        "request_civic_verdict": lambda: client.request_civic_verdict(
            "classify", "traffic", {"title": "V"}, print, print),
    }

    def test_each_request_is_handed_to_run_detached(self):
        self.assertIs(getattr(client, "run_detached", None),
                      _fixed("run_detached"),
                      "the client does not use the detached pool")
        for name, call in self.DOORS.items():
            with mock.patch.object(client, "run_detached") as seam, \
                    mock.patch.object(client, "requests") as net:
                call()
            self.assertEqual(seam.call_count, 1, name)
            (work,), wiring = seam.call_args
            self.assertTrue(callable(work), name)
            self.assertTrue(callable(wiring.get("at_return")), name)
            self.assertTrue(callable(wiring.get("at_err")), name)
            net.post.assert_not_called()    # nothing blocks the caller

    def test_the_client_no_longer_has_evennias_run_async(self):
        self.assertFalse(hasattr(client, "run_async"))


#: Code that still puts work on the reactor's pool, each with the reason
#: it is allowed to. Adding a path here is a decision: whatever it runs
#: there is waited for by every reload.
STILL_ON_THE_REACTORS_POOL = {
    # The `bug` command's calls to the issue tracker (ten-second cap).
    # The same fault in small; filed as #3856, not changed here.
    "commands/CmdBug.py",
}
BORROWS = {"run_async", "deferToThread", "callInThread"}


def borrowers(root):
    """Game files that call something which runs on the reactor's pool."""
    found = set()
    for folder in ("commands", "typeclasses", "world", "server", "web"):
        for here, dirs, files in os.walk(os.path.join(root, folder)):
            dirs[:] = [d for d in dirs if d not in ("tests", "__pycache__")]
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(here, name)
                with open(path, encoding="utf-8") as handle:
                    tree = ast.parse(handle.read())
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Call):
                        continue
                    called = getattr(node.func, "id", None) or getattr(
                        node.func, "attr", None)
                    if called in BORROWS:
                        found.add(os.path.relpath(path, root))
    return found


class TestNothingElseBorrowsThePool(TestCase):

    ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))

    def test_the_scan_can_see_a_borrower(self):
        """The control: the one known borrower is found."""
        self.assertIn("commands/CmdBug.py", borrowers(self.ROOT))

    def test_only_the_listed_files_use_the_reactors_pool(self):
        self.assertEqual(borrowers(self.ROOT), STILL_ON_THE_REACTORS_POOL)
