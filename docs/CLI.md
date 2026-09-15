# CLI examples

Run from the repository root with `uv run --locked basvuru`. Use `--help` on any
command. `--db PATH` is a global option and goes before the command. It explicitly
selects a different working database; tests and review drafts should use it.

Results are JSON on stdout. Operational errors are JSON on stderr and exit with
code 1; argument/help messages follow argparse's normal behavior. UTF-8 input
with or without a BOM is accepted. Never interpolate arbitrary job text into shell
commands: place it in a JSON file with properly escaped line breaks/quotes.

## Records

Create `company.json` with `{"name":"Example GmbH","webpage":"https://example.com"}`:

```powershell
uv run --locked basvuru records add companies --input company.json
uv run --locked basvuru records list companies --limit 20
uv run --locked basvuru records show companies 1
uv run --locked basvuru records update companies 1 --input company-update.json
```

Use the actual returned ID, not necessarily 1. An update input contains only the
fields to change, such as `{"brief_info":"Verified information goes here."}`.

Listing input example (replace ID with the existing company ID):

```json
{
  "title": "Example role",
  "company_id": 1,
  "company_name": "Example GmbH",
  "webpage": "https://example.com/jobs/example",
  "full_text": "The complete retrieved listing text goes here.\nNext line.",
  "score": null
}
```

No example is loaded into the delivered DB. `records add/update` is limited to
companies/listings. `records list/show` can inspect any of the four tables.
Use dedicated commands to write backlogs. Unknown/protected fields are rejected.

## Operational tasks

Task input: `{"source_kind":"company","source_id":1,"task_definition":"Inspect this company's career portal and report the next decision needed."}`.

```powershell
uv run --locked basvuru tasks add --input task.json
uv run --locked basvuru tasks list --status pending
uv run --locked basvuru tasks transition 1 --from pending --to in_progress --note 'Starting the assigned task.'
uv run --locked basvuru tasks note 1 --input progress.txt
uv run --locked basvuru tasks transition 1 --from in_progress --to blocked --note 'Need the user to define the collection rule; see app backlog 1.'
```

For a new record that also completes a running task atomically:

```powershell
uv run --locked basvuru tasks finish-with-record 1 job_listings --input listing.json --note 'Saved the assigned listing.'
```

This inserts a new result; it does not upsert or deduplicate. It rolls back the
record if task completion fails. Updating an existing record plus completing a
task atomically is not exposed yet; extend the helper via maintenance if needed.

## App changes and decisions

Change input: `{"type":"change","details":"Define a missing field. Operational task 1 is blocked. Ask the user for its meaning and proposed storage."}`.

```powershell
uv run --locked basvuru changes add --input change.json
uv run --locked basvuru changes list
uv run --locked basvuru changes note 1 --input user-decision.txt
uv run --locked basvuru changes transition 1 --from needs_decision --to planned --note 'The user decided the design; see the dated decision above.'
```

Use the genuine user response in the text file. A note is a record, not proof of
approval. After preparing a draft, progress through in_progress and
awaiting_patch_review. Move to done only after the user reviews that patch and it
has been applied and verified. Reviewer findings can be appended using `changes note`.

## Schema, snapshots and tests

```powershell
uv run --locked basvuru schema inspect
uv run --locked basvuru schema check
uv run --locked basvuru schema export --output '.agents\skills\basvuru-database\references\schema.sql'
uv run --locked basvuru snapshot create --label manual
uv run --locked basvuru snapshot verify 'snapshots\<EXACT_NAME>.sqlite'
uv run --locked python -m unittest discover -s tests -v
```

Export changes a file; use it in the reviewed draft when migrations change.
Snapshot restore and migration application are covered in README because they
affect the active DB. Snapshot pairs must keep their original filename relationship.

Common errors: `DB_NOT_INITIALIZED`, `SCHEMA_MISMATCH`, `REFERENCE_MISMATCH`,
`UNKNOWN_FIELD`, `INVALID_REFERENCE`, `INVALID_TRANSITION`, `STATE_CONFLICT`,
`NEEDS_USER_DECISION`, `TARGET_EXISTS`, `INVALID_SNAPSHOT`. Inspect the reported
path/ID and use maintenance where meaning or schema is missing. Do not bypass an
error with raw SQL or a second database.
