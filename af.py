"""
af.py -- a small engine for Dung-style abstract argumentation frameworks.

An argumentation framework (AF) is a pair <A, ->> where A is a finite set of
arguments and ->  is a binary "attacks" relation on A.  This module provides

    * the ArgumentationFramework class (construction + validation),
    * conflict-freeness, defence, the characteristic function F,
      admissible and complete sets,
    * grounded / complete / preferred / stable / semi-stable extensions,
    * all legal (in / out / undec) labellings,
    * acceptance status of an argument (skeptical / credulous / rejected).

Conventions
-----------
* Arguments may be any hashable objects (strings are typical).
* Attacks are (attacker, target) pairs.
* Sets of arguments are returned as ``frozenset`` objects; lists of sets are
  returned in a deterministic order (by size, then alphabetically).
* Everything that has to look at *all* candidate sets (complete, preferred,
  stable, semi-stable) enumerates the 2^n subsets of A using bit masks.  That
  is fine up to roughly 18 arguments, which is far more than needed for the
  examples and for the strategic-argumentation experiments (6-8 arguments).

Every public method is also exposed as a plain module-level function taking
the framework as its first argument, e.g. ``is_conflict_free(af, S)``.
"""

from __future__ import annotations

from typing import (
    Dict,
    FrozenSet,
    Hashable,
    Iterable,
    List,
    NamedTuple,
    Tuple,
)

Argument = Hashable
ArgSet = FrozenSet[Argument]

# Labels of a labelling.
IN, OUT, UNDEC = "in", "out", "undec"

# Acceptance statuses.
SKEPTICAL = "skeptically accepted"
CREDULOUS = "credulously accepted"
REJECTED = "rejected"

SEMANTICS = ("grounded", "complete", "preferred", "stable", "semi-stable")

__all__ = [
    "ArgumentationFramework",
    "Labelling",
    "IN",
    "OUT",
    "UNDEC",
    "SKEPTICAL",
    "CREDULOUS",
    "REJECTED",
    "SEMANTICS",
    "format_set",
    "format_sets",
    "is_conflict_free",
    "is_defended",
    "characteristic",
    "is_admissible",
    "is_complete",
    "grounded_extension",
    "complete_extensions",
    "preferred_extensions",
    "stable_extensions",
    "semi_stable_extensions",
    "all_extensions",
    "labellings",
    "acceptance_status",
]


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def _set_key(S: Iterable[Argument]) -> Tuple[str, ...]:
    return tuple(sorted(str(a) for a in S))


def _sort_sets(sets: Iterable[ArgSet]) -> List[ArgSet]:
    """Deterministic order: smaller sets first, then alphabetical."""
    return sorted(sets, key=lambda S: (len(S), _set_key(S)))


def format_set(S: Iterable[Argument]) -> str:
    """'{a, b}' with the members in alphabetical order ('{}' if empty)."""
    return "{" + ", ".join(_set_key(S)) + "}"


def format_sets(sets: Iterable[ArgSet]) -> str:
    """'{a}, {b, c}' ... or 'none' for an empty collection."""
    sets = list(sets)
    return ", ".join(format_set(S) for S in sets) if sets else "none"


def _popcount(m: int) -> int:
    return bin(m).count("1")


def _maximal(masks: Iterable[int]) -> List[int]:
    """Inclusion-maximal elements of a collection of bit masks."""
    kept: List[int] = []
    for m in sorted(set(masks), key=_popcount, reverse=True):
        if not any(m & ~k == 0 for k in kept):  # m is a subset of a kept mask
            kept.append(m)
    return kept


class Labelling(NamedTuple):
    """A labelling of the arguments into in / out / undec."""

    in_: ArgSet
    out: ArgSet
    undec: ArgSet

    def as_dict(self) -> Dict[Argument, str]:
        d: Dict[Argument, str] = {}
        for a in self.in_:
            d[a] = IN
        for a in self.out:
            d[a] = OUT
        for a in self.undec:
            d[a] = UNDEC
        return d

    def __str__(self) -> str:
        return (
            f"in={format_set(self.in_)} out={format_set(self.out)} "
            f"undec={format_set(self.undec)}"
        )


def _labelling_key(L: Labelling):
    return (
        len(L.in_),
        _set_key(L.in_),
        len(L.out),
        _set_key(L.out),
    )


# --------------------------------------------------------------------------
# the framework
# --------------------------------------------------------------------------
class ArgumentationFramework:
    """An abstract argumentation framework <A, ->>.

    Parameters
    ----------
    arguments : iterable of hashable
        The arguments A.  Duplicates are ignored.  (A string such as "abc"
        is treated as the three arguments 'a', 'b', 'c'.)
    attacks : iterable of (attacker, target) pairs
        The attack relation.  Both ends must be members of ``arguments``;
        otherwise ``ValueError`` is raised.  Self-attacks are allowed.

    The object is treated as immutable after construction.
    """

    def __init__(self, arguments: Iterable[Argument], attacks: Iterable[Tuple[Argument, Argument]] = ()):
        args = tuple(dict.fromkeys(arguments))  # ordered, de-duplicated
        arg_set = frozenset(args)

        attackers: Dict[Argument, set] = {a: set() for a in args}
        targets: Dict[Argument, set] = {a: set() for a in args}
        pairs = set()
        for pair in attacks:
            try:
                x, y = pair
            except (TypeError, ValueError):
                raise ValueError(f"attack {pair!r} is not an (attacker, target) pair") from None
            if x not in arg_set or y not in arg_set:
                unknown = [z for z in (x, y) if z not in arg_set]
                raise ValueError(f"attack {pair!r} mentions unknown argument(s) {unknown!r}")
            pairs.add((x, y))
            attackers[y].add(x)
            targets[x].add(y)

        self._args: Tuple[Argument, ...] = args
        self.arguments: ArgSet = arg_set
        self.attacks: FrozenSet[Tuple[Argument, Argument]] = frozenset(pairs)
        self._attackers: Dict[Argument, ArgSet] = {a: frozenset(s) for a, s in attackers.items()}
        self._targets: Dict[Argument, ArgSet] = {a: frozenset(s) for a, s in targets.items()}

        # bit-mask view used by the enumeration routines
        self._n = len(args)
        self._index = {a: i for i, a in enumerate(args)}
        self._full = (1 << self._n) - 1
        self._att_idx: List[List[int]] = [
            sorted(self._index[x] for x in self._attackers[a]) for a in args
        ]
        self._att_mask: List[int] = [self._mask(self._attackers[a]) for a in args]
        self._tgt_mask: List[int] = [self._mask(self._targets[a]) for a in args]
        self._admissible_cache: List[int] | None = None

    # ------------------------------------------------------------------ misc
    def __repr__(self) -> str:
        args = sorted(self.arguments, key=str)
        atts = sorted(self.attacks, key=lambda p: (str(p[0]), str(p[1])))
        return f"ArgumentationFramework(arguments={args!r}, attacks={atts!r})"

    def __len__(self) -> int:
        return self._n

    def _check_arg(self, a: Argument) -> None:
        if a not in self.arguments:
            raise ValueError(f"unknown argument {a!r}")

    def _as_set(self, S: Iterable[Argument]) -> ArgSet:
        S = frozenset(S)
        unknown = S - self.arguments
        if unknown:
            raise ValueError(f"unknown argument(s) {sorted(unknown, key=str)!r}")
        return S

    def _mask(self, S: Iterable[Argument]) -> int:
        m = 0
        for a in S:
            m |= 1 << self._index[a]
        return m

    def _from_mask(self, m: int) -> ArgSet:
        return frozenset(self._args[i] for i in range(self._n) if (m >> i) & 1)

    # ------------------------------------------------------- basic structure
    def attackers(self, a: Argument) -> ArgSet:
        """The arguments that attack ``a``."""
        self._check_arg(a)
        return self._attackers[a]

    def targets(self, a: Argument) -> ArgSet:
        """The arguments that ``a`` attacks."""
        self._check_arg(a)
        return self._targets[a]

    def attacked_by_set(self, S: Iterable[Argument]) -> ArgSet:
        """S+ : every argument attacked by some member of S."""
        S = self._as_set(S)
        out = set()
        for a in S:
            out |= self._targets[a]
        return frozenset(out)

    def range(self, S: Iterable[Argument]) -> ArgSet:
        """The range of S, i.e. S together with S+ (used by semi-stable semantics)."""
        S = self._as_set(S)
        return S | self.attacked_by_set(S)

    # ---------------------------------------------- 2. conflict-freeness
    def is_conflict_free(self, S: Iterable[Argument]) -> bool:
        """True iff no member of S attacks a member of S."""
        S = self._as_set(S)
        return not any(self._targets[a] & S for a in S)

    # ------------------------------------------------------- 3. defence
    def is_defended(self, a: Argument, S: Iterable[Argument]) -> bool:
        """True iff ``a`` is defended by (acceptable w.r.t.) S.

        That is: every attacker of ``a`` is itself attacked by some member
        of S.  An argument without attackers is defended by every set,
        including the empty one.  ``a`` need not be a member of S.
        """
        self._check_arg(a)
        S = self._as_set(S)
        return all(self._attackers[b] & S for b in self._attackers[a])

    # --------------------------------------- 4. characteristic function F
    def characteristic(self, S: Iterable[Argument]) -> ArgSet:
        """F(S) = { a in A : a is defended by S }."""
        S = self._as_set(S)
        return frozenset(a for a in self._args if all(self._attackers[b] & S for b in self._attackers[a]))

    # ----------------------------- 5. admissible and complete extensions
    def is_admissible(self, S: Iterable[Argument]) -> bool:
        """S is conflict-free and defends each of its members (S <= F(S))."""
        S = self._as_set(S)
        return self.is_conflict_free(S) and S <= self.characteristic(S)

    def is_complete(self, S: Iterable[Argument]) -> bool:
        """S is admissible and contains every argument it defends (F(S) = S)."""
        S = self._as_set(S)
        return self.is_conflict_free(S) and self.characteristic(S) == S

    # ------------------------------------------------ 6A. grounded extension
    def grounded_extension(self) -> ArgSet:
        """The least fixed point of F, obtained by iterating F from the empty set."""
        S: ArgSet = frozenset()
        while True:
            nxt = self.characteristic(S)
            if nxt == S:
                return S
            S = nxt

    # ------------------------------------------- bit-mask enumeration core
    def _conflict_free_mask(self, m: int) -> bool:
        rest = m
        while rest:
            low = rest & -rest
            if self._tgt_mask[low.bit_length() - 1] & m:
                return False
            rest ^= low
        return True

    def _defended_mask(self, m: int) -> int:
        d = 0
        for i, atts in enumerate(self._att_idx):
            if all(self._att_mask[j] & m for j in atts):
                d |= 1 << i
        return d

    def _range_mask(self, m: int) -> int:
        r = m
        rest = m
        while rest:
            low = rest & -rest
            r |= self._tgt_mask[low.bit_length() - 1]
            rest ^= low
        return r

    def _admissible_masks(self) -> List[int]:
        if self._admissible_cache is None:
            self._admissible_cache = [
                m
                for m in range(1 << self._n)
                if self._conflict_free_mask(m) and (m & ~self._defended_mask(m)) == 0
            ]
        return self._admissible_cache

    # ------------------------------------------ 6B. complete extensions
    def complete_extensions(self) -> List[ArgSet]:
        """All complete extensions (conflict-free sets S with F(S) = S; Definition 5.5)."""
        return _sort_sets(self._from_mask(m) for m in self._complete_masks())

    def _complete_masks(self) -> List[int]:
        return [
            m
            for m in range(1 << self._n)
            if self._conflict_free_mask(m) and self._defended_mask(m) == m
        ]

    # ------------------------------------------- 6C. the other extensions
    def admissible_sets(self) -> List[ArgSet]:
        """All admissible sets (including the empty set)."""
        return _sort_sets(self._from_mask(m) for m in self._admissible_masks())

    def preferred_extensions(self) -> List[ArgSet]:
        """Inclusion-maximal admissible sets."""
        return _sort_sets(self._from_mask(m) for m in _maximal(self._admissible_masks()))

    def stable_extensions(self) -> List[ArgSet]:
        """Conflict-free sets that attack every argument outside the set.

        May be empty (e.g. for an odd cycle).
        """
        found = [
            m
            for m in range(1 << self._n)
            if self._conflict_free_mask(m) and self._range_mask(m) == self._full
        ]
        return _sort_sets(self._from_mask(m) for m in found)

    def semi_stable_extensions(self) -> List[ArgSet]:
        """Complete extensions whose range S u S+ is inclusion-maximal (Definition 5.7).

        This follows the book's definition (maximal range among *complete*
        extensions).  It gives the same sets as the other common definition
        (maximal range among *admissible* sets); the test suite checks this.
        """
        comp = self._complete_masks()
        ranges = {m: self._range_mask(m) for m in comp}
        best = set(_maximal(ranges.values()))
        return _sort_sets(self._from_mask(m) for m in comp if ranges[m] in best)

    def all_extensions(self) -> Dict[str, List[ArgSet]]:
        """Every extension-based semantics at once.

        Returns a dict with keys 'grounded', 'complete', 'preferred',
        'stable' and 'semi-stable'; each value is a list of frozensets
        (the grounded list has exactly one element).
        """
        return {name: self.extensions(name) for name in SEMANTICS}

    def extensions(self, semantics: str) -> List[ArgSet]:
        """The extensions under one named semantics (see ``SEMANTICS``)."""
        if semantics == "grounded":
            return [self.grounded_extension()]
        if semantics == "complete":
            return self.complete_extensions()
        if semantics == "preferred":
            return self.preferred_extensions()
        if semantics == "stable":
            return self.stable_extensions()
        if semantics in ("semi-stable", "semi_stable", "semistable"):
            return self.semi_stable_extensions()
        raise ValueError(f"unknown semantics {semantics!r}; choose one of {SEMANTICS}")

    # ------------------------------------------------ 6D. labellings
    def _is_legal(self, a: Argument, lab: Dict[Argument, str], kind: str) -> bool:
        atts = self._attackers[a]
        label = lab[a]
        if label == IN:  # legally in: all attackers are out
            return all(lab[b] == OUT for b in atts)
        if label == OUT:  # legally out: some attacker is in
            return any(lab[b] == IN for b in atts)
        if kind == "admissible":
            return True
        # legally undec: no attacker is in, and not all attackers are out
        return not any(lab[b] == IN for b in atts) and not all(lab[b] == OUT for b in atts)

    def labellings(self, kind: str = "complete") -> List[Labelling]:
        """All legal labellings of the framework.

        kind="complete" (default)
            Every argument is *legally* labelled:
              in    -> all its attackers are out,
              out   -> at least one attacker is in,
              undec -> no attacker is in and not all attackers are out.
            These are exactly the complete labellings (Caminada); they are in
            one-to-one correspondence with the complete extensions
            (in = S, out = S+, undec = the rest).
        kind="admissible"
            Only in- and out-labels must be legal; undec is unrestricted.

        The search assigns labels argument by argument and prunes as soon as
        an argument and all of its attackers have been labelled.
        """
        if kind not in ("complete", "admissible"):
            raise ValueError("kind must be 'complete' or 'admissible'")
        order = self._args
        pos = {a: i for i, a in enumerate(order)}
        check_at: List[List[Argument]] = [[] for _ in order]
        for a in order:
            last = max([pos[a]] + [pos[b] for b in self._attackers[a]])
            check_at[last].append(a)

        lab: Dict[Argument, str] = {}
        results: List[Labelling] = []

        def build() -> Labelling:
            return Labelling(
                frozenset(a for a, l in lab.items() if l == IN),
                frozenset(a for a, l in lab.items() if l == OUT),
                frozenset(a for a, l in lab.items() if l == UNDEC),
            )

        def rec(k: int) -> None:
            if k == len(order):
                results.append(build())
                return
            a = order[k]
            for label in (IN, OUT, UNDEC):
                lab[a] = label
                if all(self._is_legal(x, lab, kind) for x in check_at[k]):
                    rec(k + 1)
            del lab[a]

        rec(0)
        return sorted(results, key=_labelling_key)

    # ------------------------------------------- 6E. acceptance status
    def acceptance_status(self, a: Argument, semantics: str = "preferred") -> str:
        """Acceptance status of ``a`` under a semantics (default: preferred).

        * 'skeptically accepted' -- ``a`` is in every extension,
        * 'credulously accepted' -- ``a`` is in some but not every extension,
        * 'rejected'             -- ``a`` is in no extension.

        This follows Definition 5.8.  There, a skeptically accepted argument is
        also credulously accepted (it is in at least one extension); this
        function reports the strongest status that applies, so the three
        answers are mutually exclusive.

        If the semantics has no extension at all (possible for stable), the
        argument is reported as 'rejected' rather than vacuously accepted.
        """
        self._check_arg(a)
        exts = self.extensions(semantics)
        if not exts:
            return REJECTED
        containing = sum(1 for E in exts if a in E)
        if containing == len(exts):
            return SKEPTICAL
        if containing > 0:
            return CREDULOUS
        return REJECTED

    def acceptance_statuses(self, semantics: str = "preferred") -> Dict[Argument, str]:
        """Acceptance status of every argument (computes the extensions once)."""
        exts = self.extensions(semantics)
        out: Dict[Argument, str] = {}
        for a in self._args:
            if not exts:
                out[a] = REJECTED
                continue
            containing = sum(1 for E in exts if a in E)
            out[a] = SKEPTICAL if containing == len(exts) else CREDULOUS if containing else REJECTED
        return out


# --------------------------------------------------------------------------
# module-level function interface
# --------------------------------------------------------------------------
def is_conflict_free(af: ArgumentationFramework, S: Iterable[Argument]) -> bool:
    return af.is_conflict_free(S)


def is_defended(af: ArgumentationFramework, a: Argument, S: Iterable[Argument]) -> bool:
    return af.is_defended(a, S)


def characteristic(af: ArgumentationFramework, S: Iterable[Argument]) -> ArgSet:
    return af.characteristic(S)


def is_admissible(af: ArgumentationFramework, S: Iterable[Argument]) -> bool:
    return af.is_admissible(S)


def is_complete(af: ArgumentationFramework, S: Iterable[Argument]) -> bool:
    return af.is_complete(S)


def grounded_extension(af: ArgumentationFramework) -> ArgSet:
    return af.grounded_extension()


def complete_extensions(af: ArgumentationFramework) -> List[ArgSet]:
    return af.complete_extensions()


def preferred_extensions(af: ArgumentationFramework) -> List[ArgSet]:
    return af.preferred_extensions()


def stable_extensions(af: ArgumentationFramework) -> List[ArgSet]:
    return af.stable_extensions()


def semi_stable_extensions(af: ArgumentationFramework) -> List[ArgSet]:
    return af.semi_stable_extensions()


def all_extensions(af: ArgumentationFramework) -> Dict[str, List[ArgSet]]:
    return af.all_extensions()


def labellings(af: ArgumentationFramework, kind: str = "complete") -> List[Labelling]:
    return af.labellings(kind)


def acceptance_status(af: ArgumentationFramework, a: Argument, semantics: str = "preferred") -> str:
    return af.acceptance_status(a, semantics)
