"""
Tests for af.py.

Run from the repository root with either
    python -m unittest discover -s tests -t . -v
or
    pytest

Layers of checking:
  1. hand-verified unit tests of the basic notions (conflict-free, defence, F, ...),
  2. the example frameworks in examples.py: the book's Figures 5.1-5.5, with every
     statement the book makes about them (TestBookChapter5), plus further
     frameworks for corner cases (expected values worked out by hand),
  3. cross-checks: an independent naive oracle written straight from the
     definitions, plus the extension <-> labelling correspondences, run on
     every framework with up to 3 arguments and on random larger ones.
"""

import random
import unittest
from itertools import combinations, product

import af as afmod
from af import (
    CREDULOUS,
    IN,
    OUT,
    REJECTED,
    SKEPTICAL,
    UNDEC,
    ArgumentationFramework,
)
from examples import BOOK_EXAMPLES, EXAMPLES


def fs(*items):
    return frozenset(items)


# --------------------------------------------------------------------------
# 1. construction and the basic notions
# --------------------------------------------------------------------------
class TestConstruction(unittest.TestCase):
    def test_basic_structure(self):
        af = ArgumentationFramework("abc", [("a", "b"), ("b", "c"), ("a", "b")])
        self.assertEqual(af.arguments, fs("a", "b", "c"))
        self.assertEqual(af.attacks, fs(("a", "b"), ("b", "c")))  # duplicate attack collapsed
        self.assertEqual(af.attackers("b"), fs("a"))
        self.assertEqual(af.targets("b"), fs("c"))
        self.assertEqual(af.attackers("a"), fs())
        self.assertEqual(af.attacked_by_set({"a", "b"}), fs("b", "c"))
        self.assertEqual(af.range({"a"}), fs("a", "b"))
        self.assertEqual(len(af), 3)

    def test_duplicate_arguments_ignored(self):
        af = ArgumentationFramework(["x", "y", "x"], [("x", "y")])
        self.assertEqual(af.arguments, fs("x", "y"))

    def test_non_string_arguments(self):
        af = ArgumentationFramework([1, 2, 3], [(1, 2), (2, 3)])
        self.assertEqual(af.grounded_extension(), fs(1, 3))

    def test_attack_on_unknown_argument(self):
        with self.assertRaises(ValueError):
            ArgumentationFramework("ab", [("a", "z")])
        with self.assertRaises(ValueError):
            ArgumentationFramework("ab", [("z", "a")])

    def test_malformed_attack(self):
        with self.assertRaises(ValueError):
            ArgumentationFramework("ab", [("a", "b", "a")])
        with self.assertRaises(ValueError):
            ArgumentationFramework("ab", [5])

    def test_unknown_argument_in_queries(self):
        af = ArgumentationFramework("ab", [("a", "b")])
        with self.assertRaises(ValueError):
            af.is_conflict_free({"a", "q"})
        with self.assertRaises(ValueError):
            af.is_defended("q", set())
        with self.assertRaises(ValueError):
            af.attackers("q")
        with self.assertRaises(ValueError):
            af.acceptance_status("q")

    def test_unknown_semantics(self):
        af = ArgumentationFramework("ab", [("a", "b")])
        with self.assertRaises(ValueError):
            af.extensions("bogus")
        with self.assertRaises(ValueError):
            af.acceptance_status("a", "bogus")
        with self.assertRaises(ValueError):
            af.labellings("bogus")


class TestBasicNotionsOnChain(unittest.TestCase):
    """Chain a -> b -> c, worked out by hand."""

    def setUp(self):
        self.af = ArgumentationFramework("abc", [("a", "b"), ("b", "c")])

    def test_conflict_free(self):
        af = self.af
        self.assertTrue(af.is_conflict_free(set()))
        self.assertTrue(af.is_conflict_free({"a"}))
        self.assertTrue(af.is_conflict_free({"a", "c"}))
        self.assertFalse(af.is_conflict_free({"a", "b"}))
        self.assertFalse(af.is_conflict_free({"b", "c"}))
        self.assertFalse(af.is_conflict_free({"a", "b", "c"}))

    def test_defended(self):
        af = self.af
        self.assertTrue(af.is_defended("a", set()))  # unattacked
        self.assertFalse(af.is_defended("b", set()))
        self.assertFalse(af.is_defended("b", {"b", "c"}))
        self.assertFalse(af.is_defended("c", set()))
        self.assertTrue(af.is_defended("c", {"a"}))  # a attacks c's only attacker b
        self.assertTrue(af.is_defended("c", {"a", "c"}))
        self.assertFalse(af.is_defended("c", {"c"}))

    def test_characteristic_function(self):
        af = self.af
        self.assertEqual(af.characteristic(set()), fs("a"))
        self.assertEqual(af.characteristic({"a"}), fs("a", "c"))
        self.assertEqual(af.characteristic({"a", "c"}), fs("a", "c"))
        self.assertEqual(af.characteristic({"b"}), fs("a"))  # b defends nothing new
        self.assertEqual(af.characteristic({"a", "b", "c"}), fs("a", "c"))

    def test_admissible_and_complete(self):
        af = self.af
        self.assertTrue(af.is_admissible(set()))
        self.assertTrue(af.is_admissible({"a"}))
        self.assertFalse(af.is_admissible({"c"}))  # c's attacker b is not attacked by {c}
        self.assertFalse(af.is_admissible({"a", "b"}))  # not conflict-free
        self.assertTrue(af.is_admissible({"a", "c"}))
        # complete: admissible and closed under F
        self.assertFalse(af.is_complete(set()))  # F({}) = {a}
        self.assertFalse(af.is_complete({"a"}))  # F({a}) = {a, c}
        self.assertTrue(af.is_complete({"a", "c"}))
        self.assertFalse(af.is_complete({"b"}))
        self.assertFalse(af.is_complete({"a", "b", "c"}))

    def test_grounded_by_iteration(self):
        self.assertEqual(self.af.grounded_extension(), fs("a", "c"))


class TestBasicNotionsMisc(unittest.TestCase):
    def test_self_attacker_is_not_conflict_free(self):
        af = ArgumentationFramework("a", [("a", "a")])
        self.assertFalse(af.is_conflict_free({"a"}))
        self.assertTrue(af.is_conflict_free(set()))
        self.assertFalse(af.is_admissible({"a"}))
        # Defence only asks that S attacks every attacker of a; S = {a} does attack a
        # (the only attacker), so a *is* defended by {a} -- but {a} is not conflict-free,
        # hence not admissible (checked above).  The empty set does not defend a.
        self.assertTrue(af.is_defended("a", {"a"}))
        self.assertFalse(af.is_defended("a", set()))
        self.assertEqual(af.grounded_extension(), fs())

    def test_mutual_attack_defends_itself(self):
        af = ArgumentationFramework("ab", [("a", "b"), ("b", "a")])
        self.assertTrue(af.is_defended("a", {"a"}))  # a counter-attacks b
        self.assertFalse(af.is_defended("a", set()))
        self.assertTrue(af.is_admissible({"a"}))
        self.assertTrue(af.is_complete({"a"}))
        self.assertTrue(af.is_complete(set()))
        self.assertFalse(af.is_conflict_free({"a", "b"}))

    def test_defence_does_not_require_membership(self):
        af = ArgumentationFramework("abc", [("a", "b"), ("b", "c")])
        self.assertTrue(af.is_defended("c", {"a"}))  # c is not in S, still defended by S

    def test_accepts_any_iterable(self):
        af = ArgumentationFramework("abc", [("a", "b"), ("b", "c")])
        self.assertTrue(af.is_conflict_free(["a", "c"]))
        self.assertTrue(af.is_conflict_free(("a", "c")))
        self.assertEqual(af.characteristic(iter(["a"])), fs("a", "c"))

    def test_empty_framework(self):
        af = ArgumentationFramework([], [])
        self.assertEqual(af.grounded_extension(), fs())
        self.assertEqual(af.complete_extensions(), [fs()])
        self.assertEqual(af.preferred_extensions(), [fs()])
        self.assertEqual(af.stable_extensions(), [fs()])
        self.assertEqual(af.semi_stable_extensions(), [fs()])
        labs = af.labellings()
        self.assertEqual(len(labs), 1)
        self.assertEqual(labs[0].as_dict(), {})

    def test_module_level_functions(self):
        af = ArgumentationFramework("abc", [("a", "b"), ("b", "c")])
        self.assertTrue(afmod.is_conflict_free(af, {"a", "c"}))
        self.assertTrue(afmod.is_defended(af, "c", {"a"}))
        self.assertEqual(afmod.characteristic(af, {"a"}), fs("a", "c"))
        self.assertTrue(afmod.is_admissible(af, {"a"}))
        self.assertTrue(afmod.is_complete(af, {"a", "c"}))
        self.assertEqual(afmod.grounded_extension(af), fs("a", "c"))
        self.assertEqual(afmod.complete_extensions(af), [fs("a", "c")])
        self.assertEqual(afmod.preferred_extensions(af), [fs("a", "c")])
        self.assertEqual(afmod.stable_extensions(af), [fs("a", "c")])
        self.assertEqual(afmod.semi_stable_extensions(af), [fs("a", "c")])
        self.assertEqual(set(afmod.all_extensions(af)), set(afmod.SEMANTICS))
        self.assertEqual(len(afmod.labellings(af)), 1)
        self.assertEqual(afmod.acceptance_status(af, "a"), SKEPTICAL)

    def test_input_not_mutated_and_results_immutable(self):
        S = {"a"}
        af = ArgumentationFramework("abc", [("a", "b"), ("b", "c")])
        af.characteristic(S)
        self.assertEqual(S, {"a"})
        self.assertIsInstance(af.grounded_extension(), frozenset)
        self.assertTrue(all(isinstance(E, frozenset) for E in af.complete_extensions()))


# --------------------------------------------------------------------------
# 2. example frameworks (expected values are hand-verified, see examples.py)
# --------------------------------------------------------------------------
def _sorted_sets(sets):
    return sorted(sets, key=lambda S: (len(S), tuple(sorted(S))))


class TestExamples(unittest.TestCase):
    def test_examples_present(self):
        self.assertGreaterEqual(len(EXAMPLES), 8)

    def test_all_semantics(self):
        for name, ex in EXAMPLES.items():
            with self.subTest(example=name):
                af = ex.af
                self.assertEqual(af.grounded_extension(), ex.grounded)
                self.assertEqual(af.complete_extensions(), _sorted_sets(ex.complete))
                self.assertEqual(af.preferred_extensions(), _sorted_sets(ex.preferred))
                self.assertEqual(af.stable_extensions(), _sorted_sets(ex.stable))
                self.assertEqual(af.semi_stable_extensions(), _sorted_sets(ex.semi_stable))

    def test_all_extensions_dict(self):
        ex = EXAMPLES["preferred_not_semi_stable"]
        d = ex.af.all_extensions()
        self.assertEqual(d["grounded"], [fs()])
        self.assertEqual(d["complete"], _sorted_sets(ex.complete))
        self.assertEqual(d["preferred"], _sorted_sets(ex.preferred))
        self.assertEqual(d["stable"], _sorted_sets(ex.stable))
        self.assertEqual(d["semi-stable"], _sorted_sets(ex.semi_stable))

    def test_acceptance_status_preferred(self):
        for name, ex in EXAMPLES.items():
            with self.subTest(example=name):
                for a, expected in ex.status.items():
                    self.assertEqual(ex.af.acceptance_status(a), expected, f"{name}: {a}")
                self.assertEqual(ex.af.acceptance_statuses(), ex.status)

    def test_acceptance_status_other_semantics(self):
        ex = EXAMPLES["preferred_not_semi_stable"]
        af = ex.af
        # preferred: a is in {a} but not in {b,d}
        self.assertEqual(af.acceptance_status("a", "preferred"), CREDULOUS)
        # semi-stable / stable: the only extension is {b,d}
        self.assertEqual(af.acceptance_status("a", "semi-stable"), REJECTED)
        self.assertEqual(af.acceptance_status("b", "semi-stable"), SKEPTICAL)
        self.assertEqual(af.acceptance_status("d", "stable"), SKEPTICAL)
        # grounded is empty
        self.assertEqual(af.acceptance_status("b", "grounded"), REJECTED)
        # complete: {}, {a}, {b,d} -> b is in some but not all
        self.assertEqual(af.acceptance_status("b", "complete"), CREDULOUS)
        # no stable extension at all -> everything rejected
        odd = EXAMPLES["odd_cycle"].af
        self.assertEqual(odd.extensions("stable"), [])
        self.assertEqual(odd.acceptance_status("a", "stable"), REJECTED)

    def test_labellings_match_complete_extensions(self):
        for name, ex in EXAMPLES.items():
            with self.subTest(example=name):
                labs = ex.af.labellings()
                self.assertEqual(len(labs), len(ex.complete))
                self.assertEqual(
                    _sorted_sets(L.in_ for L in labs),
                    _sorted_sets(ex.complete),
                )

    def test_known_labellings_of_mutual_attack(self):
        labs = EXAMPLES["mutual_attack"].af.labellings()
        self.assertEqual(
            [(L.in_, L.out, L.undec) for L in labs],
            [
                (fs(), fs(), fs("a", "b")),
                (fs("a"), fs("b"), fs()),
                (fs("b"), fs("a"), fs()),
            ],
        )
        self.assertEqual(labs[1].as_dict(), {"a": IN, "b": OUT})
        self.assertEqual(labs[0].as_dict(), {"a": UNDEC, "b": UNDEC})

    def test_odd_cycle_has_only_all_undec(self):
        (L,) = EXAMPLES["odd_cycle"].af.labellings()
        self.assertEqual(L.undec, fs("a", "b", "c"))
        self.assertEqual(L.in_, fs())
        self.assertEqual(L.out, fs())

    def test_admissible_labellings(self):
        # in-sets of admissible labellings are exactly the admissible sets
        for name, ex in EXAMPLES.items():
            with self.subTest(example=name):
                labs = ex.af.labellings("admissible")
                self.assertEqual(
                    set(L.in_ for L in labs),
                    set(ex.af.admissible_sets()),
                )
                # every complete labelling is also an admissible labelling
                self.assertTrue(set(ex.af.labellings()) <= set(labs))

    def test_labelling_is_partition_and_legal(self):
        for name, ex in EXAMPLES.items():
            af = ex.af
            for L in af.labellings():
                with self.subTest(example=name, labelling=str(L)):
                    self.assertEqual(L.in_ | L.out | L.undec, af.arguments)
                    self.assertFalse(L.in_ & L.out)
                    self.assertFalse(L.in_ & L.undec)
                    self.assertFalse(L.out & L.undec)
                    d = L.as_dict()
                    for a in af.arguments:
                        atts = af.attackers(a)
                        if d[a] == IN:
                            self.assertTrue(all(d[b] == OUT for b in atts))
                        elif d[a] == OUT:
                            self.assertTrue(any(d[b] == IN for b in atts))
                        else:
                            self.assertFalse(any(d[b] == IN for b in atts))
                            self.assertFalse(all(d[b] == OUT for b in atts))


class TestBookChapter5(unittest.TestCase):
    """Every statement Chapter 5 of Weiss (ed.), Multiagent Systems (2nd ed.)
    makes about its example graphs (alpha_i is written a<i>)."""

    def test_figure_5_1(self):
        af = BOOK_EXAMPLES["book_fig_5_1"].af
        # after Definition 5.2: {a3, a5} defends a1
        self.assertTrue(af.is_defended("a1", {"a3", "a5"}))
        self.assertFalse(af.is_defended("a1", {"a3"}))
        # Example 5.5: these sets are all admissible (and they are the only ones)
        claimed = [fs(), fs("a3"), fs("a5"), fs("a3", "a5"), fs("a1", "a3", "a5")]
        for S in claimed:
            self.assertTrue(af.is_admissible(S), S)
        self.assertEqual(set(af.admissible_sets()), set(claimed))
        # Example 5.6
        self.assertTrue(af.is_admissible({"a3", "a5"}))
        self.assertFalse(af.is_complete({"a3", "a5"}))
        self.assertIn("a1", af.characteristic({"a3", "a5"}))
        self.assertEqual(af.characteristic({"a3"}), fs("a3", "a5"))
        self.assertEqual(af.characteristic({"a5"}), fs("a3", "a5"))
        self.assertFalse(af.is_complete({"a3"}))
        self.assertFalse(af.is_complete({"a5"}))
        self.assertEqual(af.characteristic({"a1", "a3", "a5"}), fs("a1", "a3", "a5"))
        self.assertTrue(af.is_complete({"a1", "a3", "a5"}))
        self.assertEqual(af.complete_extensions(), [fs("a1", "a3", "a5")])
        # Section 3: grounded extension by iterating F from the empty set
        f1 = af.characteristic(set())
        f2 = af.characteristic(f1)
        f3 = af.characteristic(f2)
        self.assertEqual(f1, fs("a3", "a5"))
        self.assertEqual(f2, fs("a1", "a3", "a5"))
        self.assertEqual(f3, f2)
        self.assertEqual(af.grounded_extension(), f2)
        # Example 5.8
        self.assertEqual(af.preferred_extensions(), [fs("a1", "a3", "a5")])

    def test_figure_5_2(self):
        af = BOOK_EXAMPLES["book_fig_5_2"].af
        # Example 5.7
        self.assertEqual(
            set(af.complete_extensions()),
            {fs("a3"), fs("a1", "a3"), fs("a2", "a3")},
        )
        # Figure 5.2: the three labellings L^G, L1, L2
        got = {tuple(sorted(L.as_dict().items())) for L in af.labellings()}
        expected = {
            (("a1", UNDEC), ("a2", UNDEC), ("a3", IN)),  # L^G
            (("a1", IN), ("a2", OUT), ("a3", IN)),  # L1
            (("a1", OUT), ("a2", IN), ("a3", IN)),  # L2
        }
        self.assertEqual(got, expected)
        # grounded = minimal complete extension; Example 5.8: two preferred
        self.assertEqual(af.grounded_extension(), fs("a3"))
        self.assertEqual(set(af.preferred_extensions()), {fs("a1", "a3"), fs("a2", "a3")})

    def test_figure_5_3_argument_a_is_accepted(self):
        af = BOOK_EXAMPLES["book_fig_5_3"].af
        # PRO has a winning strategy for a (Figure 5.3(iii)), i.e. a is grounded-accepted
        self.assertIn("a", af.grounded_extension())
        self.assertEqual(af.acceptance_status("a", "grounded"), SKEPTICAL)

    def test_grounded_outcomes_of_examples_5_10_and_5_11(self):
        self.assertEqual(BOOK_EXAMPLES["book_fig_5_4a"].af.grounded_extension(), fs("a1", "a3"))
        self.assertEqual(BOOK_EXAMPLES["book_fig_5_4b"].af.grounded_extension(), fs("a2", "a4", "a5"))
        self.assertEqual(
            BOOK_EXAMPLES["book_fig_5_5"].af.grounded_extension(), fs("a1", "a4", "a5", "a6")
        )

    def test_every_book_example_has_its_claims_recorded(self):
        for name, ex in BOOK_EXAMPLES.items():
            with self.subTest(example=name):
                self.assertTrue(ex.source)
                self.assertTrue(ex.book_claims)


# --------------------------------------------------------------------------
# 3. cross-checks against an independent oracle
# --------------------------------------------------------------------------
class Naive:
    """Textbook definitions on raw (arguments, attack pairs), sharing no code with af.py."""

    def __init__(self, args, attacks):
        self.args = list(args)
        self.att = set(attacks)
        self.subsets = [
            frozenset(c) for r in range(len(self.args) + 1) for c in combinations(self.args, r)
        ]

    def attacks_arg(self, S, b):
        return any((x, b) in self.att for x in S)

    def cf(self, S):
        return not any((x, y) in self.att for x in S for y in S)

    def defends(self, S, a):
        return all(self.attacks_arg(S, b) for (b, t) in self.att if t == a)

    def rng(self, S):
        return frozenset(S) | {b for b in self.args if self.attacks_arg(S, b)}

    def admissible(self):
        return [S for S in self.subsets if self.cf(S) and all(self.defends(S, a) for a in S)]

    def complete(self):
        return [
            S
            for S in self.admissible()
            if all(a in S for a in self.args if self.defends(S, a))
        ]

    def grounded(self):
        S = frozenset()
        while True:
            T = frozenset(a for a in self.args if self.defends(S, a))
            if T == S:
                return S
            S = T

    def preferred(self):
        adm = self.admissible()
        return [S for S in adm if not any(S < T for T in adm)]

    def stable(self):
        return [
            S
            for S in self.subsets
            if self.cf(S) and all(self.attacks_arg(S, b) for b in self.args if b not in S)
        ]

    def semi_stable(self):
        adm = self.admissible()
        return [S for S in adm if not any(self.rng(S) < self.rng(T) for T in adm)]


def all_frameworks(n):
    """Every attack relation on n arguments (2^(n*n) frameworks)."""
    args = [chr(ord("a") + i) for i in range(n)]
    pairs = list(product(args, args))
    for bits in range(1 << len(pairs)):
        yield args, [p for i, p in enumerate(pairs) if (bits >> i) & 1]


def random_frameworks(n, count, p, seed):
    rng = random.Random(seed)
    args = [chr(ord("a") + i) for i in range(n)]
    for _ in range(count):
        yield args, [(x, y) for x in args for y in args if rng.random() < p]


def check_framework(tc, args, attacks):
    """All cross-checks for one framework; ``tc`` is a TestCase used for assertions."""
    af = ArgumentationFramework(args, attacks)
    naive = Naive(args, attacks)
    tag = f"args={args} attacks={sorted(attacks)}"

    comp = af.complete_extensions()
    pref = af.preferred_extensions()
    stab = af.stable_extensions()
    semi = af.semi_stable_extensions()
    grd = af.grounded_extension()

    # --- engine vs naive oracle
    tc.assertEqual(set(af.admissible_sets()), set(naive.admissible()), tag)
    tc.assertEqual(set(comp), set(naive.complete()), tag)
    tc.assertEqual(grd, naive.grounded(), tag)
    tc.assertEqual(set(pref), set(naive.preferred()), tag)
    tc.assertEqual(set(stab), set(naive.stable()), tag)
    tc.assertEqual(set(semi), set(naive.semi_stable()), tag)
    for S in naive.subsets:  # the predicates agree with the oracle on every subset
        tc.assertEqual(af.is_conflict_free(S), naive.cf(S), tag)
        tc.assertEqual(
            af.is_admissible(S), naive.cf(S) and all(naive.defends(S, a) for a in S), tag
        )
        tc.assertEqual(af.characteristic(S), frozenset(a for a in args if naive.defends(S, a)), tag)
        tc.assertEqual(af.is_complete(S), S in set(naive.complete()), tag)

    # --- structural facts about the semantics
    tc.assertIn(grd, comp, tag)  # grounded is complete
    tc.assertTrue(all(grd <= E for E in comp), tag)  # ... and the least complete extension
    tc.assertEqual(grd, frozenset.intersection(*comp), tag)  # = intersection of complete exts
    tc.assertTrue(set(stab) <= set(semi) <= set(pref) <= set(comp), tag)
    tc.assertTrue(len(pref) >= 1 and len(semi) >= 1, tag)  # always exist
    if stab:
        tc.assertEqual(set(stab), set(semi), tag)  # stable exists => semi-stable = stable

    # --- labellings <-> extensions
    labs = af.labellings()
    tc.assertEqual(len(labs), len(comp), tag)
    tc.assertEqual(set(L.in_ for L in labs), set(comp), tag)
    for L in labs:
        tc.assertEqual(L.out, af.attacked_by_set(L.in_), tag)  # out = S+
        tc.assertEqual(L.in_ | L.out | L.undec, af.arguments, tag)
    # grounded <-> minimal 'in' ; preferred <-> maximal 'in'
    min_in = min(len(L.in_) for L in labs)
    tc.assertEqual({L.in_ for L in labs if len(L.in_) == min_in}, {grd}, tag)
    max_in = [L.in_ for L in labs if not any(L.in_ < M.in_ for M in labs)]
    tc.assertEqual(set(max_in), set(pref), tag)
    # Table 5.1, the equivalent forms: grounded = minimal out = maximal undec,
    # preferred = maximal out
    min_out = [L.in_ for L in labs if not any(M.out < L.out for M in labs)]
    tc.assertEqual(set(min_out), {grd}, tag)
    max_undec = [L.in_ for L in labs if not any(L.undec < M.undec for M in labs)]
    tc.assertEqual(set(max_undec), {grd}, tag)
    max_out = [L.in_ for L in labs if not any(L.out < M.out for M in labs)]
    tc.assertEqual(set(max_out), set(pref), tag)
    # stable <-> no undec ; semi-stable <-> minimal undec
    tc.assertEqual({L.in_ for L in labs if not L.undec}, set(stab), tag)
    min_undec = [L.in_ for L in labs if not any(M.undec < L.undec for M in labs)]
    tc.assertEqual(set(min_undec), set(semi), tag)
    # semi-stable: the book's definition (maximal range among complete
    # extensions) and the admissible-based one give the same sets
    comp_rng = {S: af.range(S) for S in comp}
    book_semi = {S for S in comp if not any(comp_rng[S] < r for r in comp_rng.values())}
    tc.assertEqual(book_semi, set(naive.semi_stable()), tag)
    # admissible labellings <-> admissible sets
    alabs = af.labellings("admissible")
    tc.assertEqual({L.in_ for L in alabs}, set(af.admissible_sets()), tag)

    # --- acceptance status is consistent with the preferred extensions
    for a in args:
        in_all = all(a in E for E in pref)
        in_some = any(a in E for E in pref)
        expected = SKEPTICAL if in_all else CREDULOUS if in_some else REJECTED
        tc.assertEqual(af.acceptance_status(a), expected, tag)


class TestCrossChecksExhaustive(unittest.TestCase):
    """Every framework on 0, 1, 2 and 3 arguments: 1 + 2 + 16 + 512 = 531 frameworks."""

    def test_exhaustive_up_to_three_arguments(self):
        count = 0
        for n in range(0, 4):
            for args, attacks in all_frameworks(n):
                check_framework(self, args, attacks)
                count += 1
        self.assertEqual(count, 1 + 2 + 16 + 512)


class TestCrossChecksRandom(unittest.TestCase):
    def test_random_four_arguments(self):
        for args, attacks in random_frameworks(4, 1500, 0.3, seed=4):
            check_framework(self, args, attacks)

    def test_random_five_arguments(self):
        for args, attacks in random_frameworks(5, 600, 0.25, seed=5):
            check_framework(self, args, attacks)

    def test_random_six_to_seven_arguments(self):
        for n, seed in ((6, 6), (7, 7)):
            for p in (0.1, 0.2, 0.35):
                for args, attacks in random_frameworks(n, 40, p, seed=seed * 100 + int(p * 100)):
                    check_framework(self, args, attacks)


if __name__ == "__main__":
    unittest.main()
