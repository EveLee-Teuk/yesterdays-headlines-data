import json
from pathlib import Path
import tempfile
import unittest
from fetch_history import build_issue, atomic_json


class ArchiveTests(unittest.TestCase):
    def test_index_exposes_only_today_attempt_summary_without_replacing_success(self):
        from archive_window import finalize_window
        for outcome in ('ready', 'empty', 'failed', 'validation_failed', 'review_rejected'):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                last_success = {'date': '2026-09-21', 'status': 'empty'}
                atomic_json(root / 'catalog.json', {'events': [], 'lastRun': last_success})
                summary = {'date': '2026-09-22', 'outcome': outcome,
                           'completedAt': '2026-09-22T09:15:00+08:00'}
                atomic_json(root / 'collection_diagnostics/2026-09-22.json',
                            {**summary, 'candidateResults': [{'title': 'diagnostic only'}],
                             'sources': [{'url': 'https://www.gov.cn/example'}]})
                finalize_window(root, '2026-09-22')
                index = json.loads((root / 'archive_index.json').read_text('utf-8'))
                self.assertEqual(index['lastRun'], last_success)
                self.assertEqual(index['lastAttempt'], summary)

    def test_index_omits_attempt_when_no_today_diagnostic(self):
        from archive_window import finalize_window
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            atomic_json(root / 'catalog.json', {'events': []})
            atomic_json(root / 'collection_diagnostics/2026-09-21.json',
                        {'date': '2026-09-21', 'outcome': 'failed', 'completedAt': '2026-09-21T09:15:00+08:00'})
            finalize_window(root, '2026-09-22')
            index = json.loads((root / 'archive_index.json').read_text('utf-8'))
            self.assertNotIn('lastAttempt', index)

    def test_rolling_window_keeps_previous_files_and_removes_outside_dates(self):
        from archive_window import finalize_window
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            atomic_json(root / 'catalog.json', {'schemaVersion': 2, 'updatedAt': '2026-09-22', 'events': []})
            original = build_issue([], '2026-09-21')
            original['collectedAt'] = '2026-09-21T01:00:00+08:00'
            atomic_json(root / 'archives/2026-09-21.json', original)
            before = (root / 'archives/2026-09-21.json').read_bytes()
            for day in ('2026-09-01', '2026-09-23'):
                atomic_json(root / f'archives/{day}.json', build_issue([], day))
            finalize_window(root, '2026-09-22', 7)
            self.assertEqual(len(list((root / 'archives').glob('*.json'))), 7)
            self.assertEqual((root / 'archives/2026-09-21.json').read_bytes(), before)
            index = json.loads((root / 'archive_index.json').read_text())
            self.assertEqual(index['dates'], [f'2026-09-{day}' for day in range(16, 23)])
            self.assertEqual(json.loads((root / 'archives/2026-09-16.json').read_text())['status'], 'unavailable')

    def test_mixed_month_day_is_rejected_before_pruning(self):
        from archive_window import finalize_window
        from test_history import EVENT
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            atomic_json(root / 'catalog.json', {'schemaVersion': 2, 'updatedAt': '2026-09-22', 'events': [EVENT]})
            bad = build_issue([], '2026-09-22'); bad.update(events=[EVENT], status='ready')
            atomic_json(root / 'archives/2026-09-22.json', bad)
            atomic_json(root / 'archives/2026-09-01.json', build_issue([], '2026-09-01'))
            with self.assertRaises(ValueError): finalize_window(root, '2026-09-22', 7)
            self.assertTrue((root / 'archives/2026-09-01.json').exists())
