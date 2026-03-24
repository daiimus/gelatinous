"""Django models for the ``world`` package.

Currently contains only the :class:`KeywordEvent` model used by the
identity keyword tracking system.
"""

from django.db import models


class KeywordEvent(models.Model):
    """Audit log entry for keyword-related events.

    Tracks three kinds of events:

    * **custom_set** — A player set a custom (non-approved) keyword via
      ``@shortdesc``.
    * **admin_add** — An admin added a keyword to the approved list via
      ``@keywords add``.
    * **admin_remove** — An admin removed a keyword from the approved
      list via ``@keywords remove``.

    Displayed in the Evennia admin interface and queryable via the
    ``@keywords log`` command.
    """

    EVENT_TYPES = [
        ("custom_set", "Custom Keyword Set"),
        ("admin_add", "Admin Added to Approved List"),
        ("admin_remove", "Admin Removed from Approved List"),
    ]

    GENDER_LISTS = [
        ("", "N/A"),
        ("feminine", "Feminine"),
        ("masculine", "Masculine"),
        ("neutral", "Neutral"),
    ]

    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPES,
        db_index=True,
        help_text="The kind of keyword event.",
    )
    keyword = models.CharField(
        max_length=20,
        db_index=True,
        help_text="The keyword string that was set, added, or removed.",
    )
    character_name = models.CharField(
        max_length=80,
        blank=True,
        default="",
        help_text="Character key at the time of the event (for custom_set).",
    )
    account_name = models.CharField(
        max_length=80,
        blank=True,
        default="",
        db_index=True,
        help_text="Account key for attribution.",
    )
    gender_list = models.CharField(
        max_length=10,
        choices=GENDER_LISTS,
        blank=True,
        default="",
        help_text="Which gender list (for admin_add / admin_remove).",
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the event occurred.",
    )

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "keyword event"
        verbose_name_plural = "keyword events"

    def __str__(self) -> str:
        return f"[{self.event_type}] {self.keyword} ({self.timestamp:%Y-%m-%d %H:%M})"
