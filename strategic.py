"""Strategic argumentation under the grounded direct mechanism.

The functions in this module implement the second half of Assignment 3.
Reports are mappings from agent identifiers to the arguments revealed by that
agent.  Utilities count the agent's true arguments that are in the grounded
extension; hiding an argument therefore cannot create utility by merely
removing it from the utility calculation.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from itertools import product
from typing import Dict, FrozenSet, Hashable, Iterable, List, Mapping, Sequence, Tuple

from af import ArgumentationFramework

Argument = Hashable
Agent = Hashable
ArgSet = FrozenSet[Argument]
Attack = Tuple[Argument, Argument]


def _materialize_attacks(attacks: Iterable[Attack]) -> Tuple[Attack, ...]:
    result = tuple(attacks)
    for pair in result:
        try:
            x, y = pair
        except (TypeError, ValueError):
            raise ValueError(f"attack {pair!r} is not an (attacker, target) pair") from None
        if x == y:
            continue
    return result


def _normalise_reports(reports: Mapping[Agent, Iterable[Argument]]) -> Dict[Agent, ArgSet]:
    return {agent: frozenset(arguments) for agent, arguments in reports.items()}


def grounded_mechanism(
    attacks: Iterable[Attack],
    reports: Mapping[Agent, Iterable[Argument]],
) -> ArgSet:
    """Return the grounded outcome of the graph induced by all revealed arguments."""
    normalised = _normalise_reports(reports)
    revealed = frozenset().union(*normalised.values()) if normalised else frozenset()
    induced_attacks = tuple(
        (attacker, target)
        for attacker, target in _materialize_attacks(attacks)
        if attacker in revealed and target in revealed
    )
    return ArgumentationFramework(revealed, induced_attacks).grounded_extension()


def _subsets(arguments: Iterable[Argument]) -> List[ArgSet]:
    ordered = tuple(dict.fromkeys(arguments))
    return [
        frozenset(ordered[index] for index in range(len(ordered)) if mask & (1 << index))
        for mask in range(1 << len(ordered))
    ]


def utility(
    agent_arguments: Iterable[Argument],
    accepted: Iterable[Argument],
) -> int:
    """Count the agent's true arguments accepted by the mechanism."""
    return len(frozenset(agent_arguments) & frozenset(accepted))


def best_responses(
    agent_arguments: Iterable[Argument],
    attacks: Iterable[Attack],
    other_reports: Mapping[Agent, Iterable[Argument]],
    agent: Agent = "agent",
) -> List[ArgSet]:
    """Return every report by an agent that maximises that agent's utility."""
    true_arguments = frozenset(agent_arguments)
    reports = _normalise_reports(other_reports)
    reports.pop(agent, None)
    candidates: List[Tuple[ArgSet, int]] = []
    for report in _subsets(true_arguments):
        trial_reports = dict(reports)
        trial_reports[agent] = report
        outcome = grounded_mechanism(attacks, trial_reports)
        candidates.append((report, utility(true_arguments, outcome)))
    maximum = max(score for _, score in candidates)
    return [report for report, score in candidates if score == maximum]


def truthfulness_is_best_response(
    arguments_by_agent: Mapping[Agent, Iterable[Argument]],
    attacks: Iterable[Attack],
) -> bool:
    """Verify Theorem 5.3 for every agent and every reports profile of others."""
    true = {agent: frozenset(arguments) for agent, arguments in arguments_by_agent.items()}
    attack_relation = _materialize_attacks(attacks)
    for agent, own_arguments in true.items():
        others = [other for other in true if other != agent]
        for choices in product(*(_subsets(true[other]) for other in others)):
            other_reports = dict(zip(others, choices))
            if frozenset(own_arguments) not in best_responses(
                own_arguments, attack_relation, other_reports, agent
            ):
                return False
    return True


def has_odd_length_path(
    arguments: Iterable[Argument],
    attacks: Iterable[Attack],
    source: Argument,
    target: Argument,
) -> bool:
    """Return whether a non-empty odd-length directed path exists."""
    argument_set = frozenset(arguments)
    if source not in argument_set or target not in argument_set:
        raise ValueError("source and target must be arguments in the framework")
    adjacency = {argument: set() for argument in argument_set}
    for attacker, attacked in _materialize_attacks(attacks):
        if attacker in argument_set and attacked in argument_set:
            adjacency[attacker].add(attacked)

    pending = [(source, 0)]
    seen = {(source, 0)}
    while pending:
        node, parity = pending.pop()
        for successor in adjacency[node]:
            next_state = (successor, 1 - parity)
            if next_state in seen:
                continue
            if successor == target and next_state[1] == 1:
                return True
            seen.add(next_state)
            pending.append(next_state)
    return False


def theorem_5_4_condition(
    arguments_by_agent: Mapping[Agent, Iterable[Argument]],
    attacks: Iterable[Attack],
) -> bool:
    """Return True exactly when Theorem 5.4's odd-path condition holds."""
    true = {agent: frozenset(arguments) for agent, arguments in arguments_by_agent.items()}
    all_arguments = frozenset().union(*true.values()) if true else frozenset()
    attack_relation = _materialize_attacks(attacks)
    for own_arguments in true.values():
        for source in own_arguments:
            for target in own_arguments - {source}:
                if has_odd_length_path(all_arguments, attack_relation, source, target):
                    return False
    return True


def is_strategyproof(
    arguments_by_agent: Mapping[Agent, Iterable[Argument]],
    attacks: Iterable[Attack],
) -> bool:
    """Check strategyproofness by verifying every truthful report is optimal."""
    return truthfulness_is_best_response(arguments_by_agent, attacks)


@dataclass(frozen=True)
class ExperimentResult:
    probability: float
    instances: int
    strategyproof_fraction: float
    condition_fraction: float
    condition_but_not_strategyproof: Tuple[Tuple[Mapping[Agent, ArgSet], Tuple[Attack, ...]], ...]
    strategyproof_but_not_condition: Tuple[Tuple[Mapping[Agent, ArgSet], Tuple[Attack, ...]], ...]


def run_experiments(
    probabilities: Sequence[float] = (0.1, 0.3, 0.5, 0.7, 0.9),
    instances: int = 1000,
    seed: int = 3,
) -> List[ExperimentResult]:
    """Run the assignment's random 3-agent, 6-8-argument experiments."""
    rng = random.Random(seed)
    results = []
    for probability in probabilities:
        strategyproof_count = 0
        condition_count = 0
        false_negatives = []
        false_positives = []
        for _ in range(instances):
            count = rng.randint(6, 8)
            arguments = tuple(f"a{i}" for i in range(count))
            assignments = {
                agent: set() for agent in ("agent1", "agent2", "agent3")
            }
            for argument in arguments:
                assignments[rng.choice(tuple(assignments))].add(argument)
            attacks = tuple(
                (source, target)
                for source in arguments
                for target in arguments
                if rng.random() < probability
            )
            condition = theorem_5_4_condition(assignments, attacks)
            strategyproof = is_strategyproof(assignments, attacks)
            strategyproof_count += strategyproof
            condition_count += condition
            if condition and not strategyproof:
                false_negatives.append(
                    ({a: frozenset(v) for a, v in assignments.items()}, attacks)
                )
            if strategyproof and not condition:
                false_positives.append(
                    ({a: frozenset(v) for a, v in assignments.items()}, attacks)
                )
        results.append(
            ExperimentResult(
                probability,
                instances,
                strategyproof_count / instances,
                condition_count / instances,
                tuple(false_negatives),
                tuple(false_positives),
            )
        )
    return results


__all__ = [
    "ExperimentResult",
    "best_responses",
    "grounded_mechanism",
    "has_odd_length_path",
    "is_strategyproof",
    "run_experiments",
    "theorem_5_4_condition",
    "truthfulness_is_best_response",
    "utility",
]
