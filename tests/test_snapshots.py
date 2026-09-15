import json
from contextlib import closing

from pipeline import db, schema, snapshots
from pipeline.common import AppError
from test_database import DatabaseCase


class SnapshotTests(DatabaseCase):
    def snapshot(self):
        return snapshots.create(self.path, 'test', self.root / 'snapshots')['snapshot']

    def test_round_trip_and_existing_target_protection(self):
        db.add(self.path, 'companies', {'name': 'Transfer me'})
        snap = self.snapshot()
        self.assertTrue(snapshots.verify(snap)['verified'])
        target = self.root / 'restored.sqlite'
        snapshots.restore(snap, target, confirm_stopped=True)
        self.assertEqual(db.rows(target, 'companies')[0]['name'], 'Transfer me')
        with self.assertRaises(AppError):
            snapshots.restore(snap, target, confirm_stopped=True)
        db.add(target, 'companies', {'name': 'Preserve in pre-restore snapshot'})
        result = snapshots.restore(snap, target, confirm_stopped=True, replace=True, backup_directory=self.root / 'snapshots')
        self.assertEqual(len(db.rows(result['previous']['snapshot'], 'companies')), 2)
        self.assertEqual(len(db.rows(target, 'companies')), 1)

    def test_wal_commits_included_in_backup(self):
        with closing(schema.connect(self.path)) as writer:
            writer.execute('PRAGMA journal_mode = WAL')
            writer.execute('PRAGMA wal_autocheckpoint = 0')
            writer.execute("INSERT INTO companies (name,date_added) VALUES ('In WAL','2026-09-15T00:00:00Z')")
            self.assertTrue(type(self.path)(str(self.path) + '-wal').exists())
            snap = self.snapshot()
            self.assertEqual(db.rows(snap, 'companies')[0]['name'], 'In WAL')

    def test_tampered_snapshot_and_wrong_history_rejected(self):
        from pathlib import Path
        snap = Path(self.snapshot())
        metadata_path = snap.with_suffix('.json')
        metadata = json.loads(metadata_path.read_text())
        metadata['migrations']['0001_initial.sql'] = 'wrong'
        metadata_path.write_text(json.dumps(metadata))
        with self.assertRaises(AppError):
            snapshots.verify(snap)
        snap.write_bytes(b'corrupted')
        with self.assertRaises(AppError):
            snapshots.verify(snap)

    def test_unique_names_and_no_escape(self):
        self.assertNotEqual(self.snapshot(), self.snapshot())
        with self.assertRaises(AppError):
            snapshots.create(self.path, '../escape', self.root / 'snapshots')

    def test_restore_confirmation_and_sidecars(self):
        snap = self.snapshot()
        target = self.root / 'destination.sqlite'
        with self.assertRaises(AppError):
            snapshots.restore(snap, target)
        type(target)(str(target) + '-wal').write_bytes(b'not safe to remove')
        with self.assertRaises(AppError):
            snapshots.restore(snap, target, confirm_stopped=True)
        self.assertFalse(target.exists())
