"""
Custom authentication backend for email-based login.

This allows users to log into the website using their email address
instead of their username, matching the telnet email-based login system.
"""

from django.contrib.auth.backends import ModelBackend
from evennia.accounts.models import AccountDB


class EmailAuthenticationBackend(ModelBackend):
    """
    Authenticate using email address instead of username.

    This backend allows the Django web login to accept email addresses,
    aligning with the telnet email-based login system.

    Overriding ``authenticate`` and ``get_user`` means opting out of two
    protections ``ModelBackend`` performs for free, both of which were
    lost silently. Evennia's own ``CaseInsensitiveModelBackend`` defines
    only ``authenticate`` and keeps the rest; the divergence was local to
    this repository. See #2750 (timing) and #2751 (is_active).
    """

    def _burn_a_hash(self, password):
        """Run one password hash and throw the result away.

        Django does this on its own unknown-user branch, with a comment
        naming the reason (#20760): without it, "no such account"
        returns in ~0.5 ms while "wrong password" takes ~457 ms, a
        difference of roughly 850x that tells an attacker which emails
        are registered. Account enumeration is a stated in-scope threat
        here — the MESSAGE channel is handled on both doors, one generic
        failure for both causes, and the timing channel was not (#2750).

        The object is never saved; only the hasher's cost is wanted.
        """
        try:
            AccountDB().set_password(password)
        except Exception:  # noqa: BLE001 — a mitigation must not become a fault
            pass

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate user by email address.

        Args:
            request: The HTTP request object
            username: Actually contains the email address from the login form
            password: User's password

        Returns:
            Account object if authentication succeeds, None otherwise
        """
        if username is None or password is None:
            return None

        try:
            # Try to find account by email (case-insensitive)
            account = AccountDB.objects.get(email__iexact=username)
        except AccountDB.DoesNotExist:
            # Email not found. Spend the same work a real check costs,
            # or the response time answers the question the generic
            # error message refuses to (#2750).
            self._burn_a_hash(password)
            return None
        except AccountDB.MultipleObjectsReturned:
            # Shouldn't happen, but it is still a failure that must not
            # return faster than a real one.
            self._burn_a_hash(password)
            return None

        if not account.check_password(password):
            return None
        # `user_can_authenticate` is `is_active`. ModelBackend applies it
        # after the password check and this override dropped it, so
        # deactivating an account did not stop it logging IN either —
        # not merely a matter of surviving sessions (#2751).
        if not self.user_can_authenticate(account):
            return None

        # Set backend attribute required by Django
        account.backend = "web.utils.auth_backends.EmailAuthenticationBackend"
        return account

    def get_user(self, user_id):
        """
        Get user by ID (required by ModelBackend).

        Django calls this on EVERY request carrying an auth session, and
        it is the designated place where a deactivated account's existing
        sessions die. Dropping the `is_active` gate meant unchecking
        "Active" in the admin — the only lever this codebase surfaces —
        had no effect on a browser already holding a cookie, for up to
        the full 14-day SESSION_COOKIE_AGE (#2751).

        Args:
            user_id: The user's database ID

        Returns:
            Account object or None
        """
        try:
            account = AccountDB.objects.get(pk=user_id)
        except AccountDB.DoesNotExist:
            return None
        return account if self.user_can_authenticate(account) else None
