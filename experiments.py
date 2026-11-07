"""
experiments.py -- random experiments on the grounded direct argumentation mechanism.

For each attack probability p, many random instances are generated:

    * 3 agents;
    * n arguments, n drawn uniformly from {6, 7, 8};
    * every possible attack (an ordered pair of two *different* arguments) is
      present independently with probability p; with ``--self-attacks`` the
      pairs (x, x) are possible as well;
    * every argument is given to one of the 3 agents, uniformly at random (an
      agent may end up with no argument).

For each instance two things are recorded:

    strategyproof      Theorem 5.3, checked exhaustively (check_truthful_dominant):
                       revealing everything is a best response for every agent
                       against every combination of subsets the others could reveal;
    condition_holds    Theorem 5.4, no agent owns two different arguments joined by
                       an odd-length directed path (check_odd_path_condition).

Strategyproof instances whose condition fails are classified further
(``classify_condition_failure``) to explain why hiding does not pay.

Run:
    python experiments.py                       # default: 7 values of p x 1000 instances
    python experiments.py --instances 200 --p 0.2 0.4
    python experiments.py --self-attacks --outdir results_self_attacks

Outputs (in --outdir, default "results"):
    instances.csv            one row per instance
    summary_by_p.csv         counts and fractions for each p
    summary.md               the same as a readable report with the two special lists
    condition_holds_not_strategyproof.json     (empty list if the theorem is respected)
    strategyproof_condition_fails.json         every such instance, with its class
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import time
from itertools import product
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

from strategic import (
    GroundedMechanism,
    check_odd_path_condition,
    check_truthful_dominant,
    subsets,
    utility,
)

DEFAULT_P_VALUES = (0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6)
DEFAULT_INSTANCES_PER_P = 1000
DEFAULT_SEED = 2024
N_AGENTS = 3
N_ARGUMENT_CHOICES = (6, 7, 8)

# classes of "strategyproof although the Theorem 5.4 condition fails"
INERT = "inert"
TRADE_OFF = "trade-off"


class Instance(NamedTuple):
    index: int
    p: float
    n_args: int
    types: Tuple[frozenset, ...]  # A_1, A_2, A_3
    attacks: frozenset


# --------------------------------------------------------------------------
# generation
# --------------------------------------------------------------------------
def generate_instance(
    rng: random.Random,
    index: int,
    p: float,
    n_args: Optional[int] = None,
    n_agents: int = N_AGENTS,
    self_attacks: bool = False,
) -> Instance:
    """One random instance (arguments are named a1 .. an)."""
    if n_args is None:
        n_args = rng.choice(N_ARGUMENT_CHOICES)
    args = [f"a{i}" for i in range(1, n_args + 1)]
    attacks = frozenset(
        (x, y) for x in args for y in args if (self_attacks or x != y) and rng.random() < p
    )
    owner = [rng.randrange(n_agents) for _ in args]
    types = tuple(frozenset(a for a, o in zip(args, owner) if o == k) for k in range(n_agents))
    return Instance(index, p, n_args, types, attacks)


# --------------------------------------------------------------------------
# classification of strategyproof instances whose condition fails
# --------------------------------------------------------------------------
class FailureClass(NamedTuple):
    label: str  # INERT or TRADE_OFF
    biting_scenarios: int  # situations in which hiding makes a remaining own argument newly accepted
    tie_scenarios: int  # ... of which hiding is exactly as good as revealing (net gain 0)
    worst_net: int  # the best net gain over all scenarios (always <= 0 for a strategyproof instance)


def classify_condition_failure(inst: Instance, offending_agents: Sequence[int]) -> FailureClass:
    """Why does hiding not pay although some agent owns arguments joined by an odd path?

    For every agent with an offending pair, every combination of the others'
    reports and every non-empty set S of hidden arguments, compare the outcome
    with S revealed (E) and hidden (E').  Hiding *bites* when some remaining own
    argument is accepted in E' but not in E.  This is the only way hiding can
    help, because the arguments that stay hidden are lost anyway.

    inert      hiding never bites: no argument of the agent can ever be gained by
               hiding, so the odd path never has any effect on the agent's
               utility (for example because the path is cut or neutralised
               by other arguments, as a6 does in Example 5.11);
    trade-off  hiding does bite in some situations, but whenever it gains
               an argument it loses at least as many (the odd path merely
               exchanges accepted arguments).
    """
    mech = GroundedMechanism(inst.attacks)
    bites = ties = 0
    best_net = -(10**9)
    for i in offending_agents:
        own = inst.types[i]
        others = [j for j in range(len(inst.types)) if j != i]
        for combo in product(*[subsets(inst.types[j]) for j in others]):
            ctx = frozenset().union(*combo) if combo else frozenset()
            e_full = mech.outcome_of_union(own | ctx)
            u_full = utility(own, e_full)
            for reveal in subsets(own):
                if reveal == own:
                    continue
                e_hide = mech.outcome_of_union(reveal | ctx)
                newly = (reveal & e_hide) - e_full
                net = utility(own, e_hide) - u_full
                best_net = max(best_net, net)
                if newly:
                    bites += 1
                    if net == 0:
                        ties += 1
    label = INERT if bites == 0 else TRADE_OFF
    return FailureClass(label, bites, ties, best_net if best_net > -(10**9) else 0)


# --------------------------------------------------------------------------
# per-instance analysis
# --------------------------------------------------------------------------
def has_direct_conflict(inst: Instance) -> bool:
    """Does some agent own two different arguments one of which attacks the other?

    (Then that agent's type is not conflict-free, and the odd path has length 1.)
    """
    return any(
        (x, y) in inst.attacks for t in inst.types for x in t for y in t if x != y
    )


def fmt_set(s) -> str:
    return "{" + ",".join(sorted(s)) + "}"


def fmt_attacks(attacks) -> str:
    return " ".join(f"{x}>{y}" for x, y in sorted(attacks))


def analyse_instance(inst: Instance) -> dict:
    """All measurements for one instance, as a flat dict (one CSV row)."""
    mech = GroundedMechanism(inst.attacks)
    sp = check_truthful_dominant(inst.types, inst.attacks, find_all=True, _mech=mech)
    cond = check_odd_path_condition(inst.types, inst.attacks)  # odd walks, different arguments
    cond_simple = check_odd_path_condition(inst.types, inst.attacks, mode="simple")
    cond_same = check_odd_path_condition(inst.types, inst.attacks, include_same=True)
    cond_simple_same = check_odd_path_condition(inst.types, inst.attacks, mode="simple", include_same=True)

    rec = {
        "index": inst.index,
        "p": inst.p,
        "n_args": inst.n_args,
        "n_attacks": len(inst.attacks),
        "types": " | ".join(fmt_set(t) for t in inst.types),
        "attacks": fmt_attacks(inst.attacks),
        "empty_agents": sum(1 for t in inst.types if not t),
        "strategyproof": sp.holds,
        "manipulating_agents": ",".join(map(str, sp.agents_with_manipulation)),
        "condition_holds": cond.holds,
        "condition_holds_simple_paths": cond_simple.holds,
        "condition_holds_incl_same": cond_same.holds,
        "condition_holds_simple_incl_same": cond_simple_same.holds,
        "odd_pairs": ";".join(f"{i}:{a}>{b}" for i, a, b in cond.violations),
        "direct_conflict": has_direct_conflict(inst),
        "failure_class": "",
        "biting_scenarios": "",
        "tie_scenarios": "",
    }
    if sp.holds and not cond.holds:
        offenders = sorted({i for (i, _, _) in cond.violations})
        fc = classify_condition_failure(inst, offenders)
        rec["failure_class"] = fc.label
        rec["biting_scenarios"] = fc.biting_scenarios
        rec["tie_scenarios"] = fc.tie_scenarios
    return rec


# --------------------------------------------------------------------------
# the experiment
# --------------------------------------------------------------------------
def run_experiment(
    p_values: Sequence[float] = DEFAULT_P_VALUES,
    per_p: int = DEFAULT_INSTANCES_PER_P,
    seed: int = DEFAULT_SEED,
    self_attacks: bool = False,
    progress: bool = True,
) -> Tuple[List[Instance], List[dict]]:
    """Generate and analyse ``per_p`` instances for each p.  Deterministic for a given seed."""
    instances: List[Instance] = []
    records: List[dict] = []
    counter = 0
    for p in p_values:
        rng = random.Random(f"{seed}/{p}/{int(self_attacks)}")  # independent stream per p
        t0 = time.time()
        for _ in range(per_p):
            counter += 1
            inst = generate_instance(rng, counter, p, self_attacks=self_attacks)
            instances.append(inst)
            records.append(analyse_instance(inst))
        if progress:
            print(f"  p = {p:<5} {per_p} instances in {time.time() - t0:.1f}s", file=sys.stderr)
    return instances, records


def summarise(records: Sequence[dict]) -> List[dict]:
    """One row per p (in increasing order) plus a final row 'all'."""
    rows: List[dict] = []
    groups: Dict[float, List[dict]] = {}
    for r in records:
        groups.setdefault(r["p"], []).append(r)

    def row(label, rs):
        n = len(rs)
        sp = sum(r["strategyproof"] for r in rs)
        cond = sum(r["condition_holds"] for r in rs)
        cond_not_sp = sum(1 for r in rs if r["condition_holds"] and not r["strategyproof"])
        sp_not_cond = sum(1 for r in rs if r["strategyproof"] and not r["condition_holds"])

        def exceptions(key):  # the condition (in another reading) holds but the mechanism is not strategyproof
            return sum(1 for r in rs if r[key] and not r["strategyproof"])

        return {
            "p": label,
            "instances": n,
            "strategyproof": sp,
            "fraction_strategyproof": sp / n if n else float("nan"),
            "condition_holds": cond,
            "fraction_condition_holds": cond / n if n else float("nan"),
            "condition_holds_not_strategyproof": cond_not_sp,
            "strategyproof_condition_fails": sp_not_cond,
            "direct_conflict": sum(
                1 for r in rs if r["strategyproof"] and not r["condition_holds"] and r["direct_conflict"]
            ),
            "indirect_trade_off": sum(
                1 for r in rs if r["failure_class"] == TRADE_OFF and not r["direct_conflict"]
            ),
            "indirect_inert": sum(
                1 for r in rs if r["failure_class"] == INERT and not r["direct_conflict"]
            ),
            "not_strategyproof_condition_fails": sum(
                1 for r in rs if not r["strategyproof"] and not r["condition_holds"]
            ),
            "no_attacks": sum(1 for r in rs if r["n_attacks"] == 0),
            "holds_not_sp_simple_paths": exceptions("condition_holds_simple_paths"),
            "holds_not_sp_incl_same": exceptions("condition_holds_incl_same"),
            "holds_not_sp_simple_incl_same": exceptions("condition_holds_simple_incl_same"),
            "readings_differ": sum(
                1 for r in rs if r["condition_holds"] != r["condition_holds_simple_paths"]
            ),
        }

    for p in sorted(groups):
        rows.append(row(p, groups[p]))
    rows.append(row("all", list(records)))
    return rows


# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------
def write_csv(path: str, rows: Sequence[dict]) -> None:
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(summary: Sequence[dict]) -> str:
    head = (
        "| p | instances | strategyproof | fraction strategyproof | condition holds | "
        "condition holds, not strategyproof | strategyproof, condition fails |\n"
        "|---|---|---|---|---|---|---|\n"
    )
    lines = []
    for r in summary:
        lines.append(
            f"| {r['p']} | {r['instances']} | {r['strategyproof']} | {r['fraction_strategyproof']:.3f} | "
            f"{r['condition_holds']} ({r['fraction_condition_holds']:.3f}) | "
            f"{r['condition_holds_not_strategyproof']} | {r['strategyproof_condition_fails']} |"
        )
    return head + "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--instances", type=int, default=DEFAULT_INSTANCES_PER_P, help="instances per value of p")
    ap.add_argument("--p", type=float, nargs="+", default=list(DEFAULT_P_VALUES), help="attack probabilities")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--self-attacks", action="store_true", help="also allow attacks (x, x)")
    ap.add_argument("--outdir", default="results")
    ap.add_argument("--no-files", action="store_true", help="print the summary only")
    args = ap.parse_args(argv)

    print(
        f"seed={args.seed}  p={args.p}  instances per p={args.instances}  self-attacks={args.self_attacks}",
        file=sys.stderr,
    )
    t0 = time.time()
    _, records = run_experiment(args.p, args.instances, args.seed, args.self_attacks)
    summary = summarise(records)
    print(f"done: {len(records)} instances in {time.time() - t0:.1f}s\n", file=sys.stderr)
    print(markdown_table(summary))

    if args.no_files:
        return 0
    os.makedirs(args.outdir, exist_ok=True)
    write_csv(os.path.join(args.outdir, "instances.csv"), records)
    write_csv(os.path.join(args.outdir, "summary_by_p.csv"), summary)
    bad = [r for r in records if r["condition_holds"] and not r["strategyproof"]]
    good = [r for r in records if r["strategyproof"] and not r["condition_holds"]]
    with open(os.path.join(args.outdir, "condition_holds_not_strategyproof.json"), "w", encoding="utf-8") as fh:
        json.dump(bad, fh, indent=1)
    with open(os.path.join(args.outdir, "strategyproof_condition_fails.json"), "w", encoding="utf-8") as fh:
        json.dump(good, fh, indent=1)
    with open(os.path.join(args.outdir, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write(f"Seed {args.seed}; {len(records)} instances; self-attacks: {args.self_attacks}\n\n")
        fh.write(markdown_table(summary) + "\n\n")
        total = summary[-1]
        fh.write(f"Condition holds but not strategyproof: {len(bad)}\n\n")
        fh.write(
            f"Strategyproof although the condition fails: {len(good)} "
            f"(direct conflict inside one agent's arguments: {total['direct_conflict']}; "
            f"only indirect odd paths: {total['indirect_trade_off']} trade-off, {total['indirect_inert']} inert)\n\n"
        )
        fh.write(
            "Condition holds (other readings) but not strategyproof: "
            f"simple paths {total['holds_not_sp_simple_paths']}, "
            f"alpha = beta allowed {total['holds_not_sp_incl_same']}, "
            f"simple paths and alpha = beta allowed {total['holds_not_sp_simple_incl_same']}; "
            f"walk and simple-path readings differ on {total['readings_differ']} instances\n"
        )
    print(f"\nwrote {args.outdir}/", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
