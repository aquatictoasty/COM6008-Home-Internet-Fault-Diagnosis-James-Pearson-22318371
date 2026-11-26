"""checks the fixed sample and descriptive statistics used in the search test."""
import unittest

from scripts.search_experiment import GOAL, distribution, manhattan, sample_states

class SearchExperimentTests(unittest.TestCase):
    def test_sample_is_unique_and_stratified_by_exact_solution_depth(self):
        states = sample_states(seed=7)
        self.assertEqual(len(states), 50)
        values = [state for state, _ in states]
        depths = [depth for _, depth in states]
        self.assertEqual(len(values), len(set(values)))
        self.assertEqual({d: depths.count(d) for d in range(16, 21)},
                         {16: 10, 17: 10, 18: 10, 19: 10, 20: 10})
        self.assertTrue(all(sorted(state) == list(range(9)) for state in values))
        self.assertTrue(all(manhattan(state) <= depth for state, depth in states))
        self.assertEqual(manhattan(GOAL), 0)

    def test_distribution_reports_range_inclusive_iqr_and_sample_sd(self):
        result = distribution([1, 2, 3, 4, 5])
        self.assertEqual((result["min"], result["max"]), (1, 5))
        self.assertEqual((result["q1"], result["q3"], result["iqr"]), (2, 4, 2))
        self.assertGreater(result["sample_sd"], 0)

if __name__ == "__main__":
    unittest.main()
