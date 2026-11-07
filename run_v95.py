"""OptiCore v9.5 Demo and Integration Runner.

Commands:
python run_v95.py
python run_v95.py --integration --rounds 100
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys

from pathlib import Path

from v95_analysis import (
    analyze_dominance_and_loops,
    dominator_tree_dot,
)

from v95_spilling import (
    simulate_spilling,
    interference_dot,
)

from v95_regression import differential_test


def demo():

    loop = [
        "i = 0",
        "TOP:",
        "if i >= 3 goto END",
        "i = i + 1",
        "goto TOP",
        "END:",
        "print i",
    ]

    spill_code = [
        "a = 1",
        "b = 2",
        "c = 3",
        "print a",
        "print b",
        "print c",
    ]

    report = analyze_dominance_and_loops(
        loop
    )

    print(
        "=== DOMINATOR TREE ==="
    )

    for block in report.cfg.blocks:
        print(
            f"{block.name}: "
            f"idom="
            f"{report.immediate_dominator.get(block.name)}, "
            f"successors="
            f"{list(block.successors)}"
        )

    print(
        "BACK EDGES:",
        report.back_edges,
    )

    print(
        "NATURAL LOOPS:",
        report.natural_loops,
    )

    spill = simulate_spilling(
        spill_code,
        registers=2,
    )

    print(
        "\n=== SPILL SIMULATION (2 REGISTERS) ==="
    )

    print(
        "ASSIGNMENTS:",
        spill.assignments,
    )

    print(
        "SPILL SLOTS:",
        spill.slots,
    )

    print(
        f"ESTIMATED LOADS={spill.loads}, "
        f"STORES={spill.stores}"
    )

    print(
        "Note: Load/store events are "
        "illustrative; executable TAC "
        "is unchanged."
    )

    print(
        "\n=== GRAPHVIZ DOT ==="
    )

    print(
        dominator_tree_dot(
            report
        )
    )

    print(
        interference_dot(
            spill
        )
    )

    print(
        "\nV95 DEMO COMPLETED"
    )


def integration(rounds: int):

    home = (
        Path(__file__)
        .resolve()
        .parent
    )

    candidates = [
        home,
        home / "backend",
        home.parent,
        home.parent / "backend",
    ]

    for directory in candidates:
        if (
            directory / "integrated_optimizer.py"
        ).is_file():

            sys.path.insert(
                0,
                str(directory),
            )
            break

    try:
        module = importlib.import_module(
            "integrated_optimizer"
        )

        optimizer = getattr(
            module,
            "optimize",
        )

    except (
        ImportError,
        AttributeError,
    ) as exc:

        print(
            "INTEGRATION NOT RUN: "
            "could not import "
            "integrated_optimizer.optimize: "
            f"{exc}"
        )

        return 2

    report = differential_test(
        optimizer,
        rounds=rounds,
        seed=2026,
    )

    print(
        "PRODUCTION OPTIMIZER DIFFERENTIAL: "
        f"{report['passed']}/"
        f"{report['rounds']} passed; "
        f"{report['failed']} failed"
    )

    if report["failures"]:

        outfile = (
            home / "v95_failures.json"
        )

        outfile.write_text(
            json.dumps(
                report,
                indent=2,
            ),
            encoding="utf-8",
        )

        print(
            "Failure details saved to "
            f"{outfile}"
        )

        for case in report[
            "failures"
        ][:3]:

            print(
                "Case",
                case["case"],
                ":",
                case["reason"],
            )

    return (
        1
        if report["failed"]
        else 0
    )


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--integration",
        action="store_true",
        help=(
            "Test existing "
            "integrated_optimizer.optimize"
        ),
    )

    parser.add_argument(
        "--rounds",
        type=int,
        default=100,
    )

    args = parser.parse_args()

    if args.integration:
        sys.exit(
            integration(
                args.rounds
            )
        )

    demo()