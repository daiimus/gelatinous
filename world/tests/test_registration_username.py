"""Registration's uniqueness loop must ask the question that gets asked.

The loop derives a username from the email's local part and bumps a
suffix until it is free. It tested `filter(username=...)` -- exact and
case-SENSITIVE -- while the constraint it exists to avoid is
case-INSENSITIVE: `EvenniaUsernameAvailabilityValidator`, run inside
`Account.create`, filters on `username__iexact`.

The email is lowercased before the split, so a lowercase derived name
could never collide case-sensitively with a mixed-case account. The loop
exited after zero iterations and `Account.create` then rejected the very
name the loop was written to avoid -- naming a username the user never
supplied, cannot see, and cannot override, since `register` takes only
an email and a password. Nine of 24 live accounts have mixed-case
usernames, each permanently blocking a distinct unused email (#2560).
"""
from django.test import TestCase
from evennia.accounts.models import AccountDB


from commands.unloggedin_email import derive_username as _derive


class TestTheUniquenessLoopMatchesTheConstraint(TestCase):
    def setUp(self):
        self.existing = AccountDB.objects.create(username="DrSpaceman2560",
                                                 email="held@example.com")

    def test_a_mixed_case_account_is_detected(self):
        """The failing case: lowercase derived name vs a mixed-case row."""
        self.assertNotEqual(_derive("drspaceman2560@elsewhere.com"),
                            "drspaceman2560")

    def test_the_derived_name_is_actually_free(self):
        derived = _derive("drspaceman2560@elsewhere.com")
        self.assertFalse(
            AccountDB.objects.filter(username__iexact=derived).exists(),
            "the loop handed back a name Account.create will reject")

    def test_an_exact_lowercase_collision_still_works(self):
        """The case that worked before must keep working."""
        AccountDB.objects.create(username="plainname2560",
                                 email="plain@example.com")
        derived = _derive("plainname2560@elsewhere.com")
        self.assertNotEqual(derived, "plainname2560")
        self.assertFalse(
            AccountDB.objects.filter(username__iexact=derived).exists())

    def test_an_uncontested_name_is_left_alone(self):
        """The pin: the loop must not rename people gratuitously."""
        self.assertEqual(_derive("nobodyhasthis2560@example.com"),
                         "nobodyhasthis2560")

    def test_it_keeps_bumping_past_several_collisions(self):
        AccountDB.objects.create(username="Crowded2560", email="a@example.com")
        AccountDB.objects.create(username="crowded2560_1", email="b@example.com")
        AccountDB.objects.create(username="CROWDED2560_2", email="c@example.com")
        derived = _derive("crowded2560@elsewhere.com")
        self.assertEqual(derived, "crowded2560_3")

    def test_the_source_uses_iexact(self):
        """Structural, so the two cannot drift apart again."""
        import inspect
        import commands.unloggedin_email as mod
        src = inspect.getsource(mod)
        self.assertIn("filter(username__iexact=username)", src)
        self.assertNotIn("filter(username=username)", src)
