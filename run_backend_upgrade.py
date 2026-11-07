"""Run OptiCore backend upgrade demo."""

from differential_testing import run_differential_tests

from optimizer_trace import trace_optimization

from register_allocation import (
    allocate_registers,
    interference_dot
)

from ssa_phi_preview import preview_diamond_ssa


if __name__ == "__main__":

    print("===== OPTICORE BACKEND UPGRADE =====")

    original = [
        "a = 4",
        "b = 6",
        "x = a + b",
        "y = x * 2",
        "print y"
    ]

    trace = trace_optimization(original)

    print("\nBEFORE: ", original)
    print("AFTER:  ", trace["optimized"])

    print(
        "TRACKED STAGES:",
        len(trace["passes"])
    )

    for stage in trace["passes"]:

        if stage["changed"]:

            print(
                "  *",
                stage["pass"],
                f"(round {stage['round']})"
            )

    sample = [
        "a = inputA",
        "b = inputB",
        "c = a + b",
        "d = a - b",
        "print c",
        "print d"
    ]

    allocation = allocate_registers(
        sample,
        register_count=2
    )

    print(
        "\nREGISTER ALLOCATION:",
        allocation["assignments"]
    )

    print(
        "SPILL CANDIDATES:",
        allocation["spill_candidates"]
    )

    print(
        "\nINTERFERENCE GRAPH DOT:\n",
        interference_dot(
            sample,
            register_count=2
        )
    )

    diamond = [
        "if flag > 0 goto THEN",
        "x = 10",
        "goto JOIN",
        "label THEN",
        "x = 20",
        "label JOIN",
        "print x"
    ]

    print("\nSSA PHI PREVIEW:")

    for line in preview_diamond_ssa(diamond):
        print(" ", line)

    result = run_differential_tests(
        count=300
    )

    print(
        "\nDIFFERENTIAL TESTING:",
        result
    )

    if not result["all_passed"]:
        raise SystemExit(
            "FAIL: see opticore_failures.json "
            "for a counterexample"
        )

    print(
        "\nALL BACKEND UPGRADE DEMOS PASSED"
    )