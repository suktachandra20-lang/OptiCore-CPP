"""OptiCore v9.5: Register Spilling Simulation.

Important:
This module analyzes register pressure and produces
illustrative memory operations. It does NOT rewrite
executable TAC or generate machine instructions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from v95_analysis import instruction_liveness


@dataclass
class SpillReport:
    registers: int
    graph: dict[str, set[str]]
    assignments: dict[str, str | None]
    slots: dict[str, str]
    events: list[dict[str, object]]
    loads: int
    stores: int


def interference_graph(
    code: list[str] | str,
) -> dict[str, set[str]]:

    cfg, live_in, live_out = (
        instruction_liveness(code)
    )

    graph: dict[str, set[str]] = {}

    def connect(a: str, b: str) -> None:
        graph.setdefault(a, set())
        graph.setdefault(b, set())

        if a != b:
            graph[a].add(b)
            graph[b].add(a)

    def clique(names: set[str]) -> None:
        ordered = sorted(names)

        for a in ordered:
            graph.setdefault(a, set())

        for i, a in enumerate(ordered):
            for b in ordered[i + 1:]:
                connect(a, b)

    for inst, incoming, outgoing in zip(
        cfg.instructions,
        live_in,
        live_out,
    ):
        clique(incoming)
        clique(outgoing)

        for name in inst.uses:
            graph.setdefault(name, set())

        if inst.defines:
            graph.setdefault(
                inst.defines,
                set(),
            )

            for name in (
                outgoing - {inst.defines}
            ):
                connect(
                    inst.defines,
                    name,
                )

    return graph


def simulate_spilling(
    code: list[str] | str,
    registers: int = 2,
) -> SpillReport:

    if (
        isinstance(registers, bool)
        or not isinstance(registers, int)
        or not 1 <= registers <= 32
    ):
        raise ValueError(
            "registers must be an integer from 1 to 32"
        )

    graph = interference_graph(code)

    assignment = {}
    remaining = set(graph)

    while remaining:

        def key(name):
            saturation = {
                assignment[n]
                for n in graph[name]
                if n in assignment
                and assignment[n] is not None
            }

            return (
                len(saturation),
                len(graph[name]),
                name,
            )

        name = max(
            remaining,
            key=key,
        )

        taken = {
            assignment[n]
            for n in graph[name]
            if n in assignment
        }

        chosen = next(
            (
                f"R{i}"
                for i in range(registers)
                if f"R{i}" not in taken
            ),
            None,
        )

        assignment[name] = chosen
        remaining.remove(name)

    assignment = {
        name: assignment[name]
        for name in sorted(assignment)
    }

    spilled = sorted(
        name
        for name, register in (
            assignment.items()
        )
        if register is None
    )

    slots = {
        name: f"[spill_{i}]"
        for i, name in enumerate(spilled)
    }

    cfg, _, _ = instruction_liveness(code)

    events = []
    loads = 0
    stores = 0

    for pc, inst in enumerate(
        cfg.instructions
    ):
        before = [
            f"LOAD {slots[v]}  ; use {v}"
            for v in sorted(
                inst.uses & slots.keys()
            )
        ]

        after = (
            [
                f"STORE {inst.defines} -> "
                f"{slots[inst.defines]}"
            ]
            if inst.defines in slots
            else []
        )

        loads += len(before)
        stores += len(after)

        events.append(
            {
                "pc": pc,
                "instruction": inst.raw,
                "before": before,
                "after": after,
            }
        )

    return SpillReport(
        registers,
        graph,
        assignment,
        slots,
        events,
        loads,
        stores,
    )


def interference_dot(
    report: SpillReport,
) -> str:

    lines = [
        "graph Interference {",
        '  graph [bgcolor="white",'
        'overlap=false];',
        '  node [shape=circle,'
        'style=filled,fillcolor="#dbeafe",'
        'color="#2563eb",'
        'fontcolor="#111827"];',
        '  edge [color="#475569"];',
    ]

    for name, register in (
        report.assignments.items()
    ):
        label = (
            f"{name}\\n"
            f"{register or report.slots[name]}"
        )

        lines.append(
            f"  {json.dumps(name)} "
            f"[label={json.dumps(label)}];"
        )

    for a in sorted(report.graph):
        for b in sorted(report.graph[a]):
            if a < b:
                lines.append(
                    f"  {json.dumps(a)}"
                    f" -- {json.dumps(b)};"
                )

    lines.append("}")

    return "\n".join(lines)