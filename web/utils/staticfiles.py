"""Hashed static filenames (cache-busting).

Static assets shipped unversioned, so a CSS deploy stayed invisible
behind Cloudflare's edge cache until its TTL expired — the fix landed at
the origin and nobody could see it. Hashing the filename gives every
change a new URL, so caches can never serve a stale copy and may cache
each version forever.

``manifest_strict = False`` so a template referencing a file the manifest
does not know about falls back to the plain name instead of raising —
a missing asset should not 500 the site.
"""

from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class ForgivingManifestStaticFilesStorage(ManifestStaticFilesStorage):
    manifest_strict = False
