"""No submodule is shadowed by a same-named attribute (#2754).

`world/director/__init__.py` did:

    from world.director.dispatch import dispatch

Importing the submodule sets `world.director.dispatch = <module>`; the
`from ... import` then overwrites that same package attribute with the
FUNCTION. The submodule stays in `sys.modules`, so it is never reloaded
and the attribute stays a function for the life of the process.

It was armed rather than firing. Every production caller writes
`from world.director.dispatch import X`, which resolves through
`sys.modules`. What breaks is ATTRIBUTE access: anyone writing
`from world.director import dispatch as dmod` -- by analogy with the
five `import world.director.<mod> as X` sites that already exist for
other submodules -- gets a function, and the first attribute access on
it fails. And ~30 `mock.patch("world.director.dispatch.*")` targets keep
working only because 3.12+ resolves patch targets with
`pkgutil.resolve_name` (importlib first); the older getattr-first
resolver raises AttributeError at patch time.

A guard rather than a one-off fix, because the shape is invisible in
review: the import line looks completely ordinary, and nothing fails
until someone reaches for the module by attribute.

THREE SHADOWS ARE DELIBERATE AND STAY. `weather_system`, `time_system`
and `crowd_system` are module-level SINGLETONS named after their own
module, so `from world.weather import weather_system` hands back the
instance on purpose. They carry the same hazard for `mock.patch` on
those dotted paths, which is worth knowing, but they are an API choice
rather than an accident -- so they are pinned by name here instead of
being "fixed" into something nobody asked for.

If a fourth appears, this fails and the author gets to decide which kind
it is.
"""
import importlib
import pkgutil
import types

from evennia.utils.test_resources import EvenniaTest

#: Shadows that are a deliberate singleton-named-after-its-module.
#: (package, attribute name)
KNOWN_SINGLETONS = {
    ("world.crowd", "crowd_system"),
    ("world.weather", "time_system"),
    ("world.weather", "weather_system"),
}

ROOTS = ("world", "typeclasses", "commands")


def _shadowed():
    found = set()
    for root in ROOTS:
        try:
            pkg = importlib.import_module(root)
        except Exception:  # noqa: BLE001 — an unimportable root is another test's problem
            continue
        packages = [pkg]
        for mod in pkgutil.walk_packages(pkg.__path__, prefix=root + "."):
            if not mod.ispkg:
                continue
            try:
                packages.append(importlib.import_module(mod.name))
            except Exception:  # noqa: BLE001
                continue
        for package in packages:
            for _finder, name, _ispkg in pkgutil.iter_modules(package.__path__):
                got = getattr(package, name, None)
                if got is not None and not isinstance(got, types.ModuleType):
                    found.add((package.__name__, name))
    return found


class TestThePackageAttributeIsTheModule(EvenniaTest):

    def test_the_sweep_actually_finds_things(self):
        """Control. An empty sweep would satisfy every assertion below
        while checking nothing -- and this walks packages that can fail
        to import, so "found nothing" is a real possible bug."""
        self.assertTrue(_shadowed(),
                        "the sweep found no packages at all")

    def test_only_the_known_singletons_shadow_a_submodule(self):
        unexpected = _shadowed() - KNOWN_SINGLETONS
        self.assertEqual(
            unexpected, set(),
            "a submodule is shadowed by a same-named attribute: "
            f"{sorted(unexpected)}. Export it under a different name, or "
            "add it to KNOWN_SINGLETONS if it is a deliberate instance.")

    def test_director_dispatch_is_a_module(self):
        """The specific one #2754 was filed for."""
        import world.director as pkg
        self.assertIsInstance(getattr(pkg, "dispatch", None),
                              types.ModuleType)

    def test_the_function_is_still_reachable_from_the_facade(self):
        """Renamed, not removed."""
        from world.director import dispatch_event
        self.assertTrue(callable(dispatch_event))
