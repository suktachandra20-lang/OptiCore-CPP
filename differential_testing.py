"""Reproducible TAC differential testing."""

from __future__ import annotations

import json
import random
from pathlib import Path

from cfg_analysis import build_cfg, parse_instruction
from integrated_optimizer import optimize


OPS = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b
}

COMPARE = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b
}


# 1. TAC INTERPRETER
def execute_tac(
    code: list[str],
    inputs: dict | None = None,
    max_steps: int = 2000
) -> list[int]:

    lines = [
        x.strip()
        for x in code
        if x.strip()
    ]

    build_cfg(lines)

    ins = [
        parse_instruction(line)
        for line in lines
    ]

    labels = {
        inst.target: i
        for i, inst in enumerate(ins)
        if inst.kind == "label"
    }

    variables = dict(inputs or {})
    output: list[int] = []

    pc = 0
    steps = 0

    def val(token: str) -> int:

        if token.lstrip("-").isdigit():
            return int(token)

        if token not in variables:
            raise ValueError(
                f"Undefined variable: {token}"
            )

        return variables[token]

    while pc < len(lines):

        if steps >= max_steps:
            raise RuntimeError(
                "Execution step limit exceeded"
            )

        steps += 1
        inst = ins[pc]
        p = lines[pc].split()

        if inst.kind == "label":
            pc += 1

        elif inst.kind == "goto":
            pc = labels[inst.target]

        elif inst.kind == "if":
            pc = (
                labels[inst.target]
                if COMPARE[p[2]](
                    val(p[1]),
                    val(p[3])
                )
                else pc + 1
            )

        elif inst.kind == "print":
            output.append(val(p[1]))
            pc += 1

        else:
            if len(p) == 3:
                variables[p[0]] = val(p[2])

            else:
                variables[p[0]] = OPS[p[3]](
                    val(p[2]),
                    val(p[4])
                )

            pc += 1

    return output


# 2. RANDOM PROGRAM GENERATOR
def generate_program(
    rng: random.Random
) -> tuple[list[str], list[dict]]:

    kind = rng.randrange(4)

    a, b, c = (
        rng.randint(-8, 8)
        for _ in range(3)
    )

    op = rng.choice(["+", "-", "*"])

    if kind == 0:

        program = [
            f"a = {a}",
            f"b = {b}",
            f"t1 = a {op} b",
            "t2 = a + b",
            f"a = a + {c}",
            "t3 = a + b",
            "print t1",
            "print t3",
            "dead = 42"
        ]

        return program, [{}]

    if kind == 1:

        program = [
            f"a = {a}",
            f"b = {b}",
            "if flag > 0 goto THEN",
            "x = a + b",
            "goto JOIN",
            "label THEN",
            "x = a * b",
            "label JOIN",
            "print x",
            "print a"
        ]

        return program, [
            {"flag": v}
            for v in [-1, 0, 1, 3]
        ]

    if kind == 2:

        bound = rng.randint(0, 5)

        program = [
            "i = 0",
            f"total = {a}",
            "label LOOP",
            f"if i >= {bound} goto END",
            f"t = i + {b}",
            "total = total + t",
            "i = i + 1",
            "goto LOOP",
            "label END",
            "print total",
            "print i"
        ]

        return program, [{}]

    program = [
        f"a = {a}",
        f"if {a} < {b} goto YES",
        "x = a + 1",
        "goto DONE",
        "label YES",
        "x = a - 1",
        "label DONE",
        "print x"
    ]

    return program, [{}]


# 3. CHECK ONE PROGRAM
def check_program(
    code: list[str],
    cases: list[dict],
    optimizer=optimize
) -> dict:

    try:
        optimized = optimizer(code[:])

        for inputs in cases:

            before = execute_tac(
                code,
                inputs
            )

            after = execute_tac(
                optimized,
                inputs
            )

            if before != after:

                return {
                    "passed": False,
                    "reason": "Output mismatch",
                    "inputs": inputs,
                    "original_output": before,
                    "optimized_output": after,
                    "original": code,
                    "optimized": optimized
                }

        return {
            "passed": True,
            "optimized": optimized
        }

    except Exception as exc:

        return {
            "passed": False,
            "reason": (
                f"{type(exc).__name__}: {exc}"
            ),
            "original": code,
            "input_cases": cases
        }


# 4. RUN DIFFERENTIAL TEST SUITE
def run_differential_tests(
    count: int = 300,
    seed: int = 20261104,
    failure_file: str | Path | None = (
        "opticore_failures.json"
    )
) -> dict:

    if not 1 <= count <= 10000:
        raise ValueError(
            "count must be between 1 and 10000"
        )

    rng = random.Random(seed)

    failures = []
    checked = 0

    for case_no in range(1, count + 1):

        program, inputs = generate_program(rng)

        result = check_program(
            program,
            inputs
        )

        checked += len(inputs)

        if not result["passed"]:

            failures.append({
                "case_number": case_no,
                "seed": seed,
                **result
            })

    if failures and failure_file is not None:

        Path(failure_file).write_text(
            json.dumps(
                failures,
                indent=2
            ),
            encoding="utf-8"
        )

    return {
        "seed": seed,
        "programs": count,
        "input_executions": checked,
        "failures": len(failures),
        "all_passed": not failures,
        "first_failure": (
            failures[0]
            if failures
            else None
        )
    }