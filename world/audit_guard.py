"""Is a test runner driving this process?

Both audit logs write to ``settings.LOG_DIR``, which the test settings
do not override, so a suite run appends its fixtures and mock
exceptions to the PRODUCTION logs (#2328).

Lives here rather than in either audit module because BOTH need it and
the check is subtle enough that two copies would drift -- the first
version looked correct, checked for the ``test_``-prefixed database the
Django docs describe, and still let six lines through.
"""

import os
import sys


def under_test() -> bool:
    """True when a test runner owns this process.

    Detected by the DATABASE, not by argv alone: Django's test runner
    swaps in a throwaway database, and that holds however the suite was
    invoked. Evennia's is IN-MEMORY
    (``file:memorydb_default?mode=memory&cache=shared``) rather than the
    ``test_``-prefixed file the docs describe, which is the detail that
    had to be measured rather than assumed.

    Fails OPEN -- if it cannot tell, it keeps logging. A missing audit
    line is worse than a stray one.
    """
    # The runner itself. `evennia test ...` is how the suite is always
    # invoked here, and this is true before any database exists.
    if "test" in sys.argv[:3]:
        return True
    try:
        from django.db import connection
        name = str(connection.settings_dict.get("NAME") or "")
    except Exception:  # noqa: BLE001 — cannot tell, so keep logging
        return False
    return ("memory" in name
            or os.path.basename(name).startswith("test_"))
