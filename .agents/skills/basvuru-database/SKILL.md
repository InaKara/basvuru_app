---
name: basvuru-database
description: Inspect and update Basvuru SQLite records and its job/app backlogs using the shared Python CLI. Use before any Basvuru database operation.
---

Read root `AGENTS.md` and [data-model.md](references/data-model.md) before a new
database assignment. Use [schema.sql](references/schema.sql) as a generated
reference; inspect the actual DB with `uv run --locked basvuru schema inspect`.
Use `schema check` after changes or when resuming unfamiliar work.

Commands run from the repository root. `--db PATH` before the command explicitly
selects a test/review DB; the default is this checkout's `data/pipeline.sqlite`.
Do not silently switch databases after an error.

1. Identify the task and target record IDs. Read what already exists.
2. Use `records list/show/add/update` with UTF-8 JSON input files. Look at `--help`
   and `docs/CLI.md` for exact arguments. Update by ID; do not auto-merge names.
3. Use `tasks` for operational work and `changes` for application development.
   Creation defaults are documented in the data model. Status transitions need
   the expected old status and a genuine progress/decision note.
4. If saving a new record and completing its running task together, use
   `tasks finish-with-record`; the helper performs both in one transaction.
   Other combined operations need an approved helper extension if atomicity matters.
5. Preserve unknown values as NULL. `score=0` is a value, not unknown. Never assign
   meaning to `reserved`; do not invent missing information or scoring criteria.
6. On `UNKNOWN_FIELD`, `SCHEMA_MISMATCH`, or another undefined operation, stop the
   affected write and follow `../basvuru-maintenance/SKILL.md`. Actual schema
   describes what exists; unexpected drift is not approval to adapt silently.
7. Persist completion, failure/blocker notes and affected IDs. Do not say a write
   succeeded without a successful helper result.

Routine CRUD has no delete or schema-edit command. A user request to add/remove a
field, delete records, or change their meaning follows maintenance. Migration
application is explicit and snapshots first. Skill text itself is not the schema.

If the DB or app backlog is unavailable, report that fact in the conversation.
Do not pretend a backlog write succeeded. Reconcile the recovery decision into
app backlog after the database becomes usable.
