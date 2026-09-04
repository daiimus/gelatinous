"""The service handler contract must be enforced, not just documented.

The module docstring published `handler(post, speech, patron, by)` while
`serve` called handlers with a fifth keyword. A handler written to the
docstring raised TypeError on EVERY line; the blanket except at the call
site swallowed it into `False` — which `serve`'s own docstring defines as
"the post did not claim it", an entirely ordinary outcome. The venue was
silently mute forever, with no error reaching the player or the room and
nothing in the log but a trace that looks like one of many (#2797).

Latent when found — all eight live registrations happen to match the real
signature — which is exactly what makes it a trap for the next venue
author rather than an active fault.
"""
from unittest import TestCase, mock

from world import service


def _four_arg(post, speech, patron, by):
    """A handler written to the OLD module docstring."""
    return True


def _five_arg(post, speech, patron, by, addressed=False):
    return True


class TestTheContractIsChecked(TestCase):
    def setUp(self):
        self._saved = dict(service.SERVICE)
        self.addCleanup(lambda: (service.SERVICE.clear(),
                                 service.SERVICE.update(self._saved)))

    def test_a_four_arg_handler_is_reported_at_registration(self):
        with mock.patch("evennia.utils.logger.log_err") as err:
            service.register("test_role", _four_arg)
        self.assertTrue(err.called, "a wrong signature registered silently")
        self.assertIn("never serve", err.call_args.args[0])

    def test_a_correct_handler_registers_quietly(self):
        with mock.patch("evennia.utils.logger.log_err") as err:
            service.register("test_role", _five_arg)
        self.assertFalse(err.called)

    def test_a_four_arg_on_receive_is_reported_too(self):
        def _wrong(post, obj):
            return True
        with mock.patch("evennia.utils.logger.log_err") as err:
            service.register("test_role", _five_arg, on_receive=_wrong)
        self.assertTrue(err.called)

    def test_a_correct_on_receive_registers_quietly(self):
        def _right(post, obj, giver, by):
            return True
        with mock.patch("evennia.utils.logger.log_err") as err:
            service.register("test_role", _five_arg, on_receive=_right)
        self.assertFalse(err.called)

    def test_no_on_receive_is_not_a_complaint(self):
        with mock.patch("evennia.utils.logger.log_err") as err:
            service.register("test_role", _five_arg, on_receive=None)
        self.assertFalse(err.called)


class TestTheMuteVenueIsLoud(TestCase):
    """A TypeError from CALLING the handler is categorically different
    from one raised inside it, and only the second is what the blanket
    except is defending against."""

    def _worker(self, handler):
        worker = mock.MagicMock()
        with mock.patch.object(service, "_ensure_loaded"), \
             mock.patch.object(service, "post_for", return_value="a post"), \
             mock.patch.object(service, "handler_for", return_value=handler), \
             mock.patch("evennia.utils.logger.log_err") as err, \
             mock.patch("evennia.utils.logger.log_trace") as trace:
            out = service.serve(worker, "a drink", mock.MagicMock())
        return out, err, trace

    def test_a_signature_mismatch_logs_an_error(self):
        out, err, trace = self._worker(_four_arg)
        self.assertFalse(out)
        self.assertTrue(err.called, "a mute venue left only a trace")
        self.assertIn("wrong signature", err.call_args.args[0])

    def test_a_failure_inside_the_handler_stays_a_trace(self):
        """The pin against the over-correction: a genuine fault inside a
        handler must not be reclassified as a signature problem."""
        def _explodes(post, speech, patron, by, addressed=False):
            raise TypeError("something inside went wrong")
        out, err, trace = self._worker(_explodes)
        self.assertFalse(out)
        self.assertFalse(err.called)
        self.assertTrue(trace.called)

    def test_a_working_handler_still_claims_the_line(self):
        out, err, trace = self._worker(_five_arg)
        self.assertTrue(out)
        self.assertFalse(err.called)
        self.assertFalse(trace.called)


class TestTheDocstringMatchesTheCall(TestCase):
    def test_the_module_docstring_publishes_five_arguments(self):
        """The docstring is the contract a venue author reads. It said
        four for years while the call site passed five."""
        self.assertIn("handler(post, speech, patron, by, addressed)",
                      service.__doc__)
