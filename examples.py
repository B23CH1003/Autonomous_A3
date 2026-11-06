"""
examples.py -- example frameworks with expected results.

BOOK_EXAMPLES  frameworks from Chapter 5 ("Argumentation among Agents",
               I. Rahwan) of G. Weiss (ed.), Multiagent Systems, 2nd ed.,
               MIT Press, 2013: Figures 5.1, 5.2, 5.3(i), 5.4(a), 5.4(b), 5.5.
               The argument alpha_i of the book is written "a<i>" here.
EXTRA_EXAMPLES further standard frameworks that exercise corner cases the
               book's figures do not cover (odd cycles, self-attack, a
               preferred extension that is not semi-stable, no stable
               extension, ...).
EXAMPLES       both of the above (book first).

Each Example records the framework together with the expected grounded,
complete, preferred, stable and semi-stable extensions and the acceptance
status of every argument under preferred semantics.  ``book_claims`` lists
what the book itself states about the figure; the remaining expectations were
worked out by hand from the book's definitions.  Everything is checked against
the engine in tests/test_af.py and printed by demo.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from af import ArgumentationFramework, CREDULOUS, REJECTED, SKEPTICAL


def sets(*specs: str) -> List[frozenset]:
    """sets("", "a", "bd") -> [frozenset(), frozenset({'a'}), frozenset({'b','d'})]

    Each string lists the (single-letter) arguments of one set.
    """
    return [frozenset(s) for s in specs]


@dataclass(frozen=True)
class Example:
    name: str
    description: str
    af: ArgumentationFramework
    grounded: frozenset
    complete: List[frozenset]
    preferred: List[frozenset]
    stable: List[frozenset]
    semi_stable: List[frozenset]
    status: Dict[str, str]  # acceptance status under preferred semantics
    source: str = ""  # where the framework comes from
    book_claims: Tuple[str, ...] = ()  # statements made about it in the book


def asets(*specs: str) -> List[frozenset]:
    """asets("", "3", "135") -> [frozenset(), {'a3'}, {'a1','a3','a5'}]

    For the book's alpha_i arguments: each string lists the indices of one set.
    """
    return [frozenset(f"a{d}" for d in s) for s in specs]


def args(n: int) -> List[str]:
    return [f"a{i}" for i in range(1, n + 1)]


BOOK_EXAMPLES: Dict[str, Example] = {}
EXTRA_EXAMPLES: Dict[str, Example] = {}

# ---------------------------------------------------------------------------
# Book: Weiss (ed.), Multiagent Systems (2nd ed.), Chapter 5
# ---------------------------------------------------------------------------
_fig_5_1 = ArgumentationFramework(args(5), [("a2", "a1"), ("a4", "a1"), ("a3", "a2"), ("a5", "a4")])
BOOK_EXAMPLES["book_fig_5_1"] = Example(
    name="book_fig_5_1",
    description=(
        "Figure 5.1 'A simple argument graph': a1 has two defeaters a2 and a4, "
        "which are themselves defeated by a3 and a5 respectively."
    ),
    af=_fig_5_1,
    grounded=frozenset({"a1", "a3", "a5"}),
    complete=asets("135"),
    preferred=asets("135"),
    stable=asets("135"),
    semi_stable=asets("135"),
    status={"a1": SKEPTICAL, "a2": REJECTED, "a3": SKEPTICAL, "a4": REJECTED, "a5": SKEPTICAL},
    source="Figure 5.1; Examples 5.5, 5.6, 5.8; grounded iteration in Section 3",
    book_claims=(
        "{a3, a5} defends a1 (after Definition 5.2)",
        "Example 5.5: {}, {a3}, {a5}, {a3, a5} and {a1, a3, a5} are admissible",
        "Example 5.6: {a3, a5} is admissible but not complete (it defends a1)",
        "Example 5.6: F({a3}) = F({a5}) = {a3, a5}; {a1, a3, a5} is the only complete extension",
        "Grounded by iteration: F^1 = {a3, a5}, F^2 = {a1, a3, a5}, F^3 = F^2",
        "Example 5.8: {a1, a3, a5} is the only preferred extension",
    ),
)

_fig_5_2 = ArgumentationFramework(args(3), [("a1", "a2"), ("a2", "a1")])
BOOK_EXAMPLES["book_fig_5_2"] = Example(
    name="book_fig_5_2",
    description=(
        "Figure 5.2 'Graph with three labelings/complete extensions': a1 and a2 "
        "defeat each other; a3 is not involved in any defeat."
    ),
    af=_fig_5_2,
    grounded=frozenset({"a3"}),
    complete=asets("3", "13", "23"),
    preferred=asets("13", "23"),
    stable=asets("13", "23"),
    semi_stable=asets("13", "23"),
    status={"a1": CREDULOUS, "a2": CREDULOUS, "a3": SKEPTICAL},
    source="Figure 5.2; Examples 5.7, 5.8; grounded remark in Section 3",
    book_claims=(
        "Example 5.7: three complete extensions {a3}, {a1, a3}, {a2, a3}",
        "Figure 5.2: labellings L^G (a1, a2 undec; a3 in), L1 (a1 in, a2 out, a3 in), "
        "L2 (a2 in, a1 out, a3 in)",
        "The grounded extension is {a3}, the minimal complete extension",
        "Example 5.8: two preferred extensions {a1, a3} and {a2, a3}",
    ),
)

_fig_5_3 = ArgumentationFramework(
    "abcde",
    [("b", "a"), ("c", "b"), ("d", "b"), ("c", "d"), ("d", "c"), ("e", "d")],
)
BOOK_EXAMPLES["book_fig_5_3"] = Example(
    name="book_fig_5_3",
    description=(
        "Figure 5.3(i) (Example 5.9, dispute trees): b defeats a; c and d defeat b; "
        "c and d defeat each other; e defeats d."
    ),
    af=_fig_5_3,
    grounded=frozenset("ace"),
    complete=sets("ace"),
    preferred=sets("ace"),
    stable=sets("ace"),
    semi_stable=sets("ace"),
    status={"a": SKEPTICAL, "b": REJECTED, "c": SKEPTICAL, "d": REJECTED, "e": SKEPTICAL},
    source="Figure 5.3(i); Example 5.9",
    book_claims=(
        "Figure 5.3(iii): PRO has a winning strategy for a (a is acceptable)",
    ),
)

_r_5_10 = [("a1", "a2"), ("a2", "a3"), ("a3", "a4"), ("a3", "a5")]
BOOK_EXAMPLES["book_fig_5_4a"] = Example(
    name="book_fig_5_4a",
    description=(
        "Figure 5.4(a) / Example 5.10, everything revealed: "
        "R = {(a1,a2), (a2,a3), (a3,a4), (a3,a5)}."
    ),
    af=ArgumentationFramework(args(5), _r_5_10),
    grounded=frozenset({"a1", "a3"}),
    complete=asets("13"),
    preferred=asets("13"),
    stable=asets("13"),
    semi_stable=asets("13"),
    status={"a1": SKEPTICAL, "a2": REJECTED, "a3": SKEPTICAL, "a4": REJECTED, "a5": REJECTED},
    source="Figure 5.4(a); Example 5.10",
    book_claims=("Example 5.10: the grounded outcome is o = {a1, a3}",),
)

BOOK_EXAMPLES["book_fig_5_4b"] = Example(
    name="book_fig_5_4b",
    description="Figure 5.4(b) / Example 5.10 with a1 withheld: a2 -> a3, a3 -> a4, a3 -> a5.",
    af=ArgumentationFramework(["a2", "a3", "a4", "a5"], [p for p in _r_5_10 if "a1" not in p]),
    grounded=frozenset({"a2", "a4", "a5"}),
    complete=asets("245"),
    preferred=asets("245"),
    stable=asets("245"),
    semi_stable=asets("245"),
    status={"a2": SKEPTICAL, "a3": REJECTED, "a4": SKEPTICAL, "a5": SKEPTICAL},
    source="Figure 5.4(b); Example 5.10",
    book_claims=("Example 5.10: withholding a1 gives the outcome o' = {a2, a4, a5}",),
)

BOOK_EXAMPLES["book_fig_5_5"] = Example(
    name="book_fig_5_5",
    description="Figure 5.5 / Example 5.11: Example 5.10 plus argument a6 with a6 -> a3.",
    af=ArgumentationFramework(args(6), _r_5_10 + [("a6", "a3")]),
    grounded=frozenset({"a1", "a4", "a5", "a6"}),
    complete=asets("1456"),
    preferred=asets("1456"),
    stable=asets("1456"),
    semi_stable=asets("1456"),
    status={"a1": SKEPTICAL, "a2": REJECTED, "a3": REJECTED, "a4": SKEPTICAL, "a5": SKEPTICAL, "a6": SKEPTICAL},
    source="Figure 5.5; Example 5.11",
    book_claims=("Example 5.11: under full revelation the outcome is o = {a1, a4, a5, a6}",),
)


# ---------------------------------------------------------------------------
# Further standard frameworks (corner cases)
# ---------------------------------------------------------------------------
def _add(ex: Example) -> None:
    EXTRA_EXAMPLES[ex.name] = ex


_add(
    Example(
        name="mutual_attack",
        description="Two arguments attacking each other: a <-> b.",
        af=ArgumentationFramework("ab", [("a", "b"), ("b", "a")]),
        grounded=frozenset(),
        complete=sets("", "a", "b"),
        preferred=sets("a", "b"),
        stable=sets("a", "b"),
        semi_stable=sets("a", "b"),
        status={"a": CREDULOUS, "b": CREDULOUS},
    )
)

_add(
    Example(
        name="chain",
        description="A chain a -> b -> c: acceptance propagates down the chain.",
        af=ArgumentationFramework("abc", [("a", "b"), ("b", "c")]),
        grounded=frozenset("ac"),
        complete=sets("ac"),
        preferred=sets("ac"),
        stable=sets("ac"),
        semi_stable=sets("ac"),
        status={"a": SKEPTICAL, "b": REJECTED, "c": SKEPTICAL},
    )
)

_add(
    Example(
        name="odd_cycle",
        description="Three-cycle a -> b -> c -> a: nothing can be accepted; no stable extension.",
        af=ArgumentationFramework("abc", [("a", "b"), ("b", "c"), ("c", "a")]),
        grounded=frozenset(),
        complete=sets(""),
        preferred=sets(""),
        stable=[],
        semi_stable=sets(""),
        status={"a": REJECTED, "b": REJECTED, "c": REJECTED},
    )
)

_add(
    Example(
        name="even_cycle",
        description="Four-cycle a -> b -> c -> d -> a: two alternating extensions.",
        af=ArgumentationFramework("abcd", [("a", "b"), ("b", "c"), ("c", "d"), ("d", "a")]),
        grounded=frozenset(),
        complete=sets("", "ac", "bd"),
        preferred=sets("ac", "bd"),
        stable=sets("ac", "bd"),
        semi_stable=sets("ac", "bd"),
        status={x: CREDULOUS for x in "abcd"},
    )
)

_add(
    Example(
        name="self_attack_defended",
        description="a attacks itself and b; c attacks a, so c reinstates b.",
        af=ArgumentationFramework("abc", [("c", "a"), ("a", "a"), ("a", "b")]),
        grounded=frozenset("bc"),
        complete=sets("bc"),
        preferred=sets("bc"),
        stable=sets("bc"),
        semi_stable=sets("bc"),
        status={"a": REJECTED, "b": SKEPTICAL, "c": SKEPTICAL},
    )
)

_add(
    Example(
        name="diamond",
        description="a <-> b, and both attack c (a classic 'Nixon diamond' shape).",
        af=ArgumentationFramework("abc", [("a", "b"), ("b", "a"), ("a", "c"), ("b", "c")]),
        grounded=frozenset(),
        complete=sets("", "a", "b"),
        preferred=sets("a", "b"),
        stable=sets("a", "b"),
        semi_stable=sets("a", "b"),
        status={"a": CREDULOUS, "b": CREDULOUS, "c": REJECTED},
    )
)

_add(
    Example(
        name="preferred_not_semi_stable",
        description=(
            "a <-> b, b -> c, and the odd cycle c -> d -> e -> c.  {a} is preferred "
            "but not semi-stable: its range {a, b} is strictly smaller than the "
            "range of {b, d}, which is the only stable / semi-stable extension."
        ),
        af=ArgumentationFramework(
            "abcde",
            [("a", "b"), ("b", "a"), ("b", "c"), ("c", "d"), ("d", "e"), ("e", "c")],
        ),
        grounded=frozenset(),
        complete=sets("", "a", "bd"),
        preferred=sets("a", "bd"),
        stable=sets("bd"),
        semi_stable=sets("bd"),
        status={"a": CREDULOUS, "b": CREDULOUS, "c": REJECTED, "d": CREDULOUS, "e": REJECTED},
    )
)

_add(
    Example(
        name="no_stable_but_semi_stable",
        description=(
            "a <-> b plus a self-attacker c that nobody else attacks.  c can never be "
            "attacked by an extension, so there is no stable extension, yet semi-stable "
            "extensions exist (as they always do)."
        ),
        af=ArgumentationFramework("abc", [("a", "b"), ("b", "a"), ("c", "c")]),
        grounded=frozenset(),
        complete=sets("", "a", "b"),
        preferred=sets("a", "b"),
        stable=[],
        semi_stable=sets("a", "b"),
        status={"a": CREDULOUS, "b": CREDULOUS, "c": REJECTED},
    )
)


EXAMPLES: Dict[str, Example] = {**BOOK_EXAMPLES, **EXTRA_EXAMPLES}
