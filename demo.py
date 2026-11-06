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
Section D  the grounded direct mechanism and Theorem 5.4 condition.

Book: G. Weiss (ed.), Multiagent Systems, 2nd ed., MIT Press 2013, Chapter 5.
The argument alpha_i of the book is written a<i>.
Output of a full run is saved in demo_output.txt.
"""

from af import ArgumentationFramework, format_set, format_sets
from examples import BOOK_EXAMPLES, EXTRA_EXAMPLES
from strategic import grounded_mechanism, is_strategyproof, theorem_5_4_condition


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


def main() -> None:
    walkthrough()
    banner("Section B - example graphs from the book (Chapter 5)")
    for ex in BOOK_EXAMPLES.values():
        show_example(ex)
    banner("Section C - further frameworks (corner cases)")
    for ex in EXTRA_EXAMPLES.values():
        show_example(ex)
    banner("Section D - strategic argumentation")
    attacks = [("a1", "a2"), ("a2", "a3"), ("a3", "a4")]
    reports = {"agent1": {"a1", "a2"}, "agent2": {"a3", "a4"}}
    print(f"reports: {reports}")
    print(f"grounded direct-mechanism outcome: {format_set(grounded_mechanism(attacks, reports))}")
    print(f"Theorem 5.4 condition holds: {theorem_5_4_condition(reports, attacks)}")
    print(f"mechanism is strategyproof: {is_strategyproof(reports, attacks)}")


if __name__ == "__main__":
    main()
