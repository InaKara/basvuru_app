# Validation of the delivered draft

Checked in the build environment on 2026-09-15. This records observed results;
it is not a claim that agent behavior or the Windows host was exercised.

- Python 3.13.15 on Linux; uv 0.12.11.
- `uv lock` generated a real lockfile; `uv sync --locked` built the editable
  package and exposed the `basvuru` CLI successfully.
- `uv run --locked python -m unittest discover -s tests -v`: **19 tests passed**.
- Tests cover four-table initialization, repeat initialization, Unicode/multiline
  text, NULL vs zero, unknown/protected fields, foreign references, schema drift,
  future schema refusal, migration rollback, read-only DB access, structured CLI
  errors, guarded task claiming, transaction rollback across record+task writes,
  interruption state, app-backlog transitions, snapshot/restore preservation,
  WAL commits in backups, metadata tampering, path labels and restore protections.
- All seven skill files passed the skill-creator structural validator.
- All Codex TOML files and Copilot YAML frontmatter parsed successfully; all ten
  wrappers refer to existing shared role skills.
- Bundled working DB and initial snapshot are empty schema-version-1 databases.
  Schema/reference comparison and integrity checks passed. Initial snapshot pair
  verified against its checksum and migration metadata.

Not tested here: native Windows execution, VS Code/Copilot discovery/delegation,
the local Codex desktop/CLI loading these project definitions, or actual research
and scoring behavior. Check host availability locally. Direct role-skill prompts
are documented as the fallback when a native role picker is unavailable.

Tests demonstrate helper behavior, not tamper-proof approvals or compliance by
all future LLM responses. The user's design and patch review remain workflow
requirements.
