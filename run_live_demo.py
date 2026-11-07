"""OptiCore Live Trace Console Demo."""

from live_optimization import iter_trace


sample = [
    "a = 4",
    "b = 6",
    "c = a + b",
    "d = a - b",
    "print c",
    "print d",
]


print(
    "=== OPTICORE LIVE TRACE DEMO ==="
)

for i, step in enumerate(
    iter_trace(sample),
    start=1,
):

    print(
        f"Step {i}: {step.name}"
    )

    print(
        f"  instructions: "
        f"{len(step.before)} -> "
        f"{len(step.after)}"
    )

    print(
        "  TAC:",
        " | ".join(step.after),
    )


print(
    "LIVE DEMO COMPLETED"
)