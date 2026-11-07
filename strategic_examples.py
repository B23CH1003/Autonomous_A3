"""
strategic_examples.py -- the strategic-argumentation examples of Chapter 5.

Examples 5.10 and 5.11 of Weiss (ed.), Multiagent Systems, 2nd ed. (Figures 5.4
and 5.5).  The book's argument alpha_i is written "a<i>"; agents x, y, z are
agents 0, 1, 2.

Two misprints of the book are corrected here:

* Example 5.10 prints u_y(o, {a3}) = 1 and u_z(o, {a2}) = 0, i.e. with the
  agents' argument sets swapped.  Agent y owns {a2} and agent z owns {a3}, so
  the correct values are u_y(o, {a2}) = 0 and u_z(o, {a3}) = 1.
* The discussion after Example 5.11 says that a5 cancels out the effect of the
  indirect self-defeat among x's arguments.  The argument that does so is a6,
  which defeats a3.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

AGENT_NAMES = ("x", "y", "z")


@dataclass(frozen=True)
class StrategicExample:
    name: str
    description: str
    types: Tuple[frozenset, ...]  # A_x, A_y, A_z
    attacks: frozenset
    truthful_outcome: frozenset
    truthful_utilities: Tuple[int, ...]
    strategyproof: bool  # does revealing everything dominate for every agent?
    odd_path_condition: bool  # Theorem 5.4 condition
    book_claims: Tuple[str, ...] = ()


_R_5_10 = frozenset({("a1", "a2"), ("a2", "a3"), ("a3", "a4"), ("a3", "a5")})

EXAMPLE_5_10 = StrategicExample(
    name="example_5_10",
    description=(
        "Example 5.10 / Figure 5.4: hiding an argument is beneficial.  x owns "
        "{a1, a4, a5}, y owns {a2}, z owns {a3}; a1 -> a2 -> a3 -> a4, a3 -> a5."
    ),
    types=(frozenset({"a1", "a4", "a5"}), frozenset({"a2"}), frozenset({"a3"})),
    attacks=_R_5_10,
    truthful_outcome=frozenset({"a1", "a3"}),
    truthful_utilities=(1, 0, 1),  # u_x = 1, u_y = 0, u_z = 1 (misprint corrected)
    strategyproof=False,
    odd_path_condition=False,
    book_claims=(
        "full revelation gives the outcome o = {a1, a3}",
        "u_x(o, {a1, a4, a5}) = 1; u_y(o, {a2}) = 0; u_z(o, {a3}) = 1 (book prints y and z swapped)",
        "for y and z, revealing their true types weakly dominates revealing nothing",
        "x is better off revealing {a4, a5}: the outcome becomes {a2, a4, a5} and u_x = 2",
        "so the mechanism is not strategyproof",
    ),
)

EXAMPLE_5_11 = StrategicExample(
    name="example_5_11",
    description=(
        "Example 5.11 / Figure 5.5: Example 5.10 plus argument a6 owned by x, with "
        "a6 -> a3.  Truth revelation is a dominant strategy for x although a1 "
        "indirectly defeats a4 and a5."
    ),
    types=(frozenset({"a1", "a4", "a5", "a6"}), frozenset({"a2"}), frozenset({"a3"})),
    attacks=_R_5_10 | {("a6", "a3")},
    truthful_outcome=frozenset({"a1", "a4", "a5", "a6"}),
    truthful_utilities=(4, 0, 0),
    strategyproof=True,
    odd_path_condition=False,
    book_claims=(
        "full revelation gives the outcome o = {a1, a4, a5, a6}",
        "truth revelation is a dominant strategy for x (all of its arguments are accepted)",
        "this holds although a1 indirectly defeats a4 and a5",
        "the argument that cancels the indirect self-defeat is a6 (book prints a5)",
    ),
)

STRATEGIC_EXAMPLES: Dict[str, StrategicExample] = {
    EXAMPLE_5_10.name: EXAMPLE_5_10,
    EXAMPLE_5_11.name: EXAMPLE_5_11,
}
