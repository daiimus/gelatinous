"""Two reports that described something that did not happen
(#2596, #2613).

## #2596 — "You remove a coverall" for a coverall that tore apart

`remove_item` fires the garment's `at_removed` hook, **discards its
return value**, and then unconditionally reports *"You remove
&lt;item&gt;."* For single-use issue clothing the hook calls `_perish`,
which narrates *"tears along its welded seams"* to the wearer and the
room and then `delete()`s the object.

So the player was told it came apart, then told they had folded it away,
for an object that no longer exists.

**The callers needed fixing too.** `.key` still reads after `delete()` —
the cached value survives, `pk` does not — so `undress` with no argument
was appending a destroyed garment's name to *"You remove: …"* regardless
of what `remove_item` returned. Fixing only the mixin would have left
that path lying.

## #2613 — MudInfo logged 2,847 disconnects and zero connects

`Account.at_post_login` replaces Evennia's default wholesale. The
default does three things before it puppets:

1. restore `_saved_protocol_flags` onto the session
2. send the `logged_in` OOB message to the client
3. post *"|G{key} connected|n"* to the connect channel

The override dropped **all three**. `at_disconnect` is not overridden,
so its matching red line still posts — staff saw every departure and no
arrivals, in the channel whose job is telling them who is on.

The issue reported only the connect line; the protocol-flag restore and
the `logged_in` OOB were also gone.

Restored inline rather than by calling `super()`: the default **ends by
auto-puppeting**, and the override exists precisely to do that
differently — calling it would run puppeting twice.
"""
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class _GarmentCase(EvenniaTest):
    def garment(self, key="a coverall", single_use=False):
        obj = create_object("typeclasses.items.Item", key=key,
                            location=self.char1)
        obj.coverage = ["chest"]
        obj.worn_desc = key
        if single_use:
            obj.db.single_use = True
        return obj


class TestADeletedObjectStillAnswers(_GarmentCase):
    """The trap under #2596: `pk` is the only honest test."""

    def test_key_survives_deletion(self):
        item = self.garment()
        item.delete()
        self.assertEqual(item.key, "a coverall")

    def test_pk_does_not(self):
        item = self.garment()
        item.delete()
        self.assertIsNone(item.pk)


class TestATornGarmentIsNotRemoved(_GarmentCase):
    def tearing_garment(self):
        item = self.garment()
        self.assertTrue(self.char1.wear_item(item)[0])

        def _tear(wearer):
            item.delete()
        item.at_removed = _tear
        return item

    def test_the_removal_reports_nothing(self):
        item = self.tearing_garment()
        success, message = self.char1.remove_item(item)
        self.assertTrue(success)
        self.assertEqual(message, "")

    def test_an_intact_garment_still_reports(self):
        """The control — the fix must silence only the torn case."""
        item = self.garment("a work shirt")
        self.assertTrue(self.char1.wear_item(item)[0])
        success, message = self.char1.remove_item(item)
        self.assertTrue(success)
        self.assertIn("work shirt", message)


class TestTheCallersDoNotNameIt(EvenniaTest):
    """`.key` reads fine on a deleted object, so every caller that
    builds a list from it needs the `pk` test too."""

    def _source(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / "commands" / "CmdClothing.py").read_text(
            errors="ignore")

    def test_the_remove_all_path_checks_survival(self):
        self.assertIn('if success and getattr(item, "pk", 1) is not None:',
                      self._source())

    def test_the_third_party_path_checks_survival(self):
        body = self._source()
        self.assertEqual(
            body.count('getattr(item, "pk", 1) is not None'), 2,
            "both remove_item callers must test survival")

    def test_an_empty_message_is_not_printed(self):
        self.assertIn("if message:\n            caller.msg(message)",
                      self._source())


class TestTheLoginAnnouncesItself(EvenniaTest):
    def _source(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / "typeclasses" / "accounts.py").read_text(
            errors="ignore")

    def test_it_posts_a_connect_line(self):
        self.assertIn("_send_to_connect_channel", self._source())

    def test_the_line_matches_evennias_wording(self):
        """Staff read these two lines as a pair; the disconnect half is
        Evennia's and untouched."""
        self.assertIn('f"|G{self.key} connected|n"', self._source())

    def test_it_restores_saved_protocol_flags(self):
        self.assertIn("_saved_protocol_flags", self._source())

    def test_it_sends_the_logged_in_oob(self):
        self.assertIn("session.msg(logged_in={})", self._source())

    def test_it_does_not_call_super(self):
        """`super()` would auto-puppet a second time — the very thing
        this override exists to do differently."""
        self.assertNotIn("super().at_post_login", self._source())

    def test_the_announcement_cannot_block_a_login(self):
        body = self._source()
        idx = body.index("_send_to_connect_channel")
        self.assertIn("except Exception", body[idx - 200:idx + 300])


class TestEvenniaStillDoesTheseThings(EvenniaTest):
    """Pinned against the installed default, so an upgrade that changes
    the preamble is visible rather than silently diverging again."""

    def _default(self):
        import inspect

        from evennia.accounts.accounts import DefaultAccount
        return inspect.getsource(DefaultAccount.at_post_login)

    def test_the_default_posts_a_connect_line(self):
        self.assertIn("_send_to_connect_channel", self._default())

    def test_the_default_restores_flags_and_sends_logged_in(self):
        src = self._default()
        self.assertIn("_saved_protocol_flags", src)
        self.assertIn("logged_in={}", src)

    def test_the_default_also_auto_puppets(self):
        """Which is why this is copied rather than delegated."""
        self.assertIn("puppet_object", self._default())

    def test_at_disconnect_is_not_overridden_here(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        body = (root / "typeclasses" / "accounts.py").read_text(
            errors="ignore")
        self.assertNotIn("def at_disconnect", body)
