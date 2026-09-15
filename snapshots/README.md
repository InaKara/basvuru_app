# Database snapshots

Keep each immutable `.sqlite` file with its same-stem `.json` metadata file.
Use `basvuru snapshot create/verify/restore` (see root README), not a byte copy of
an open DB. Snapshot pairs are tracked in Git; `data/pipeline.sqlite` is ignored.

The bundled `initial` pair contains the empty version-1 database. Its metadata
has no source commit if created before local Git initialization. Future snapshots
record Git state when available; a dirty tree is not reproducible from HEAD alone.

Stop processing and save checkpoints before handover. Commit approved source
changes, create the snapshot, then commit its exact pair. Transfer code and the
pair together. Explicitly select the snapshot when restoring. Never silently
merge divergent histories or assume the last filename is authoritative.

Snapshots accumulate; no automatic deletion/retention rule has been chosen.
