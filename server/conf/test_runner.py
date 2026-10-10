"""The project's test runner: the default database is ALWAYS a test database.

Django's runner sets up a test database only for the aliases the suite's
Django-style test classes declare (`DiscoverRunner.get_databases`). A module
whose classes are all plain `unittest.TestCase` declares none, so when such a
module is run on its own the connection stays on the LIVE file and every
write it makes lands in production. That is how a test fixture put a real
account into `server/evennia.db3` and wedged the next reload for three hours
(#3738).

This runner adds the default alias to whatever the suite declared, so the
in-memory sqlite test database is created for every run, whatever the test
style. Serialisation stays as the suite declared it.
"""
from django.db import DEFAULT_DB_ALIAS

from evennia.server.tests.testrunner import EvenniaTestSuiteRunner


class GelatinousTestSuiteRunner(EvenniaTestSuiteRunner):

    def get_databases(self, suite):
        databases = dict(super().get_databases(suite))
        databases.setdefault(DEFAULT_DB_ALIAS, False)
        return databases
