import unittest

from strategic import (
    best_responses,
    grounded_mechanism,
    has_odd_length_path,
    is_strategyproof,
    theorem_5_4_condition,
    truthfulness_is_best_response,
)


class TestGroundedMechanism(unittest.TestCase):
    def test_induces_graph_from_union_of_reports(self):
        attacks = [("a1", "a2"), ("a2", "a3"), ("a3", "a4")]
        reports = {"one": {"a1", "a3"}, "two": {"a2", "a4"}}
        self.assertEqual(grounded_mechanism(attacks, reports), frozenset({"a1", "a3"}))

    def test_hidden_argument_and_incident_attacks_are_removed(self):
        attacks = [("a1", "a2"), ("a2", "a3")]
        self.assertEqual(
            grounded_mechanism(attacks, {"one": {"a1"}, "two": {"a3"}}),
            frozenset({"a1", "a3"}),
        )


class TestStrategicProperties(unittest.TestCase):
    def test_best_response_includes_truthful_report(self):
        attacks = [("a1", "a2"), ("a2", "a3")]
        self.assertIn(
            frozenset({"a1", "a2"}),
            best_responses({"a1", "a2"}, attacks, {"other": {"a3"}}, "me"),
        )

    def test_odd_path_handles_cycles_without_looping(self):
        attacks = [("a", "b"), ("b", "c"), ("c", "a")]
        self.assertTrue(has_odd_length_path({"a", "b", "c"}, attacks, "a", "b"))
        self.assertTrue(has_odd_length_path({"a", "b", "c"}, attacks, "a", "c"))

    def test_theorem_condition_and_truthfulness_agree(self):
        assignments = {"one": {"a1", "a2"}, "two": {"a3"}}
        attacks = [("a1", "a2"), ("a2", "a3")]
        self.assertFalse(theorem_5_4_condition(assignments, attacks))
        self.assertTrue(is_strategyproof(assignments, attacks))
        self.assertEqual(
            truthfulness_is_best_response(assignments, attacks),
            is_strategyproof(assignments, attacks),
        )

    def test_even_path_satisfies_condition(self):
        assignments = {"one": {"a1", "a3"}, "two": {"a2"}}
        attacks = [("a1", "a2"), ("a2", "a3")]
        self.assertTrue(theorem_5_4_condition(assignments, attacks))
        self.assertTrue(is_strategyproof(assignments, attacks))


if __name__ == "__main__":
    unittest.main()
