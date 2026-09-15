"""Validated CRUD. Unknown/reserved fields never become hidden overflow data."""
import math
from contextlib import closing, contextmanager

from .common import now, require
from . import schema

FIELDS = {
    'companies': {'name', 'status', 'brief_info', 'detailed_info', 'keywords', 'webpage', 'careers_webpage', 'careers_webpage_structure'},
    'job_listings': {'title', 'status', 'company_name', 'company_id', 'score', 'webpage', 'full_text'},
    'job_backlog': {'source_kind', 'source_id', 'task_definition'},
    'app_backlog': {'type', 'details'},
}


@contextmanager
def transaction(path):
    with closing(schema.connect(path)) as conn:
        conn.execute('BEGIN IMMEDIATE')
        try:
            schema.ensure(conn)
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise


def table_ok(table):
    require(table in FIELDS, 'UNKNOWN_TABLE', f'Unsupported table: {table}. Ask before adding schema.')


def validate(table, values, *, conn, creating=False):
    table_ok(table)
    require(isinstance(values, dict), 'INVALID_INPUT', 'Input must be a JSON object.')
    unknown = set(values) - FIELDS[table]
    require(not unknown, 'UNKNOWN_FIELD', f'Unknown or protected fields: {sorted(unknown)}. Follow maintenance; do not repurpose reserved.')
    for field, value in values.items():
        if field in ('company_id', 'source_id'):
            require(value is None or (type(value) is int and value > 0), 'INVALID_INPUT', f'{field} must be a positive integer or null.')
        elif field == 'score':
            require(value is None or (type(value) in (int, float) and math.isfinite(value)), 'INVALID_INPUT', 'score must be finite numeric or null.')
        else:
            require(value is None or isinstance(value, str), 'INVALID_INPUT', f'{field} must be text or null.')
    required = {'companies': ['name'], 'job_listings': ['title'],
                'job_backlog': ['source_kind', 'task_definition'], 'app_backlog': ['type', 'details']}[table]
    for field in required:
        if creating or field in values:
            require(isinstance(values.get(field), str) and bool(values[field].strip()), 'INVALID_INPUT', f'{field} is required and cannot be blank.')
    if values.get('company_id') is not None:
        require(conn.execute('SELECT 1 FROM companies WHERE id=?', (values['company_id'],)).fetchone(), 'INVALID_REFERENCE', 'company_id does not exist.')
    if table == 'job_backlog':
        kind, source = values.get('source_kind'), values.get('source_id')
        require(kind in ('company', 'job_listing', 'other'), 'INVALID_INPUT', 'source_kind must be company, job_listing, or other.')
        require(kind != 'other' or source is None, 'INVALID_REFERENCE', 'other tasks use a null source_id; describe their subject in task_definition.')
        if source is not None:
            target = {'company': 'companies', 'job_listing': 'job_listings'}[kind]
            require(conn.execute(f'SELECT 1 FROM {target} WHERE id=?', (source,)).fetchone(), 'INVALID_REFERENCE', 'Task source does not exist.')


def insert(conn, table, values):
    validate(table, values, conn=conn, creating=True)
    fields = dict(values)
    fields['date_added'] = now()
    if table != 'companies':
        fields['date_updated'] = fields['date_added']
    names = list(fields)
    cursor = conn.execute(f"INSERT INTO {table} ({','.join(names)}) VALUES ({','.join('?' for _ in names)})", list(fields.values()))
    return cursor.lastrowid


def add(path, table, values):
    with transaction(path) as conn:
        return {'id': insert(conn, table, values)}


def update(path, table, row_id, values):
    require(table in ('companies', 'job_listings'), 'INVALID_INPUT', 'Use dedicated task/change commands for backlogs.')
    require(bool(values), 'INVALID_INPUT', 'Supply at least one field to update.')
    with transaction(path) as conn:
        validate(table, values, conn=conn)
        fields = dict(values)
        if table == 'job_listings':
            fields['date_updated'] = now()
        cursor = conn.execute(f"UPDATE {table} SET {','.join(k+'=?' for k in fields)} WHERE id=?", [*fields.values(), row_id])
        require(cursor.rowcount == 1, 'NOT_FOUND', f'{table} id {row_id} not found.')
        return {'id': row_id, 'updated': True}


def rows(path, table, *, row_id=None, status=None, limit=100):
    table_ok(table)
    require(type(limit) is int and 1 <= limit <= 1000, 'INVALID_INPUT', 'limit must be 1..1000.')
    with closing(schema.connect(path, readonly=True)) as conn:
        schema.ensure(conn)
        sql, params = f'SELECT * FROM {table}', []
        if row_id is not None:
            sql += ' WHERE id=?'
            params.append(row_id)
        elif status is not None:
            sql += ' WHERE status=?'
            params.append(status)
        result = [dict(r) for r in conn.execute(sql + ' ORDER BY id LIMIT ?', [*params, limit])]
        require(row_id is None or bool(result), 'NOT_FOUND', f'{table} id {row_id} not found.')
        return result[0] if row_id is not None else result
