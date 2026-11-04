"""
OptiCore Member 2 - Standalone Auto Backend

No Member 1 or Member 3 required.
Existing backend files remain unchanged.

Usage:
python auto_backend.py
python auto_backend.py --tests
python auto_backend.py --tests --dashboard
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from datetime import datetime
from pathlib import Path


DEMO = [
    "a = 4",
    "b = 6",
    "c = a + b",
    "d = a - b",
    "print c",
    "print d",
]


# =====================================
# 1. AUTOMATIC TAC INPUT
# =====================================

def load_tac(filename=None, folder=None):

    folder = folder or Path(__file__).resolve().parent

    path = (
        Path(filename)
        if filename
        else folder / "my_backend_input.tac"
    )

    if filename and not path.is_file():
        raise FileNotFoundError(path)

    if path.is_file():

        lines = [
            line.strip()
            for line in path.read_text(
                encoding="utf-8-sig"
            ).splitlines()
            if line.strip()
        ]

        if not lines:
            raise ValueError("TAC input is empty")

        return lines, str(path)

    return (
        DEMO.copy(),
        "Built-in Member 2 demo TAC"
    )


# =====================================
# 2. EXECUTION RESULT
# =====================================

def behavior(result):

    return {
        "outputs": list(result.outputs),
        "returned": result.returned,
        "halted": result.halted,
    }


# =====================================
# 3. AUTOMATIC ADVANCED ANALYSIS
# =====================================

def analyze(code, registers):

    from v95_analysis import (
        analyze_dominance_and_loops,
        dominator_tree_dot,
    )

    from v95_spilling import (
        simulate_spilling,
        interference_dot,
    )

    dominance = analyze_dominance_and_loops(
        code
    )

    spilling = simulate_spilling(
        code,
        registers=registers,
    )

    data = {
        "basic_blocks": len(
            dominance.cfg.blocks
        ),

        "cfg_edges": [
            [block.name, next_name]
            for block in dominance.cfg.blocks
            for next_name in block.successors
        ],

        "immediate_dominators":
            dominance.immediate_dominator,

        "back_edges": [
            list(edge)
            for edge in dominance.back_edges
        ],

        "natural_loops":
            dominance.natural_loops,

        "unreachable_blocks":
            dominance.unreachable,

        "register_assignments":
            spilling.assignments,

        "spill_slots":
            spilling.slots,

        "estimated_loads":
            spilling.loads,

        "estimated_stores":
            spilling.stores,
    }

    return (
        data,
        dominator_tree_dot(dominance),
        interference_dot(spilling),
    )


# =====================================
# 4. FULL BACKEND PIPELINE
# =====================================

def perform(folder, tac, registers, run_tests=False):

    from integrated_optimizer import optimize

    from v95_regression import (
        execute,
        optimizer_compatible_tac,
        normalize_tac,
    )

    original, input_name = load_tac(
        tac,
        folder,
    )

    print(
        f"[1/5] TAC Loaded: {input_name}",
        flush=True
    )

    # Run original program
    before = behavior(
        execute(original)
    )

    print(
        "[2/5] Original Output:",
        before["outputs"],
        flush=True
    )

    # Run existing optimization backend
    compatible = optimizer_compatible_tac(
        original.copy()
    )

    optimized = normalize_tac(
        optimize(compatible)
    )

    # Run optimized program
    after = behavior(
        execute(optimized)
    )

    correct = before == after

    print(
        "[3/5] Optimized Output:",
        after["outputs"],
        flush=True
    )

    print(
        "CORRECTNESS:",
        "PASS" if correct else "FAIL",
        flush=True
    )

    # Create a new result folder
    stamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    output = (
        folder
        / "auto_backend_results"
        / stamp
    )

    output.mkdir(
        parents=True,
        exist_ok=False
    )

    reduction = (
        100
        * (len(original) - len(optimized))
        / len(original)
    )

    report = {
        "input": input_name,
        "original": original,
        "optimized_candidate": optimized,
        "original_behavior": before,
        "optimized_behavior": after,
        "correctness": (
            "PASS" if correct else "FAIL"
        ),
        "instruction_reduction_percent":
            round(reduction, 2),
    }

    # Never accept incorrect optimized TAC
    if correct:

        analysis, dominator_dot, register_dot = (
            analyze(original, registers)
        )

        report["analysis"] = analysis

        (output / "optimized.tac").write_text(
            "\n".join(optimized) + "\n",
            encoding="utf-8"
        )

        (output / "dominator_tree.dot").write_text(
            dominator_dot,
            encoding="utf-8"
        )

        (output / "interference_graph.dot").write_text(
            register_dot,
            encoding="utf-8"
        )

        print(
            "[4/5] CFG Blocks:",
            analysis["basic_blocks"],
            flush=True
        )

        print(
            "Natural Loops:",
            len(analysis["natural_loops"])
        )

        print(
            "Register Assignments:",
            analysis["register_assignments"]
        )

        print(
            "Spill Slots:",
            analysis["spill_slots"]
        )

    else:

        print(
            "[4/5] Correctness failed. "
            "Verified optimized TAC not saved."
        )

    # =================================
    # 5. AUTOMATED TESTING
    # =================================

    tests_ok = True

    if run_tests:

        test_files = [
            "test_v95.py",
            "test_live_optimization.py",
            "test_auto_backend.py",
        ]

        suites = [
            Path(name).stem
            for name in test_files
            if (folder / name).is_file()
        ]

        if suites:

            print(
                "[5/5] Running:",
                ", ".join(suites),
                flush=True
            )

            process = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "unittest",
                    "-v",
                    *suites,
                ],
                cwd=folder,
                check=False,
            )

            tests_ok = (
                process.returncode == 0
            )

            report["tests_status"] = (
                "PASS" if tests_ok else "FAIL"
            )

        else:

            tests_ok = False
            report["tests_status"] = (
                "NOT RUN"
            )

    else:

        report["tests_status"] = "NOT RUN"

    # Save JSON report
    report_path = output / "report.json"

    report_path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8"
    )

    print(
        "Report:",
        report_path,
        flush=True
    )

    success = correct and tests_ok

    print(
        "AUTO BACKEND "
        + (
            "COMPLETED"
            if success
            else "NEEDS REVIEW"
        ),
        flush=True
    )

    return success


# =====================================
# 6. OPTIONAL LIVE DASHBOARD
# =====================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--tac")

    parser.add_argument(
        "--registers",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--tests",
        action="store_true",
    )

    parser.add_argument(
        "--dashboard",
        action="store_true",
    )

    args = parser.parse_args()

    folder = Path(__file__).resolve().parent

    if not 1 <= args.registers <= 32:
        parser.error(
            "Registers must be between 1 and 32"
        )

    try:

        success = perform(
            folder,
            args.tac,
            args.registers,
            args.tests,
        )

    except Exception as exc:

        print(
            "AUTO BACKEND ERROR:",
            type(exc).__name__,
            str(exc),
            file=sys.stderr,
        )

        return 1

    if not success:
        return 1

    if args.dashboard:

        dashboard = folder / "live_dashboard.py"

        if not dashboard.is_file():

            print(
                "Dashboard not found:",
                dashboard
            )

            return 2

        print(
            "Dashboard: http://127.0.0.1:8507",
            flush=True
        )

        return subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(dashboard),
                "--server.port",
                "8507",
            ],
            cwd=folder,
            check=False,
        ).returncode

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )