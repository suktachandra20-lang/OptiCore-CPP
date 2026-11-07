"""Trace existing optimizer stages."""

from cfg_analysis import (
    build_cfg,
    dead_code_elimination_cfg
)

from control_flow import control_flow_optimize
from integrated_optimizer import optimize_block


def trace_optimization(
    code: list[str],
    max_rounds: int = 20
) -> dict:

    current = [
        line.strip()
        for line in code
        if line.strip()
    ]

    build_cfg(current)

    original = current[:]
    snapshots: list[dict] = []

    def run_stage(
        name: str,
        fn,
        iteration: int
    ) -> None:

        nonlocal current

        before = current[:]
        after = fn(before)

        snapshots.append({
            "round": iteration,
            "pass": name,
            "before": before,
            "after": after[:],
            "changed": before != after,
            "instruction_delta": (
                len(after) - len(before)
            ),
        })

        current = after

    def optimize_blocks(
        lines: list[str]
    ) -> list[str]:

        return [
            line
            for block in build_cfg(lines)
            for line in optimize_block(block.lines)
        ]

    for iteration in range(1, max_rounds + 1):

        before_round = current[:]

        run_stage(
            "Control-flow simplification",
            control_flow_optimize,
            iteration
        )

        run_stage(
            "Local folding / propagation / CSE",
            optimize_blocks,
            iteration
        )

        run_stage(
            "Branch simplification",
            control_flow_optimize,
            iteration
        )

        run_stage(
            "CFG-based dead-code elimination",
            dead_code_elimination_cfg,
            iteration
        )

        run_stage(
            "Final control-flow cleanup",
            control_flow_optimize,
            iteration
        )

        if current == before_round:
            return {
                "original": original,
                "optimized": current,
                "passes": snapshots,
                "rounds": iteration,
                "converged": True
            }

    raise RuntimeError(
        "Optimization trace did not converge"
    )