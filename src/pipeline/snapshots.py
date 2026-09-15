"""Consistent, immutable snapshot pairs and deliberate restore."""
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import tempfile
import uuid
from contextlib import closing
from pathlib import Path

from . import schema
from .common import ROOT, now, require


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def git_state():
    try:
        top = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=ROOT, stderr=subprocess.DEVNULL, text=True).strip()
        if Path(top).resolve() != ROOT:
            return {'commit': None, 'dirty': None}
        commit = subprocess.run(['git', 'rev-parse', '--verify', 'HEAD'], cwd=ROOT, capture_output=True, text=True)
        dirty = subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)
        return {'commit': commit.stdout.strip() if commit.returncode == 0 else None, 'dirty': bool(dirty)}
    except (OSError, subprocess.CalledProcessError):
        return {'commit': None, 'dirty': None}


def create(db_path, label='manual', directory=None):
    require(isinstance(label, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,48}', label), 'INVALID_INPUT', 'Label must be 1..48 letters, digits, underscores or hyphens.')
    directory = Path(directory or ROOT / 'snapshots').resolve()
    directory.mkdir(parents=True, exist_ok=True)
    stamp = now()
    filename = stamp.replace(':', '').replace('.', '') + '_' + label + '_' + uuid.uuid4().hex[:8] + '.sqlite'
    final = directory / filename
    fd, temporary = tempfile.mkstemp(prefix='.snapshot-', suffix='.tmp', dir=directory)
    os.close(fd)
    temporary = Path(temporary)
    metadata_temp = temporary.with_suffix('.json.tmp')
    installed_file = False
    try:
        with closing(schema.connect(db_path, readonly=True)) as source:
            schema.ensure(source, current=False)
            with closing(sqlite3.connect(temporary, isolation_level=None)) as target:
                source.backup(target)
                schema.ensure(target, current=False)
                schema.integrity(target)
                installed = schema.version(target)
        metadata = {
            'format_version': 1, 'filename': filename, 'created_at': stamp,
            'schema_version': installed, 'sha256': digest(temporary),
            'migrations': schema.migration_hashes(installed), 'git': git_state(),
        }
        metadata_temp.write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
        require(not final.exists() and not final.with_suffix('.json').exists(), 'SNAPSHOT_EXISTS', 'Snapshot collision; existing files are never overwritten.')
        os.replace(temporary, final)
        installed_file = True
        os.replace(metadata_temp, final.with_suffix('.json'))
        return {'snapshot': str(final), 'metadata': str(final.with_suffix('.json')), 'schema_version': installed}
    except BaseException:
        if installed_file:
            final.unlink(missing_ok=True)
        raise
    finally:
        temporary.unlink(missing_ok=True)
        metadata_temp.unlink(missing_ok=True)


def verify(path):
    path = Path(path).resolve()
    require(path.is_file() and path.with_suffix('.json').is_file(), 'INVALID_SNAPSHOT', 'Choose an existing .sqlite snapshot with its paired .json metadata.')
    metadata = json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
    require(isinstance(metadata, dict) and metadata.get('format_version') == 1, 'INVALID_SNAPSHOT', 'Unsupported snapshot metadata.')
    require(metadata.get('filename') == path.name and metadata.get('sha256') == digest(path), 'INVALID_SNAPSHOT', 'Snapshot filename/checksum mismatch.')
    with closing(schema.connect(path, readonly=True)) as conn:
        schema.ensure(conn, current=False)
        schema.integrity(conn)
        installed = schema.version(conn)
    require(metadata.get('schema_version') == installed and metadata.get('migrations') == schema.migration_hashes(installed),
            'INVALID_SNAPSHOT', 'Snapshot migration history does not match this checkout.')
    return {'snapshot': str(path), 'verified': True, 'schema_version': installed}


def restore(snapshot, destination, *, replace=False, confirm_stopped=False, backup_directory=None):
    snapshot, destination = Path(snapshot).resolve(), Path(destination).resolve()
    require(confirm_stopped, 'NEEDS_USER_DECISION', 'Stop DB users, then explicitly pass --confirm-stopped to restore.')
    require(snapshot != destination, 'INVALID_INPUT', 'Snapshot and working DB must be different files.')
    verified = verify(snapshot)
    require(replace or not destination.exists(), 'TARGET_EXISTS', 'Target exists; use --replace only after deciding to overwrite it.')
    require(not any(Path(str(destination) + suffix).exists() for suffix in ('-wal', '-shm', '-journal')),
            'DB_NOT_QUIESCENT', 'Target has journal/sidecar files. Close its users cleanly; do not delete sidecars manually.')
    previous = None
    if destination.exists():
        previous = create(destination, 'pre_restore', backup_directory)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.restore-', suffix='.sqlite', dir=destination.parent)
    os.close(fd)
    temporary = Path(temporary)
    try:
        with closing(schema.connect(snapshot, readonly=True)) as source:
            with closing(sqlite3.connect(temporary, isolation_level=None)) as target:
                source.backup(target)
                schema.ensure(target, current=False)
                schema.integrity(target)
        # This is deliberately not a distributed lock. The caller must stop all
        # DB users; see README. Recheck file existence before replacement.
        require(replace or not destination.exists(), 'TARGET_EXISTS', 'Target appeared during restore; inspect it before retrying.')
        os.replace(temporary, destination)
        return {'restored': str(destination), 'schema_version': verified['schema_version'], 'previous': previous,
                'needs_migration': verified['schema_version'] != len(schema.files())}
    finally:
        temporary.unlink(missing_ok=True)
