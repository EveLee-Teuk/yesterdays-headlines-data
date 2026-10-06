import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import preparation
from fetch_history import atomic_json, build_issue
from test_collect import CANDIDATE, DOC
from collect_history import validate_candidate


class PreparationTests(unittest.TestCase):
    def setup_root(self, root):
        atomic_json(root / 'catalog.json', {'schemaVersion': 2, 'updatedAt': '2026-09-21', 'events': []})

    def event(self):
        return {**validate_candidate(CANDIDATE, [DOC], '2026-09-22'), 'reviewedAt': '2026-09-21'}

    def test_verified_prepared_today_can_publish_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_root(root)
            atomic_json(root / 'prepared/2026-09-22.json', build_issue([self.event()], '2026-09-22'))
            self.assertTrue(preparation.restore_day(root, '2026-09-22', '2026-09-22'))
            issue = json.loads((root / 'archives/2026-09-22.json').read_text('utf-8'))
            self.assertEqual(issue['status'], 'ready')
            self.assertEqual(issue['events'][0]['date'], '1990-09-22')

    def test_wrong_date_and_unverified_drafts_never_publish(self):
        for issue in [build_issue([self.event()], '2026-09-21'), [], None,
                      {**build_issue([self.event()], '2026-09-22'), 'events': [{**self.event(), 'verification': None}]}]:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.setup_root(root)
                atomic_json(root / 'prepared/2026-09-22.json', issue)
                self.assertFalse(preparation.restore_day(root, '2026-09-22', '2026-09-22'))
                self.assertFalse((root / 'archives/2026-09-22.json').exists())

    def test_future_cannot_be_promoted_even_when_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_root(root)
            atomic_json(root / 'prepared/2026-09-22.json', build_issue([self.event()], '2026-09-22'))
            with self.assertRaises(ValueError): preparation.restore_day(root, '2026-09-22', '2026-09-21')

    def test_upcoming_work_is_bounded_and_never_publishes_archives(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_root(root)
            calls = []
            def collect(root, day, **kwargs):
                calls.append((day, kwargs))
                if day == '2026-09-22':
                    atomic_json(root / 'prepared' / f'{day}.json', build_issue([self.event()], day))
                else:
                    raise RuntimeError('no qualifying result')
            with patch('collect_history.collect', side_effect=collect):
                result = preparation.prepare_upcoming(root, '2026-09-21', 2)
            self.assertEqual([item[0] for item in calls], ['2026-09-22', '2026-09-23'])
            self.assertTrue(all(item[1]['prepare'] for item in calls))
            self.assertEqual(result['readyDates'], ['2026-09-22'])
            self.assertEqual(len(result['missingDates']), 6)
            self.assertFalse((root / 'archives').exists())
            self.assertEqual(len(json.loads((root / 'coverage_status.json').read_text('utf-8'))['upcomingDates']), 7)

    def test_ready_draft_is_reused_without_model_call(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_root(root)
            atomic_json(root / 'prepared/2026-09-22.json', build_issue([self.event()], '2026-09-22'))
            with patch('collect_history.collect') as collect:
                result = preparation.prepare_upcoming(root, '2026-09-21', 0)
            self.assertEqual(collect.call_count, 0)
            self.assertEqual(result['readyDates'], ['2026-09-22'])
            self.assertEqual(result['calendarTotalDays'], 366)

    def test_failed_preparation_retries_are_capped_per_day_and_reset_next_day(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_root(root)
            with patch('collect_history.collect', side_effect=RuntimeError('offline')) as collect:
                for _ in range(4):
                    preparation.prepare_upcoming(root, '2026-09-21', 1)
                self.assertEqual([call.args[1] for call in collect.call_args_list],
                                 ['2026-09-22'] * 3 + ['2026-09-23'])
                preparation.prepare_upcoming(root, '2026-09-22', 1)
                self.assertEqual(collect.call_args_list[-1].args[1], '2026-09-23')

    def test_preparation_retention_spans_recent_and_future_week(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_root(root)
            for day in ('2026-09-15', '2026-09-16', '2026-09-29', '2026-09-30'):
                atomic_json(root / 'prepared' / f'{day}.json', {})
            preparation.prepare_upcoming(root, '2026-09-22', 0)
            self.assertEqual(sorted(path.stem for path in (root / 'prepared').glob('*.json')),
                             ['2026-09-16', '2026-09-29'])

    def test_expired_budget_does_not_start_more_model_work(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_root(root)
            with patch('collect_history.collect') as collect:
                result = preparation.prepare_upcoming(root, '2026-09-22', 7, deadline=0)
            collect.assert_not_called()
            self.assertEqual(len(result['missingDates']), 7)

    def test_final_coverage_includes_this_runs_historical_backfill(self):
        from archive_window import run
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_root(root)
            def collect(root, day):
                if day == '2026-09-22':
                    atomic_json(root / 'catalog.json', {'schemaVersion': 2, 'events': [self.event()], 'updatedAt': day})
                    atomic_json(root / 'archives' / f'{day}.json', build_issue([self.event()], day))
            with patch('collect_history.collect', side_effect=collect):
                run(root, '2026-09-23', backfill_budget=1)
            report = json.loads((root / 'coverage_status.json').read_text('utf-8'))
            self.assertEqual(report['calendarCoveredDays'], 1)
            self.assertEqual(report['coveredMonthDays'], ['09-22'])


if __name__ == '__main__':
    unittest.main()
