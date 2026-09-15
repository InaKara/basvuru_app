import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from pipeline import db, schema
from pipeline.common import AppError


class DatabaseCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = self.root / 'working.sqlite'
        schema.init(self.path)

    def tearDown(self):
        self.temp.cleanup()


class DatabaseTests(DatabaseCase):
    def test_initial_structure_and_idempotent_init(self):
        tables = schema.inspect(self.path)['tables']
        self.assertEqual(set(tables), {'companies', 'job_listings', 'job_backlog', 'app_backlog'})
        for table in ('companies', 'job_listings', 'job_backlog'):
            self.assertIn('reserved', [c['name'] for c in tables[table]['columns']])
        row_id = db.add(self.path, 'companies', {'name': 'Örnek GmbH'})['id']
        self.assertFalse(schema.init(self.path)['created'])
        self.assertEqual(db.rows(self.path, 'companies', row_id=row_id)['name'], 'Örnek GmbH')
        self.assertEqual(schema.check(self.path)['version'], 1)

    def test_read_missing_does_not_create(self):
        missing = self.root / 'typo.sqlite'
        with self.assertRaises(AppError) as error:
            db.rows(missing, 'companies')
        self.assertEqual(error.exception.code, 'DB_NOT_INITIALIZED')
        self.assertFalse(missing.exists())

    def test_text_null_zero_and_update(self):
        company = db.add(self.path, 'companies', {'name': "Örnek ' şirket; GmbH"})['id']
        values = {'title': 'Geliştirme – München', 'company_id': company,
                  'full_text': 'Complete text\nİkinci satır\n"quoted"'}
        job = db.add(self.path, 'job_listings', values)['id']
        original = db.rows(self.path, 'job_listings', row_id=job)
        self.assertIsNone(original['score'])
        self.assertIsNone(original['status'])
        self.assertIsNone(original['reserved'])
        db.update(self.path, 'job_listings', job, {'score': 0})
        updated = db.rows(self.path, 'job_listings', row_id=job)
        self.assertEqual(updated['score'], 0)
        self.assertEqual(updated['full_text'], values['full_text'])
        self.assertEqual(updated['date_added'], original['date_added'])
        self.assertGreaterEqual(updated['date_updated'], original['date_updated'])

    def test_reserved_unknown_and_protected_rejected(self):
        company = db.add(self.path, 'companies', {'name': 'Test'})['id']
        for field in ('reserved', 'unknown', 'id', 'date_added'):
            with self.subTest(field=field), self.assertRaises(AppError):
                db.update(self.path, 'companies', company, {field: 'not allowed'})
        self.assertIsNone(db.rows(self.path, 'companies', row_id=company)['reserved'])

    def test_invalid_references_and_values(self):
        for values in ({'title': 'Bad', 'company_id': 123}, {'title': 'Bad', 'score': float('nan')}, {'title': ' '}):
            with self.assertRaises(AppError):
                db.add(self.path, 'job_listings', values)
        with self.assertRaises(AppError):
            db.add(self.path, 'job_backlog', {'source_kind': 'company', 'source_id': 999, 'task_definition': 'Research'})
        self.assertEqual(db.rows(self.path, 'job_listings'), [])

    def test_schema_drift_prevents_writes(self):
        with closing(schema.connect(self.path)) as conn:
            conn.execute('ALTER TABLE companies ADD COLUMN unapproved TEXT')
        with self.assertRaises(AppError) as error:
            db.add(self.path, 'companies', {'name': 'Must not insert'})
        self.assertEqual(error.exception.code, 'SCHEMA_MISMATCH')

    def test_future_schema_rejected(self):
        with closing(schema.connect(self.path)) as conn:
            conn.execute('PRAGMA user_version = 999')
        with self.assertRaises(AppError):
            schema.init(self.path)

    def test_migration_rollback(self):
        folder = self.root / 'migrations'
        folder.mkdir()
        (folder / '0001_initial.sql').write_bytes(schema.files()[0].read_bytes())
        (folder / '0002_failure.sql').write_text('ALTER TABLE companies ADD COLUMN new_field TEXT;\nINSERT INTO no_such_table VALUES (1);\n')
        with patch.object(schema, 'MIGRATIONS', folder):
            with self.assertRaises(sqlite3.Error):
                schema.migrate(self.path)
        details = schema.inspect(self.path)
        self.assertEqual(details['version'], 1)
        self.assertNotIn('new_field', [c['name'] for c in details['tables']['companies']['columns']])
        schema.check(self.path)

    def test_cli_reports_json_and_does_not_create_missing_db(self):
        missing = self.root / 'missing.sqlite'
        result = subprocess.run([sys.executable, '-m', 'pipeline', '--db', str(missing), 'status'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stderr)['code'], 'DB_NOT_INITIALIZED')
        self.assertFalse(missing.exists())

    def test_read_only_connection_enforced(self):
        with closing(schema.connect(self.path, readonly=True)) as conn:
            with self.assertRaises(sqlite3.Error):
                conn.execute("DELETE FROM companies")


if __name__ == '__main__':
    unittest.main()
