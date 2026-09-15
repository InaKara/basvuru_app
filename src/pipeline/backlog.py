"""Small guarded state machines; approvals remain user decisions, not flags."""
from . import db
from .common import now, require

TRANSITIONS = {
    'job_backlog': {
        'pending': {'in_progress', 'cancelled'},
        'in_progress': {'pending', 'blocked', 'done', 'cancelled'},
        'blocked': {'pending', 'cancelled'}, 'done': set(), 'cancelled': set(),
    },
    'app_backlog': {
        'needs_decision': {'planned', 'cancelled'},
        'planned': {'in_progress', 'needs_decision', 'cancelled'},
        'in_progress': {'awaiting_patch_review', 'needs_decision', 'cancelled'},
        'awaiting_patch_review': {'in_progress', 'needs_decision', 'done', 'cancelled'},
        'done': set(), 'cancelled': set(),
    },
}


def transition_in(conn, table, row_id, before, after, note):
    require(table in TRANSITIONS and after in TRANSITIONS[table].get(before, set()), 'INVALID_TRANSITION', f'Not allowed: {before} -> {after}')
    require(isinstance(note, str) and bool(note.strip()), 'INVALID_INPUT', 'A progress/decision note is required.')
    field = 'task_definition' if table == 'job_backlog' else 'details'
    stamp = now()
    cursor = conn.execute(
        f"UPDATE {table} SET status=?, date_updated=?, {field}=COALESCE({field},'') || ? WHERE id=? AND status=?",
        (after, stamp, f'\n\n[{stamp}] {before} -> {after}: {note}', row_id, before))
    require(cursor.rowcount == 1, 'STATE_CONFLICT', 'Task missing or status changed. Inspect it before retrying.')
    return {'id': row_id, 'status': after}


def transition(path, table, row_id, before, after, note):
    with db.transaction(path) as conn:
        return transition_in(conn, table, row_id, before, after, note)


def append_note(path, table, row_id, note):
    require(table in TRANSITIONS, 'INVALID_INPUT', 'Notes belong to a backlog.')
    require(isinstance(note, str) and bool(note.strip()), 'INVALID_INPUT', 'Note cannot be blank.')
    field = 'task_definition' if table == 'job_backlog' else 'details'
    with db.transaction(path) as conn:
        stamp = now()
        cursor = conn.execute(f"UPDATE {table} SET {field}=COALESCE({field},'') || ?,date_updated=? WHERE id=?",
                              (f'\n\n[{stamp}] {note}', stamp, row_id))
        require(cursor.rowcount == 1, 'NOT_FOUND', f'Backlog id {row_id} not found.')
    return {'id': row_id, 'noted': True}


def finish_with_record(path, task_id, table, values, note):
    """Save one new result and finish its task atomically, when explicitly requested."""
    require(table in ('companies', 'job_listings'), 'INVALID_INPUT', 'Result must be a company or listing.')
    with db.transaction(path) as conn:
        row_id = db.insert(conn, table, values)
        result = transition_in(conn, 'job_backlog', task_id, 'in_progress', 'done',
                               f'{note}\nSaved {table} id={row_id}.')
        return {**result, 'record_table': table, 'record_id': row_id}
