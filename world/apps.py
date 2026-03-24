"""Django application configuration for the ``world`` package."""

from django.apps import AppConfig


class WorldConfig(AppConfig):
    """AppConfig for the world package.

    Registers ``world`` as a Django app so that custom models
    (e.g. :class:`~world.models.KeywordEvent`) are discovered by the
    ORM and appear in the Evennia admin interface.
    """

    name = "world"
    verbose_name = "World"
    default_auto_field = "django.db.models.BigAutoField"
