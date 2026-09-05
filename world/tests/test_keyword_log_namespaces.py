"""The keyword audit log must not mix two namespaces in one column
(#2790).

`KeywordEvent.account_name` is documented as the acting ACCOUNT, and the
player writer fills it with a real account key. Both admin writers put
the acting CHARACTER there instead -- callers pass `caller.key`.

The live rows showed both at once:

    custom_set    account_name='monster'    character_name='Iver Kestrel I'
    admin_remove  account_name='Drivel X'   character_name=''

'monster' is an account. 'Drivel X' is a character -- confirmed: there
is an account named 'Drivel' and a character lineage Drivel, Drivel III,
IV, V, VI.

So `@keywords log player` matched a field that is only sometimes a
player: searching 'Iver Kestrel I' -- the name the log itself PRINTS --
returned nothing, and searching 'Drivel X' returned an admin row under a
"Keyword Events for player" heading. An audit log whose lookup silently
returns the wrong subset is worse than one that returns nothing.
"""
from django.test import TestCase

from world.models import KeywordEvent


class TestAdminEventsRecordBothNames(TestCase):
    def test_an_admin_add_records_the_character_and_the_account(self):
        from world.identity import add_approved_keyword
        add_approved_keyword("testkw2790a", "neutral",
                             "Drivel X", "Drivel")
        evt = KeywordEvent.objects.get(keyword="testkw2790a")
        self.assertEqual(evt.character_name, "Drivel X")
        self.assertEqual(evt.account_name, "Drivel")

    def test_an_admin_remove_records_both_too(self):
        from world.identity import add_approved_keyword, remove_approved_keyword
        add_approved_keyword("testkw2790b", "neutral", "Drivel X", "Drivel")
        remove_approved_keyword("testkw2790b", "neutral",
                                "Drivel X", "Drivel")
        evt = KeywordEvent.objects.filter(
            keyword="testkw2790b", event_type="admin_remove").get()
        self.assertEqual(evt.character_name, "Drivel X")
        self.assertEqual(evt.account_name, "Drivel")

    def test_a_character_name_never_lands_in_the_account_column(self):
        """The defect stated as an invariant."""
        from world.identity import add_approved_keyword
        add_approved_keyword("testkw2790c", "neutral", "Drivel X", "Drivel")
        evt = KeywordEvent.objects.get(keyword="testkw2790c")
        self.assertNotEqual(evt.account_name, "Drivel X")


class TestTheLogIsSearchableByWhatItPrints(TestCase):
    """The log line shows `char=` and `acct=`; a staff member types
    whichever they read, so both must resolve."""

    def _events_for(self, value):
        from django.db.models import Q
        return list(KeywordEvent.objects.filter(
            Q(account_name__iexact=value)
            | Q(character_name__iexact=value)))

    def setUp(self):
        KeywordEvent.objects.create(
            event_type="custom_set", keyword="kw2790",
            character_name="Iver Kestrel I", account_name="monster")

    def test_searching_the_character_name_finds_the_row(self):
        """The name the log prints, which previously matched nothing."""
        self.assertEqual(len(self._events_for("Iver Kestrel I")), 1)

    def test_searching_the_account_name_still_finds_it(self):
        """The pin: the lookup that already worked must keep working."""
        self.assertEqual(len(self._events_for("monster")), 1)

    def test_the_search_is_case_insensitive_on_both(self):
        self.assertEqual(len(self._events_for("iver kestrel i")), 1)
        self.assertEqual(len(self._events_for("MONSTER")), 1)

    def test_an_unrelated_name_finds_nothing(self):
        self.assertEqual(self._events_for("Nobody At All"), [])
