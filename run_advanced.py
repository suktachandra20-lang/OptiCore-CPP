# OptiCore - Final Advanced Backend Demo

from advanced_optimizer import (
    analyze_errors,
    run_advanced_pipeline
)

from correctness_checker import check_equivalence
from benchmark import benchmark_tac


code = [
    "a = 4",
    "b = 6",
    "i = 0",
    "label LOOP",
    "if i >= 3 goto END",
    "t = a * b",
    "print t",
    "i = i + 1",
    "goto LOOP",
    "label END",
    "print i"
]


if __name__ == "__main__":

    problems = analyze_errors(code)

    if problems:
        raise SystemExit(
            f"Error detector found: {problems}"
        )

    result = run_advanced_pipeline(code)
    optimized = result["optimized"]

    print("=== ORIGINAL TAC ===")
    print("\n".join(code))

    print("\n=== OPTIMIZED TAC ===")
    print("\n".join(optimized))

    print("\n=== OPTIMIZATION PASS TRACKER ===")

    for step in result["passes"]:
        print(
            f"{step['pass']}: "
            f"changed={step['changed']}, "
            f"lines={step['before_count']} "
            f"-> {step['after_count']}"
        )

    check = check_equivalence(
        code,
        optimized,
        [{}]
    )

    print("\n=== CORRECTNESS CHECK ===")
    print(
        f"{check['passed']}/"
        f"{check['total']} cases passed"
    )

    if not check["all_passed"]:
        raise SystemExit(
            "Verification failed; "
            "do not trust optimized output"
        )

    timings = benchmark_tac(
        code,
        optimized,
        repeats=10
    )

    print(
        "\n=== BENCHMARK "
        "(PYTHON INTERPRETER) ==="
    )

    print(
        "Original median (ms):",
        timings["original_median_ms"]
    )

    print(
        "Optimized median (ms):",
        timings["optimized_median_ms"]
    )

    print(
        "NOTE:",
        timings["note"]
    )