---
name: basvuru-maintenance
description: Propose, draft, review, and apply changes to the evolving Basvuru application. Use for missing schema/procedures, user corrections, bugs, and new capabilities.
---

Follow root `AGENTS.md`. The user must decide the design and then review the
concrete patch. The reviewer helps find inconsistencies; it cannot grant either
approval. Existing approved procedures do not need repeated design approval.

1. Preserve completed work and stop the affected unsupported operation. Use the
   database skill to block the operational task and create/reuse an app-backlog
   item. Describe the missing rule or correction and link the two IDs.
2. Present a minimal concrete proposal, its affected files/data, and the decision
   needed. Ask rather than assigning meaning to fields or silently adding rules.
   Record the actual user's answer in app-backlog details.
3. Once the design is decided, prepare the complete patch in an isolated draft
   directory/worktree, with a snapshot/copy for DB tests. Do not apply the draft
   to active skills or the active database while awaiting review.
4. Use `docs/changes/TEMPLATE.md` for evidence under `docs/changes/<id>/`. Keep
   live task status/decisions in the SQLite backlog; reference files by relative
   path. Include new files in the patch, not just tracked-file edits.
5. Add a numbered migration for schema changes. Update relevant Python callers,
   data-model meanings, and generated schema reference. Update skills if their
   procedure changes and wrappers if their role/tools/routing change. One source
   of truth per fact; do not copy new rules into every agent.
6. Test affected behavior and ask basvuru-reviewer to inspect the draft. The
   orchestrator records findings. Fix within the agreed scope; ask if new design
   decisions arise. No parallel writers or nested agents.
7. Show the actual patch, SQL changes, test/audit evidence, and effect summary.
   Identify the exact patch revision (for example SHA-256). Record
   awaiting_patch_review and wait for the user's review. Revised executable
   content needs review of the revised patch.
8. After patch approval, check for intervening changes, stop affected agents and
   DB users, snapshot, and apply the approved files/migrations. The CLI migrate
   command snapshots and needs --confirm-reviewed --confirm-stopped; these flags
   acknowledge a real decision, never manufacture one.
9. Check installed schema and affected behavior. Filesystem changes and SQLite
   transactions are not one atomic operation. On partial failure keep the item
   open, describe the actual state, and recover using the patch/snapshot as
   appropriate. Never mark done merely because editing finished.
10. Reread changed instructions before resuming. Restart the host if configuration
    remains cached. Record completion/evidence, mark done and explicitly resume
    the blocked task. Commit/push only if the user requested it.

Mechanical schema/reference checks catch structural drift; the reviewer checks
semantic consistency. Neither guarantees every future agent follows Markdown
instructions. If backlog storage itself is broken, report the blocker in chat
and record the approved recovery under docs/changes until it can be reconciled.
