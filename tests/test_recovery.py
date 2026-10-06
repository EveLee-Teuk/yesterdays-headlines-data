import json
import datetime as dt
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import archive_window
import collect_history as collector
from fetch_history import atomic_json, build_issue
from test_collect import CANDIDATE, DOC


class RecoveryTests(unittest.TestCase):
    def setup_root(self, root):
        atomic_json(root / 'catalog.json', {'schemaVersion': 2, 'events': [], 'updatedAt': '2026-09-22'})

    def test_invalid_category_can_be_repaired_but_still_requires_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_root(root)
            replies = [{'events': [{**CANDIDATE, 'category': '体育'}]},
                       {'events': [CANDIDATE]}, {'approved': [0]}]
            with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test-only'}, clear=True), \
                 patch.object(collector, 'retrieve', return_value=[DOC]), \
                 patch.object(collector, 'deepseek_json', side_effect=replies) as model:
                collector.collect(root, '2026-09-22')
            issue = json.loads((root / 'archives/2026-09-22.json').read_text('utf-8'))
            self.assertEqual(issue['events'][0]['title'], CANDIDATE['title'])
            repair = model.call_args_list[1].args[1]
            self.assertEqual(repair['sources'], [DOC])
            self.assertIn('Invalid category', str(repair['validationErrors']))
            self.assertEqual(model.call_args_list[-1].args[0], collector.REVIEWER)

    def test_failed_repair_preserves_published_files_and_records_failure(self):
        for repaired in [[], [{**CANDIDATE, 'evidence': '1990年9月22日，这是并未出现在原文中的虚构事件。'}]]:
            with self.subTest(repaired=repaired), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.setup_root(root)
                original = (root / 'catalog.json').read_bytes()
                previous = build_issue([], '2026-09-22')
                atomic_json(root / 'archives/2026-09-22.json', previous)
                with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test-only'}, clear=True), \
                     patch.object(collector, 'retrieve', return_value=[DOC]), \
                     patch.object(collector, 'deepseek_json', side_effect=[
                         {'events': [{**CANDIDATE, 'category': '体育'}]}, {'events': repaired}]):
                    with self.assertRaises(RuntimeError):
                        collector.collect(root, '2026-09-22')
                self.assertEqual((root / 'catalog.json').read_bytes(), original)
                self.assertEqual(json.loads((root / 'archives/2026-09-22.json').read_text('utf-8')), previous)
                diagnostic = json.loads((root / 'collection_diagnostics/2026-09-22.json').read_text('utf-8'))
                self.assertEqual(diagnostic['outcome'], 'validation_failed')
                self.assertEqual(dt.datetime.fromisoformat(diagnostic['completedAt']).utcoffset(), dt.timedelta(hours=8))
                self.assertEqual(diagnostic['candidateResults'][0]['title'], CANDIDATE['title'])
                self.assertEqual(diagnostic['candidateResults'][0]['reason'], 'Invalid category')
                self.assertNotIn('test-only', json.dumps(diagnostic))

    def test_reviewer_rejection_is_failure_and_genuine_zero_remains_empty(self):
        for replies, outcome in [([{'events': [CANDIDATE]}, {'approved': []}], 'review_rejected'),
                                  ([{'events': []}], 'empty')]:
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.setup_root(root)
                with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test-only'}, clear=True), \
                     patch.object(collector, 'retrieve', return_value=[DOC]), \
                     patch.object(collector, 'deepseek_json', side_effect=replies):
                    if outcome == 'review_rejected':
                        with self.assertRaises(RuntimeError): collector.collect(root, '2026-09-22')
                    else:
                        collector.collect(root, '2026-09-22')
                        self.assertEqual(json.loads((root / 'archives/2026-09-22.json').read_text('utf-8'))['status'], 'empty')
                self.assertEqual(json.loads((root / 'collection_diagnostics/2026-09-22.json').read_text('utf-8'))['outcome'], outcome)

    def test_backfill_keeps_latest_success_status_and_existing_ready_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_root(root)
            catalog = json.loads((root / 'catalog.json').read_text('utf-8'))
            latest = {'date': '2026-09-23', 'status': 'empty', 'sourceCount': 3, 'addedCount': 0}
            catalog.update(lastRun=latest, updatedAt='2026-09-23')
            atomic_json(root / 'catalog.json', catalog)
            with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test-only'}, clear=True), \
                 patch.object(collector, 'retrieve', return_value=[DOC]), \
                 patch.object(collector, 'deepseek_json', side_effect=[{'events': [CANDIDATE]}, {'approved': [0]}]):
                collector.collect(root, '2026-09-22')
            original = (root / 'archives/2026-09-22.json').read_bytes()
            self.assertEqual(json.loads((root / 'catalog.json').read_text('utf-8'))['lastRun'], latest)
            with patch.object(collector, 'collect') as collect:
                archive_window.run(root, '2026-09-23', backfill_budget=1)
            self.assertEqual([call.args[1] for call in collect.call_args_list], ['2026-09-23', '2026-09-21'])
            self.assertEqual((root / 'archives/2026-09-22.json').read_bytes(), original)
            self.assertEqual(json.loads((root / 'archive_index.json').read_text('utf-8'))['lastRun'], latest)

    def test_low_recall_gets_bounded_supplement_and_keeps_source_allowlist(self):
        queries = []
        def search(query, **kwargs):
            queries.append(query)
            if len(queries) <= 5:
                return [{'href': 'https://www.gov.cn/one'}]
            return [{'href': 'https://www.gov.cn/two'}, {'href': 'https://evil.test/injected'}]
        fake_ddgs = types.SimpleNamespace(DDGS=lambda **kwargs: types.SimpleNamespace(text=search))
        metrics = {}
        with patch.dict('sys.modules', {'ddgs': fake_ddgs}), \
             patch.object(collector, 'read_document', side_effect=lambda url, day: {**DOC, 'url': url}) as read:
            documents = collector.retrieve('2026-09-22', [], metrics)
        self.assertEqual(len(queries), 8)
        self.assertEqual({doc['url'] for doc in documents}, {'https://www.gov.cn/one', 'https://www.gov.cn/two'})
        self.assertEqual(read.call_count, 2)
        self.assertEqual(metrics['searchSucceeded'], 8)
        self.assertEqual(metrics['sourceReadable'], 2)

    def test_healthy_recall_does_not_pay_for_supplement(self):
        fake_ddgs = types.SimpleNamespace(DDGS=lambda **kwargs: types.SimpleNamespace(
            text=lambda *args, **kwargs: [{'href': f'https://www.gov.cn/{i}'} for i in range(4)]))
        metrics = {}
        with patch.dict('sys.modules', {'ddgs': fake_ddgs}), \
             patch.object(collector, 'read_document', side_effect=lambda url, day: {**DOC, 'url': url}):
            collector.retrieve('2026-09-22', [], metrics)
        self.assertEqual(metrics['searchAttempted'], 5)
        self.assertEqual(metrics['supplementalSearches'], 0)

    def test_explicit_recovery_budget_is_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_root(root)
            with patch.object(collector, 'collect') as collect:
                archive_window.run(root, '2026-09-22', backfill_budget=5)
            self.assertEqual(collect.call_count, 6)
            with self.assertRaises(ValueError):
                archive_window.run(root, '2026-09-22', backfill_budget=7)

    def test_all_search_failures_are_diagnosed_without_model_or_publication(self):
        def fail(*args, **kwargs):
            raise RuntimeError('simulated search outage')
        fake_ddgs = types.SimpleNamespace(DDGS=lambda **kwargs: types.SimpleNamespace(text=fail))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_root(root)
            original = (root / 'catalog.json').read_bytes()
            with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test-only'}, clear=True), \
                 patch.dict('sys.modules', {'ddgs': fake_ddgs}), \
                 patch.object(collector, 'deepseek_json') as model:
                with self.assertRaises(RuntimeError): collector.collect(root, '2026-09-22')
            self.assertEqual(model.call_count, 0)
            self.assertEqual((root / 'catalog.json').read_bytes(), original)
            diagnostic = json.loads((root / 'collection_diagnostics/2026-09-22.json').read_text('utf-8'))
            self.assertEqual(diagnostic['searchAttempted'], 8)
            self.assertEqual(diagnostic['searchSucceeded'], 0)
            self.assertEqual(diagnostic['outcome'], 'failed')

    def test_window_prioritizes_today_and_caps_historical_retries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_root(root)
            for day in archive_window.window_dates('2026-09-22'):
                atomic_json(root / f'archives/{day}.json', build_issue([], day))
            for run_day, expected in [
                ('2026-09-22', ['2026-09-22', '2026-09-21', '2026-09-20']),
                ('2026-09-22', ['2026-09-22', '2026-09-19', '2026-09-18']),
                ('2026-09-23', ['2026-09-23', '2026-09-22', '2026-09-21']),
                ('2026-09-24', ['2026-09-24', '2026-09-23', '2026-09-22'])]:
                called = []
                def fake_collect(root, day):
                    called.append(day)
                    atomic_json(root / f'archives/{day}.json', build_issue([], day))
                with patch.object(collector, 'collect', side_effect=fake_collect):
                    archive_window.run(root, run_day)
                self.assertEqual(called, expected)
            state = json.loads((root / 'window_status.json').read_text('utf-8'))
            self.assertEqual(state['historicalRetries']['2026-09-21']['count'], 2)

    def test_failure_does_not_stop_today_or_other_backfills(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_root(root)
            def fail(root, day):
                raise RuntimeError('simulated')
            with patch.object(collector, 'collect', side_effect=fail) as collect:
                failures = archive_window.run(root, '2026-09-22')
            self.assertEqual(failures, ['2026-09-22', '2026-09-21', '2026-09-20'])
            self.assertEqual(collect.call_count, 3)
            self.assertEqual(len(list((root / 'archives').glob('*.json'))), 7)


if __name__ == '__main__':
    unittest.main()
