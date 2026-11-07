"""
strategic.py -- strategic argumentation with the grounded direct mechanism.

The setting (Chapter 5, Section 5.4 of Weiss (ed.), Multiagent Systems, 2nd ed.)
------------------------------------------------------------------------------
There is one global argumentation framework <A, R>.  Agent i owns a set of
arguments A_i (its *type*) and the A_i together cover A.  Every agent reports
("reveals") a subset A_i' of A_i; agents may hide arguments but never invent
them.  The *grounded direct argumentation mechanism* (Definition 5.21) takes
the reports and returns the grounded extension of the framework induced by the
union of the revealed arguments.  An agent with *acceptability maximizing
preferences* (Definition 5.22) has utility |outcome ∩ A_i|, the number of its
own arguments that end up accepted.

This module provides

    mechanism(attacks, reports)             the outcome rule g
    utility(agent_type, outcome)            |outcome ∩ A_i|
    best_responses(agent, types, attacks, others_reports)
                                            every report of one agent that
                                            maximizes its utility, given fixed
                                            reports of the others
    check_truthful_dominant(types, attacks) Theorem 5.3: is revealing all of A_i
                                            a best response for every agent
                                            against every combination of
                                            subsets the others could reveal?
    check_odd_path_condition(types, attacks)
                                            Theorem 5.4: does any agent own two
                                            arguments joined by an odd-length
                                            directed path?  (A sufficient
                                            condition for strategyproofness.)

Conventions
-----------
* ``attacks``  an iterable of (attacker, target) pairs: the global attack
  relation R.  Pairs that mention an argument outside the revealed set are
  ignored by the mechanism (the *induced* graph keeps only pairs whose two ends
  are both revealed).
* ``types``    a sequence of sets, ``types[i]`` = A_i.  Agents are identified by
  their index 0 .. m-1.
* ``reports``  a sequence of sets, ``reports[i]`` = what agent i reveals.
* Sets of arguments are returned as ``frozenset``.

The grounded extension is computed with the engine in af.py
(``ArgumentationFramework.grounded_extension``).
"""

from __future__ import annotations

from collections import deque
from itertools import product
from typing import (
    Dict,
    FrozenSet,
    Hashable,
    Iterable,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
)

from af import ArgumentationFramework

Argument = Hashable
ArgSet = FrozenSet[Argument]
Attack = Tuple[Argument, Argument]

__all__ = [
    "GroundedMechanism",
    "mechanism",
    "utility",
    "utilities",
    "subsets",
    "best_responses",
    "BestResponses",
    "check_truthful_dominant",
    "TruthfulnessCheck",
    "Manipulation",
    "indirectly_defeats",
    "odd_path_pairs",
    "check_odd_path_condition",
    "OddPathCheck",
]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _norm_types(types: Sequence[Iterable[Argument]]) -> List[ArgSet]:
    return [frozenset(t) for t in types]


def subsets(items: Iterable[Argument]) -> List[ArgSet]:
    """All 2^k subsets of ``items`` as frozensets, smallest first.

    The order is deterministic (by size, then by the sorted string form).
    """
    pool = sorted(set(items), key=str)
    out: List[ArgSet] = []
    for mask in range(1 << len(pool)):
        out.append(frozenset(pool[i] for i in range(len(pool)) if (mask >> i) & 1))
    out.sort(key=lambda s: (len(s), sorted(map(str, s))))
    return out


def _check_attacks(attacks: Iterable[Attack]) -> frozenset:
    pairs = set()
    for pair in attacks:
        try:
            x, y = pair
        except (TypeError, ValueError):
            raise ValueError(f"attack {pair!r} is not an (attacker, target) pair") from None
        pairs.add((x, y))
    return frozenset(pairs)


def utility(agent_type: Iterable[Argument], outcome: Iterable[Argument]) -> int:
    """Acceptability-maximizing utility: the number of the agent's own arguments accepted."""
    return len(frozenset(agent_type) & frozenset(outcome))


def utilities(types: Sequence[Iterable[Argument]], outcome: Iterable[Argument]) -> List[int]:
    """The utility of every agent for one outcome."""
    outcome = frozenset(outcome)
    return [utility(t, outcome) for t in types]


# --------------------------------------------------------------------------
# the mechanism (Definition 5.21)
# --------------------------------------------------------------------------
class GroundedMechanism:
    """The grounded direct argumentation mechanism for a fixed attack relation R.

    Calling the object on the agents' reports returns the outcome
    g(A_1', ..., A_m') = grounded extension of <∪A_i', R restricted to ∪A_i'>.
    Outcomes are cached by the union of the reports (the outcome depends on
    nothing else), which makes exhaustive strategy checks cheap.
    """

    def __init__(self, attacks: Iterable[Attack]):
        self.attacks: frozenset = _check_attacks(attacks)
        self._cache: Dict[ArgSet, ArgSet] = {}

    def outcome_of_union(self, revealed: Iterable[Argument]) -> ArgSet:
        """Grounded extension of the graph induced by ``revealed``."""
        revealed = frozenset(revealed)
        hit = self._cache.get(revealed)
        if hit is None:
            induced = [(x, y) for (x, y) in self.attacks if x in revealed and y in revealed]
            hit = ArgumentationFramework(revealed, induced).grounded_extension()
            self._cache[revealed] = hit
        return hit

    def __call__(self, reports: Sequence[Iterable[Argument]]) -> ArgSet:
        union: Set[Argument] = set()
        for r in reports:
            union |= set(r)
        return self.outcome_of_union(union)


def mechanism(attacks: Iterable[Attack], reports: Sequence[Iterable[Argument]]) -> ArgSet:
    """The outcome rule of the grounded direct argumentation mechanism.

    Takes the global attack relation and one revealed argument set per agent,
    and returns the grounded extension of the graph induced by the union of the
    revealed arguments (attacks with an unrevealed end are dropped).
    """
    return GroundedMechanism(attacks)(reports)


# --------------------------------------------------------------------------
# best responses
# --------------------------------------------------------------------------
class BestResponses(NamedTuple):
    """Result of ``best_responses``."""

    utility: int  # the maximal utility the agent can reach
    reports: List[ArgSet]  # every report reaching it (smallest first)
    truthful_is_best: bool  # is revealing the whole type among them?


def _resolve_others(
    agent: int, types: List[ArgSet], others_reports: Mapping[int, Iterable[Argument]]
) -> Dict[int, ArgSet]:
    expected = set(range(len(types))) - {agent}
    if set(others_reports) != expected:
        raise ValueError(
            f"others_reports must give a report for exactly the agents {sorted(expected)}, "
            f"got {sorted(others_reports)}"
        )
    fixed = {j: frozenset(r) for j, r in others_reports.items()}
    for j, r in fixed.items():
        if not r <= types[j]:
            raise ValueError(f"agent {j} may only reveal arguments it owns; {sorted(r - types[j], key=str)!r} are not its own")
    return fixed


def best_responses(
    agent: int,
    types: Sequence[Iterable[Argument]],
    attacks: Iterable[Attack],
    others_reports: Mapping[int, Iterable[Argument]],
    _mech: Optional[GroundedMechanism] = None,
) -> BestResponses:
    """Enumerate every subset of A_agent that the agent could reveal, given the
    fixed reports of the others, and return those that maximize its utility.

    Parameters
    ----------
    agent          index of the agent choosing a report
    types          A_i for every agent
    attacks        the global attack relation
    others_reports {j: report of agent j} for every other agent j (each must be
                   a subset of A_j)

    Returns ``BestResponses(utility, reports, truthful_is_best)``.
    """
    types = _norm_types(types)
    if not 0 <= agent < len(types):
        raise ValueError(f"unknown agent {agent!r}")
    fixed = _resolve_others(agent, types, others_reports)
    mech = _mech or GroundedMechanism(attacks)
    others_union: ArgSet = frozenset().union(*fixed.values()) if fixed else frozenset()
    own = types[agent]

    best = -1
    winners: List[ArgSet] = []
    for report in subsets(own):  # smallest first
        u = utility(own, mech.outcome_of_union(report | others_union))
        if u > best:
            best, winners = u, [report]
        elif u == best:
            winners.append(report)
    return BestResponses(best, winners, own in winners)


# --------------------------------------------------------------------------
# Theorem 5.3: truthful revelation is a best response against everything
# --------------------------------------------------------------------------
class Manipulation(NamedTuple):
    """A profitable deviation: ``agent`` gains by hiding ``hidden`` when the
    others reveal ``others_reports``."""

    agent: int
    others_reports: Dict[int, ArgSet]
    hidden: ArgSet
    truthful_utility: int
    deviation_utility: int
    truthful_outcome: ArgSet
    deviation_outcome: ArgSet

    def __str__(self) -> str:
        def fmt(s):
            return "{" + ", ".join(sorted(map(str, s))) + "}"

        others = "; ".join(f"agent {j} reveals {fmt(r)}" for j, r in sorted(self.others_reports.items()))
        return (
            f"agent {self.agent} hides {fmt(self.hidden)} when {others}: "
            f"utility {self.truthful_utility} -> {self.deviation_utility} "
            f"(outcome {fmt(self.truthful_outcome)} -> {fmt(self.deviation_outcome)})"
        )


class TruthfulnessCheck(NamedTuple):
    """Result of ``check_truthful_dominant``."""

    holds: bool  # revealing everything is a best response for every agent in every context
    manipulations: List[Manipulation]  # profitable deviations found (first only unless find_all)
    agents_with_manipulation: List[int]
    contexts_checked: int  # (agent, others' combination, hidden subset) triples examined

    def __bool__(self) -> bool:
        return self.holds


def check_truthful_dominant(
    types: Sequence[Iterable[Argument]],
    attacks: Iterable[Attack],
    find_all: bool = False,
    _mech: Optional[GroundedMechanism] = None,
) -> TruthfulnessCheck:
    """Check the condition of Theorem 5.3.

    For every agent i, every combination of subsets A_-i' that the other agents
    could reveal, and every S ⊆ A_i, verify

        |A_i ∩ E(A_i ∪ A_-i')|  >=  |A_i ∩ E((A_i \\ S) ∪ A_-i')|

    where E is the grounded extension of the induced graph.  This says exactly
    that revealing all of A_i (truthfulness) is a best response for agent i
    against every combination of the others' reports.  By Theorem 5.3 the
    grounded direct mechanism is strategyproof for acceptability maximizers iff
    this holds.

    The check is exhaustive: with n arguments in total it examines about
    m * 2^n situations, which is trivial for n <= 8 (and fine up to about 14).

    Returns ``TruthfulnessCheck``.  Unless ``find_all`` is true the search stops
    at the first profitable deviation, which is then ``manipulations[0]``.
    """
    types = _norm_types(types)
    mech = _mech or GroundedMechanism(attacks)
    found: List[Manipulation] = []
    checked = 0

    for i, own in enumerate(types):
        others = [j for j in range(len(types)) if j != i]
        other_choices = [subsets(types[j]) for j in others]
        own_subsets = subsets(own)
        for combo in product(*other_choices):
            union_others: ArgSet = frozenset().union(*combo) if combo else frozenset()
            truthful_outcome = mech.outcome_of_union(own | union_others)
            u_true = utility(own, truthful_outcome)
            for reveal in own_subsets:
                checked += 1
                dev_outcome = mech.outcome_of_union(reveal | union_others)
                u_dev = utility(own, dev_outcome)
                if u_dev > u_true:
                    found.append(
                        Manipulation(
                            agent=i,
                            others_reports=dict(zip(others, combo)),
                            hidden=own - reveal,
                            truthful_utility=u_true,
                            deviation_utility=u_dev,
                            truthful_outcome=truthful_outcome,
                            deviation_outcome=dev_outcome,
                        )
                    )
                    if not find_all:
                        return TruthfulnessCheck(False, found, [i], checked)
    agents = sorted({m.agent for m in found})
    return TruthfulnessCheck(not found, found, agents, checked)


# --------------------------------------------------------------------------
# Theorem 5.4: no odd-length directed path between two arguments of one agent
# --------------------------------------------------------------------------
def _successors(attacks: Iterable[Attack], universe: Optional[Set[Argument]] = None) -> Dict[Argument, List[Argument]]:
    succ: Dict[Argument, List[Argument]] = {}
    for x, y in attacks:
        if universe is not None and (x not in universe or y not in universe):
            continue
        succ.setdefault(x, []).append(y)
    return succ


def _odd_walk_targets(succ: Mapping[Argument, Sequence[Argument]], source: Argument) -> Set[Argument]:
    """All arguments reachable from ``source`` by a directed walk of odd length.

    Breadth-first search over states (argument, parity of the walk length so
    far).  Cycles cannot make it loop: every state is expanded at most once, so
    the search touches at most 2n states.  ``source`` itself is in the result
    exactly when it lies on an odd closed walk.
    """
    seen = {(source, 0)}
    queue = deque([(source, 0)])
    while queue:
        node, parity = queue.popleft()
        for nxt in succ.get(node, ()):
            state = (nxt, 1 - parity)
            if state not in seen:
                seen.add(state)
                queue.append(state)
    return {node for (node, parity) in seen if parity == 1}


def _has_odd_simple_path(
    succ: Mapping[Argument, Sequence[Argument]], source: Argument, target: Argument
) -> bool:
    """Is there a path without repeated vertices of odd length from source to target?

    (For source == target: a simple cycle of odd length through source.)
    Depth-first search; exponential in the worst case, which is fine for the
    small graphs used here.
    """
    on_path = {source}

    def dfs(node: Argument, length: int) -> bool:
        for nxt in succ.get(node, ()):
            if nxt == target and (length + 1) % 2 == 1:
                return True
            if nxt not in on_path:
                on_path.add(nxt)
                found = dfs(nxt, length + 1)
                on_path.discard(nxt)
                if found:
                    return True
        return False

    return dfs(source, 0)


def indirectly_defeats(
    attacks: Iterable[Attack],
    alpha: Argument,
    beta: Argument,
    mode: str = "walk",
    universe: Optional[Iterable[Argument]] = None,
) -> bool:
    """alpha "indirectly defeats" beta: is there an odd-length directed path from alpha to beta?

    mode="walk"    the path may revisit arguments (an odd-length *walk*).  Decided
                   by breadth-first search over (argument, parity) states, so
                   cycles are handled and the cost is linear in the size of the
                   graph.  This is the default.
    mode="simple"  the path may not repeat an argument (a simple path; for
                   alpha == beta, a simple odd cycle).  Exponential-time search.

    ``universe`` restricts the graph to attacks whose two ends are both in it
    (the "full graph" is normally the union of all agents' types).
    """
    uni = None if universe is None else set(universe)
    succ = _successors(_check_attacks(attacks), uni)
    if mode == "walk":
        return beta in _odd_walk_targets(succ, alpha)
    if mode == "simple":
        return _has_odd_simple_path(succ, alpha, beta)
    raise ValueError("mode must be 'walk' or 'simple'")


class OddPathCheck(NamedTuple):
    """Result of ``check_odd_path_condition``."""

    holds: bool  # True iff NO agent owns two arguments joined by an odd path
    violations: List[Tuple[int, Argument, Argument]]  # (agent, alpha, beta) with alpha -> beta odd

    def __bool__(self) -> bool:
        return self.holds


def odd_path_pairs(
    types: Sequence[Iterable[Argument]],
    attacks: Iterable[Attack],
    mode: str = "walk",
    include_same: bool = False,
) -> List[Tuple[int, Argument, Argument]]:
    """All (agent, alpha, beta) with alpha, beta in A_agent and an odd path alpha -> beta.

    ``include_same`` also reports pairs alpha == beta, i.e. an argument that lies
    on an odd cycle (this includes a self-attacking argument).  By default only
    two *different* arguments count, as in "no agent holds two arguments α, β".
    """
    types = _norm_types(types)
    universe: Set[Argument] = set().union(*types) if types else set()
    pairs = _check_attacks(attacks)
    succ = _successors(pairs, universe)
    if mode not in ("walk", "simple"):
        raise ValueError("mode must be 'walk' or 'simple'")
    out: List[Tuple[int, Argument, Argument]] = []
    for i, own in enumerate(types):
        ordered = sorted(own, key=str)
        for alpha in ordered:
            odd_targets = _odd_walk_targets(succ, alpha) if mode == "walk" else None
            for beta in ordered:
                if alpha == beta and not include_same:
                    continue
                if mode == "walk":
                    hit = beta in odd_targets  # type: ignore[operator]
                else:
                    hit = _has_odd_simple_path(succ, alpha, beta)
                if hit:
                    out.append((i, alpha, beta))
    return out


def check_odd_path_condition(
    types: Sequence[Iterable[Argument]],
    attacks: Iterable[Attack],
    mode: str = "walk",
    include_same: bool = False,
) -> OddPathCheck:
    """The graph-theoretic condition of Theorem 5.4.

    Holds iff no agent i owns two arguments α, β ∈ A_i such that α indirectly
    defeats β, i.e. there is an odd-length directed path from α to β in the
    full graph.  (Note that a direct attack α ⇀ β is a path of length 1.)  If it
    holds, the grounded direct mechanism is strategyproof for acceptability
    maximizers.  The converse is false (Example 5.11).

    See ``odd_path_pairs`` for ``mode`` and ``include_same``.
    """
    violations = odd_path_pairs(types, attacks, mode=mode, include_same=include_same)
    return OddPathCheck(not violations, violations)
