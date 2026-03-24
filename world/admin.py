"""Django admin registration for ``world`` models."""

from django.contrib import admin

from world.models import KeywordEvent


@admin.register(KeywordEvent)
class KeywordEventAdmin(admin.ModelAdmin):
    """Admin view for :class:`~world.models.KeywordEvent`."""

    list_display = (
        "timestamp",
        "event_type",
        "keyword",
        "character_name",
        "account_name",
        "gender_list",
    )
    list_filter = ("event_type", "gender_list")
    search_fields = ("keyword", "character_name", "account_name")
    readonly_fields = ("timestamp",)
    date_hierarchy = "timestamp"
    ordering = ("-timestamp",)
