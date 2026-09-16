# Build scripts — legacy, one-shot

These numbered scripts constructed the city, one build each, in order. They
were each run **once** against the live database and are kept as the record
of how the world was made (what was placed where, and under which issue).

- **Never re-run one.** They create rooms, exits and objects; a second run
  duplicates them.
- **Imports may rot.** A script references the code as it stood on its
  build day; classes it imports may since have been removed (e.g. 048, 066
  and 068 import a `Shopkeeper` typeclass that was folded into the single
  NPC typeclass in #2378). That is expected for a historical log and is not
  fixed.
- **New builds** follow `specs/BUILDING_PLAYBOOK.md`; the playbook, not
  these files, is the how-to.

Owner ruling 2026-09-15: keep as history, document as legacy.
