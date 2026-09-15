"""Terminal interface for agents and humans. --help is the command reference."""
import argparse
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

from . import backlog, db, schema, snapshots
from .common import AppError, DEFAULT_DB, require


def parser():
    root = argparse.ArgumentParser(prog='basvuru')
    root.add_argument('--db', type=Path, default=DEFAULT_DB)
    groups = root.add_subparsers(dest='command', required=True)
    groups.add_parser('init', help='Initialize a missing DB; preserve an existing current DB.')
    groups.add_parser('status', help='Inspect schema and backlog counts without making changes.')
    migrate = groups.add_parser('migrate', help='Apply reviewed migrations after snapshotting.')
    migrate.add_argument('--confirm-reviewed', action='store_true')
    migrate.add_argument('--confirm-stopped', action='store_true')
    sg = groups.add_parser('schema').add_subparsers(dest='action', required=True)
    sg.add_parser('inspect')
    sg.add_parser('check')
    export = sg.add_parser('export')
    export.add_argument('--output', required=True, type=Path)
    rg = groups.add_parser('records').add_subparsers(dest='action', required=True)
    for action in ('list', 'show', 'add', 'update'):
        p = rg.add_parser(action)
        p.add_argument('table', choices=list(db.FIELDS) if action in ('list', 'show') else ['companies', 'job_listings'])
        if action in ('show', 'update'):
            p.add_argument('id', type=int)
        if action in ('add', 'update'):
            p.add_argument('--input', required=True, type=Path)
        if action == 'list':
            p.add_argument('--status')
            p.add_argument('--limit', type=int, default=100)
    for group in ('tasks', 'changes'):
        sub = groups.add_parser(group).add_subparsers(dest='action', required=True)
        p = sub.add_parser('list')
        p.add_argument('--status')
        p.add_argument('--limit', type=int, default=100)
        p = sub.add_parser('add')
        p.add_argument('--input', required=True, type=Path)
        p = sub.add_parser('note')
        p.add_argument('id', type=int)
        p.add_argument('--input', required=True, type=Path, help='UTF-8 text file')
        p = sub.add_parser('transition')
        p.add_argument('id', type=int)
        p.add_argument('--from', dest='before', required=True)
        p.add_argument('--to', dest='after', required=True)
        p.add_argument('--note', required=True)
        if group == 'tasks':
            p = sub.add_parser('finish-with-record', help='Insert one record and complete its running task atomically.')
            p.add_argument('id', type=int)
            p.add_argument('table', choices=['companies', 'job_listings'])
            p.add_argument('--input', required=True, type=Path)
            p.add_argument('--note', required=True)
    sp = groups.add_parser('snapshot').add_subparsers(dest='action', required=True)
    p = sp.add_parser('create')
    p.add_argument('--label', default='manual')
    p = sp.add_parser('verify')
    p.add_argument('path', type=Path)
    p = sp.add_parser('restore')
    p.add_argument('path', type=Path)
    p.add_argument('--replace', action='store_true')
    p.add_argument('--confirm-stopped', action='store_true')
    return root


def json_input(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def execute(args):
    path = args.db.resolve()
    if args.command == 'init':
        return schema.init(path)
    if args.command == 'status':
        with closing(schema.connect(path, readonly=True)) as conn:
            schema.ensure(conn, current=False)
            tables = {r[1] for r in schema.structure(conn) if r[0] == 'table'}
            counts, active = {}, {}
            for table in ('job_backlog', 'app_backlog'):
                if table in tables:
                    counts[table] = dict(conn.execute(f'SELECT status,count(*) FROM {table} GROUP BY status'))
                    active[table] = [dict(r) for r in conn.execute(f"SELECT id,status FROM {table} WHERE status NOT IN ('done','cancelled') ORDER BY id LIMIT 100")]
            return {'version': schema.version(conn), 'expected_version': len(schema.files()), 'counts': counts,
                    'open_items': active, 'note': 'Read the selected backlog row for details; never auto-resume in_progress work.'}
    if args.command == 'migrate':
        require(args.confirm_reviewed and args.confirm_stopped, 'NEEDS_USER_DECISION',
                'Review the concrete migration patch and stop affected work; then pass --confirm-reviewed --confirm-stopped.')
        with closing(schema.connect(path, readonly=True)) as conn:
            schema.ensure(conn, current=False)
            if schema.version(conn) == len(schema.files()):
                return {'version': schema.version(conn), 'changed': False}
        backup = snapshots.create(path, 'pre_migration')
        return {**schema.migrate(path), 'backup': backup}
    if args.command == 'schema':
        if args.action == 'inspect':
            return schema.inspect(path)
        if args.action == 'check':
            return schema.check(path)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(schema.export_sql(), encoding='utf-8', newline='\n')
        return {'exported': str(args.output.resolve())}
    if args.command == 'records':
        if args.action == 'list':
            return db.rows(path, args.table, status=args.status, limit=args.limit)
        if args.action == 'show':
            return db.rows(path, args.table, row_id=args.id)
        if args.action == 'add':
            return db.add(path, args.table, json_input(args.input))
        return db.update(path, args.table, args.id, json_input(args.input))
    if args.command in ('tasks', 'changes'):
        table = 'job_backlog' if args.command == 'tasks' else 'app_backlog'
        if args.action == 'list':
            return db.rows(path, table, status=args.status, limit=args.limit)
        if args.action == 'add':
            return db.add(path, table, json_input(args.input))
        if args.action == 'note':
            return backlog.append_note(path, table, args.id, args.input.read_text(encoding='utf-8-sig'))
        if args.action == 'finish-with-record':
            return backlog.finish_with_record(path, args.id, args.table, json_input(args.input), args.note)
        return backlog.transition(path, table, args.id, args.before, args.after, args.note)
    if args.action == 'create':
        return snapshots.create(path, args.label)
    if args.action == 'verify':
        return snapshots.verify(args.path)
    return snapshots.restore(args.path, path, replace=args.replace, confirm_stopped=args.confirm_stopped)


def main():
    args = parser().parse_args()
    # PowerShell/Windows consoles must also be able to receive non-ASCII JSON.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    try:
        result = execute(args)
        print(json.dumps({'ok': True, 'db': str(args.db.resolve()), 'result': result}, ensure_ascii=False, indent=2))
    except (AppError, sqlite3.Error, OSError, ValueError) as error:
        code = error.code if isinstance(error, AppError) else 'OPERATION_FAILED'
        print(json.dumps({'ok': False, 'code': code, 'message': str(error), 'db': str(args.db.resolve())}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
