from pipeline import backlog, db
from pipeline.common import AppError
from test_database import DatabaseCase


class BacklogTests(DatabaseCase):
    def task(self):
        return db.add(self.path, 'job_backlog', {'source_kind': 'other', 'task_definition': 'User assignment'})['id']

    def test_second_claim_rejected_and_state_persists(self):
        task = self.task()
        backlog.transition(self.path, 'job_backlog', task, 'pending', 'in_progress', 'Starting')
        with self.assertRaises(AppError):
            backlog.transition(self.path, 'job_backlog', task, 'pending', 'in_progress', 'Duplicate')
        saved = db.rows(self.path, 'job_backlog', row_id=task)
        self.assertEqual(saved['status'], 'in_progress')
        self.assertIn('User assignment', saved['task_definition'])
        self.assertIn('Starting', saved['task_definition'])

    def test_atomic_record_completion_and_rollback(self):
        task = self.task()
        with self.assertRaises(AppError):
            backlog.finish_with_record(self.path, task, 'companies', {'name': 'Must roll back'}, 'Not running')
        self.assertEqual(db.rows(self.path, 'companies'), [])
        backlog.transition(self.path, 'job_backlog', task, 'pending', 'in_progress', 'Starting')
        result = backlog.finish_with_record(self.path, task, 'companies', {'name': 'Saved'}, 'Completed')
        self.assertEqual(result['status'], 'done')
        self.assertEqual(db.rows(self.path, 'companies', row_id=result['record_id'])['name'], 'Saved')

    def test_invalid_transition_and_append_preserve_history(self):
        task = self.task()
        with self.assertRaises(AppError):
            backlog.transition(self.path, 'job_backlog', task, 'pending', 'done', 'Skip')
        backlog.append_note(self.path, 'job_backlog', task, 'Checkpoint')
        row = db.rows(self.path, 'job_backlog', row_id=task)
        self.assertEqual(row['status'], 'pending')
        self.assertIn('Checkpoint', row['task_definition'])

    def test_app_backlog_review_progression(self):
        item = db.add(self.path, 'app_backlog', {'type': 'feature', 'details': 'Describe feature'})['id']
        with self.assertRaises(AppError):
            backlog.transition(self.path, 'app_backlog', item, 'needs_decision', 'done', 'Skip review')
        for before, after in [('needs_decision', 'planned'), ('planned', 'in_progress'), ('in_progress', 'awaiting_patch_review')]:
            backlog.transition(self.path, 'app_backlog', item, before, after, 'Test note; this test is not user approval.')
        self.assertEqual(db.rows(self.path, 'app_backlog', row_id=item)['status'], 'awaiting_patch_review')
