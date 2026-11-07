"""
Tests for experiments.py.

  * instance generation (shape, determinism, the options),
  * the per-instance analysis and the classification of strategyproof instances
    whose Theorem 5.4 condition fails, on small hand-checked instances (these are
    the instances discussed in REPORT.md),
  * the experiment driver, the summary arithmetic and the files written,
  * the committed files in results/ are consistent with each other and with a
    fresh analysis of a sample of their instances.
"""

import contextlib
import csv
import io
import os
import random
import tempfile
import unittest

from experiments import (
    INERT,
    TRADE_OFF,
    Instance,
    analyse_instance,
    classify_condition_failure,
    generate_instance,
    has_direct_conflict,
    main,
    run_experiment,
    summarise,
)
from strategic import check_odd_path_condition, check_truthful_dominant
from strategic_examples import EXAMPLE_5_10, EXAMPLE_5_11

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")


def fs(*items):
    return frozenset(items)


def make(types, attacks, index=1, p=0.0):
    types = tuple(fs(*t) for t in types)
    n = len(frozenset().union(*types))
    return Instance(index, p, n, types, frozenset(attacks))


def parse_set(text):
    text = text.strip().strip("{}")
    return frozenset(x for x in text.split(",") if x)


def parse_instance(row):
    types = tuple(parse_set(t) for t in row["types"].split("|"))
    attacks = frozenset(tuple(a.split(">")) for a in row["attacks"].split()) if row["attacks"] else frozenset()
    return Instance(int(row["index"]), float(row["p"]), int(row["n_args"]), types, attacks)


class TestGeneration(unittest.TestCase):
    def test_shape(self):
        rng = random.Random(1)
        for k in range(300):
            inst = generate_instance(rng, k, 0.3)
            self.assertIn(inst.n_args, (6, 7, 8))
            self.assertEqual(len(inst.types), 3)
            all_args = {f"a{i}" for i in range(1, inst.n_args + 1)}
            self.assertEqual(frozenset().union(*inst.types), all_args)  # every argument is owned ...
            self.assertEqual(sum(len(t) for t in inst.types), inst.n_args)  # ... by exactly one agent
            for x, y in inst.attacks:
                self.assertIn(x, all_args)
                self.assertIn(y, all_args)
                self.assertNotEqual(x, y)  # no self-attacks by default

    def test_all_sizes_and_agents_occur(self):
        rng = random.Random(2)
        sizes = set()
        empty_agent = False
        for k in range(400):
            inst = generate_instance(rng, k, 0.2)
            sizes.add(inst.n_args)
            empty_agent |= any(not t for t in inst.types)
        self.assertEqual(sizes, {6, 7, 8})
        self.assertTrue(empty_agent)  # random assignment can leave an agent without arguments

    def test_self_attacks_only_when_asked(self):
        rng = random.Random(3)
        plain = [generate_instance(rng, k, 0.5) for k in range(100)]
        self.assertFalse(any(x == y for inst in plain for (x, y) in inst.attacks))
        with_self = [generate_instance(rng, k, 0.5, self_attacks=True) for k in range(100)]
        self.assertTrue(any(x == y for inst in with_self for (x, y) in inst.attacks))

    def test_attack_probability_is_respected(self):
        rng = random.Random(4)
        for p in (0.0, 1.0):
            inst = generate_instance(rng, 0, p, n_args=6)
            self.assertEqual(len(inst.attacks), 0 if p == 0 else 30)
        total = sum(len(generate_instance(rng, k, 0.25, n_args=8).attacks) for k in range(400))
        self.assertAlmostEqual(total / (400 * 56), 0.25, delta=0.02)

    def test_deterministic_for_a_seed(self):
        a = generate_instance(random.Random(9), 1, 0.3)
        b = generate_instance(random.Random(9), 1, 0.3)
        self.assertEqual(a, b)


class TestAnalysis(unittest.TestCase):
    def test_book_examples(self):
        r = analyse_instance(Instance(1, 0, 5, EXAMPLE_5_10.types, EXAMPLE_5_10.attacks))
        self.assertFalse(r["strategyproof"])
        self.assertFalse(r["condition_holds"])
        self.assertEqual(r["manipulating_agents"], "0")
        self.assertEqual(r["failure_class"], "")  # only classified when strategyproof
        r = analyse_instance(Instance(2, 0, 6, EXAMPLE_5_11.types, EXAMPLE_5_11.attacks))
        self.assertTrue(r["strategyproof"])
        self.assertFalse(r["condition_holds"])
        self.assertEqual(r["odd_pairs"], "0:a1>a4;0:a1>a5")
        self.assertFalse(r["direct_conflict"])
        # a6 -> a3 cuts the path a1 -> a2 -> a3 -> a4/a5, so hiding never gains anything: inert
        self.assertEqual(r["failure_class"], INERT)
        self.assertEqual(r["biting_scenarios"], 0)

    def test_no_attacks_is_trivially_fine(self):
        r = analyse_instance(make([{"a1", "a2"}, {"a3"}, set()], []))
        self.assertTrue(r["strategyproof"])
        self.assertTrue(r["condition_holds"])
        self.assertEqual(r["empty_agents"], 1)
        self.assertEqual(r["n_attacks"], 0)

    def test_direct_conflict_detection(self):
        self.assertTrue(has_direct_conflict(make([{"a", "b"}, {"c"}], [("a", "b")])))
        self.assertFalse(has_direct_conflict(make([{"a"}, {"b", "c"}], [("a", "b")])))  # attack across agents
        self.assertFalse(has_direct_conflict(make([{"a", "b"}], [("a", "a")])))  # self-attack is not a pair

    def test_record_fields(self):
        r = analyse_instance(make([{"a1", "a2", "a3"}, {"a4", "a5", "a6"}, set()], [("a5", "a6")], index=9, p=0.05))
        for key in (
            "index", "p", "n_args", "n_attacks", "types", "attacks", "strategyproof",
            "condition_holds", "condition_holds_simple_paths", "condition_holds_incl_same",
            "condition_holds_simple_incl_same", "odd_pairs", "direct_conflict", "failure_class",
        ):
            self.assertIn(key, r)
        self.assertEqual(r["types"], "{a1,a2,a3} | {a4,a5,a6} | {}")
        self.assertEqual(r["attacks"], "a5>a6")


class TestClassification(unittest.TestCase):
    """The instances discussed in REPORT.md (instance numbers refer to the default run)."""

    def check(self, inst, expected_class, direct):
        r = analyse_instance(inst)
        self.assertTrue(r["strategyproof"])
        self.assertFalse(r["condition_holds"])
        self.assertEqual(r["direct_conflict"], direct)
        self.assertEqual(r["failure_class"], expected_class)
        return r

    def test_direct_conflict_is_a_swap(self):
        # instance 9: agent 1 owns a4, a5, a6 and a5 -> a6: revealing all gives {a4, a5} (2);
        # hiding a5 gives {a4, a6} (2); hiding a6 gives {a4, a5} (2): a tie, never a gain
        inst = make([{"a1", "a2", "a3"}, {"a4", "a5", "a6"}, set()], [("a5", "a6")], index=9)
        r = self.check(inst, TRADE_OFF, direct=True)
        self.assertGreater(r["tie_scenarios"], 0)

    def test_indirect_odd_path_is_also_a_swap(self):
        # instance 30: agent 1 owns a1, a2, a3, a6; a3 -> a5 -> a4 -> a1 has length 3.
        # reveal all: outcome {a2, a3, a4, a6} (3); hide a3: {a1, a2, a5, a6} (3): a3 traded for a1
        inst = make([{"a4"}, {"a1", "a2", "a3", "a6"}, {"a5"}], [("a3", "a5"), ("a4", "a1"), ("a5", "a4")], index=30)
        r = self.check(inst, TRADE_OFF, direct=False)
        self.assertGreater(r["tie_scenarios"], 0)

    def test_odd_path_absorbed_by_mutual_attacks(self):
        # instance 1098: a3 -> a5 -> a1 -> a4 has length 3, but a4 and a5 each attack a1 and are
        # attacked back, so a4 stays undecided whether or not a3 is revealed: hiding never gains
        inst = make(
            [{"a2", "a5"}, {"a3", "a4"}, {"a1", "a6"}],
            [("a1", "a4"), ("a1", "a5"), ("a2", "a6"), ("a3", "a5"), ("a4", "a1"), ("a5", "a1")],
            index=1098,
        )
        self.check(inst, INERT, direct=False)

    def test_endpoint_defeated_whatever_happens(self):
        # instance 8: a2 -> a1 -> a5 -> a6 has length 3 but a2 -> a1 -> a6 has length 2.  Whether a1
        # is accepted (it attacks a6) or not (then a5 is accepted and attacks a6), a6 is always out.
        inst = make(
            [{"a3", "a5"}, {"a2", "a4", "a6"}, {"a1"}],
            [("a1", "a4"), ("a1", "a5"), ("a1", "a6"), ("a2", "a1"), ("a5", "a6")],
            index=8,
        )
        self.check(inst, INERT, direct=False)

    def test_classify_directly(self):
        inst = make([{"a", "b"}, {"c"}, set()], [("a", "b")])
        fc = classify_condition_failure(inst, [0])
        self.assertEqual(fc.label, TRADE_OFF)
        self.assertEqual(fc.worst_net, 0)
        self.assertLessEqual(fc.tie_scenarios, fc.biting_scenarios)

    def test_not_strategyproof_instances_have_no_class(self):
        r = analyse_instance(Instance(1, 0, 5, EXAMPLE_5_10.types, EXAMPLE_5_10.attacks))
        self.assertEqual((r["failure_class"], r["biting_scenarios"], r["tie_scenarios"]), ("", "", ""))


class TestDriver(unittest.TestCase):
    def test_deterministic(self):
        _, a = run_experiment([0.2, 0.4], 25, seed=11, progress=False)
        _, b = run_experiment([0.2, 0.4], 25, seed=11, progress=False)
        self.assertEqual(a, b)
        _, c = run_experiment([0.2, 0.4], 25, seed=12, progress=False)
        self.assertNotEqual(a, c)

    def test_counts_and_indices(self):
        insts, recs = run_experiment([0.1, 0.3, 0.5], 40, seed=5, progress=False)
        self.assertEqual(len(insts), 120)
        self.assertEqual(len(recs), 120)
        self.assertEqual([r["index"] for r in recs], list(range(1, 121)))
        self.assertEqual([i.p for i in insts], [0.1] * 40 + [0.3] * 40 + [0.5] * 40)

    def test_records_agree_with_the_strategic_module(self):
        insts, recs = run_experiment([0.15, 0.35], 40, seed=6, progress=False)
        for inst, r in zip(insts, recs):
            self.assertEqual(r["strategyproof"], check_truthful_dominant(inst.types, inst.attacks).holds)
            self.assertEqual(r["condition_holds"], check_odd_path_condition(inst.types, inst.attacks).holds)

    def test_condition_implies_strategyproof(self):
        _, recs = run_experiment([0.05, 0.1, 0.2], 80, seed=7, progress=False)
        self.assertTrue(any(r["condition_holds"] for r in recs))
        for r in recs:
            if r["condition_holds"]:
                self.assertTrue(r["strategyproof"], r)
            for key in ("condition_holds_simple_paths", "condition_holds_incl_same", "condition_holds_simple_incl_same"):
                if r[key]:
                    self.assertTrue(r["strategyproof"], (key, r))

    def test_class_is_only_set_for_strategyproof_condition_failures(self):
        _, recs = run_experiment([0.05, 0.2], 80, seed=8, progress=False)
        for r in recs:
            expected = r["strategyproof"] and not r["condition_holds"]
            self.assertEqual(bool(r["failure_class"]), expected)

    def test_summary_arithmetic(self):
        _, recs = run_experiment([0.1, 0.3], 60, seed=10, progress=False)
        s = summarise(recs)
        self.assertEqual([r["p"] for r in s], [0.1, 0.3, "all"])
        for row in s[:2]:
            rs = [r for r in recs if r["p"] == row["p"]]
            self.assertEqual(row["instances"], len(rs))
            self.assertEqual(row["strategyproof"], sum(r["strategyproof"] for r in rs))
            self.assertAlmostEqual(row["fraction_strategyproof"], row["strategyproof"] / len(rs))
            self.assertEqual(
                row["strategyproof_condition_fails"],
                row["direct_conflict"] + row["indirect_trade_off"] + row["indirect_inert"],
            )
            # every instance falls in exactly one of four boxes
            self.assertEqual(
                row["condition_holds"]
                + row["strategyproof_condition_fails"]
                + row["not_strategyproof_condition_fails"]
                + row["condition_holds_not_strategyproof"],
                row["instances"],
            )
        total = s[-1]
        self.assertEqual(total["instances"], 120)
        self.assertEqual(total["strategyproof"], s[0]["strategyproof"] + s[1]["strategyproof"])

    def test_main_writes_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "res")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                rc = main(["--instances", "15", "--p", "0.2", "0.4", "--seed", "3", "--outdir", out])
            self.assertEqual(rc, 0)
            for name in (
                "instances.csv",
                "summary_by_p.csv",
                "summary.md",
                "condition_holds_not_strategyproof.json",
                "strategyproof_condition_fails.json",
            ):
                self.assertTrue(os.path.exists(os.path.join(out, name)), name)
            with open(os.path.join(out, "instances.csv"), newline="", encoding="utf-8") as fh:
                self.assertEqual(len(list(csv.DictReader(fh))), 30)

    def test_main_no_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "never")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                rc = main(["--instances", "5", "--p", "0.3", "--no-files", "--outdir", out])
            self.assertEqual(rc, 0)
            self.assertFalse(os.path.exists(out))


@unittest.skipUnless(os.path.exists(os.path.join(RESULTS_DIR, "instances.csv")), "results/ not generated")
class TestCommittedResults(unittest.TestCase):
    """The files in results/ are what `python experiments.py` produces."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(RESULTS_DIR, "instances.csv"), newline="", encoding="utf-8") as fh:
            cls.rows = list(csv.DictReader(fh))
        with open(os.path.join(RESULTS_DIR, "summary_by_p.csv"), newline="", encoding="utf-8") as fh:
            cls.summary = list(csv.DictReader(fh))

    def test_enough_instances(self):
        self.assertGreaterEqual(len(self.rows), 1000)
        for p in {r["p"] for r in self.rows}:
            self.assertGreaterEqual(sum(1 for r in self.rows if r["p"] == p), 1000)

    def test_summary_matches_instances(self):
        for row in self.summary:
            rs = self.rows if row["p"] == "all" else [r for r in self.rows if r["p"] == row["p"]]
            sp = sum(r["strategyproof"] == "True" for r in rs)
            self.assertEqual(int(row["instances"]), len(rs))
            self.assertEqual(int(row["strategyproof"]), sp)
            self.assertAlmostEqual(float(row["fraction_strategyproof"]), sp / len(rs), places=9)
            self.assertEqual(
                int(row["condition_holds_not_strategyproof"]),
                sum(1 for r in rs if r["condition_holds"] == "True" and r["strategyproof"] != "True"),
            )

    def test_sample_of_instances_reanalyses_identically(self):
        rng = random.Random(0)
        for row in rng.sample(self.rows, 60):
            fresh = analyse_instance(parse_instance(row))
            self.assertEqual(str(fresh["strategyproof"]), row["strategyproof"], row["index"])
            self.assertEqual(str(fresh["condition_holds"]), row["condition_holds"], row["index"])
            self.assertEqual(fresh["failure_class"], row["failure_class"], row["index"])
            self.assertEqual(fresh["odd_pairs"], row["odd_pairs"], row["index"])

    def test_no_instance_where_the_condition_holds_but_not_strategyproof(self):
        self.assertEqual(
            [r["index"] for r in self.rows if r["condition_holds"] == "True" and r["strategyproof"] != "True"],
            [],
        )


if __name__ == "__main__":
    unittest.main()
