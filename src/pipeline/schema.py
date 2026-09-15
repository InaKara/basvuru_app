"""Versioned migrations and deterministic comparison of actual/expected schema."""
import hashlib
import sqlite3
from contextlib import closing
from pathlib import Path

from .common import ROOT, AppError, require

MIGRATIONS = ROOT / 'migrations'
REFERENCE = ROOT / '.agents/skills/basvuru-database/references/schema.sql'


def connect(path, *, readonly=False):
    path = Path(path).resolve()
    require(path.is_file(), 'DB_NOT_INITIALIZED', f'Database not found: {path}. Use init or restore explicitly.')
    conn = sqlite3.connect(path.as_uri() + ('?mode=ro' if readonly else '?mode=rw'),
                           uri=True, timeout=5, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def files():
    paths = sorted(MIGRATIONS.glob('[0-9][0-9][0-9][0-9]_*.sql'))
    require(bool(paths), 'SCHEMA_MISMATCH', 'No migrations found in this checkout.')
    versions = [int(p.name[:4]) for p in paths]
    require(versions == list(range(1, len(paths) + 1)), 'SCHEMA_MISMATCH', 'Migration numbers must be contiguous from 0001.')
    return paths


def version(conn):
    return conn.execute('PRAGMA user_version').fetchone()[0]


def structure(conn):
    return [tuple(row) for row in conn.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name")]


def execute_migration(conn, path):
    # executescript() can commit an existing transaction. Parse complete SQL
    # statements instead, so the runner owns the transaction, including rollback.
    buffer = ''
    for line in path.read_text(encoding='utf-8').splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            conn.execute(buffer)
            buffer = ''
    require(not buffer.strip(), 'INVALID_MIGRATION', f'Incomplete SQL statement: {path.name}')


def expected(target=None):
    paths = files()
    target = len(paths) if target is None else target
    require(0 <= target <= len(paths), 'SCHEMA_MISMATCH', f'Unsupported schema version: {target}')
    with closing(sqlite3.connect(':memory:', isolation_level=None)) as conn:
        conn.execute('PRAGMA foreign_keys = ON')
        for path in paths[:target]:
            execute_migration(conn, path)
        return structure(conn)


def export_sql():
    order = {'table': 0, 'view': 1, 'index': 2, 'trigger': 3}
    objects = sorted(expected(), key=lambda row: (order[row[0]], row[1]))
    return '-- Generated from migrations; do not edit by hand.\n' + '\n'.join(
        row[3] + ';' for row in objects if row[3]) + '\n'


def ensure(conn, *, current=True):
    installed = version(conn)
    latest = len(files())
    require(0 <= installed <= latest, 'SCHEMA_MISMATCH', f'Unknown schema version {installed}; checkout supports {latest}.')
    require(structure(conn) == expected(installed), 'SCHEMA_MISMATCH', 'Actual schema differs from approved migrations. Ask before changing it.')
    require(not current or installed == latest, 'SCHEMA_MISMATCH', f'Schema {installed}; expected {latest}. Migration needs explicit review/application.')


def integrity(conn):
    result = [row[0] for row in conn.execute('PRAGMA integrity_check')]
    require(result == ['ok'], 'INTEGRITY_ERROR', f'SQLite integrity check failed: {result}')
    require(not conn.execute('PRAGMA foreign_key_check').fetchall(), 'INTEGRITY_ERROR', 'Foreign-key check failed.')


def inspect(path):
    with closing(connect(path, readonly=True)) as conn:
        tables = {}
        for kind, name, _, _ in structure(conn):
            if kind == 'table':
                # Identifier is escaped because inspection can encounter drift.
                safe = name.replace('"', '""')
                tables[name] = {
                    'columns': [dict(r) for r in conn.execute(f'PRAGMA table_info("{safe}")')],
                    'foreign_keys': [dict(r) for r in conn.execute(f'PRAGMA foreign_key_list("{safe}")')],
                }
        return {'version': version(conn), 'tables': tables, 'objects': structure(conn)}


def check(path):
    with closing(connect(path, readonly=True)) as conn:
        ensure(conn)
        integrity(conn)
        require(REFERENCE.is_file() and REFERENCE.read_text(encoding='utf-8') == export_sql(),
                'REFERENCE_MISMATCH', 'Generated schema reference is missing/stale; prepare its update for review.')
        return {'version': version(conn), 'schema': 'ok', 'integrity': 'ok', 'reference': 'ok'}


def migration_hashes(target):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files()[:target]}


def migrate(path):
    with closing(connect(path)) as conn:
        conn.execute('BEGIN IMMEDIATE')
        try:
            ensure(conn, current=False)
            start = version(conn)
            for n, migration in enumerate(files(), 1):
                if n > start:
                    execute_migration(conn, migration)
                    conn.execute(f'PRAGMA user_version = {n}')
            ensure(conn)
            integrity(conn)
            conn.commit()
            return {'previous_version': start, 'version': version(conn)}
        except BaseException:
            conn.rollback()
            raise


def init(path):
    path = Path(path).resolve()
    if path.exists():
        with closing(connect(path, readonly=True)) as conn:
            ensure(conn)
        return {'created': False, 'version': len(files())}
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents overwriting an existing file.
    with path.open('xb'):
        pass
    try:
        result = migrate(path)
        return {'created': True, **result}
    except BaseException:
        path.unlink(missing_ok=True)
        raise
