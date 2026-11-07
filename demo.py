"""
demo.py -- demonstration of the argumentation engine.

Run:  python demo.py

Section A  walks through the building blocks (conflict-free, defence, the
           characteristic function F, admissible, complete, grounded by
           iterating F) on Figure 5.1 of the book, reproducing Examples 5.5,
           5.6 and the grounded-extension computation of Section 3.
Section B  the book's example graphs (Figures 5.1-5.5): extensions under every
           semantics, all legal labellings, acceptance statuses, and the
           statements the book makes about each figure.
Section C  further frameworks covering corner cases.
Section D  strategic argumentation: the grounded direct mechanism on Examples
           5.10 and 5.11 (utilities, best responses, the checks of Theorems 5.3
           and 5.4), and why the argument a6 matters in Example 5.11.
Section E  a short run of the random experiment (the full one is
           `python experiments.py`) and four strategyproof instances whose
           Theorem 5.4 condition fails, with the reason in each case.

Book: G. Weiss (ed.), Multiagent Systems, 2nd ed., MIT Press 2013, Chapter 5.
The argument alpha_i of the book is written a<i>.
Output of a full run is saved in demo_output.txt.
"""

from itertools import product

from af import ArgumentationFramework, format_set, format_sets
from examples import BOOK_EXAMPLES, EXTRA_EXAMPLES
from experiments import Instance, analyse_instance, markdown_table, run_experiment, summarise
from strategic import (
    GroundedMechanism,
    best_responses,
    check_odd_path_condition,
    check_truthful_dominant,
    mechanism,
    subsets,
    utilities,
    utility,
)
from strategic_examples import AGENT_NAMES, EXAMPLE_5_10, EXAMPLE_5_11


def banner(text: str) -> None:
    print()
    print("=" * 72)
    print(text)
    print("=" * 72)


def walkthrough() -> None:
    banner("Section A - building blocks on the book's Figure 5.1")
    af: ArgumentationFramework = BOOK_EXAMPLES["book_fig_5_1"].af
    print("a2 -> a1, a4 -> a1, a3 -> a2, a5 -> a4")

    print("\nConflict-free?")
    for S in [set(), {"a3", "a5"}, {"a1", "a3", "a5"}, {"a1", "a2"}, {"a3", "a2"}]:
        print(f"  {format_set(S):16} -> {af.is_conflict_free(S)}")

    print("\nDefended by S?  (book: '{a3, a5} defends a1')")
    for a, S in [("a1", {"a3", "a5"}), ("a1", {"a3"}), ("a3", set()), ("a2", {"a1"})]:
        print(f"  {a} defended by {format_set(S):10} -> {af.is_defended(a, S)}")

    print("\nCharacteristic function F(S)  (book, Example 5.6: F({a3}) = F({a5}) = {a3, a5})")
    for S in [set(), {"a3"}, {"a5"}, {"a3", "a5"}, {"a1", "a3", "a5"}]:
        print(f"  F({format_set(S)}) = {format_set(af.characteristic(S))}")

    print("\nAdmissible / complete?  (book, Examples 5.5 and 5.6)")
    for S in [set(), {"a3"}, {"a5"}, {"a3", "a5"}, {"a1", "a3", "a5"}, {"a1"}]:
        print(
            f"  {format_set(S):16} admissible={af.is_admissible(S)!s:5}  "
            f"complete={af.is_complete(S)}"
        )

    print("\nGrounded extension by iterating F from the empty set  (book, Section 3)")
    S = frozenset()
    step = 0
    while True:
        nxt = af.characteristic(S)
        step += 1
        print(f"  F^{step}({{}}) = {format_set(nxt)}")
        if nxt == S:
            break
        S = nxt
    print(f"  fixed point reached -> grounded = {format_set(af.grounded_extension())}")


def show_example(ex) -> None:
    af = ex.af
    banner(ex.name)
    print(ex.description)
    if ex.source:
        print(f"source: {ex.source}")
    atts = ", ".join(f"{x}->{y}" for x, y in sorted(af.attacks)) or "(no attacks)"
    print(f"arguments: {format_set(af.arguments)}    attacks: {atts}\n")

    print(f"  grounded    : {format_set(af.grounded_extension())}")
    print(f"  complete    : {format_sets(af.complete_extensions())}")
    print(f"  preferred   : {format_sets(af.preferred_extensions())}")
    print(f"  stable      : {format_sets(af.stable_extensions())}")
    print(f"  semi-stable : {format_sets(af.semi_stable_extensions())}")

    labs = af.labellings()
    print(f"\n  legal labellings ({len(labs)}):")
    for L in labs:
        print(f"    {L}")

    print("\n  acceptance status (preferred semantics):")
    for a, st in sorted(af.acceptance_statuses().items(), key=lambda kv: str(kv[0])):
        print(f"    {a}: {st}")

    if ex.book_claims:
        print("\n  what the book states (all checked in tests/test_af.py):")
        for claim in ex.book_claims:
            print(f"    - {claim}")

    ok = (
        af.grounded_extension() == ex.grounded
        and set(af.complete_extensions()) == set(ex.complete)
        and set(af.preferred_extensions()) == set(ex.preferred)
        and set(af.stable_extensions()) == set(ex.stable)
        and set(af.semi_stable_extensions()) == set(ex.semi_stable)
        and af.acceptance_statuses() == ex.status
    )
    print(f"\n  matches the expected results: {ok}")


def show_strategic_example(ex) -> None:
    banner(f"{ex.name}")
    print(ex.description)
    atts = ", ".join(f"{x}->{y}" for x, y in sorted(ex.attacks))
    print(f"defeats: {atts}")
    for name, t in zip(AGENT_NAMES, ex.types):
        print(f"  agent {name} owns {format_set(t)}")

    out = mechanism(ex.attacks, ex.types)
    print(f"\n  everybody reveals everything -> outcome {format_set(out)}")
    for name, t, u in zip(AGENT_NAMES, ex.types, utilities(ex.types, out)):
        print(f"    u_{name}(o, {format_set(t)}) = {u}")

    print("\n  best response of each agent when the others reveal everything:")
    for i, name in enumerate(AGENT_NAMES):
        others = {j: ex.types[j] for j in range(3) if j != i}
        br = best_responses(i, ex.types, ex.attacks, others)
        shown = " or ".join(format_set(r) for r in br.reports)
        print(f"    agent {name}: reveal {shown}  (utility {br.utility}; truthful is a best response: {br.truthful_is_best})")

    chk = check_truthful_dominant(ex.types, ex.attacks, find_all=True)
    print(f"\n  Theorem 5.3 check (truth is a best response against every combination): {chk.holds}")
    print(f"    {chk.contexts_checked} situations examined; agents who can gain by hiding: "
          f"{[AGENT_NAMES[i] for i in chk.agents_with_manipulation] or 'none'}")
    if chk.manipulations:
        print(f"    e.g. {chk.manipulations[0]}")
    cond = check_odd_path_condition(ex.types, ex.attacks)
    print(f"  Theorem 5.4 condition (no agent owns two arguments joined by an odd path): {cond.holds}")
    for i, a, b in cond.violations:
        print(f"    agent {AGENT_NAMES[i]}: {a} indirectly defeats {b}")
    print("\n  what the book states (all checked in tests/test_strategic.py):")
    for claim in ex.book_claims:
        print(f"    - {claim}")


def weak_dominance_of_revealing(ex, agent) -> bool:
    """Revealing the whole type is never worse than revealing nothing (all contexts)."""
    mech = GroundedMechanism(ex.attacks)
    others = [j for j in range(3) if j != agent]
    for combo in product(*[subsets(ex.types[j]) for j in others]):
        ctx = frozenset().union(*combo)
        if utility(ex.types[agent], mech.outcome_of_union(ex.types[agent] | ctx)) < utility(
            ex.types[agent], mech.outcome_of_union(ctx)
        ):
            return False
    return True


def strategic_section() -> None:
    banner("Section D - strategic argumentation (grounded direct mechanism)")
    print("Each agent reveals a subset of its arguments; the outcome is the grounded extension of the")
    print("graph induced by the union of the revealed arguments; an agent's utility is the number")
    print("of its own arguments in the outcome.  Agents are x, y, z.")
    show_strategic_example(EXAMPLE_5_10)
    print("\n  for y and z revealing their true types weakly dominates revealing nothing:",
          weak_dominance_of_revealing(EXAMPLE_5_10, 1), weak_dominance_of_revealing(EXAMPLE_5_10, 2))
    r = mechanism(EXAMPLE_5_10.attacks, [{"a4", "a5"}, {"a2"}, {"a3"}])
    print(f"  x withholds a1 -> outcome {format_set(r)} and u_x = {utility(EXAMPLE_5_10.types[0], r)}  (Figure 5.4(b))")

    show_strategic_example(EXAMPLE_5_11)
    without = set(EXAMPLE_5_11.attacks) - {("a6", "a3")}
    print("\n  the role of a6 (it defeats a3, so a3 can no longer pass a2's defeat on to a4 and a5):")
    print(f"    with a6 -> a3:    truth is a best response for everybody: "
          f"{check_truthful_dominant(EXAMPLE_5_11.types, EXAMPLE_5_11.attacks).holds}")
    print(f"    without a6 -> a3: truth is a best response for everybody: "
          f"{check_truthful_dominant(EXAMPLE_5_11.types, without).holds}")


# four strategyproof instances of the default experiment whose Theorem 5.4 condition fails
CASES = [
    (
        "instance 9: a direct defeat inside one agent's own arguments (a swap)",
        Instance(9, 0.05, 6, (frozenset({"a1", "a2", "a3"}), frozenset({"a4", "a5", "a6"}), frozenset()),
                 frozenset({("a5", "a6")})),
        1,
        [{"a4", "a5", "a6"}, {"a4", "a6"}, {"a4", "a5"}],
        "a5 -> a6: hiding a5 frees a6 but loses a5, hiding a6 keeps a5: always 2 accepted, so no gain.",
    ),
    (
        "instance 30: an odd path of length 3 that only swaps a3 for a1",
        Instance(30, 0.05, 6, (frozenset({"a4"}), frozenset({"a1", "a2", "a3", "a6"}), frozenset({"a5"})),
                 frozenset({("a3", "a5"), ("a4", "a1"), ("a5", "a4")})),
        1,
        [{"a1", "a2", "a3", "a6"}, {"a1", "a2", "a6"}, {"a2", "a3", "a6"}],
        "a3 -> a5 -> a4 -> a1: a3 accepted <=> a1 defeated, so hiding a3 trades it for a1.",
    ),
    (
        "instance 1098: the odd path ends in a mutual defeat that stays undecided",
        Instance(1098, 0.1, 6, (frozenset({"a2", "a5"}), frozenset({"a3", "a4"}), frozenset({"a1", "a6"})),
                 frozenset({("a1", "a4"), ("a1", "a5"), ("a2", "a6"), ("a3", "a5"), ("a4", "a1"), ("a5", "a1")})),
        1,
        [{"a3", "a4"}, {"a4"}, {"a3"}],
        "a3 -> a5 -> a1 -> a4, but a4 <-> a1 and a5 <-> a1 are mutual defeats: a4 is undecided either way.",
    ),
    (
        "instance 8: the end of the odd path is defeated whatever happens",
        Instance(8, 0.05, 6, (frozenset({"a3", "a5"}), frozenset({"a2", "a4", "a6"}), frozenset({"a1"})),
                 frozenset({("a1", "a4"), ("a1", "a5"), ("a1", "a6"), ("a2", "a1"), ("a5", "a6")})),
        1,
        [{"a2", "a4", "a6"}, {"a4", "a6"}, {"a2", "a4"}],
        "a2 -> a1 -> a5 -> a6 is odd, but if a1 is out then a5 defeats a6, and if a1 is in it defeats a6 itself.",
    ),
]


def experiment_section() -> None:
    banner("Section E - random experiments")
    print("A short run: attack probabilities 0.1, 0.3, 0.5; 60 instances each, 6-8 arguments,")
    print("3 agents (the full experiment, 7 probabilities x 1000 instances: python experiments.py).\n")
    _, records = run_experiment([0.1, 0.3, 0.5], 60, seed=1, progress=False)
    print(markdown_table(summarise(records)))
    bad = sum(1 for r in records if r["condition_holds"] and not r["strategyproof"])
    print(f"\n  instances where the condition holds but the mechanism is not strategyproof: {bad}")

    print("\nStrategyproof although the Theorem 5.4 condition fails - four instances from the full run:")
    for title, inst, agent, reveals, why in CASES:
        rec = analyse_instance(inst)
        print(f"\n  {title}")
        print(f"    agents own {rec['types']};  defeats: {rec['attacks']}")
        print(f"    odd paths between one agent's arguments: {rec['odd_pairs']};  strategyproof: {rec['strategyproof']}")
        mech = GroundedMechanism(inst.attacks)
        others = frozenset().union(*[t for j, t in enumerate(inst.types) if j != agent])
        for rev in reveals:
            out = mech.outcome_of_union(frozenset(rev) | others)
            print(f"      agent {agent} reveals {format_set(rev):<22} -> outcome {format_set(out):<26} "
                  f"utility {utility(inst.types[agent], out)}")
        print(f"    why: {why}")


def main() -> None:
    walkthrough()
    banner("Section B - example graphs from the book (Chapter 5)")
    for ex in BOOK_EXAMPLES.values():
        show_example(ex)
    banner("Section C - further frameworks (corner cases)")
    for ex in EXTRA_EXAMPLES.values():
        show_example(ex)
    strategic_section()
    experiment_section()


if __name__ == "__main__":
    main()
