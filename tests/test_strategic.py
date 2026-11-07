"""
Tests for strategic.py.

Run from the repository root with either
    python -m unittest discover -s tests -t . -v
or
    pytest

Layers:
  1. the mechanism (Definition 5.21) and the utility (Definition 5.22),
  2. Examples 5.10 and 5.11 of the book, including the two misprint corrections,
  3. best responses,
  4. the odd-path condition of Theorem 5.4 (cycles, walks versus simple paths),
  5. cross-checks against independent brute-force oracles on random instances,
     and the logical relation between the two theorems.
"""

import random
import unittest
from itertools import product

from af import ArgumentationFramework
from strategic import (
    GroundedMechanism,
    best_responses,
    check_odd_path_condition,
    check_truthful_dominant,
    indirectly_defeats,
    mechanism,
    odd_path_pairs,
    subsets,
    utilities,
    utility,
)
from strategic_examples import EXAMPLE_5_10, EXAMPLE_5_11, STRATEGIC_EXAMPLES


def fs(*items):
    return frozenset(items)


def random_instance(rng, n, p, agents=3, self_attacks=False):
    args = [f"a{i}" for i in range(1, n + 1)]
    attacks = {(x, y) for x in args for y in args if (self_attacks or x != y) and rng.random() < p}
    owner = [rng.randrange(agents) for _ in args]
    types = [fs(*[a for a, o in zip(args, owner) if o == k]) for k in range(agents)]
    return types, attacks


# --------------------------------------------------------------------------
# independent oracles (share no code with strategic.py or af.py)
# --------------------------------------------------------------------------
def naive_grounded(args, attacks):
    """Least fixed point of the characteristic function, on raw sets."""
    args = set(args)
    att = {(x, y) for (x, y) in attacks if x in args and y in args}
    E = set()
    while True:
        nxt = {
            a
            for a in args
            if all(any((d, b) in att for d in E) for (b, t) in att if t == a)
        }
        if nxt == E:
            return frozenset(E)
        E = nxt


def naive_subsets(s):
    s = sorted(s)
    for mask in range(1 << len(s)):
        yield frozenset(s[i] for i in range(len(s)) if (mask >> i) & 1)


def naive_strategyproof(types, attacks):
    """Enumerate every profile of reports; compare each agent's truthful report
    with each of its deviations, holding the others' reports fixed."""
    for profile in product(*[list(naive_subsets(t)) for t in types]):
        for i, own in enumerate(types):
            truthful = list(profile)
            truthful[i] = own
            u_true = len(own & naive_grounded(set().union(*truthful), attacks))
            u_dev = len(own & naive_grounded(set().union(*profile), attacks))
            if u_dev > u_true:
                return False
    return True


def naive_odd_walk(args, attacks, alpha, beta):
    """Is there a walk of odd length from alpha to beta?  Boolean matrix powers up to 2n."""
    args = sorted(args)
    att = {(x, y) for (x, y) in attacks if x in args and y in args}
    cur = {alpha}
    for length in range(1, 2 * len(args) + 2):
        cur = {y for (x, y) in att if x in cur}
        if length % 2 == 1 and beta in cur:
            return True
    return False


def naive_odd_simple_path(args, attacks, alpha, beta):
    att = {(x, y) for (x, y) in attacks if x in args and y in args}

    def rec(node, visited, length):
        for (x, y) in att:
            if x != node:
                continue
            if y == beta and (length + 1) % 2 == 1:
                return True
            if y not in visited and rec(y, visited | {y}, length + 1):
                return True
        return False

    return rec(alpha, {alpha}, 0)


# --------------------------------------------------------------------------
# 1. mechanism and utility
# --------------------------------------------------------------------------
class TestMechanism(unittest.TestCase):
    def test_grounded_of_union(self):
        # chain a -> b -> c: grounded extension {a, c}
        attacks = {("a", "b"), ("b", "c")}
        self.assertEqual(mechanism(attacks, [{"a"}, {"b"}, {"c"}]), fs("a", "c"))

    def test_induced_graph_drops_attacks_with_hidden_ends(self):
        attacks = {("a", "b"), ("b", "c")}
        # b is hidden: nothing attacks c any more, so c is accepted along with a
        self.assertEqual(mechanism(attacks, [{"a"}, {"c"}]), fs("a", "c"))
        # a is hidden: b is no longer attacked, so b is accepted and c is not
        self.assertEqual(mechanism(attacks, [{"b"}, {"c"}]), fs("b"))

    def test_empty_reports(self):
        self.assertEqual(mechanism({("a", "b")}, [set(), set(), set()]), fs())
        self.assertEqual(mechanism({("a", "b")}, []), fs())

    def test_order_and_duplication_of_reports_do_not_matter(self):
        attacks = {("a", "b"), ("b", "c"), ("c", "a")}
        r1 = mechanism(attacks, [{"a", "b"}, {"c"}, set()])
        r2 = mechanism(attacks, [set(), {"c"}, {"b", "a"}])
        r3 = mechanism(attacks, [{"a", "b"}, {"c", "a"}, {"b"}])
        self.assertEqual(r1, r2)
        self.assertEqual(r1, r3)

    def test_overlapping_reports_are_merged(self):
        self.assertEqual(mechanism({("a", "b")}, [{"a"}, {"a"}]), fs("a"))

    def test_outcome_is_subset_of_revealed(self):
        rng = random.Random(1)
        for _ in range(100):
            types, att = random_instance(rng, 6, 0.3)
            reports = [rng.sample(sorted(t), rng.randint(0, len(t))) for t in types]
            out = mechanism(att, reports)
            self.assertTrue(out <= frozenset().union(*map(frozenset, reports)))

    def test_matches_engine_and_naive_oracle(self):
        rng = random.Random(2)
        for _ in range(200):
            types, att = random_instance(rng, 7, rng.choice([0.1, 0.25, 0.4]), self_attacks=True)
            reports = [rng.sample(sorted(t), rng.randint(0, len(t))) for t in types]
            union = frozenset().union(*map(frozenset, reports))
            induced = [(x, y) for (x, y) in att if x in union and y in union]
            engine = ArgumentationFramework(union, induced).grounded_extension()
            self.assertEqual(mechanism(att, reports), engine)
            self.assertEqual(mechanism(att, reports), naive_grounded(union, att))

    def test_attacks_on_unknown_arguments_are_ignored(self):
        self.assertEqual(mechanism({("a", "zzz"), ("zzz", "b")}, [{"a", "b"}]), fs("a", "b"))

    def test_malformed_attack_raises(self):
        with self.assertRaises(ValueError):
            mechanism([("a", "b", "c")], [{"a"}])
        with self.assertRaises(ValueError):
            GroundedMechanism([5])

    def test_cache_gives_same_answers(self):
        m = GroundedMechanism({("a", "b"), ("b", "a")})
        first = m([{"a"}, {"b"}])
        again = m([{"b"}, {"a"}])
        self.assertEqual(first, again)
        self.assertEqual(first, fs())  # mutual attack: grounded extension is empty

    def test_accepts_any_iterables(self):
        self.assertEqual(mechanism(iter([("a", "b")]), [iter(["a"]), ("b",)]), fs("a"))


class TestUtility(unittest.TestCase):
    def test_counts_own_accepted_arguments(self):
        self.assertEqual(utility({"a", "b", "c"}, {"a", "c", "z"}), 2)
        self.assertEqual(utility(set(), {"a"}), 0)
        self.assertEqual(utility({"a"}, set()), 0)

    def test_utilities_vector(self):
        self.assertEqual(utilities([{"a"}, {"b", "c"}, set()], {"a", "b"}), [1, 1, 0])

    def test_subsets_enumeration(self):
        s = subsets({"b", "a", "c"})
        self.assertEqual(len(s), 8)
        self.assertEqual(s[0], fs())
        self.assertEqual(s[-1], fs("a", "b", "c"))
        self.assertEqual(len(set(s)), 8)
        self.assertEqual(subsets(set()), [fs()])


# --------------------------------------------------------------------------
# 2. the book's examples
# --------------------------------------------------------------------------
class TestBookExample510(unittest.TestCase):
    ex = EXAMPLE_5_10
    X, Y, Z = 0, 1, 2

    def test_types_and_full_revelation_outcome(self):
        self.assertEqual(self.ex.types[self.X], fs("a1", "a4", "a5"))
        self.assertEqual(self.ex.types[self.Y], fs("a2"))
        self.assertEqual(self.ex.types[self.Z], fs("a3"))
        o = mechanism(self.ex.attacks, self.ex.types)
        self.assertEqual(o, fs("a1", "a3"))
        self.assertEqual(o, self.ex.truthful_outcome)

    def test_utilities_with_the_misprint_corrected(self):
        o = mechanism(self.ex.attacks, self.ex.types)
        self.assertEqual(utility({"a1", "a4", "a5"}, o), 1)  # u_x
        self.assertEqual(utility({"a2"}, o), 0)  # u_y  (the book prints {a3} here)
        self.assertEqual(utility({"a3"}, o), 1)  # u_z  (the book prints {a2} here)
        self.assertEqual(utilities(self.ex.types, o), [1, 0, 1])
        self.assertEqual(tuple(utilities(self.ex.types, o)), self.ex.truthful_utilities)

    def test_x_gains_by_withholding_a1(self):
        reports = [fs("a4", "a5"), self.ex.types[1], self.ex.types[2]]
        o = mechanism(self.ex.attacks, reports)
        self.assertEqual(o, fs("a2", "a4", "a5"))  # Figure 5.4(b)
        self.assertEqual(utility(self.ex.types[self.X], o), 2)

    def test_x_best_response_is_unique(self):
        br = best_responses(self.X, self.ex.types, self.ex.attacks, {1: fs("a2"), 2: fs("a3")})
        self.assertEqual(br.utility, 2)
        self.assertEqual(br.reports, [fs("a4", "a5")])
        self.assertFalse(br.truthful_is_best)

    def test_revealing_weakly_dominates_hiding_everything_for_y_and_z(self):
        for agent in (self.Y, self.Z):
            others = [j for j in range(3) if j != agent]
            for combo in product(*[subsets(self.ex.types[j]) for j in others]):
                fixed = dict(zip(others, combo))
                reveal_all = best_responses(agent, self.ex.types, self.ex.attacks, fixed)
                union_others = frozenset().union(*combo)
                u_reveal = utility(
                    self.ex.types[agent],
                    mechanism(self.ex.attacks, [self.ex.types[agent], union_others]),
                )
                u_hide = utility(self.ex.types[agent], mechanism(self.ex.attacks, [union_others]))
                self.assertGreaterEqual(u_reveal, u_hide)
                self.assertTrue(reveal_all.truthful_is_best)

    def test_not_strategyproof_only_x_can_manipulate(self):
        chk = check_truthful_dominant(self.ex.types, self.ex.attacks, find_all=True)
        self.assertFalse(chk.holds)
        self.assertEqual(chk.agents_with_manipulation, [self.X])
        self.assertFalse(self.ex.strategyproof)
        first = check_truthful_dominant(self.ex.types, self.ex.attacks)
        self.assertEqual(len(first.manipulations), 1)  # stops at the first one

    def test_odd_path_condition_fails_for_x(self):
        res = check_odd_path_condition(self.ex.types, self.ex.attacks)
        self.assertFalse(res.holds)
        # a1 -> a2 -> a3 -> a4 and a1 -> a2 -> a3 -> a5 have length 3
        self.assertEqual(sorted(res.violations), [(0, "a1", "a4"), (0, "a1", "a5")])


class TestBookExample511(unittest.TestCase):
    ex = EXAMPLE_5_11

    def test_full_revelation_outcome(self):
        o = mechanism(self.ex.attacks, self.ex.types)
        self.assertEqual(o, fs("a1", "a4", "a5", "a6"))
        self.assertEqual(utilities(self.ex.types, o), [4, 0, 0])

    def test_truth_revelation_is_dominant_for_x(self):
        # x gets all four of its arguments accepted, which is the most it can ever get
        o = mechanism(self.ex.attacks, self.ex.types)
        self.assertEqual(utility(self.ex.types[0], o), len(self.ex.types[0]))
        chk = check_truthful_dominant(self.ex.types, self.ex.attacks, find_all=True)
        self.assertTrue(chk.holds)
        self.assertEqual(chk.manipulations, [])
        self.assertTrue(self.ex.strategyproof)

    def test_condition_fails_although_strategyproof(self):
        res = check_odd_path_condition(self.ex.types, self.ex.attacks)
        self.assertFalse(res.holds)
        self.assertEqual(sorted(res.violations), [(0, "a1", "a4"), (0, "a1", "a5")])
        # "a1 indirectly defeats a4 and a5"
        self.assertTrue(indirectly_defeats(self.ex.attacks, "a1", "a4"))
        self.assertTrue(indirectly_defeats(self.ex.attacks, "a1", "a5"))

    def test_a6_is_the_argument_that_cancels_the_indirect_self_defeat(self):
        # Remove only the defeat a6 -> a3 (keep a6 as an isolated argument): x can manipulate again.
        without_cancel = set(self.ex.attacks) - {("a6", "a3")}
        self.assertFalse(check_truthful_dominant(self.ex.types, without_cancel).holds)
        # With a6 -> a3 present it is strategyproof.
        self.assertTrue(check_truthful_dominant(self.ex.types, self.ex.attacks).holds)
        # a5 does not do that job: removing a5's role changes nothing, a5 is simply defeated by a3
        # when a6 is absent and accepted when a6 is present; the cancelling is a6's.
        o_with = mechanism(self.ex.attacks, self.ex.types)
        o_without_a6 = mechanism(self.ex.attacks, [fs("a1", "a4", "a5"), fs("a2"), fs("a3")])
        self.assertNotIn("a5", o_without_a6)
        self.assertIn("a5", o_with)

    def test_example_records_are_consistent_with_the_code(self):
        for ex in STRATEGIC_EXAMPLES.values():
            with self.subTest(example=ex.name):
                o = mechanism(ex.attacks, ex.types)
                self.assertEqual(o, ex.truthful_outcome)
                self.assertEqual(tuple(utilities(ex.types, o)), ex.truthful_utilities)
                self.assertEqual(check_truthful_dominant(ex.types, ex.attacks).holds, ex.strategyproof)
                self.assertEqual(check_odd_path_condition(ex.types, ex.attacks).holds, ex.odd_path_condition)
                self.assertTrue(ex.book_claims)


# --------------------------------------------------------------------------
# 3. best responses
# --------------------------------------------------------------------------
class TestBestResponses(unittest.TestCase):
    def test_ties_are_all_reported(self):
        # agent 0 owns a, b with no attacks at all: only revealing both gives utility 2
        br = best_responses(0, [{"a", "b"}, set()], set(), {1: set()})
        self.assertEqual(br.utility, 2)
        self.assertEqual(br.reports, [fs("a", "b")])
        # agent 0 owns a and a self-attacker s: s is never accepted, so revealing it or not ties
        br = best_responses(0, [{"a", "s"}, set()], {("s", "s")}, {1: set()})
        self.assertEqual(br.utility, 1)
        self.assertEqual(br.reports, [fs("a"), fs("a", "s")])
        self.assertTrue(br.truthful_is_best)

    def test_agent_with_empty_type(self):
        br = best_responses(1, [{"a"}, set()], set(), {0: {"a"}})
        self.assertEqual(br.utility, 0)
        self.assertEqual(br.reports, [fs()])
        self.assertTrue(br.truthful_is_best)

    def test_hiding_everything_can_be_a_best_response(self):
        # a1 -> a2 and a2 -> a3: agent 0 owns a1 and a3; agent 1 owns a2.
        # With a1 hidden, a2 is accepted and a3 is not; with a1 revealed a2 is out so a3 is in.
        types = [{"a1", "a3"}, {"a2"}]
        attacks = {("a1", "a2"), ("a2", "a3")}
        br = best_responses(0, types, attacks, {1: {"a2"}})
        self.assertEqual(br.utility, 2)
        self.assertEqual(br.reports, [fs("a1", "a3")])

    def test_validation(self):
        types = [{"a"}, {"b"}, {"c"}]
        with self.assertRaises(ValueError):
            best_responses(0, types, set(), {1: {"b"}})  # agent 2 missing
        with self.assertRaises(ValueError):
            best_responses(0, types, set(), {1: {"b"}, 2: {"c"}, 0: {"a"}})  # includes the agent itself
        with self.assertRaises(ValueError):
            best_responses(0, types, set(), {1: {"c"}, 2: {"c"}})  # agent 1 reveals what it does not own
        with self.assertRaises(ValueError):
            best_responses(7, types, set(), {})

    def test_consistent_with_theorem_5_3_check(self):
        # truthful is a best response against every context  <=>  check_truthful_dominant holds
        rng = random.Random(3)
        for _ in range(150):
            types, att = random_instance(rng, 6, rng.choice([0.15, 0.3]))
            all_truthful_best = True
            for i in range(3):
                others = [j for j in range(3) if j != i]
                for combo in product(*[subsets(types[j]) for j in others]):
                    br = best_responses(i, types, att, dict(zip(others, combo)))
                    all_truthful_best &= br.truthful_is_best
            self.assertEqual(all_truthful_best, check_truthful_dominant(types, att).holds)


# --------------------------------------------------------------------------
# 4. Theorem 5.4: odd-length paths
# --------------------------------------------------------------------------
class TestOddPath(unittest.TestCase):
    def test_direct_attack_is_an_odd_path(self):
        self.assertTrue(indirectly_defeats({("a", "b")}, "a", "b"))
        self.assertFalse(indirectly_defeats({("a", "b")}, "b", "a"))  # direction matters

    def test_path_lengths(self):
        chain = {("a", "b"), ("b", "c"), ("c", "d"), ("d", "e")}
        self.assertTrue(indirectly_defeats(chain, "a", "b"))  # 1
        self.assertFalse(indirectly_defeats(chain, "a", "c"))  # 2
        self.assertTrue(indirectly_defeats(chain, "a", "d"))  # 3
        self.assertFalse(indirectly_defeats(chain, "a", "e"))  # 4

    def test_cycles_terminate_and_use_parity(self):
        odd_cycle = {("a", "b"), ("b", "c"), ("c", "a")}
        # on a 3-cycle every argument is reachable by both an odd and an even walk
        for x in "abc":
            for y in "abc":
                self.assertTrue(indirectly_defeats(odd_cycle, x, y), (x, y))
        even_cycle = {("a", "b"), ("b", "c"), ("c", "d"), ("d", "a")}
        self.assertTrue(indirectly_defeats(even_cycle, "a", "b"))
        self.assertFalse(indirectly_defeats(even_cycle, "a", "c"))
        self.assertTrue(indirectly_defeats(even_cycle, "a", "d"))
        self.assertFalse(indirectly_defeats(even_cycle, "a", "a"))  # only even closed walks
        self.assertTrue(indirectly_defeats(odd_cycle, "a", "a"))

    def test_dense_cyclic_graph_terminates(self):
        args = [f"n{i}" for i in range(40)]
        attacks = {(x, y) for x in args for y in args}  # complete digraph with self-loops
        self.assertTrue(indirectly_defeats(attacks, "n0", "n39"))

    def test_walk_versus_simple_path(self):
        # alpha -> gamma -> beta is the only simple path (length 2, even); but gamma lies on
        # the odd cycle gamma -> d -> e -> gamma, giving the odd walk of length 5.
        attacks = {("alpha", "gamma"), ("gamma", "beta"), ("gamma", "d"), ("d", "e"), ("e", "gamma")}
        self.assertTrue(indirectly_defeats(attacks, "alpha", "beta", mode="walk"))
        self.assertFalse(indirectly_defeats(attacks, "alpha", "beta", mode="simple"))
        # the cycle's arguments belong to three different agents, so only agent 0's pair matters
        types = [{"alpha", "beta"}, {"gamma"}, {"d"}, {"e"}]
        self.assertEqual(odd_path_pairs(types, attacks, mode="walk"), [(0, "alpha", "beta")])
        self.assertEqual(odd_path_pairs(types, attacks, mode="simple"), [])
        self.assertFalse(check_odd_path_condition(types, attacks, mode="walk").holds)
        self.assertTrue(check_odd_path_condition(types, attacks, mode="simple").holds)

    def test_same_argument_pairs(self):
        types = [{"a", "b"}, {"c"}]
        # a self-attacker: odd closed walk of length 1 from a to a
        self.assertEqual(odd_path_pairs(types, {("a", "a")}), [])  # distinct pairs only (default)
        self.assertEqual(odd_path_pairs(types, {("a", "a")}, include_same=True), [(0, "a", "a")])
        # a triangle a -> c -> b -> a through another agent's argument c: every argument on an
        # odd cycle odd-reaches every other one (and itself)
        tri = {("a", "c"), ("c", "b"), ("b", "a")}
        self.assertEqual(sorted(odd_path_pairs(types, tri)), [(0, "a", "b"), (0, "b", "a")])
        self.assertEqual(
            sorted(odd_path_pairs(types, tri, include_same=True)),
            [(0, "a", "a"), (0, "a", "b"), (0, "b", "a"), (0, "b", "b"), (1, "c", "c")],
        )

    def test_only_pairs_owned_by_the_same_agent_count(self):
        # a -> b is an odd path, but a and b belong to different agents
        self.assertTrue(check_odd_path_condition([{"a"}, {"b"}], {("a", "b")}).holds)
        self.assertFalse(check_odd_path_condition([{"a", "b"}, set()], {("a", "b")}).holds)

    def test_even_path_is_fine(self):
        types = [{"a", "c"}, {"b"}]
        self.assertTrue(check_odd_path_condition(types, {("a", "b"), ("b", "c")}).holds)

    def test_graph_is_restricted_to_the_arguments_of_the_game(self):
        # the path a -> ghost -> b would have length 2 anyway; a -> ghost -> g2 -> b has length 3,
        # but 'ghost' and 'g2' are not arguments of any agent, so the path does not exist
        types = [{"a", "b"}]
        attacks = {("a", "ghost"), ("ghost", "g2"), ("g2", "b")}
        self.assertTrue(check_odd_path_condition(types, attacks).holds)
        self.assertFalse(
            indirectly_defeats(attacks, "a", "b", universe={"a", "b"}),
        )
        self.assertTrue(indirectly_defeats(attacks, "a", "b"))

    def test_invalid_mode(self):
        with self.assertRaises(ValueError):
            indirectly_defeats({("a", "b")}, "a", "b", mode="bogus")
        with self.assertRaises(ValueError):
            odd_path_pairs([{"a"}], set(), mode="bogus")

    def test_matches_independent_oracles_on_random_graphs(self):
        rng = random.Random(4)
        for _ in range(250):
            n = rng.choice([4, 5, 6, 7])
            types, att = random_instance(rng, n, rng.choice([0.1, 0.2, 0.35, 0.5]), self_attacks=True)
            args = sorted(set().union(*types))
            for mode, naive in (("walk", naive_odd_walk), ("simple", naive_odd_simple_path)):
                got = set(odd_path_pairs(types, att, mode=mode, include_same=True))
                want = {
                    (i, a, b)
                    for i, t in enumerate(types)
                    for a in t
                    for b in t
                    if naive(args, att, a, b)
                }
                self.assertEqual(got, want, (mode, types, sorted(att)))


# --------------------------------------------------------------------------
# 5. cross-checks and the relation between the theorems
# --------------------------------------------------------------------------
class TestCrossChecks(unittest.TestCase):
    def test_theorem_5_3_check_matches_brute_force_oracle(self):
        rng = random.Random(5)
        agree_true = agree_false = 0
        for _ in range(300):
            n = rng.choice([4, 5, 6])
            types, att = random_instance(rng, n, rng.choice([0.1, 0.2, 0.3, 0.4]), self_attacks=True)
            expected = naive_strategyproof(types, att)
            self.assertEqual(check_truthful_dominant(types, att).holds, expected, (types, sorted(att)))
            agree_true += expected
            agree_false += not expected
        self.assertGreater(agree_true, 20)  # the sample contains both kinds of instance
        self.assertGreater(agree_false, 20)

    def test_manipulations_are_genuine(self):
        rng = random.Random(6)
        found = 0
        for _ in range(150):
            types, att = random_instance(rng, 6, 0.3)
            res = check_truthful_dominant(types, att, find_all=True)
            for m in res.manipulations:
                found += 1
                reveal = types[m.agent] - m.hidden
                others = [m.others_reports[j] for j in sorted(m.others_reports)]
                reports_true = [None] * 3
                reports_dev = [None] * 3
                for j, r in m.others_reports.items():
                    reports_true[j] = r
                    reports_dev[j] = r
                reports_true[m.agent] = types[m.agent]
                reports_dev[m.agent] = reveal
                o_true = mechanism(att, reports_true)
                o_dev = mechanism(att, reports_dev)
                self.assertEqual(o_true, m.truthful_outcome)
                self.assertEqual(o_dev, m.deviation_outcome)
                self.assertEqual(utility(types[m.agent], o_true), m.truthful_utility)
                self.assertEqual(utility(types[m.agent], o_dev), m.deviation_utility)
                self.assertGreater(m.deviation_utility, m.truthful_utility)
                self.assertTrue(others is not None and str(m))
            self.assertEqual(
                res.holds, not res.manipulations
            )
        self.assertGreater(found, 50)

    def test_theorem_5_4_is_sound_on_random_instances(self):
        """If the odd-path condition holds, the mechanism is strategyproof.

        Checked for every reading of the condition (odd walks or simple paths, with or
        without the case alpha == beta), with and without self-attacking arguments.
        """
        rng = random.Random(7)
        holds_count = 0
        for self_attacks in (False, True):
            for _ in range(450):
                n = rng.choice([5, 6, 7, 8])
                p = rng.choice([0.05, 0.1, 0.15, 0.2, 0.3])
                types, att = random_instance(rng, n, p, self_attacks=self_attacks)
                sp = check_truthful_dominant(types, att).holds
                for mode in ("walk", "simple"):
                    for same in (False, True):
                        if check_odd_path_condition(types, att, mode, same).holds:
                            holds_count += 1
                            self.assertTrue(sp, (mode, same, types, sorted(att)))
        self.assertGreater(holds_count, 400)

    def test_hiding_can_only_gain_an_argument_through_an_odd_walk(self):
        """The lemma behind Theorem 5.4.

        Let E be the outcome when agent i reveals A_i and E' the outcome when it hides S
        (the others' reports fixed).  If an argument b in A_i \\ S is accepted in E' but not
        in E, then some hidden argument s in S has an odd-length directed walk to b.
        So if no argument of A_i odd-reaches another one, hiding S can never newly accept
        any remaining own argument, and the utility cannot increase.
        """
        rng = random.Random(9)
        checked_gain = 0
        for _ in range(250):
            n = rng.choice([5, 6, 7])
            types, att = random_instance(rng, n, rng.choice([0.1, 0.2, 0.3, 0.4]), self_attacks=True)
            mech = GroundedMechanism(att)
            universe = set().union(*types)
            for i, own in enumerate(types):
                others = [j for j in range(3) if j != i]
                for combo in product(*[subsets(types[j]) for j in others]):
                    ctx = frozenset().union(*combo)
                    e_full = mech.outcome_of_union(own | ctx)
                    for reveal in subsets(own):
                        hidden = own - reveal
                        if not hidden:
                            continue
                        e_hide = mech.outcome_of_union(reveal | ctx)
                        for b in (reveal & e_hide) - e_full:
                            checked_gain += 1
                            self.assertTrue(
                                any(
                                    indirectly_defeats(att, s, b, mode="walk", universe=universe)
                                    for s in hidden
                                ),
                                (types, sorted(att), i, hidden, b),
                            )
        self.assertGreater(checked_gain, 200)  # the lemma was exercised many times

    def test_condition_is_not_necessary(self):
        # Example 5.11 is an instance with a violated condition and a strategyproof mechanism
        self.assertFalse(check_odd_path_condition(EXAMPLE_5_11.types, EXAMPLE_5_11.attacks).holds)
        self.assertTrue(check_truthful_dominant(EXAMPLE_5_11.types, EXAMPLE_5_11.attacks).holds)

    def test_more_conditions_make_the_condition_stronger(self):
        # allowing alpha == beta can only add violations
        rng = random.Random(8)
        for _ in range(150):
            types, att = random_instance(rng, 6, 0.3, self_attacks=True)
            a = set(odd_path_pairs(types, att, include_same=False))
            b = set(odd_path_pairs(types, att, include_same=True))
            self.assertTrue(a <= b)
            # a simple path is in particular a walk
            s = set(odd_path_pairs(types, att, mode="simple", include_same=True))
            self.assertTrue(s <= b)

    def test_single_agent_and_trivial_games(self):
        # no attacks: nothing to gain
        self.assertTrue(check_truthful_dominant([{"a", "b", "c"}], set()).holds)
        # a single agent owning a chain a -> b -> c: revealing everything gives {a, c},
        # which is already the most it can get
        self.assertTrue(check_truthful_dominant([{"a", "b", "c"}], {("a", "b"), ("b", "c")}).holds)
        # with nobody else to react, the number of situations examined is 2^|A_i|
        res = check_truthful_dominant([{"a", "b", "c", "d"}], {("a", "b"), ("b", "c"), ("c", "d")})
        self.assertTrue(res.holds)
        self.assertEqual(res.contexts_checked, 16)

    def test_odd_path_violation_with_a_trade_off_is_still_strategyproof(self):
        # chain a -> b -> c -> d; agent 0 owns a and d, so a odd-reaches d (length 3).
        # Truthfully: a in, b out, c in, d out -> utility 1.  Hiding a: b in, c out, d in -> utility 1.
        # Hiding gives a different accepted argument but no extra one: a trade-off, not a gain.
        types = [{"a", "d"}, {"b"}, {"c"}]
        attacks = {("a", "b"), ("b", "c"), ("c", "d")}
        self.assertFalse(check_odd_path_condition(types, attacks).holds)
        self.assertTrue(check_truthful_dominant(types, attacks).holds)
        self.assertEqual(utility({"a", "d"}, mechanism(attacks, types)), 1)
        self.assertEqual(utility({"a", "d"}, mechanism(attacks, [{"d"}, {"b"}, {"c"}])), 1)


if __name__ == "__main__":
    unittest.main()
