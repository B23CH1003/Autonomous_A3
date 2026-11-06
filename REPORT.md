# Report: Argumentation Engine

## 1. Overview

This project implements Dung's abstract argumentation frameworks (AFs) in Python (`af.py`, standard library only), following
the definitions in Chapter 5 ("Argumentation among Agents", I. Rahwan) of *Multiagent Systems*, 2nd ed., G. Weiss (ed.), MIT
Press, 2013. An AF is a pair ⟨A, ⇀⟩ of a finite set of arguments A and a defeat (attack) relation ⇀ ⊆ A × A. The engine
provides conflict-freeness, defence, the characteristic function, admissible and complete sets, the grounded, complete,
preferred, stable and semi-stable extensions, all legal labellings, and the acceptance status of an argument. It is tested on
every example graph of the chapter.

## 2. Definitions used

Let S ⊆ A, S⁺ = {β : α ⇀ β for some α ∈ S}, α⁻ = {β : β ⇀ α}, and range(S) = S ∪ S⁺.

| Notion | Book | Definition |
|---|---|---|
| Argumentation framework | Def. 5.1 | ⟨A, ⇀⟩ with A finite, ⇀ ⊆ A × A |
| Conflict-free | Def. 5.2 | S ∩ S⁺ = ∅ |
| Defended | Def. 5.2 | S defends α iff α⁻ ⊆ S⁺ |
| Characteristic function | Def. 5.3 | F(S) = {α ∈ A : S defends α} |
| Admissible | Def. 5.4 | S conflict-free and S ⊆ F(S) |
| Complete | Def. 5.5 | S conflict-free and S = F(S) |
| Labelling | Def. 5.6 | in ⇔ all defeaters out; out ⇔ some defeater in; undec otherwise |
| Grounded | Def. 5.7 | minimal complete extension = least fixed point of F |
| Preferred | Def. 5.7 | maximal complete extension = maximal admissible set |
| Stable | Def. 5.7 | conflict-free S with S⁺ = A \ S |
| Semi-stable | Def. 5.7 | complete extension with ⊆-maximal range S ∪ S⁺ |
| Argument status | Def. 5.8 | skeptically accepted (in all extensions), credulously accepted (in some), rejected (in none) |

## 3. Design

`ArgumentationFramework(arguments, attacks)` stores the arguments, the attack pairs, and for every argument the set of its
attackers and of its targets. The constructor rejects attacks that mention unknown arguments or that are not pairs. Query
methods validate their inputs and raise `ValueError` for unknown arguments or unknown semantics. All returned sets are
`frozenset`s, so results can be compared, hashed and stored safely.

Every required function is a method, and each is also a module-level function taking the framework as its first argument.

## 4. Algorithms

| Function | Method | Cost |
|---|---|---|
| `is_conflict_free(S)` | check that no member's target set meets S | O(\|S\| · deg) |
| `is_defended(a, S)` | for each attacker b of a, check attackers(b) ∩ S ≠ ∅ | O(deg²) |
| `characteristic(S)` | apply the defence test to every argument | O(\|A\| · deg²) |
| `is_admissible(S)`, `is_complete(S)` | conflict-free test plus S ⊆ F(S) resp. F(S) = S | as above |
| `grounded_extension()` | iterate F from ∅ until it stops changing (at most \|A\| + 1 applications, since F is monotone) | O(\|A\|) applications of F |
| `complete_extensions()` | enumerate all 2ⁿ subsets as bit masks, keep conflict-free S with F(S) = S | O(2ⁿ · n · deg) |
| `preferred_extensions()` | enumerate admissible sets, keep the ⊆-maximal ones | O(2ⁿ) plus a maximality pass |
| `stable_extensions()` | conflict-free S whose range is all of A | O(2ⁿ · n) |
| `semi_stable_extensions()` | among complete extensions keep those with ⊆-maximal range | O(2ⁿ) plus a maximality pass |
| `labellings()` | backtracking over in/out/undec; an argument is checked as soon as it and all its attackers are labelled | worst case 3ⁿ, far less in practice thanks to pruning |
| `acceptance_status(a)` | count the extensions (of the chosen semantics) that contain a | one extension computation |

Subsets are handled as integer bit masks, so conflict-freeness, defence and range are a few bitwise operations. This keeps the
2ⁿ enumeration comfortably fast up to about 18 arguments; 200 random 8-argument graphs, with every semantics and all labellings,
take about 0.15 s in total.

Decisions about details the definitions leave open:

* **Labellings.** `labellings()` returns exactly the labellings of Definition 5.6. As the book notes, their in-sets are precisely
  the complete extensions. `labellings("admissible")` additionally returns the weaker admissible labellings, where only the in
  and out labels have to be justified.
* **Semi-stable.** The book takes the maximum range over *complete* extensions; the literature often takes it over *admissible*
  sets. The engine follows the book, and the tests check on all 2,871 test frameworks that both give the same sets.
* **Acceptance status.** The semantics is a parameter (preferred by default). Under Definition 5.8 a skeptically accepted argument
  is also credulously accepted. The function reports the strongest status that applies, so its three answers are mutually
  exclusive. If a semantics has no extension at all (possible only for stable), every argument is reported as rejected rather
  than vacuously skeptically accepted.

## 5. Results on the book's examples

The book's arguments α1, α2, ... are written a1, a2, ... in the code. Figures 5.4(a), 5.4(b) and 5.5 come from the chapter's
mechanism-design examples (5.10 and 5.11). Here they are used only to check the engine's grounded extension against the
outcomes the book states.

| Figure | Defeats | Grounded | Complete | Preferred | Stable | Semi-stable |
|---|---|---|---|---|---|---|
| 5.1 | a2→a1, a4→a1, a3→a2, a5→a4 | {a1,a3,a5} | {a1,a3,a5} | {a1,a3,a5} | {a1,a3,a5} | {a1,a3,a5} |
| 5.2 | a1⇄a2 (a3 isolated) | {a3} | {a3}, {a1,a3}, {a2,a3} | {a1,a3}, {a2,a3} | {a1,a3}, {a2,a3} | {a1,a3}, {a2,a3} |
| 5.3(i) | b→a, c→b, d→b, c⇄d, e→d | {a,c,e} | {a,c,e} | {a,c,e} | {a,c,e} | {a,c,e} |
| 5.4(a) | a1→a2, a2→a3, a3→a4, a3→a5 | {a1,a3} | {a1,a3} | {a1,a3} | {a1,a3} | {a1,a3} |
| 5.4(b) | a2→a3, a3→a4, a3→a5 | {a2,a4,a5} | {a2,a4,a5} | {a2,a4,a5} | {a2,a4,a5} | {a2,a4,a5} |
| 5.5 | Fig. 5.4(a) + a6→a3 | {a1,a4,a5,a6} | {a1,a4,a5,a6} | {a1,a4,a5,a6} | {a1,a4,a5,a6} | {a1,a4,a5,a6} |

Every statement the book makes about these graphs is reproduced exactly:

| Book statement | Engine |
|---|---|
| {α3, α5} defends α1 (after Def. 5.2) | `is_defended("a1", {"a3","a5"})` = True |
| Ex. 5.5: ∅, {α3}, {α5}, {α3, α5}, {α1, α3, α5} are admissible | all True, and these are the only admissible sets |
| Ex. 5.6: {α3, α5} is not complete; F({α3}) = F({α5}) = {α3, α5}; {α1, α3, α5} is the only complete extension | reproduced |
| Section 3: F¹(∅) = {α3, α5}, F²(∅) = {α1, α3, α5} = F³(∅) | reproduced (see the demo output) |
| Ex. 5.7: complete extensions {α3}, {α1, α3}, {α2, α3} | reproduced |
| Fig. 5.2: labellings L^G, L1, L2 | exactly these three labellings |
| Grounded extension of Fig. 5.2 is {α3} | reproduced |
| Ex. 5.8: Fig. 5.1 has one preferred extension {α1, α3, α5}; Fig. 5.2 has {α1, α3} and {α2, α3} | reproduced |
| Fig. 5.3(iii): PRO has a winning strategy for a | a is in the grounded extension |
| Ex. 5.10: outcome {α1, α3}; with α1 withheld, {α2, α4, α5} | reproduced |
| Ex. 5.11: outcome {α1, α4, α5, α6} | reproduced |

Labellings of Figure 5.2 (as printed by the demo):

```
in={a3}     out={}    undec={a1, a2}     (L^G)
in={a1, a3} out={a2}  undec={}           (L1)
in={a2, a3} out={a1}  undec={}           (L2)
```

Acceptance status under preferred semantics:

| Figure | skeptically accepted | credulously accepted | rejected |
|---|---|---|---|
| 5.1 | a1, a3, a5 | none | a2, a4 |
| 5.2 | a3 | a1, a2 | none |
| 5.3(i) | a, c, e | none | b, d |
| 5.4(a) | a1, a3 | none | a2, a4, a5 |
| 5.4(b) | a2, a4, a5 | none | a3 |
| 5.5 | a1, a4, a5, a6 | none | a2, a3 |

Most of the book's graphs are acyclic or have a single even cycle, so all semantics coincide or nearly do. To show where the
semantics differ, eight further frameworks are included:

| Example | Defeats | Grounded | Complete | Preferred | Stable | Semi-stable |
|---|---|---|---|---|---|---|
| mutual_attack | a⇄b | ∅ | ∅, {a}, {b} | {a}, {b} | {a}, {b} | {a}, {b} |
| chain | a→b→c | {a,c} | {a,c} | {a,c} | {a,c} | {a,c} |
| odd_cycle | a→b→c→a | ∅ | ∅ | ∅ | none | ∅ |
| even_cycle | a→b→c→d→a | ∅ | ∅, {a,c}, {b,d} | {a,c}, {b,d} | {a,c}, {b,d} | {a,c}, {b,d} |
| self_attack_defended | c→a, a→a, a→b | {b,c} | {b,c} | {b,c} | {b,c} | {b,c} |
| diamond | a⇄b, a→c, b→c | ∅ | ∅, {a}, {b} | {a}, {b} | {a}, {b} | {a}, {b} |
| preferred_not_semi_stable | a⇄b, b→c, c→d, d→e, e→c | ∅ | ∅, {a}, {b,d} | {a}, {b,d} | {b,d} | {b,d} |
| no_stable_but_semi_stable | a⇄b, c→c | ∅ | ∅, {a}, {b} | {a}, {b} | none | {a}, {b} |

* **odd_cycle**: the only labelling puts everything undec, and there is no stable extension ("stable extensions may not always
  exist").
* **preferred_not_semi_stable**: {a} is preferred, but its range {a, b} is strictly smaller than the range of {b, d}, which is all
  of A. So only {b, d} is semi-stable. Under semi-stable semantics a is therefore rejected, while under preferred semantics it is
  credulously accepted, which shows that the choice of semantics matters.
* **no_stable_but_semi_stable**: only c attacks c, so no conflict-free set can attack it and there is no stable extension.
  Semi-stable extensions still exist, as they always do in finite frameworks.

`demo_output.txt` contains the complete printout, including every labelling and acceptance status.

## 6. Testing

`tests/test_af.py` contains 38 tests.

1. **Hand-worked unit tests.** Each basic notion is checked on a small chain, for example F(∅) = {a}, F({a}) = {a, c}, and {c} is
   not admissible. Self-attack, mutual attack, the empty framework, input validation, non-string arguments and immutability of
   results are also covered.
2. **The book's examples** (`TestBookChapter5`). Every statement in the table of Section 5 is asserted literally. In addition,
   every book and extra example is checked against its full expected results for every semantics, the acceptance status of each
   argument, and the number and content of its labellings.
3. **Cross-checks against an independent oracle.** A naive implementation written straight from the definitions on raw tuples
   (it shares no code with `af.py`) is compared with the engine on every subset of every framework. The tests also check:
   * the grounded extension is complete, is the least complete extension, and equals the intersection of all complete
     extensions;
   * stable ⊆ semi-stable ⊆ preferred ⊆ complete; preferred and semi-stable extensions always exist; if a stable extension
     exists, semi-stable = stable;
   * all of Table 5.1: the in-sets of the labellings are exactly the complete extensions, and out = S⁺. Grounded = minimal in =
     minimal out = maximal undec; preferred = maximal in = maximal out; semi-stable = minimal undec; stable = empty undec;
   * the book's semi-stable definition (over complete extensions) equals the admissible-based one;
   * the in-sets of admissible labellings are exactly the admissible sets;
   * the acceptance status agrees with the preferred extensions.

   These checks run on **all 531 frameworks** with 0-3 arguments (1 + 2 + 16 + 512) and on **2,340 random frameworks** (1,500
   with 4 arguments, 600 with 5 and 240 with 6-7), all with fixed seeds.

All 38 tests pass in about 8 seconds, under both `unittest` and `pytest`.

One test initially failed because my expectation was wrong, not because of an engine bug. For a self-attacking argument a, the
set {a} *does* defend a under Definition 5.2, since it attacks a's only attacker (a itself). But {a} is not conflict-free and
therefore not admissible. The test was corrected to say exactly that.

## 7. Limitations

* Extension enumeration is exponential in the number of arguments. That is unavoidable for these problems in general and is fine
  for the sizes used here.
* Only the semantics asked for are implemented (no ideal, eager or CF2 semantics, and no ranking-based acceptance).
