import copy
import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).parents[1] / 'collect_history.py'
DOC = {'id': 's1', 'url': 'https://www.gov.cn/example.html', 'name': '中国政府网',
       'text': '往事回顾：1990年9月22日，第十一届亚洲运动会在北京开幕。比赛于10月7日结束。'}
CANDIDATE = {'date': '1990-09-22', 'title': '北京亚运会开幕', 'category': '社会', 'location': '北京',
             'summary': '第十一届亚洲运动会在北京开幕。', 'sourceId': 's1',
             'evidence': '1990年9月22日，第十一届亚洲运动会在北京开幕。'}


class CollectionTests(unittest.TestCase):
    def module(self):
        self.assertTrue(MODULE.exists(), 'Daily collection must perform retrieval before DeepSeek generation')
        spec = importlib.util.spec_from_file_location('collector', MODULE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_valid_evidence_is_accepted_with_stable_id(self):
        m = self.module()
        event = m.validate_candidate(CANDIDATE, [DOC], '2026-09-22')
        self.assertEqual(event['date'], '1990-09-22')
        self.assertEqual(event['verification'], 'source-matched')
        self.assertEqual(event['sources'][0]['evidence'], CANDIDATE['evidence'])
        self.assertEqual(event['id'], m.validate_candidate(CANDIDATE, [DOC], '2027-09-22')['id'])

    def test_invented_date_quote_or_source_rejected(self):
        m = self.module()
        for patch in [{'date': '1964-09-22'}, {'date': '1990-09-23'}, {'sourceId': 'invented'},
                      {'evidence': '1990年9月22日，中国第一颗原子弹爆炸成功。'}]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                m.validate_candidate({**CANDIDATE, **patch}, [DOC], '2026-09-22')

    def test_publication_date_alone_is_not_evidence(self):
        m = self.module()
        doc = {**DOC, 'text': '发布时间：1990年9月22日\n中国第一颗原子弹爆炸成功。'}
        with self.assertRaises(ValueError):
            m.validate_candidate({**CANDIDATE, 'evidence': '1990年9月22日'}, [doc], '2026-09-22')

    def test_only_allowlisted_source_hosts(self):
        m = self.module()
        for url in ['https://www.gov.cn.evil.test/a', 'http://www.gov.cn/a', 'https://127.0.0.1/a', 'https://www.gov.cn@evil.test/a']:
            self.assertFalse(m.allowed_url(url))
        self.assertTrue(m.allowed_url('https://www.cnsa.gov.cn/example.html'))

    def test_merge_keeps_reviewed_record_and_avoids_duplicate_source(self):
        m = self.module()
        event = m.validate_candidate(CANDIDATE, [DOC], '2026-09-22')
        editorial = {**event, 'id': 'editorial-id', 'verification': 'editorial', 'summary': '已人工核对的摘要'}
        self.assertEqual(m.merge_events([editorial], [event]), [editorial])


if __name__ == '__main__':
    unittest.main()
