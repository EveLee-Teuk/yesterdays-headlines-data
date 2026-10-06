"""Daily coverage must be earned by verified events, never by readable-page counts."""
import copy
import datetime as dt
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import collect_history as collector
from fetch_history import atomic_json
from test_collect import CANDIDATE, DOC


class CoverageTests(unittest.TestCase):
    def root(self, directory, events=None):
        root = Path(directory)
        atomic_json(root / 'catalog.json', {'schemaVersion': 2, 'updatedAt': '2026-09-22',
                                           'events': events or [],
                                           'lastRun': {'date': '2026-09-22', 'status': 'ready'}})
        return root

    def layers(self, count=3):
        return [[{**DOC, 'id': f's{index+1}', 'url': f'https://www.gov.cn/layer{index}'}]
                for index in range(count)]

    def test_leader_itinerary_from_real_1989_source_is_not_a_scientific_milestone(self):
        evidence = '1989年10月6日，江泽民同志视察北京正负电子对撞机。'
        document = {'id': 's1', 'url': 'https://ihep.cas.cn/gk/lsyg/',
                    'name': '中国科学院高能物理研究所', 'text': evidence}
        candidate = {**CANDIDATE, 'date': '1989-10-06', 'title': '江泽民视察北京正负电子对撞机',
                     'category': '科技', 'evidence': evidence, 'summary': evidence}
        with self.assertRaisesRegex(ValueError, 'itinerary'):
            collector.validate_candidate(candidate, [document], '2026-10-06')
        stored = {key: candidate[key] for key in ('date', 'title', 'category', 'location', 'summary')}
        stored.update(id='history-itinerary', verification='source-matched', reviewedAt='2026-10-06',
                      sources=[{'name': document['name'], 'url': document['url'],
                                'date': candidate['date'], 'evidence': evidence}])
        self.assertEqual(collector.verified_for_date([stored], '2026-10-06'), [])

    def test_explicit_itinerary_titles_are_rejected_without_blocking_scientific_expeditions(self):
        for title in ('领导视察科研机构', '领导会见科学家', '领导接见考察队', '领导听取科研工作汇报'):
            with self.subTest(title=title), self.assertRaisesRegex(ValueError, 'itinerary'):
                collector.validate_candidate({**CANDIDATE, 'title': title}, [DOC], '2026-09-22')
        # Synthetic fixture: the word 考察 alone must not classify a scientific expedition as a visit.
        evidence = '1990年9月22日，中国科学考察队完成海洋调查任务。'
        event = collector.validate_candidate({**CANDIDATE, 'title': '科学考察队完成海洋调查',
                                               'category': '科技', 'evidence': evidence},
                                             [{**DOC, 'text': evidence}], '2026-09-22')
        self.assertEqual(collector.verified_for_date([event], '2026-09-22'), [event])

    def test_empty_first_layer_continues_until_reviewer_approved(self):
        batches = self.layers()
        batches[0] = [{**DOC, 'id': f'first-{index}', 'url': f'https://www.gov.cn/first-{index}'}
                      for index in range(6)]
        second = {**CANDIDATE, 'sourceId': 's2'}
        with tempfile.TemporaryDirectory() as directory:
            root = self.root(directory)
            with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test-only'}, clear=True), \
                 patch.object(collector, 'retrieve_layers', return_value=iter(batches)), \
                 patch.object(collector, 'deepseek_json', side_effect=[
                     {'events': []}, {'events': [second]}, {'approved': [0]}]) as model:
                collector.collect(root, '2026-09-22')
            issue = json.loads((root / 'archives/2026-09-22.json').read_text('utf-8'))
            self.assertEqual(issue['status'], 'ready')
            self.assertEqual(len(issue['events']), 1)
            self.assertEqual(model.call_count, 3)
            self.assertEqual(model.call_args_list[-1].args[0], collector.REVIEWER)

    def test_reviewer_rejection_continues_to_new_sources(self):
        batches = self.layers()
        second = {**CANDIDATE, 'sourceId': 's2'}
        with tempfile.TemporaryDirectory() as directory:
            root = self.root(directory)
            with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test-only'}, clear=True), \
                 patch.object(collector, 'retrieve_layers', return_value=iter(batches)), \
                 patch.object(collector, 'deepseek_json', side_effect=[
                     {'events': [CANDIDATE]}, {'approved': []},
                     {'events': [second]}, {'approved': [0]}]):
                collector.collect(root, '2026-09-22')
            events = json.loads((root / 'archives/2026-09-22.json').read_text('utf-8'))['events']
            self.assertEqual(events[0]['sources'][0]['url'], batches[1][0]['url'])

    def test_exhausted_empty_layers_fail_without_publishing_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.root(directory)
            before = (root / 'catalog.json').read_bytes()
            with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test-only'}, clear=True), \
                 patch.object(collector, 'retrieve_layers', return_value=iter(self.layers())), \
                 patch.object(collector, 'deepseek_json', return_value={'events': []}):
                with self.assertRaisesRegex(RuntimeError, 'verified'):
                    collector.collect(root, '2026-09-22')
            self.assertEqual((root / 'catalog.json').read_bytes(), before)
            self.assertFalse((root / 'archives').exists())
            diagnostic = json.loads((root / 'collection_diagnostics/2026-09-22.json').read_text('utf-8'))
            self.assertEqual(diagnostic['outcome'], 'failed')

    def test_verified_catalog_event_survives_model_outage(self):
        event = collector.validate_candidate(CANDIDATE, [DOC], '2026-09-22')
        with tempfile.TemporaryDirectory() as directory:
            root = self.root(directory, [event])
            with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test-only'}, clear=True), \
                 patch.object(collector, 'retrieve_layers', return_value=iter(self.layers())), \
                 patch.object(collector, 'deepseek_json', side_effect=RuntimeError('test outage')):
                collector.collect(root, '2026-09-22')
            issue = json.loads((root / 'archives/2026-09-22.json').read_text('utf-8'))
            self.assertEqual(issue['events'], [event])
            diagnostic = json.loads((root / 'collection_diagnostics/2026-09-22.json').read_text('utf-8'))
            self.assertEqual(diagnostic['outcome'], 'ready')
            self.assertTrue(diagnostic['degraded'])

    def test_unmarked_legacy_entry_does_not_satisfy_guarantee(self):
        event = collector.validate_candidate(CANDIDATE, [DOC], '2026-09-22')
        event.pop('verification')
        event['sources'][0].pop('evidence')
        with tempfile.TemporaryDirectory() as directory:
            root = self.root(directory, [event])
            with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test-only'}, clear=True), \
                 patch.object(collector, 'retrieve_layers', return_value=iter([])):
                with self.assertRaises(RuntimeError): collector.collect(root, '2026-09-22')
            self.assertFalse((root / 'archives').exists())

    def test_prepare_does_not_advance_publication_and_uses_actual_reference_date(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.root(directory)
            before = json.loads((root / 'catalog.json').read_text('utf-8'))
            with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test-only'}, clear=True), \
                 patch.object(collector, 'retrieve_layers', return_value=iter(self.layers())), \
                 patch.object(collector, 'deepseek_json', side_effect=[
                     {'events': [CANDIDATE]}, {'approved': [0]}]):
                collector.collect(root, '2027-09-22', prepare=True, reference_date='2026-10-06')
            catalog = json.loads((root / 'catalog.json').read_text('utf-8'))
            self.assertEqual(catalog['lastRun'], before['lastRun'])
            self.assertEqual(catalog['updatedAt'], dt.datetime.now(collector.BEIJING).date().isoformat())
            self.assertEqual(json.loads((root / 'prepared/2027-09-22.json').read_text('utf-8'))['status'], 'ready')
            for name in ('archives', 'issue.json', 'today_news.json', 'collection_status.json'):
                self.assertFalse((root / name).exists(), name)

    def test_future_issue_never_accepts_planned_event(self):
        doc = {**DOC, 'text': '2027年9月22日，北京某博物馆新馆计划正式开馆。'}
        candidate = {**CANDIDATE, 'date': '2027-09-22', 'evidence': doc['text']}
        with self.assertRaises(ValueError):
            collector.validate_candidate(candidate, [doc], '2028-09-22', reference_date='2026-10-06')

    def test_full_numeric_dates_supported_but_partial_dates_not_inferred(self):
        for value in ('1990-09-22', '1990.9.22'):
            evidence = value + '，第十一届亚洲运动会在北京开幕。'
            event = collector.validate_candidate({**CANDIDATE, 'evidence': evidence},
                                                 [{**DOC, 'text': evidence}], '2026-09-22')
            self.assertEqual(event['date'], '1990-09-22')
        evidence = '9月22日，第十一届亚洲运动会在北京开幕。'
        with self.assertRaises(ValueError):
            collector.validate_candidate({**CANDIDATE, 'evidence': evidence},
                                         [{**DOC, 'text': '1990年大事记：' + evidence}], '2026-09-22')

    def test_omitting_publication_label_from_quote_does_not_make_it_event_evidence(self):
        evidence = '1990-09-22，第十一届亚洲运动会在北京开幕的历史报道。'
        with self.assertRaises(ValueError):
            collector.validate_candidate({**CANDIDATE, 'evidence': evidence},
                                         [{**DOC, 'text': '发布日期：' + evidence}], '2026-09-22')

    def test_extended_hosts_remain_exact_suffix_https_allowlist(self):
        for url in ('https://www.tsinghua.edu.cn/history', 'https://news.cctv.com/a',
                    'https://www.chinanews.com/a', 'https://news.gmw.cn/a'):
            self.assertTrue(collector.allowed_url(url), url)
        for url in ('https://edu.cn.evil.test/a', 'https://evil-cctv.com/a',
                    'http://news.cctv.com/a', 'https://news.cctv.com:444/a'):
            self.assertFalse(collector.allowed_url(url), url)

    def test_verified_helper_rejects_missing_or_conflicting_evidence(self):
        event = collector.validate_candidate(CANDIDATE, [DOC], '2026-09-22')
        self.assertEqual(collector.verified_for_date([event], '2026-09-22'), [event])
        self.assertEqual(collector.verified_for_date([event], '2026-09-23'), [])
        bad = copy.deepcopy(event)
        bad['sources'][0]['evidence'] = '1990年9月23日，第十一届亚洲运动会在北京开幕。'
        self.assertEqual(collector.verified_for_date([bad], '2026-09-22'), [])

    def test_verified_helper_rejects_review_dates_after_reference_day(self):
        event = collector.validate_candidate(CANDIDATE, [DOC], '2026-09-22')
        event['reviewedAt'] = '2026-09-23'
        self.assertEqual(collector.verified_for_date([event], '2026-09-22', '2026-09-22'), [])
        event['reviewedAt'] = '2026-09-22'
        self.assertEqual(collector.verified_for_date([event], '2026-09-22', '2026-09-22'), [event])

    def test_future_review_label_does_not_block_a_newly_verified_record(self):
        event = collector.validate_candidate(CANDIDATE, [DOC], '2026-09-22')
        invalid = {**event, 'reviewedAt': '2999-01-01'}
        self.assertEqual(collector.merge_events([invalid], [event]), [event])

    def test_expired_budget_does_not_start_external_requests(self):
        fake = types.SimpleNamespace(DDGS=lambda **kw: None)
        with patch.dict('sys.modules', {'ddgs': fake}), \
             patch.object(collector, 'read_document') as read:
            metrics = {}
            layers = list(collector.retrieve_layers('2026-09-22', [], metrics,
                                                    deadline=collector.time.monotonic() - 1))
        self.assertEqual(layers, [])
        self.assertEqual(read.call_count, 0)
        self.assertTrue(metrics['budgetExhausted'])

    def test_layers_deduplicate_sources_and_keep_model_batches_bounded(self):
        results = [{'href': f'https://www.gov.cn/{number}'} for number in range(30)]
        fake = types.SimpleNamespace(DDGS=lambda **kw: types.SimpleNamespace(
            text=lambda *a, **kw: results))
        def document(url, day, **kwargs):
            return {**DOC, 'url': url}
        with patch.dict('sys.modules', {'ddgs': fake}), \
             patch.object(collector, 'read_document', side_effect=document) as read:
            metrics = {}
            layers = list(collector.retrieve_layers('2026-09-22', [], metrics))
        urls = [doc['url'] for layer in layers for doc in layer]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertTrue(all(len(layer) <= collector.MAX_MODEL_SOURCES_PER_LAYER for layer in layers))
        self.assertEqual(metrics['searchAttempted'], 15)
        self.assertEqual(read.call_count, 8)
        # Readable documents 7 and 8 must be considered by the next layer, not discarded.
        self.assertEqual(len(urls), 8)

    def test_reverified_legacy_duplicate_replaces_legacy_record(self):
        event = collector.validate_candidate(CANDIDATE, [DOC], '2026-09-22')
        legacy = copy.deepcopy(event)
        legacy.pop('verification')
        legacy['sources'][0].pop('evidence')
        merged = collector.merge_events([legacy], [event])
        self.assertEqual(merged, [event])

    def test_invalid_evidence_is_not_protected_by_verification_marker(self):
        event = collector.validate_candidate(CANDIDATE, [DOC], '2026-09-22')
        for old_id in (event['id'], 'legacy-different-id'):
            with self.subTest(old_id=old_id):
                invalid = copy.deepcopy(event)
                invalid['id'] = old_id
                invalid['sources'][0]['evidence'] = '1990年9月23日，第十一届亚洲运动会在北京开幕。'
                self.assertEqual(collector.merge_events([invalid], [event]), [event])

    def test_legacy_entries_are_hints_not_model_deduplication_and_can_be_reverified(self):
        event = collector.validate_candidate(CANDIDATE, [DOC], '2026-09-22')
        for marker in (None, 'source-matched', 'editorial'):
            with self.subTest(marker=marker), tempfile.TemporaryDirectory() as directory:
                legacy = copy.deepcopy(event)
                if marker is None:
                    legacy.pop('verification')
                else:
                    legacy['verification'] = marker
                if marker != 'editorial':
                    legacy['sources'][0].pop('evidence')
                root = self.root(directory, [legacy])
                with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test-only'}, clear=True), \
                     patch.object(collector, 'retrieve_layers', return_value=[[DOC]]) as retrieve, \
                     patch.object(collector, 'deepseek_json', side_effect=[
                         {'events': [CANDIDATE]}, {'approved': [0]}]) as model:
                    issue = collector.collect(root, '2026-09-22')
                self.assertEqual(retrieve.call_args.args[1], [legacy])
                self.assertEqual(model.call_args_list[0].args[1]['existing'], [])
                self.assertEqual(model.call_args_list[-1].args[1]['existing'], [])
                self.assertEqual(issue['events'], [event])
                self.assertEqual(len(json.loads((root / 'catalog.json').read_text('utf-8'))['events']), 1)

    def test_published_issue_excludes_unverified_legacy_but_preserves_catalog(self):
        event = collector.validate_candidate(CANDIDATE, [DOC], '2026-09-22')
        legacy = copy.deepcopy(event)
        legacy.update(id='legacy-another', title='未经本轮原文核验的旧记录')
        legacy.pop('verification')
        with tempfile.TemporaryDirectory() as directory:
            root = self.root(directory, [event, legacy])
            issue = collector.publish_verified(root, '2026-09-22')
            self.assertEqual(issue['events'], [event])
            catalog = json.loads((root / 'catalog.json').read_text('utf-8'))
            self.assertEqual(len(catalog['events']), 2)
            self.assertEqual(json.loads((root / 'today_news.json').read_text('utf-8'))[0]['id'], event['id'])

    def test_hints_are_retrieved_and_validated_even_when_search_is_unavailable(self):
        fake = types.SimpleNamespace(DDGS=lambda **kw: types.SimpleNamespace(
            text=lambda *a, **kw: (_ for _ in ()).throw(RuntimeError('outage'))))
        with tempfile.TemporaryDirectory() as directory:
            root = self.root(directory)
            atomic_json(root / 'source_hints.json', {'schemaVersion': 1, 'byMonthDay': {
                '09-22': [DOC['url'], 'https://evil.test/a']}, 'evergreen': []})
            with patch.dict('sys.modules', {'ddgs': fake}), \
                 patch.object(collector, 'read_document', return_value=copy.deepcopy(DOC)) as read:
                layers = list(collector.retrieve_layers('2026-09-22', [], root=root))
            self.assertEqual(sum(len(layer) for layer in layers), 1)
            self.assertEqual(read.call_count, 1)
            self.assertEqual(read.call_args.args[0], DOC['url'])


if __name__ == '__main__':
    unittest.main()
