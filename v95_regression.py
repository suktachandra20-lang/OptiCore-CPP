"""
OptiCore v9.5
Advanced Regression Testing - Fixed Version

Features:
1. TAC Execution
2. Branch and Loop Support
3. Label Syntax Compatibility
4. Random Program Generation
5. Differential Testing
6. Live Testing Progress
7. Detailed Failure Reports

Does not modify the existing optimizer.
"""

from __future__ import annotations

import ast
import operator
import random
import re

from dataclasses import dataclass
from typing import Callable

from v95_analysis import (
    build_cfg,
    expression_variables,
)


# ==========================================
# 1. EXPRESSION OPERATORS
# ==========================================

BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}

UNARY = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.Not: operator.not_,
}

COMPARE = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}


# ==========================================
# 2. SAFE EXPRESSION EVALUATION
# ==========================================

def evaluate(expression: str, env: dict):

    expression_variables(expression)

    tree = ast.parse(
        expression,
        mode="eval"
    )

    def visit(node):

        if isinstance(node, ast.Expression):
            return visit(node.body)

        if isinstance(node, ast.Constant):

            if type(node.value) in (
                int, float, bool
            ):
                return node.value

        if isinstance(node, ast.Name):

            if node.id not in env:
                raise ValueError(
                    f"Read before assignment: {node.id}"
                )

            return env[node.id]

        if isinstance(node, ast.BinOp):

            operation = BINOPS.get(type(node.op))

            if operation is not None:
                return operation(
                    visit(node.left),
                    visit(node.right)
                )

        if isinstance(node, ast.UnaryOp):

            operation = UNARY.get(type(node.op))

            if operation is not None:
                return operation(
                    visit(node.operand)
                )

        if isinstance(node, ast.Compare):

            left = visit(node.left)

            for op, right_node in zip(
                node.ops,
                node.comparators
            ):

                right = visit(right_node)

                operation = COMPARE.get(
                    type(op)
                )

                if (
                    operation is None
                    or not operation(left, right)
                ):
                    return False

                left = right

            return True

        if isinstance(node, ast.BoolOp):

            if isinstance(node.op, ast.And):

                for part in node.values:

                    if not bool(visit(part)):
                        return False

                return True

            if isinstance(node.op, ast.Or):

                for part in node.values:

                    if bool(visit(part)):
                        return True

                return False

        raise ValueError(
            f"Unsupported expression: {expression}"
        )

    return visit(tree)


# ==========================================
# 3. EXECUTION RESULT
# ==========================================

@dataclass(frozen=True)
class Execution:

    outputs: tuple[object, ...]
    returned: object | None
    halted: bool
    steps: int


# ==========================================
# 4. TAC INTERPRETER
# ==========================================

def execute(
    code: list[str] | str,
    inputs: dict | None = None,
    max_steps: int = 2000
) -> Execution:

    cfg = build_cfg(code)

    env = dict(inputs or {})

    printed = []

    pc = 0
    steps = 0

    returned = None
    halted = False

    while pc < len(cfg.instructions):

        if steps >= max_steps:

            raise RuntimeError(
                "Execution step limit exceeded "
                "(possible infinite loop)"
            )

        inst = cfg.instructions[pc]

        steps += 1

        if inst.kind == "assign":

            env[inst.defines] = evaluate(
                inst.expr,
                env
            )

        elif inst.kind == "print":

            printed.append(
                evaluate(
                    inst.expr,
                    env
                )
            )

        elif inst.kind == "return":

            returned = (
                evaluate(inst.expr, env)
                if inst.expr
                else None
            )

            halted = True
            break

        elif inst.kind == "goto":

            pc = cfg.labels[
                inst.target
            ]

            continue

        elif inst.kind in {
            "if",
            "if_false"
        }:

            condition = bool(
                evaluate(
                    inst.expr,
                    env
                )
            )

            should_jump = (
                condition
                if inst.kind == "if"
                else not condition
            )

            if should_jump:

                pc = cfg.labels[
                    inst.target
                ]

                continue

        pc += 1

    return Execution(
        tuple(printed),
        returned,
        halted,
        steps
    )


# ==========================================
# 5. RANDOM TAC GENERATOR
# ==========================================

def random_program(
    rng: random.Random
) -> list[str]:

    mode = rng.randrange(3)

    x = rng.randint(-10, 10)
    y = rng.randint(-10, 10)
    n = rng.randint(0, 8)

    # Straight-line program
    if mode == 0:

        return [
            f"a = {x}",
            f"b = {y}",
            "c = a + b",
            "d = c * 2",
            "print d",
        ]

    # Branch program
    if mode == 1:

        return [
            f"a = {x}",
            f"b = {y}",
            "if a > b goto THEN",
            "c = b - a",
            "goto END",
            "THEN:",
            "c = a - b",
            "END:",
            "print c",
        ]

    # Loop program
    return [
        f"n = {n}",
        "i = 0",
        "sum = 0",
        "TOP:",
        "if i >= n goto DONE",
        "sum = sum + i",
        "i = i + 1",
        "goto TOP",
        "DONE:",
        "print sum",
    ]


# ==========================================
# 6. LABEL SYNTAX COMPATIBILITY
# ==========================================

def optimizer_compatible_tac(
    code: list[str]
) -> list[str]:

    """
    Converts:
        TOP:     -> label TOP
        DONE:    -> label DONE

    Original TAC remains unchanged.
    """

    converted = []

    for line in code:

        s = line.strip()

        if re.fullmatch(
            r"[A-Za-z_]\w*:",
            s
        ):

            converted.append(
                "label " + s[:-1]
            )

        else:
            converted.append(line)

    return converted


# ==========================================
# 7. NORMALIZE OPTIMIZER OUTPUT
# ==========================================

def normalize_tac(result) -> list[str]:

    if (
        isinstance(result, tuple)
        and len(result) == 2
    ):
        result = result[0]

    if isinstance(result, dict):

        for key in (
            "optimized",
            "optimized_code",
            "optimized_tac",
            "code"
        ):

            if key in result:

                result = result[key]
                break

        else:

            raise TypeError(
                "Optimizer dictionary has "
                "no optimized TAC field"
            )

    if isinstance(result, str):
        result = result.splitlines()

    if (
        not isinstance(result, list)
        or any(
            not isinstance(line, str)
            for line in result
        )
    ):

        raise TypeError(
            "Optimizer must return "
            "list[str], string, or "
            "supported tuple/dict"
        )

    return [
        line.strip()
        for line in result
        if line.strip()
    ]


# ==========================================
# 8. ADVANCED DIFFERENTIAL TESTING
# ==========================================

def differential_test(
    optimizer: Callable,
    rounds: int = 100,
    seed: int = 2026,
    verbose: bool = True
) -> dict:

    if (
        not isinstance(rounds, int)
        or isinstance(rounds, bool)
        or rounds < 1
    ):

        raise ValueError(
            "rounds must be a positive integer"
        )

    rng = random.Random(seed)

    failures = []

    if verbose:

        print(
            f"Starting {rounds} differential "
            f"checks (seed={seed})...",
            flush=True
        )

    for index in range(rounds):

        original = random_program(rng)

        stage = "executing original"

        optimized = None
        before = None
        after = None

        try:

            # Execute original TAC
            before = execute(original)

            # Convert labels only for optimizer
            stage = "running optimizer"

            compatible = optimizer_compatible_tac(
                original.copy()
            )

            # Run actual optimization engine
            optimized = normalize_tac(
                optimizer(compatible)
            )

            # Execute optimized TAC
            stage = "executing optimized"

            after = execute(optimized)

            # Compare observable behavior
            observed_original = (
                before.outputs,
                before.returned,
                before.halted
            )

            observed_optimized = (
                after.outputs,
                after.returned,
                after.halted
            )

            if (
                observed_original
                != observed_optimized
            ):

                failures.append({
                    "case": index,
                    "original": original,
                    "optimizer_input": compatible,
                    "optimized": optimized,
                    "before": list(before.outputs),
                    "after": list(after.outputs),
                    "reason": (
                        "Observable behavior differs"
                    )
                })

        except Exception as exc:

            failures.append({
                "case": index,
                "original": original,
                "optimized": optimized,
                "stage": stage,
                "reason": (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )
            })

        # Show live progress
        if verbose and (
            (index + 1) % 10 == 0
            or index + 1 == rounds
        ):

            completed = index + 1

            passed = (
                completed - len(failures)
            )

            print(
                f"Progress {completed}/{rounds} "
                f"| passed={passed} "
                f"| failed={len(failures)}",
                flush=True
            )

    return {
        "rounds": rounds,
        "passed": rounds - len(failures),
        "failed": len(failures),
        "seed": seed,
        "failures": failures
    }