import copy
import datetime as dt
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('history', Path(__file__).parents[1] / 'fetch_history.py')
history = importlib.util.module_from_spec(SPEC)
try:
    SPEC.loader.exec_module(history)
except ModuleNotFoundError:
    pass  # The old publisher depends on an unused search package.

EVENT = {'id': 'first-atomic-test', 'date': '1964-10-16', 'title': '中国第一颗原子弹爆炸成功',
         'category': '科技', 'location': '新疆罗布泊', 'summary': '中国进行了第一次核试验。',
         'sources': [{'name': '国家原子能机构', 'url': 'https://www.caea.gov.cn/example.html',
                      'date': '1964-10-16'}], 'reviewedAt': '2026-09-22'}


class HistoryTests(unittest.TestCase):
    def publisher(self):
        self.assertTrue(callable(getattr(history, 'build_issue', None)), 'Publisher must select verified records, not generate dates with an LLM')
        return history

    def test_wrong_anniversary_cannot_enter_today(self):
        h = self.publisher()
        self.assertEqual(h.build_issue([EVENT], '2026-09-22')['events'], [])
        self.assertEqual(h.build_issue([EVENT], '2026-10-16')['events'][0]['id'], EVENT['id'])

    def test_missing_or_conflicting_source_rejected(self):
        h = self.publisher()
        for sources in [[], [{'name': '来源', 'url': 'https://example.org', 'date': '1964-09-22'}],
                        [{'name': '来源', 'url': 'javascript:alert(1)', 'date': EVENT['date']}]]:
            with self.subTest(sources=sources), self.assertRaises(ValueError):
                h.build_issue([{**EVENT, 'sources': sources}], '2026-10-16')

    def test_invalid_date_and_duplicates_rejected(self):
        h = self.publisher()
        for records in [[{**EVENT, 'date': '1964-02-30'}], [EVENT, EVENT]]:
            with self.assertRaises(ValueError):
                h.build_issue(records, '2026-09-22')

    def test_leap_day_and_future_events(self):
        h = self.publisher()
        leap = copy.deepcopy(EVENT)
        leap['date'] = leap['sources'][0]['date'] = '2000-02-29'
        self.assertEqual(len(h.build_issue([leap], '2024-02-29')['events']), 1)
        self.assertEqual(h.build_issue([leap], '2025-02-28')['events'], [])
        self.assertEqual(h.build_issue([EVENT], '1960-10-16')['events'], [])

    def test_empty_issue_is_explicit(self):
        issue = self.publisher().build_issue([EVENT], '2026-09-22')
        self.assertEqual(issue['date'], '2026-09-22')
        self.assertEqual(issue['status'], 'empty')
        self.assertEqual(issue['timezone'], 'Asia/Shanghai')

    def test_invalid_catalog_preserves_existing_output(self):
        h = self.publisher()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'today_news.json').write_text('["last-good"]', encoding='utf-8')
            (root / 'catalog.json').write_text(json.dumps({'schemaVersion': 2, 'updatedAt': '2026-09-22', 'events': [{**EVENT, 'sources': []}]}), encoding='utf-8')
            with self.assertRaises(ValueError):
                h.publish(root, '2026-09-22')
            self.assertEqual((root / 'today_news.json').read_text(), '["last-good"]')

    def test_reviewed_catalog_keeps_known_corrections(self):
        h = self.publisher()
        catalog = json.loads((Path(__file__).parents[1] / 'catalog.json').read_text(encoding='utf-8-sig'))
        h.validate_events(catalog['events'])
        dates = {event['id']: event['date'] for event in catalog['events']}
        expected = {'first-atomic-test': '1964-10-16', 'synthetic-insulin': '1965-09-17',
                    'dongfanghong-1': '1970-04-24', 'un-resolution-2758': '1971-10-25',
                    'three-gorges-start': '1994-12-14', 'china-wto': '2001-12-11',
                    'shenzhou-5': '2003-10-15', 'beijing-tianjin-rail': '2008-08-01',
                    'change-3-landing': '2013-12-14', 'poverty-alleviation': '2021-02-25'}
        for event_id, correct_date in expected.items():
            self.assertEqual(dates[event_id], correct_date)


if __name__ == '__main__':
    unittest.main()
