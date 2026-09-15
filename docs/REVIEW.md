# Review this draft before adopting it

This ZIP is a reviewable scaffold, not a deployment or an approved patch to an
existing application. Review the source and the SQL migration. No Windows files,
remote repository or account settings have been changed.

## Implemented requirements

- Python 3.13 + uv; standard-library runtime with SQLite.
- Four tables with all requested fields and three undetermined-purpose columns.
- Job-search work and application development have separate backlogs.
- Five roles, including the suggested reviewer, with shared procedures and thin
  Copilot/Codex adapters. A direct role prompt works without a native agent picker.
- Deterministic scripts perform CRUD, status transitions, migrations and snapshots.
- Database snapshots and metadata are Git-trackable; the active DB and venv are ignored.
- Design decision followed by concrete patch review for application changes.

## Starter conventions to inspect

These are explicit, reversible scaffold choices, not business rules supplied by
you. If you want a different interpretation, change this draft before adopting it.

| Choice | Implemented convention |
| --- | --- |
| “Added company/job listing/other” | `source_kind` plus nullable `source_id`, so a backlog task can identify its target. |
| Company/listing status | Nullable free text; no invented business vocabulary. |
| Job backlog status | pending, in_progress, blocked, done, cancelled. |
| App backlog status | needs_decision, planned, in_progress, awaiting_patch_review, done, cancelled. |
| App general-purpose column | `details TEXT`, used for description, decisions and relative review references. |
| Job company name | Supplied/captured text; `company_id` expresses the relationship. Renames do not silently rewrite it. |
| Future-purpose columns | Named `reserved`, initially NULL, blocked by ordinary helpers. |
| Keywords and portal structure | Free text; no extra schema, parser, taxonomy or executable content. |
| Score | Nullable numeric with no assumed scale or rubric. |
| Python | 3.13, no runtime dependencies beyond the standard library; uv_build is a build dependency. |
| Workflow ordering | One active operator, sequential delegation; no distributed locks or worker leases. |
| Deletion/deduplication | Not exposed until you define their semantics. |
| Migration tracking | SQLite user_version; no fifth application table. |
| Journal mode | SQLite's default rollback journal; backup is tested with WAL too. |

Inspect `migrations/0001_initial.sql` for exact column names and constraints.
Inspect `AGENTS.md` and the maintenance skill for the decision/review procedure.
The CLI flags and backlog states are not an authentication/authorization system.

## Intentionally undefined

Company search filters and qualification rules; duplicate matching; portal-specific
extraction and expiry rules; automatic follow-up triggers; job scoring algorithm,
weights and scale; statuses for companies/listings; the meaning of reserved fields.
Agents must ask when these are needed, not silently choose them.

## Review and install

For a new folder, inspect the ZIP's source and then follow README installation
when you accept the scaffold. For an existing repo, give this draft to a local
Codex instance and ask it to compare files, resolve substantive choices with you,
prepare the full patch including added files, and show it before applying it.
The local instance must inspect existing instructions/data and preserve your work.

No role configuration pins a paid model. The Codex desktop's Copilot-style direct
agent dropdown was not verified. Use the shared role-skill prompt in README.
The reviewer requests read-only tools/sandbox where supported; host overrides
can affect actual permissions. Do not treat its role name as a security boundary.
