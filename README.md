# Argumentation Engine and Strategic Argumentation

A dependency-free Python implementation of Dung-style abstract argumentation frameworks, and of the *grounded direct
argumentation mechanism* that studies when agents gain by hiding arguments. It follows Chapter 5 ("Argumentation among
Agents", I. Rahwan) of *Multiagent Systems*, 2nd ed., G. Weiss (ed.), MIT Press, 2013.

The engine (`af.py`) computes conflict-free, admissible and complete sets, the grounded, complete, preferred, stable and
semi-stable extensions, all legal labellings and the acceptance status of an argument. The strategic module (`strategic.py`)
builds on it: the mechanism, best responses, and exhaustive checks of Theorems 5.3 and 5.4. `experiments.py` runs random
experiments on thousands of instances.

* Python 3.9+, **standard library only** (`matplotlib` is needed only by `plot_results.py`, `pytest` is optional).
* Everything is deterministic: all random experiments use fixed seeds.

## Repository layout

| File | Purpose |
|---|---|
| `af.py` | The argumentation engine: `ArgumentationFramework` class and every function listed below |
| `strategic.py` | Grounded direct mechanism, best responses, Theorem 5.3 check, Theorem 5.4 (odd-path) check |
| `examples.py` | The book's example graphs (Figures 5.1-5.5) and eight further frameworks, with expected results |
| `strategic_examples.py` | Examples 5.10 and 5.11 (Figures 5.4, 5.5) with the two misprint corrections |
| `experiments.py` | Random experiments, summaries and result files |
| `plot_results.py` | Draws `results/fraction_strategyproof.png` |
| `demo.py`, `demo_output.txt` | Demonstration (engine, book examples, strategic examples, a short experiment) and its saved output |
| `results/` | Output of the full experiment: `instances.csv`, `summary_by_p.csv`, `summary.md`, the two lists of special instances, the figure; `results/with_self_attacks/` is the same with self-attacking arguments allowed |
| `tests/` | 115 tests (`test_af.py`, `test_strategic.py`, `test_experiments.py`) |
| `REPORT.md` | Report: definitions, design, algorithms, results, analysis of the experiments, testing |

## Quick start

```python
from af import ArgumentationFramework

# Figure 5.1 of the book (alpha_i written a<i>): arguments and (attacker, target) pairs
af = ArgumentationFramework(["a1", "a2", "a3", "a4", "a5"],
                            [("a2", "a1"), ("a4", "a1"), ("a3", "a2"), ("a5", "a4")])

af.is_conflict_free({"a1", "a3", "a5"})   # True
af.is_defended("a1", {"a3", "a5"})        # True   ("{a3, a5} defends a1")
af.characteristic({"a3"})                 # frozenset({'a3', 'a5'})            F(S), Example 5.6
af.is_admissible({"a3", "a5"})            # True                                Example 5.5
af.is_complete({"a3", "a5"})              # False  (it defends a1 but omits it)  Example 5.6

af.grounded_extension()                   # frozenset({'a1', 'a3', 'a5'})
af.complete_extensions()                  # [frozenset({'a1', 'a3', 'a5'})]
af.preferred_extensions()
af.stable_extensions()
af.semi_stable_extensions()
af.all_extensions()                       # dict: grounded / complete / preferred / stable / semi-stable
af.labellings()                           # every legal in/out/undec labelling
af.acceptance_status("a1")                # 'skeptically accepted'
af.acceptance_status("a1", "grounded")    # any semantics can be chosen
```

Arguments can be any hashable objects. Every method is also available as a plain function taking the framework first, e.g.
`from af import is_conflict_free; is_conflict_free(af, S)`.

### Strategic argumentation

```python
from strategic import (mechanism, best_responses, check_truthful_dominant,
                       check_odd_path_condition, utilities)

# Example 5.10: agents x, y, z own {a1,a4,a5}, {a2}, {a3}
types   = [{"a1", "a4", "a5"}, {"a2"}, {"a3"}]
attacks = {("a1", "a2"), ("a2", "a3"), ("a3", "a4"), ("a3", "a5")}

o = mechanism(attacks, types)                          # frozenset({'a1', 'a3'})
utilities(types, o)                                    # [1, 0, 1]

best_responses(0, types, attacks, {1: {"a2"}, 2: {"a3"}})
#   BestResponses(utility=2, reports=[frozenset({'a4', 'a5'})], truthful_is_best=False)

check_truthful_dominant(types, attacks).holds          # False  (Theorem 5.3: x gains by hiding a1)
check_odd_path_condition(types, attacks).violations    # [(0, 'a1', 'a4'), (0, 'a1', 'a5')]  (Theorem 5.4)
```

## Feature map

| Task | Where |
|---|---|
| Framework class ⟨A, ⇀⟩ | `ArgumentationFramework(arguments, attacks)` (Definition 5.1; validates that attacks only mention known arguments) |
| Conflict-free test | `is_conflict_free(S)` (Definition 5.2) |
| Is an argument defended by S | `is_defended(a, S)` (Definition 5.2) |
| Characteristic function | `characteristic(S)` -> F(S) (Definition 5.3) |
| Admissible / complete | `is_admissible(S)`, `is_complete(S)` (Definitions 5.4, 5.5) |
| Grounded extension | `grounded_extension()` (iterates F from the empty set to its fixed point) |
| All complete extensions | `complete_extensions()` |
| Preferred, stable, semi-stable | `preferred_extensions()`, `stable_extensions()`, `semi_stable_extensions()`, `all_extensions()` (Definition 5.7) |
| All legal labellings | `labellings()` (Definition 5.6; returns `Labelling(in_, out, undec)` tuples) |
| Acceptance status | `acceptance_status(a, semantics="preferred")`, `acceptance_statuses()` (Definition 5.8) |
| The mechanism | `strategic.mechanism(attacks, reports)` (Definition 5.21): grounded extension of the graph induced by the union of the reports |
| Best responses | `strategic.best_responses(agent, types, attacks, others_reports)`: every subset the agent could reveal, and those maximising its utility |
| Theorem 5.3 | `strategic.check_truthful_dominant(types, attacks)`: revealing everything is a best response for every agent against every combination of the others' subsets (returns the profitable deviations if there are any) |
| Theorem 5.4 | `strategic.check_odd_path_condition(types, attacks)`: no agent owns two arguments joined by an odd-length directed path; breadth-first search over (argument, parity) states, so cycles are handled |
| Experiments | `python experiments.py` |
| Book examples | `examples.py`, `strategic_examples.py`; asserted in `tests/` |

## Conventions worth knowing

* The book calls ⇀ a *defeat* relation; the code calls it *attacks*. They are the same thing.
* **Sets** are returned as `frozenset`; lists of sets come back in a deterministic order (by size, then alphabetically).
* **Defence** (Def. 5.2): `a` is defended by `S` when every attacker of `a` is attacked by a member of `S`. `a` need not be in `S`;
  unattacked arguments are defended by every set.
* **Legal labelling** (Def. 5.6): *in* iff all attackers are *out*; *out* iff some attacker is *in*; *undec* otherwise. These
  correspond one-to-one with the complete extensions (in = S, out = S⁺, undec = the rest). `labellings("admissible")` also
  returns the weaker admissible labellings.
* **Semi-stable** (Def. 5.7): complete extensions whose range S ∪ S⁺ is inclusion-maximal (the tests confirm this equals the
  admissible-based definition).
* **Acceptance status** (Def. 5.8) is computed for a chosen semantics, preferred by default, and reports the strongest status that
  applies: *skeptically accepted* = in every extension, *credulously accepted* = in some but not all, *rejected* = in none (also
  when a semantics has no extension at all, which only happens for stable).
* **Strategic setting.** `types[i]` is the set A_i of agent i, `reports[i]` what it reveals (always a subset of A_i; agents can hide
  arguments but not invent them). The utility is the number of the agent's own arguments in the outcome (Def. 5.22).
  Attacks whose ends are not both revealed are dropped (the induced graph).
* **Theorem 5.4 condition.** "Odd-length path" is decided on *walks* (arguments may repeat); this is the reading for which the
  theorem can be proved (see `REPORT.md`). Only two *different* arguments of one agent count; `mode="simple"` and
  `include_same=True` select the other readings, and the experiments show all four give the same verdicts on the strategyproofness question.
* **Size limit**: the extension functions enumerate all 2^n subsets with bit masks (comfortable up to about 18 arguments); the
  strategy checks examine about m·2^n situations for m agents and n arguments.

## Running

```bash
python demo.py                                   # demonstration (writes to stdout)
python -m unittest discover -s tests -t . -v     # all tests (about 11 s); `pytest` works too
python experiments.py                            # 7 values of p x 1000 instances -> results/  (about 20 s)
python experiments.py --instances 200 --p 0.2 0.4 --no-files          # a quick look
python experiments.py --self-attacks --seed 2025 --outdir results/with_self_attacks
python plot_results.py                           # results/fraction_strategyproof.png (needs matplotlib)
```

To reproduce the committed results exactly, use the default seed (2024) for `results/` and `--self-attacks --seed 2025` for
`results/with_self_attacks/`. `tests/test_experiments.py` checks that the committed files are consistent with each other and with
a fresh analysis of a sample of their instances.

## Experiment in one paragraph

3 agents, 6-8 arguments, every possible attack present with probability p, arguments dealt at random to the agents; for each p in
{0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6}, 1000 instances. For each instance the mechanism is checked exhaustively for
strategyproofness (Theorem 5.3) and the odd-path condition (Theorem 5.4) is evaluated. The fraction of strategyproof instances
falls from 0.94 (p = 0.05) to 0.015 (p = 0.6); the condition never holds without the mechanism being strategyproof (0 of 795
instances), while 1692 instances are strategyproof although the condition fails. `REPORT.md` explains these instances.

## Using the engine from other code

```python
from af import ArgumentationFramework
af = ArgumentationFramework(revealed_arguments, attacks_restricted_to_revealed)
grounded = af.grounded_extension()
```
