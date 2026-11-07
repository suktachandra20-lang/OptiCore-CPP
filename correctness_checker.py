# OptiCore - Execution Correctness Checker

from cfg_analysis import (
    build_cfg,
    parse_instruction
)


OPS = {
    "+": lambda x, y: x + y,
    "-": lambda x, y: x - y,
    "*": lambda x, y: x * y
}

COMPARISONS = {
    "==": lambda x, y: x == y,
    "!=": lambda x, y: x != y,
    ">": lambda x, y: x > y,
    "<": lambda x, y: x < y,
    ">=": lambda x, y: x >= y,
    "<=": lambda x, y: x <= y
}


# 1. TAC INTERPRETER
def execute_tac(
    code,
    inputs=None,
    max_steps=10000
):
    lines = [
        line.strip()
        for line in code
        if line.strip()
    ]

    build_cfg(lines)

    labels = {
        line.split()[1]: i
        for i, line in enumerate(lines)
        if line.startswith("label ")
    }

    env = dict(inputs or {})
    outputs = []

    pc = 0
    steps = 0

    def value(token):
        if token.lstrip("-").isdigit():
            return int(token)

        if token not in env:
            raise ValueError(
                f"Undefined variable: {token}"
            )

        return env[token]

    while pc < len(lines):

        if steps >= max_steps:
            raise RuntimeError(
                "Execution step limit exceeded"
            )

        steps += 1

        inst = parse_instruction(lines[pc])
        p = lines[pc].split()

        if inst.kind == "label":
            pc += 1

        elif inst.kind == "goto":
            pc = labels[inst.target]

        elif inst.kind == "if":
            condition = COMPARISONS[p[2]](
                value(p[1]),
                value(p[3])
            )

            if condition:
                pc = labels[inst.target]
            else:
                pc += 1

        elif inst.kind == "print":
            outputs.append(
                value(p[1])
            )
            pc += 1

        else:
            if len(p) == 3:
                env[p[0]] = value(p[2])

            else:
                a = value(p[2])
                b = value(p[4])

                env[p[0]] = OPS[p[3]](
                    a, b
                )

            pc += 1

    return outputs


# 2. ORIGINAL VS OPTIMIZED CHECK
def check_equivalence(
    original,
    optimized,
    input_cases,
    max_steps=10000
):
    results = []

    for case in input_cases:
        before = None
        after = None

        try:
            before = execute_tac(
                original,
                case,
                max_steps
            )

            after = execute_tac(
                optimized,
                case,
                max_steps
            )

            passed = before == after

            if passed:
                reason = "same output"
            else:
                reason = "output mismatch"

        except (
            ValueError,
            RuntimeError,
            TypeError
        ) as exc:
            passed = False
            reason = (
                "not verified: "
                f"{type(exc).__name__}: {exc}"
            )

        results.append({
            "inputs": dict(case),
            "passed": passed,
            "original_output": before,
            "optimized_output": after,
            "reason": reason
        })

    return {
        "passed": sum(
            r["passed"]
            for r in results
        ),
        "total": len(results),
        "all_passed": all(
            r["passed"]
            for r in results
        ),
        "cases": results
    }