"""A bystander is not told your name (#2612, #2600).

Two leaks past the identity layer, in the same family.

## #2612 — `rent` broadcast the renter's real key

```python
caller.location.msg_contents(
    f"{caller.get_display_name(caller)} leases a locker.",
    exclude=[caller])
```

`get_display_name(caller)` is the **self** case — `characters.py` returns
`self.key` there, commented *"Self-perception — always own real name"*.
So the string was rendered *as the renter sees themselves* and pushed to
**people who are not the renter**. Everyone in the room learned the
renter's name regardless of what they knew.

**This is why it survived review: the code looks like it uses the
identity system.** #2600 is the same leak reached through a raw
attribute; this one goes through the recognition API and still leaks,
because the looker and the audience are different people.

Every other fixture verb in the repo — `bar.py`, `terminals.py` —
broadcasts through `msg_room_identity`, which renders per observer.

## #2600 — the off-shift keeper named itself by key

`_off_shift_deflection` returned `f"{speaker.key} isn't working this
shift."` straight to the buyer, with no per-observer rendering anywhere
between. A buyer who had never met the keeper was told their name — and
a buyer who *had* given them a nickname saw the key instead of it.

**The line the keeper SAYS still names the holder plainly, and
deliberately.** That is an NPC choosing to tell you a colleague's name
out loud, which is one of the ways a name is meant to be learned. Speech
content is not identity-rendered anywhere in this codebase, and the line
goes to the whole room, so there is no single observer to render it for.
Only the narration returned to the buyer is fixed.
"""
from evennia.utils.test_resources import EvenniaTest


class TestTheSelfBranchIsTheTrap(EvenniaTest):
    """Pinned, because the whole defect is that this call LOOKS right."""

    def test_looking_at_yourself_gives_your_real_key(self):
        self.assertEqual(self.char1.get_display_name(self.char1),
                         self.char1.key)

    def test_the_self_branch_is_explicit_in_the_source(self):
        """The other half — that a STRANGER reads an sdesc — is not
        asserted here. `char1` has no authored sdesc in this harness, so
        a stranger legitimately reads the key, and an assertion either
        way would be about the fixture rather than the code. The
        load-bearing fact is that the self branch returns the key
        unconditionally, which is what made broadcasting it a leak."""
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        body = (root / "typeclasses" / "characters.py").read_text(
            errors="ignore")
        self.assertIn("if looker is self:", body)
        self.assertIn("Self-perception", body)


class TestTheLockerBroadcastIsPerObserver(EvenniaTest):
    def _source(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / "typeclasses" / "lockers.py").read_text(errors="ignore")

    def test_the_broadcast_no_longer_renders_for_the_renter(self):
        body = self._source()
        self.assertNotIn(
            'f"{caller.get_display_name(caller)} leases a locker."', body)

    def test_it_uses_the_identity_broadcast(self):
        body = self._source()
        self.assertIn("msg_room_identity(", body)
        self.assertIn('template="{actor} leases a locker."', body)

    def test_the_renter_is_still_excluded(self):
        """They get their own second-person line; the room gets this."""
        self.assertIn("exclude=[caller]", self._source())

    def test_no_msg_contents_renders_for_the_caller(self):
        """The shape, swept across the fixtures — looker and audience
        differing is the leak wherever it appears."""
        import pathlib
        import re
        root = pathlib.Path(__file__).resolve().parents[2]
        offenders = []
        for sub in ("typeclasses", "commands", "world"):
            for path in (root / sub).rglob("*.py"):
                if "/tests/" in str(path):
                    continue
                text = path.read_text(errors="ignore")
                for match in re.finditer(r"msg_contents\(", text):
                    window = text[match.start():match.start() + 300]
                    if "get_display_name(caller)" in window:
                        offenders.append(path.name)
        self.assertEqual(offenders, [])


class TestTheKeeperRendersForTheBuyer(EvenniaTest):
    def test_the_deflection_takes_a_buyer(self):
        import inspect

        from typeclasses.shopkeeper import ShopContainer
        sig = inspect.signature(ShopContainer._off_shift_deflection)
        self.assertIn("buyer", sig.parameters)

    def test_the_narration_no_longer_uses_a_raw_key(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        body = (root / "typeclasses" / "shopkeeper.py").read_text(
            errors="ignore")
        self.assertNotIn('f"{speaker.key} isn\'t working this shift."', body)

    def test_the_narration_renders_for_an_observer(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        body = (root / "typeclasses" / "shopkeeper.py").read_text(
            errors="ignore")
        self.assertIn("speaker.get_display_name(buyer)", body)

    def test_the_call_site_passes_the_buyer(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        body = (root / "typeclasses" / "shopkeeper.py").read_text(
            errors="ignore")
        self.assertIn("self._off_shift_deflection(buyer)", body)

    def test_the_spoken_line_still_names_the_holder(self):
        """Deliberate, not an oversight: an NPC saying a colleague's
        name aloud is how a name is meant to be learned, and speech
        content is never identity-rendered."""
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        body = (root / "typeclasses" / "shopkeeper.py").read_text(
            errors="ignore")
        self.assertIn("{holder.key} has the {shift}", body)
