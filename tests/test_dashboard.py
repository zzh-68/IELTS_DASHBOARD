import io
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from learning import load_data, window_stats, weaknesses, build_plan

ROOT = Path(__file__).resolve().parents[1]
class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.df = load_data(ROOT / 'data/demo_sessions.csv')

    def test_demo_provenance(self):
        self.assertEqual(len(self.df), 20)
        self.assertTrue(self.df.is_demo.all())
        self.assertEqual(set(self.df.score_source), {'simulated_practice'})

    def test_trend_requires_six(self):
        self.assertIsNone(window_stats(pd.Series([5., 5., 5., 6., 6.]))[1])
        self.assertEqual(window_stats(pd.Series([6., 6., 6., 5., 5., 5.]))[1], -1)

    def test_priority_and_missing(self):
        weak = weaknesses(self.df, 7)
        row = weak[(weak.skill=='Writing') & (weak.criterion=='grammar')].iloc[0]
        self.assertAlmostEqual(row.priority, 7 - (5+5.5+5.5)/3)
        self.assertTrue(weak.change.isna().all())
        self.assertTrue(weaknesses(self.df.iloc[:0], 7).empty)

    def test_budget_and_diagnostics(self):
        for minutes in [35, 210, 420]:
            plan = build_plan(self.df, 7, minutes, '2026-11-02')
            self.assertEqual(plan.minutes.sum(), minutes)
            self.assertTrue((plan.minutes > 0).all())
            self.assertLessEqual(len(plan), 7)
        plan = build_plan(self.df.iloc[:0], 7, 210, '2026-11-02')
        self.assertEqual(set(plan.skill), {'Writing','Speaking','Reading','Listening'})
        self.assertTrue(plan.focus.eq('Diagnostic').all())

    def test_source_isolation(self):
        bad = self.df.copy(); bad.loc[0, 'score_source'] = 'human_assessed'
        with self.assertRaises(ValueError):
            build_plan(bad, 7, 210, '2026-11-02')

    def test_validation(self):
        for column, value in [('score', 10), ('score', 6.2), ('date', 'bad-date'), ('duration_minutes', -5), ('score_source', 'official_ielts'), ('is_demo', 'maybe')]:
            with self.subTest(column=column, value=value):
                bad = self.df.copy(); bad[column] = bad[column].astype(object); bad.loc[0,column] = value
                with self.assertRaises((ValueError, TypeError)):
                    load_data(io.StringIO(bad.to_csv(index=False)))

class PageTests(unittest.TestCase):
    def test_default_and_empty_source(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(ROOT / 'app.py')).run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.metric), 4)
        app.sidebar.selectbox[1].select('official_ielts').run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any('No matching records' in w.value for w in app.warning))
        app.sidebar.selectbox[1].select('simulated_practice').run(timeout=30)
        app.sidebar.slider[1].set_value(35).run(timeout=30)
        self.assertEqual(len(app.exception), 0)

if __name__ == '__main__':
    unittest.main()
