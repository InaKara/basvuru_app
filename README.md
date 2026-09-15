# Basvuru app

A small starting point for company research, job collection and job evaluation,
driven by agents in GitHub Copilot or Codex. Python provides exact database and
snapshot operations. Shared skills describe reusable procedures. You develop the
research methods and evaluation algorithm as you use the application.

**Review `docs/REVIEW.md` before adopting this draft.** It distinguishes your
requirements from the starter conventions used to make the scaffold runnable.
Nothing has been installed into `c:\git\basvuru_app` by this ZIP.

## Install and initialize

The ZIP contains one `basvuru_app` directory. Extract it under `c:\git`, yielding
`c:\git\basvuru_app\README.md`. If that folder already has content, inspect/merge
the draft first; do not overwrite an existing DB, Git history or instructions.
The ZIP has no `.git` or `.venv`; create those locally. An empty working DB and an
empty initial snapshot are included. They contain no companies, jobs or tasks.

Prerequisites: Git and uv, plus your existing Copilot or Codex installation and
account access. The application needs no model API key and starts no MCP server.

PowerShell:

```powershell
Set-Location 'c:\git\basvuru_app'
uv python install 3.13
uv sync --locked
uv run --locked basvuru init
uv run --locked basvuru status
uv run --locked basvuru schema check
```

`init` preserves an already-current DB. It does not overwrite, repair, upgrade or
restore an existing database. A fresh Git clone does not have the ignored working
DB: initialize a new one, or restore a chosen snapshot to continue existing work.

Initialize Git **only if this is not already its own repository**:

```powershell
git init -b main
git status --short
git add AGENTS.md README.md pyproject.toml uv.lock .python-version .gitignore .gitattributes
git add .agents .github .codex src migrations tests docs snapshots data/.gitkeep
git diff --cached --stat
git diff --cached
git commit -m "Initial Basvuru scaffold"
```

Inspect the staged changes before committing. Git may ask you to configure your
name/email; use your own identity.

To use a remote you created, supply its actual URL; no remote has been selected:

```powershell
git remote add origin <REMOTE_URL>
git push -u origin main
```

## Choose the agent you talk to

Open this repository root in your host. All five roles can communicate directly
with you. They share the same DB, backlog, and maintenance rules.

| Role | Skill / agent name | Initial responsibility |
| --- | --- | --- |
| Orchestrator | `basvuru-orchestrator` | Coordinate assignments, sequential delegation and decisions. |
| Company researcher | `basvuru-company-researcher` | Find companies and their information for your assignment. |
| Job collector | `basvuru-job-collector` | Retrieve and record listings from assigned portals. |
| Job evaluator | `basvuru-job-evaluator` | Apply your rubric; ask for it while undefined. |
| Reviewer/auditor | `basvuru-reviewer` | Report inconsistencies in proposed changes without repairing or approving them. |

**Copilot:** select the role from the VS Code chat agent dropdown. Definitions
are in `.github/agents/` and set `user-invocable: true`. No model is pinned.
The orchestrator has specialist delegation enabled; specialists cannot delegate.
If a host tool set is unavailable, report that capability gap rather than pretending
it ran. [Copilot custom-agent documentation](https://code.visualstudio.com/docs/agent-customization/custom-agents)

**Codex:** project TOML definitions are supplied for subagent use. For a direct
conversation in a selected role, explicitly select/mention the role skill where
your client supports it, or paste this prompt after substituting the role name:

```text
Read AGENTS.md and .agents/skills/basvuru-company-researcher/SKILL.md.
Act as the company researcher in this conversation and talk to me directly.
Inspect current backlog state, then ask for my research assignment.
```

Use `basvuru-orchestrator`, `basvuru-job-collector`, `basvuru-job-evaluator`, or
`basvuru-reviewer` in the same prompt for the other roles. Role skills define the
shared responsibilities once; both hosts' wrappers require reading them.

Codex CLI/IDE document `/skills` and `$` mentions. CLI `/agent` switches between
existing agent threads; it is not a promise of a Copilot-style primary-agent
dropdown in the desktop app. Explicitly loading a role skill changes the
conversation's instructions, not necessarily its tools/model permissions.
The desktop agent dropdown was not verified. [Codex skills](https://learn.chatgpt.com/docs/build-skills),
[Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)

Only one active operator/orchestrator should work on the DB at a time. Specialists
run sequentially. Pause one host before taking over in another. Starting a new
conversation reconstructs state from the DB; chat memory does not transfer.

## Layout

| Location | Purpose |
| --- | --- |
| `AGENTS.md` | Shared project behavior, decision boundaries and role selection. |
| `.agents/skills/` | Seven shared skills: five roles, database management, maintenance. |
| `.agents/skills/basvuru-database/references/` | Field meanings and generated schema. |
| `.github/agents/` | Thin Copilot role wrappers. |
| `.github/copilot-instructions.md` | Pointer to shared project rules. |
| `.codex/agents/` | Thin Codex custom-agent wrappers. |
| `.codex/config.toml` | One open delegated agent at a time. |
| `src/pipeline/` | CLI, validation, SQL operations, backlog, migrations and snapshots. |
| `migrations/` | Ordered SQL schema changes; never rewrite an applied migration. |
| `data/pipeline.sqlite` | Active DB; ignored by Git. |
| `snapshots/` | Immutable DB/metadata pairs, tracked in Git. |
| `docs/CLI.md` | Command examples and errors. |
| `docs/REVIEW.md` | Reviewable starter conventions and scope. |
| `docs/VALIDATION.md` | Actual validation evidence and host limitations. |
| `docs/changes/` | Concrete change proposals/patch evidence, linked from app backlog. |
| `tests/` | Focused persistence, transaction, migration and snapshot tests. |
| `pyproject.toml`, `uv.lock`, `.python-version` | Python package, lockfile and interpreter choice. |
| `.venv/`, optional `.env` | Machine-local environment/configuration, ignored by Git. |

## Database and backlogs

There are four tables: `companies`, `job_listings`, `job_backlog`, `app_backlog`.
See the database skill's `references/data-model.md` for all fields and meanings.
The three `reserved` fields remain NULL until you approve their purpose.
App backlog's general-purpose `details` holds description and decision notes.

Use `job_backlog` for company/job work. Use `app_backlog` for changes to the app,
including a missing field or unclear skill procedure. Both hold dated notes so
another host/computer can resume. There is no automatic scheduler, worker lease,
duplicate merger, scoring rubric, or automatic follow-up task creation yet.

The CLI refuses unknown fields, invalid references, protected-field writes and
unexpected schema drift. Its expected-prior-status update prevents two claims of
one pending task in a single database. This does not coordinate divergent copies
of the database or enforce exclusive operator access.

## Developing the app during use

Every agent must recognize missing rules. The reviewer checks proposed changes;
it is not the sole place where development awareness lives.

1. Record the missing capability/correction in app backlog; block affected work.
2. Present a concrete design and record your decision.
3. Prepare a complete patch in a separate review directory/worktree, with tests
   against a DB copy. Update affected code, migrations, model reference and skills.
4. Have the reviewer inspect it and present the exact patch for your review.
5. After your patch approval, stop affected work, snapshot, apply, verify, reread
   changed instructions, and resume the blocked task.

For a missing field, agents cannot silently use `reserved`, ALTER the table during
research, or say a write succeeded. `SKILL.md` changes if procedure changes;
field meanings normally change in `data-model.md`. Generated `schema.sql` comes
from migrations, not manual editing. Wrapper changes are needed only when their
host settings/routing change.

The draft is kept separate while awaiting review. Application files and SQLite
cannot be committed as one atomic transaction; a failed installation must report
its partial state and keep the change open. Changed instructions must be reread
before processing resumes. A host restart may be necessary for cached settings.

Use `docs/changes/TEMPLATE.md` for patch evidence. The SQLite row remains the
source of live status and user decisions. A reviewer recommendation is not your
approval. CLI confirmation flags acknowledge your review; they are not secure
approval tokens. Markdown policies cannot prevent every misuse of unrestricted
terminal access.

## Create snapshots and switch computers

Stop active work and save checkpoints first. Python's SQLite backup API produces
a consistent snapshot even if committed data is in WAL; copying an open `.sqlite`
file alone does not provide that guarantee. [Python backup API](https://docs.python.org/3.13/library/sqlite3.html#sqlite3.Connection.backup)

```powershell
uv run --locked basvuru snapshot create --label handover
```

The result returns the exact `.sqlite` and `.json` paths. Keep both together. The
JSON records checksum, schema, migration hashes and the source Git state if known.
Snapshots are never overwritten; historical pairs accumulate deliberately.

Commit approved source changes before a handover snapshot so it refers to a
reproducible code version. Then review and commit that exact snapshot pair:

```powershell
git add snapshots/<EXACT_NAME>.sqlite snapshots/<EXACT_NAME>.json
git diff --cached --stat
git commit -m "Database handover snapshot"
git push
```

On the other computer, stop its old session, pull, recreate/sync the environment,
and explicitly choose the snapshot:

```powershell
git pull
uv sync --locked
uv run --locked basvuru snapshot verify 'snapshots\<EXACT_NAME>.sqlite'
uv run --locked basvuru snapshot restore 'snapshots\<EXACT_NAME>.sqlite' --confirm-stopped
uv run --locked basvuru status
uv run --locked basvuru schema check
```

Restore refuses to overwrite an existing DB. If you decide to replace it, add
`--replace`; the helper first saves its current contents as a `pre_restore`
snapshot. Close all DB users. Restore refuses stale journal/WAL sidecars and does
not delete them. It cannot prove every external process has stopped; the flag
records your confirmation.

Snapshots from unknown/newer schema versions, corrupted pairs or different
applied migrations are rejected. An older compatible snapshot is reported as
needing migration; it is not auto-upgraded. Use explicit reviewed migrations:

```powershell
uv run --locked basvuru migrate --confirm-reviewed --confirm-stopped
```

The command snapshots before changing schema. Use those flags only after the
actual design and patch approval. `init` never upgrades an existing DB.

After handover, inspect in-progress tasks; do not automatically reset them. For
whole-folder transfer, copy `.git` if you want the same Git history/remotes, plus
source and snapshots. Recreate `.venv` rather than relying on a copied environment.
[Python virtual environment portability](https://docs.python.org/3.13/library/venv.html#how-venvs-work)

Git cannot merge SQLite rows from independently modified databases. Multiple
snapshot filenames may coexist without representing a merged history. If both
computers changed data, stop and decide how to reconcile; do not silently select
the newest filename. Snapshot history may contain personal information: choose
your remote and its access accordingly.

## Verification and known limits

```powershell
uv run --locked python -m unittest discover -s tests -v
```

Tests use temporary databases, including a WAL backup check. `docs/VALIDATION.md`
records the actual environment and results. Host discovery and Windows execution
must be checked on your machine; Python tests do not prove agent-host behavior.

The package is intended for an editable checkout managed by `uv sync`, not a
standalone wheel installation: migrations and skills live in the repository.
No external crawler, model service, MCP server or front end is installed.
