# OptiCore - Interpreter Benchmark

from statistics import median
from time import perf_counter
from correctness_checker import execute_tac


def benchmark_tac(
    original,
    optimized,
    inputs=None,
    repeats=15,
    max_steps=10000
):

    if not 1 <= repeats <= 1000:
        raise ValueError(
            "repeats must be from 1 to 1000"
        )

    inputs = dict(inputs or {})

    before_output = execute_tac(
        original,
        inputs,
        max_steps
    )

    after_output = execute_tac(
        optimized,
        inputs,
        max_steps
    )

    if before_output != after_output:
        raise ValueError(
            "Outputs differ; do not benchmark "
            "an incorrect optimization"
        )

    def measure(lines):
        samples = []

        for _ in range(repeats):
            start = perf_counter()

            execute_tac(
                lines,
                inputs,
                max_steps
            )

            duration = (
                perf_counter() - start
            ) * 1000

            samples.append(duration)

        return round(
            median(samples),
            4
        )

    original_ms = measure(original)
    optimized_ms = measure(optimized)

    return {
        "original_instructions": len(original),
        "optimized_instructions": len(optimized),
        "original_median_ms": original_ms,
        "optimized_median_ms": optimized_ms,
        "repeats": repeats,
        "note": (
            "Python TAC interpreter timing only; "
            "not native execution speed"
        )
    }