"""
OptiCore - Automated Bug Minimizer

Algorithm: Delta Debugging (ddmin)

Features:
- Detect optimizer mismatches
- Detect optimizer exceptions
- Minimize failing TAC programs
- Preserve original observable output
- Preserve failure category
- Save minimized TAC and JSON report

Commands:
python bug_minimizer.py --demo
python bug_minimizer.py --report v95_failures.json
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import sys

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable

from v95_regression import (
    execute,
    normalize_tac,
)


# ==========================================
# 1. TAC COMPATIBILITY
# ==========================================

try:
    from v95_regression import (
        optimizer_compatible_tac
    )

except ImportError:

    def optimizer_compatible_tac(code):

        converted = []

        for line in code:

            s = line.strip()

            if (
                s.endswith(":")
                and s[:-1].isidentifier()
            ):

                converted.append(
                    "label " + s[:-1]
                )

            else:
                converted.append(line)

        return converted


# ==========================================
# 2. FAILURE INFORMATION
# ==========================================

@dataclass
class Failure:

    kind: str
    error_type: str = ""
    detail: str = ""

    original_output: list | None = None
    original_returned: object | None = None
    original_halted: bool = False

    optimized_output: list | None = None
    optimized_tac: list[str] | None = None

    @property
    def signature(self):

        family = self.detail.split(
            ":", 1
        )[0].strip()

        return (
            self.kind,
            self.error_type,
            family
        )


# ==========================================
# 3. DETECT A REAL FAILURE
# ==========================================

def diagnose(
    code: list[str],
    optimizer: Callable,
    max_steps: int = 2000
):

    if not code:
        return None

    if not all(
        isinstance(line, str)
        for line in code
    ):
        return None

    # Original TAC must execute correctly
    try:

        before = execute(
            code,
            max_steps=max_steps
        )

    except Exception:
        return None

    # Run optimization
    try:

        compatible = optimizer_compatible_tac(
            code.copy()
        )

        result = optimizer(
            compatible
        )

        optimized = normalize_tac(
            result
        )

    except Exception as exc:

        return Failure(
            kind="optimizer_error",
            error_type=type(exc).__name__,
            detail=str(exc),
            original_output=list(
                before.outputs
            ),
            original_returned=before.returned,
            original_halted=before.halted
        )

    # Execute optimized TAC
    try:

        after = execute(
            optimized,
            max_steps=max_steps
        )

    except Exception as exc:

        return Failure(
            kind="optimized_execution_error",
            error_type=type(exc).__name__,
            detail=str(exc),
            original_output=list(
                before.outputs
            ),
            original_returned=before.returned,
            original_halted=before.halted,
            optimized_tac=optimized
        )

    original_behavior = (
        before.outputs,
        before.returned,
        before.halted
    )

    optimized_behavior = (
        after.outputs,
        after.returned,
        after.halted
    )

    if original_behavior != optimized_behavior:

        return Failure(
            kind="behavior_mismatch",
            detail="Observable behavior differs",
            original_output=list(
                before.outputs
            ),
            original_returned=before.returned,
            original_halted=before.halted,
            optimized_output=list(
                after.outputs
            ),
            optimized_tac=optimized
        )

    return None


# ==========================================
# 4. MINIMIZATION RESULT
# ==========================================

@dataclass
class MinimizeResult:

    original: list[str]
    minimized: list[str]
    before: Failure
    after: Failure
    evaluations: int


# ==========================================
# 5. DELTA DEBUGGING ALGORITHM
# ==========================================

def minimize_failure(
    code: list[str],
    optimizer: Callable,
    max_checks: int = 200,
    max_steps: int = 2000,
    verbose: bool = True
):

    if max_checks < 1:
        raise ValueError(
            "max_checks must be at least 1"
        )

    if max_steps < 1:
        raise ValueError(
            "max_steps must be at least 1"
        )

    original = [
        line.strip()
        for line in code
        if line.strip()
    ]

    if not original:
        raise ValueError(
            "Cannot minimize empty TAC"
        )

    evaluations = 0
    cache = {}

    def assess(lines):

        nonlocal evaluations

        key = tuple(lines)

        if key in cache:
            return cache[key]

        if evaluations >= max_checks:
            return None

        evaluations += 1

        outcome = diagnose(
            lines,
            optimizer,
            max_steps=max_steps
        )

        cache[key] = outcome

        return outcome

    # Verify initial bug
    baseline = assess(original)

    if baseline is None:

        raise ValueError(
            "No reproducible optimizer failure. "
            "The bug may already be fixed, "
            "or the input is invalid."
        )

    target_signature = baseline.signature

    current = original.copy()

    granularity = 2

    if verbose:

        print(
            f"Confirmed: {baseline.kind} "
            f"({len(current)} instructions)",
            flush=True
        )

    # Delta debugging
    while (
        len(current) > 1
        and evaluations < max_checks
    ):

        chunk = math.ceil(
            len(current) / granularity
        )

        reduced = False

        for start in range(
            0,
            len(current),
            chunk
        ):

            candidate = (
                current[:start]
                + current[start + chunk:]
            )

            if not candidate:
                continue

            outcome = assess(
                candidate
            )

            # Only accept same failure
            # with same original behavior
            if (
                outcome is not None
                and outcome.signature
                == target_signature
                and outcome.original_output
                == baseline.original_output
                and outcome.original_returned
                == baseline.original_returned
                and outcome.original_halted
                == baseline.original_halted
            ):

                current = candidate

                granularity = max(
                    2,
                    granularity - 1
                )

                reduced = True

                if verbose:

                    print(
                        f"Reduced to "
                        f"{len(current)} instructions",
                        flush=True
                    )

                break

            if evaluations >= max_checks:
                break

        if not reduced:

            if granularity >= len(current):
                break

            granularity = min(
                len(current),
                granularity * 2
            )

    final = cache[tuple(current)]

    assert final is not None

    return MinimizeResult(
        original,
        current,
        baseline,
        final,
        evaluations
    )


# ==========================================
# 6. DEMO OPTIMIZER
# ==========================================

def demo_optimizer(code):

    # Deliberately wrong for testing
    return [
        "print 999"
    ]


# ==========================================
# 7. LOAD FAILURE REPORT
# ==========================================

def load_failure(
    report_path: Path,
    index: int
):

    data = json.loads(
        report_path.read_text(
            encoding="utf-8-sig"
        )
    )

    failures = data.get(
        "failures"
    )

    if (
        not isinstance(failures, list)
        or not failures
    ):

        raise ValueError(
            "Report contains no failures"
        )

    if (
        index < 0
        or index >= len(failures)
    ):

        raise IndexError(
            "Invalid failure index"
        )

    code = failures[index].get(
        "original"
    )

    if (
        not isinstance(code, list)
        or not all(
            isinstance(x, str)
            for x in code
        )
    ):

        raise ValueError(
            "Failure lacks original TAC"
        )

    return code


# ==========================================
# 8. COMMAND LINE INTERFACE
# ==========================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "OptiCore Automated Bug Minimizer"
        )
    )

    parser.add_argument(
        "--demo",
        action="store_true"
    )

    parser.add_argument(
        "--report",
        default="v95_failures.json"
    )

    parser.add_argument(
        "--index",
        type=int,
        default=0
    )

    parser.add_argument(
        "--max-checks",
        type=int,
        default=200
    )

    parser.add_argument(
        "--output",
        default="minimized_failure.tac"
    )

    args = parser.parse_args()

    try:

        if args.demo:

            code = [
                "a = 2",
                "b = 3",
                "unused = 999",
                "c = a + b",
                "print c"
            ]

            optimizer = demo_optimizer

            print(
                "DEMO: intentionally broken optimizer",
                flush=True
            )

        else:

            code = load_failure(
                Path(args.report),
                args.index
            )

            module = importlib.import_module(
                "integrated_optimizer"
            )

            optimizer = getattr(
                module,
                "optimize"
            )

        result = minimize_failure(
            code,
            optimizer,
            max_checks=args.max_checks
        )

    except (
        FileNotFoundError,
        ImportError,
        AttributeError,
        ValueError,
        IndexError,
        json.JSONDecodeError
    ) as exc:

        print(
            f"MINIMIZER: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr
        )

        return 1

    # Save the minimized program
    output = Path(
        args.output
    )

    output.write_text(
        "\n".join(result.minimized) + "\n",
        encoding="utf-8"
    )

    # Save failure details
    report_path = output.with_suffix(
        ".json"
    )

    report_data = {
        "original_line_count": len(
            result.original
        ),
        "minimized_line_count": len(
            result.minimized
        ),
        "evaluations": result.evaluations,
        "failure_before": asdict(
            result.before
        ),
        "failure_after": asdict(
            result.after
        ),
        "minimized_tac": result.minimized
    }

    report_path.write_text(
        json.dumps(
            report_data,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print(
        "\n=== MINIMIZED TAC ==="
    )

    print(
        "\n".join(result.minimized)
    )

    print(
        f"\nRESULT: "
        f"{len(result.original)} -> "
        f"{len(result.minimized)} "
        f"instructions; "
        f"{result.evaluations} evaluations"
    )

    print(
        f"Failure category: "
        f"{result.after.kind}"
    )

    print(
        f"Saved: {output} "
        f"and {report_path}"
    )

    print(
        "BUG MINIMIZATION COMPLETED"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )