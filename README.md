# Argumentation Engine

A small, dependency-free Python implementation of Dung-style abstract argumentation frameworks, following the definitions of
Chapter 5 ("Argumentation among Agents", I. Rahwan) of *Multiagent Systems*, 2nd ed., G. Weiss (ed.), MIT Press, 2013. It can
also be used as a building block by other code, for example a strategic-argumentation mechanism that needs the framework class
and the grounded extension.

* Python 3.9+, **standard library only** (no installation step).
* `pytest` is optional; the tests also run with `unittest`.

## Repository layout

| File | Purpose |
|---|---|
| `af.py` | The engine: `ArgumentationFramework` class and every function listed below |
| `examples.py` | The book's example graphs (Figures 5.1-5.5) and eight further frameworks, with expected results |
| `demo.py` | Demonstration: walk-through on Figure 5.1, then extensions, labellings and acceptance statuses for every example |
| `demo_output.txt` | Saved output of `python demo.py` |
| `tests/test_af.py` | 38 tests: unit tests, every statement the book makes about its figures, cross-checks against a naive oracle |
| `REPORT.md` | Report: definitions, design, algorithms, results on the book's examples, testing |

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

Arguments can be any hashable objects (strings, ints, ...). Every method is also available as a plain function taking the
framework first, e.g. `from af import is_conflict_free; is_conflict_free(af, S)`.

## Feature map

| Task | Where |
|---|---|
| 1. Framework class ⟨A, ⇀⟩ | `ArgumentationFramework(arguments, attacks)` (Definition 5.1; validates that attacks only mention known arguments) |
| 2. Conflict-free test | `is_conflict_free(S)` (Definition 5.2) |
| 3. Is an argument defended by S | `is_defended(a, S)` (Definition 5.2) |
| 4. Characteristic function | `characteristic(S)` -> F(S) (Definition 5.3) |
| 5. Admissible / complete | `is_admissible(S)`, `is_complete(S)` (Definitions 5.4, 5.5) |
| 6A. Grounded extension | `grounded_extension()` (iterates F from the empty set to its fixed point) |
| 6B. All complete extensions | `complete_extensions()` |
| 6C. Preferred, stable, semi-stable | `preferred_extensions()`, `stable_extensions()`, `semi_stable_extensions()`, `all_extensions()` (Definition 5.7) |
| 6D. All legal labellings | `labellings()` (Definition 5.6; returns `Labelling(in_, out, undec)` tuples) |
| 6E. Acceptance status | `acceptance_status(a, semantics="preferred")`, `acceptance_statuses()` (Definition 5.8) |
| Tests on the book's examples | `examples.py` (`BOOK_EXAMPLES`) and `TestBookChapter5` in `tests/test_af.py` |

## Conventions worth knowing

* The book calls ⇀ a *defeat* relation; the code calls it *attacks*. They are the same thing.
* **Sets** are returned as `frozenset`; lists of sets come back in a deterministic order (by size, then alphabetically).
* **Defence** (Def. 5.2): `a` is defended by `S` when every attacker of `a` is attacked by a member of `S` (α⁻ ⊆ S⁺). `a` need
  not be in `S`; unattacked arguments are defended by every set.
* **Legal labelling** (Def. 5.6): *in* iff all attackers are *out*; *out* iff some attacker is *in*; *undec* otherwise. These
  correspond one-to-one with the complete extensions (in = S, out = S⁺, undec = the rest), and Table 5.1's correspondences
  (grounded, preferred, stable, semi-stable) are checked in the tests. `labellings("admissible")` additionally returns the weaker
  admissible labellings.
* **Semi-stable** (Def. 5.7): complete extensions whose range S ∪ S⁺ is inclusion-maximal. The tests confirm this gives the same
  sets as the other common definition (maximal range among admissible sets).
* **Acceptance status** (Def. 5.8) is computed for a chosen semantics, preferred by default. In the book a skeptically accepted
  argument is also credulously accepted; `acceptance_status` reports the strongest status, so the three answers are mutually
  exclusive: *skeptically accepted* = in every extension, *credulously accepted* = in some but not all, *rejected* = in none. If a
  semantics has no extension at all (only possible for stable), the argument is reported as *rejected*.
* **Size limit**: complete/preferred/stable/semi-stable enumerate all 2^n subsets with bit masks, which is comfortable up to about
  18 arguments (graphs with 6-8 arguments take well under a millisecond). `labellings()` uses pruned backtracking.

## Running

```bash
python demo.py                                   # demonstration (writes to stdout)
python -m unittest discover -s tests -t . -v     # tests, standard library
pytest                                           # tests, if pytest is installed
```

## Tests and validation

`tests/test_af.py` checks the engine in four layers:

1. hand-worked unit tests of each basic notion;
2. **the book's examples**: every statement Chapter 5 makes about Figures 5.1, 5.2, 5.3, 5.4 and 5.5 (Examples 5.5-5.11 and the
   grounded-extension iteration), plus the full expected results for every semantics;
3. eight further frameworks for corner cases the figures do not cover (odd cycles, self-attack, no stable extension, a preferred
   extension that is not semi-stable);
4. cross-checks of every extension against an independent naive oracle written straight from the definitions, plus all of
   Table 5.1's extension/labelling correspondences, on **all 531 frameworks with 0-3 arguments** and **2,340 random frameworks
   with 4-7 arguments**.

See `REPORT.md` for details.

## Using it from other code

```python
from af import ArgumentationFramework
af = ArgumentationFramework(revealed_arguments, attacks_restricted_to_revealed)
grounded = af.grounded_extension()
```
