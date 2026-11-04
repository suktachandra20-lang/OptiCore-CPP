"""
OptiCore - Intelligent Optimizing Compiler

Advanced Register Allocation
Interference Graph Visualization
Graph Coloring Algorithm
Liveness Analysis

Member 2 - Optimization Backend
"""

from __future__ import annotations

import json

from cfg_analysis import build_cfg, parse_instruction


# ==========================================
# 1. INSTRUCTION LIVENESS ANALYSIS
# ==========================================

def instruction_liveness(code: list[str]) -> dict:

    lines = [
        line.strip()
        for line in code
        if line.strip()
    ]

    blocks = build_cfg(lines)

    n = len(lines)

    parsed = [
        parse_instruction(line)
        for line in lines
    ]

    labels = {
        inst.target: i
        for i, inst in enumerate(parsed)
        if inst.kind == "label"
    }

    successors = []

    for i, inst in enumerate(parsed):

        if inst.kind == "goto":

            nxt = [
                labels[inst.target]
            ]

        elif inst.kind == "if":

            nxt = [
                labels[inst.target]
            ]

            if i + 1 < n:
                nxt.append(i + 1)

        else:

            nxt = (
                [i + 1]
                if i + 1 < n
                else []
            )

        successors.append(
            sorted(set(nxt))
        )

    live_in = [
        set()
        for _ in range(n)
    ]

    live_out = [
        set()
        for _ in range(n)
    ]

    changed = True

    while changed:

        changed = False

        for i in range(n - 1, -1, -1):

            outgoing = set().union(
                *(
                    live_in[j]
                    for j in successors[i]
                )
            )

            killed = (
                {parsed[i].defines}
                if parsed[i].defines is not None
                else set()
            )

            incoming = (
                set(parsed[i].uses)
                | (outgoing - killed)
            )

            if (
                outgoing != live_out[i]
                or incoming != live_in[i]
            ):

                live_out[i] = outgoing
                live_in[i] = incoming

                changed = True

    return {
        "lines": lines,
        "blocks": len(blocks),
        "instructions": parsed,
        "successors": successors,
        "live_in": live_in,
        "live_out": live_out
    }


# ==========================================
# 2. BUILD INTERFERENCE GRAPH
# ==========================================

def build_interference_graph(
    code: list[str]
) -> dict[str, set[str]]:

    data = instruction_liveness(code)

    graph = {}

    def node(name):

        graph.setdefault(
            name,
            set()
        )

    def clique(names):

        ordered = sorted(names)

        for name in ordered:
            node(name)

        for index, first in enumerate(ordered):

            for second in ordered[index + 1:]:

                graph[first].add(second)
                graph[second].add(first)

    for inst, incoming, outgoing in zip(
        data["instructions"],
        data["live_in"],
        data["live_out"]
    ):

        clique(incoming)
        clique(outgoing)

        if inst.defines is not None:

            node(inst.defines)

            for other in outgoing - {inst.defines}:

                graph[inst.defines].add(other)
                graph[other].add(inst.defines)

        for used in inst.uses:
            node(used)

    return graph


# ==========================================
# 3. REGISTER ALLOCATION
# GRAPH COLORING (DSATUR)
# ==========================================

def allocate_registers(
    code: list[str],
    register_count: int = 3
) -> dict:

    if (
        not isinstance(register_count, int)
        or isinstance(register_count, bool)
    ):

        raise ValueError(
            "register_count must be a positive integer"
        )

    if not 1 <= register_count <= 32:

        raise ValueError(
            "register_count must be between 1 and 32"
        )

    graph = build_interference_graph(code)

    coloring = {}

    uncolored = set(graph)

    while uncolored:

        def priority(var):

            neighbor_colors = {
                coloring[x]
                for x in graph[var]
                if x in coloring
                and coloring[x] is not None
            }

            return (
                len(neighbor_colors),
                len(graph[var]),
                var
            )

        var = max(
            uncolored,
            key=priority
        )

        taken = {
            coloring[x]
            for x in graph[var]
            if x in coloring
        }

        chosen = next(
            (
                f"R{j}"
                for j in range(register_count)
                if f"R{j}" not in taken
            ),
            None
        )

        coloring[var] = chosen

        uncolored.remove(var)

    assignments = {
        var: coloring[var]
        for var in sorted(coloring)
    }

    spill_candidates = sorted(
        var
        for var in coloring
        if coloring[var] is None
    )

    edges = [
        [a, b]
        for a in sorted(graph)
        for b in sorted(graph[a])
        if a < b
    ]

    return {
        "register_count": register_count,
        "assignments": assignments,
        "spill_candidates": spill_candidates,
        "edges": edges,
        "note": (
            "Register allocation proposal only. "
            "Physical register code generation "
            "and spill insertion not implemented."
        )
    }


# ==========================================
# 4. GRAPH VISUALIZATION
# UPDATED COLOR DESIGN
# ==========================================

def interference_dot(
    code: list[str],
    register_count: int = 3
) -> str:

    result = allocate_registers(
        code,
        register_count
    )

    # Professional graph color styling
    lines = [
        "graph Interference {",

        'graph [overlap=false, '
        'bgcolor="#ffffff", '
        'pad="0.4", '
        'nodesep="0.7"];',

        'node [shape=circle, '
        'style=filled, '
        'fillcolor="#dbeafe", '
        'color="#2563eb", '
        'fontcolor="#111827", '
        'fontname="Arial", '
        'fontsize=14, '
        'penwidth=2];',

        'edge [color="#475569", '
        'penwidth=2];'
    ]

    # Create nodes
    for name, register in result["assignments"].items():

        label = (
            f"{name}\\n"
            f"{register or 'SPILL'}"
        )

        lines.append(
            f'  {json.dumps(name)} '
            f'[label={json.dumps(label)}];'
        )

    # Create connections
    for a, b in result["edges"]:

        lines.append(
            f"  {json.dumps(a)} -- "
            f"{json.dumps(b)};"
        )

    lines.append("}")

    return "\n".join(lines)


# ==========================================
# 5. STANDALONE DEMO
# ==========================================

if __name__ == "__main__":

    code = [
        "a = 4",
        "b = 6",
        "c = a + b",
        "d = a - b",
        "print c",
        "print d"
    ]

    print("===== OPTICORE REGISTER ALLOCATION =====")

    print("\nOriginal TAC:")

    for line in code:
        print(line)

    print("\nRegister Allocation:")

    result = allocate_registers(
        code,
        register_count=3
    )

    for variable, register in result["assignments"].items():

        print(
            f"{variable} -> "
            f"{register or 'SPILL'}"
        )

    print("\nSpill Candidates:")

    print(
        result["spill_candidates"]
    )

    print("\nInterference Edges:")

    for a, b in result["edges"]:

        print(
            f"{a} -- {b}"
        )

    print("\nGraphviz DOT Code:")

    print(
        interference_dot(
            code,
            register_count=3
        )
    )

    print(
        "\nREGISTER ALLOCATION ANALYSIS COMPLETED"
    )