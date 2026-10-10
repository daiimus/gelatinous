"""Run on its own, a module of plain `unittest.TestCase` classes used to run
against the LIVE database (#3738): Django sets up a test database only for
the aliases Django-style test classes declare, and this module declares
none. This file is deliberately plain so it exercises exactly that path. It
must pass when run alone: `evennia test --settings settings.py
world.tests.test_the_test_database_is_never_the_live_one`.
"""
from unittest import TestCase

from django.db import connection


class TestTheConnectionIsATestDatabase(TestCase):

    def test_the_default_alias_is_in_memory_not_the_live_file(self):
        name = str(connection.settings_dict["NAME"])
        self.assertIn("mode=memory", name, f"the test run is on {name!r}")
        self.assertNotIn("evennia.db3", name)

    def test_the_file_list_names_no_disk_database(self):
        with connection.cursor() as cur:
            cur.execute("PRAGMA database_list")
            files = [row[2] for row in cur.fetchall()]
        self.assertFalse(any(f.endswith(".db3") for f in files), files)
