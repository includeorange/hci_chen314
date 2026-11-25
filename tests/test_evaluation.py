import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'evaluation'))
from evaluate_counts import evaluate


class EventEvaluationTest(unittest.TestCase):
    def test_equal_totals_can_hide_both_errors(self):
        session = {'events': [{'id': 3, 'type': 'auto_count'}, {'id': 5, 'type': 'auto_count'}],
                   'automatic_count': 2, 'manual_adjustment': 0, 'final_count': 2}
        rows = [dict(action_id='A01', matched_auto_event_id='3', action_time_ms='1000', display_time_ms='1250'),
                dict(action_id='A02', matched_auto_event_id='', action_time_ms='', display_time_ms='')]
        r = evaluate(session, rows)
        self.assertEqual(r['误计次数'], 1)
        self.assertEqual(r['漏计次数'], 1)
        self.assertEqual(r['反馈延迟均值_ms'], 250)

    def test_missing_timing_is_not_reported_as_zero(self):
        session = {'events': [{'id': 3, 'type': 'auto_count'}], 'automatic_count': 1, 'manual_adjustment': 0, 'final_count': 1}
        rows = [dict(action_id='A01', matched_auto_event_id='3', action_time_ms='', display_time_ms='')]
        self.assertIsNone(evaluate(session, rows)['反馈延迟均值_ms'])
        with self.assertRaises(ValueError):
            evaluate(session, rows + [dict(rows[0], action_id='A02')])


if __name__ == '__main__':
    unittest.main()
