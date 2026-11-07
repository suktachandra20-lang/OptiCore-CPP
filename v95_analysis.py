"""OptiCore v9.5: CFG, dominators, loops and liveness.

Supported TAC:
L: / label L
goto L
if EXPR goto L
ifFalse EXPR goto L
x = EXPR
print EXPR
return [EXPR]
nop
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

NAME = r"[A-Za-z_]\w*"


@dataclass(frozen=True)
class Instruction:
    raw: str
    kind: str
    uses: frozenset[str] = frozenset()
    defines: str | None = None
    target: str | None = None
    expr: str | None = None


def expression_variables(expr: str) -> frozenset[str]:
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise ValueError(
            f"Unsupported TAC expression: {expr!r}"
        ) from exc

    allowed = (
        ast.Expression, ast.Constant, ast.Name, ast.Load,
        ast.BinOp, ast.UnaryOp, ast.Compare, ast.BoolOp,
        ast.Add, ast.Sub, ast.Mult, ast.Div,
        ast.FloorDiv, ast.Mod, ast.USub, ast.UAdd,
        ast.Eq, ast.NotEq, ast.Lt, ast.LtE,
        ast.Gt, ast.GtE, ast.And, ast.Or, ast.Not,
    )

    if any(
        not isinstance(node, allowed)
        for node in ast.walk(tree)
    ):
        raise ValueError(
            f"Unsupported TAC expression: {expr!r}"
        )

    return frozenset(
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
    )


def parse_instruction(line: str) -> Instruction:
    s = line.strip()

    if not s:
        raise ValueError("Blank instruction")

    match = re.fullmatch(rf"({NAME}):", s)
    if match:
        return Instruction(
            s, "label", target=match.group(1)
        )

    match = re.fullmatch(
        rf"label\s+({NAME})", s, re.I
    )
    if match:
        return Instruction(
            s, "label", target=match.group(1)
        )

    match = re.fullmatch(
        rf"goto\s+({NAME})", s, re.I
    )
    if match:
        return Instruction(
            s, "goto", target=match.group(1)
        )

    match = re.fullmatch(
        rf"(ifFalse|ifnot|if)\s+(.+?)\s+goto\s+({NAME})",
        s,
        re.I,
    )
    if match:
        cond = match.group(2)
        kind = (
            "if_false"
            if match.group(1).lower() != "if"
            else "if"
        )
        return Instruction(
            s,
            kind,
            expression_variables(cond),
            target=match.group(3),
            expr=cond,
        )

    match = re.fullmatch(
        r"print\s+(.+)", s, re.I
    )
    if match:
        expr = match.group(1)
        return Instruction(
            s,
            "print",
            expression_variables(expr),
            expr=expr,
        )

    match = re.fullmatch(
        r"return(?:\s+(.+))?", s, re.I
    )
    if match:
        expr = match.group(1)
        return Instruction(
            s,
            "return",
            expression_variables(expr)
            if expr
            else frozenset(),
            expr=expr,
        )

    match = re.fullmatch(
        rf"({NAME})\s*=\s*(.+)", s
    )
    if match:
        expr = match.group(2)
        return Instruction(
            s,
            "assign",
            expression_variables(expr),
            defines=match.group(1),
            expr=expr,
        )

    if s.lower() == "nop":
        return Instruction(s, "nop")

    raise ValueError(
        f"Unsupported TAC instruction: {s!r}"
    )


@dataclass(frozen=True)
class Block:
    name: str
    start: int
    end: int
    successors: tuple[str, ...]
    predecessors: tuple[str, ...]


@dataclass
class CFG:
    instructions: list[Instruction]
    labels: dict[str, int]
    instruction_successors: list[tuple[int, ...]]
    blocks: list[Block]
    entry: str | None


def build_cfg(code: list[str] | str) -> CFG:
    lines = (
        code.splitlines()
        if isinstance(code, str)
        else code
    )

    instructions = [
        parse_instruction(line)
        for line in lines
        if line.strip()
    ]

    n = len(instructions)
    labels: dict[str, int] = {}

    for i, inst in enumerate(instructions):
        if inst.kind == "label":
            assert inst.target is not None

            if inst.target in labels:
                raise ValueError(
                    f"Duplicate label: {inst.target}"
                )

            labels[inst.target] = i

    instruction_successors = []
    leaders = {0} if n else set()

    for i, inst in enumerate(instructions):
        if inst.kind in {
            "goto", "if", "if_false"
        }:
            if inst.target not in labels:
                raise ValueError(
                    f"Unknown label: {inst.target}"
                )

            dest = labels[inst.target]
            successors = [dest]
            leaders.add(dest)

            if (
                inst.kind != "goto"
                and i + 1 < n
            ):
                successors.append(i + 1)

        elif inst.kind == "return":
            successors = []

        else:
            successors = (
                [i + 1]
                if i + 1 < n
                else []
            )

        instruction_successors.append(
            tuple(sorted(set(successors)))
        )

        if (
            inst.kind in {
                "goto", "if", "if_false", "return"
            }
            and i + 1 < n
        ):
            leaders.add(i + 1)

        if inst.kind == "label":
            leaders.add(i)

    starts = sorted(leaders)

    spans = [
        (
            start,
            starts[j + 1] - 1
            if j + 1 < len(starts)
            else n - 1,
        )
        for j, start in enumerate(starts)
    ]

    index_to_block = {
        i: f"B{k}"
        for k, (start, end) in enumerate(spans)
        for i in range(start, end + 1)
    }

    successor_names = {}

    predecessor_names = {
        f"B{k}": set()
        for k in range(len(spans))
    }

    for k, (start, end) in enumerate(spans):
        name = f"B{k}"

        next_blocks = tuple(
            sorted(
                {
                    index_to_block[s]
                    for s in instruction_successors[end]
                },
                key=lambda b: int(b[1:]),
            )
        )

        successor_names[name] = next_blocks

        for dest in next_blocks:
            predecessor_names[dest].add(name)

    blocks = [
        Block(
            f"B{k}",
            start,
            end,
            successor_names[f"B{k}"],
            tuple(
                sorted(
                    predecessor_names[f"B{k}"],
                    key=lambda b: int(b[1:]),
                )
            ),
        )
        for k, (start, end) in enumerate(spans)
    ]

    return CFG(
        instructions,
        labels,
        instruction_successors,
        blocks,
        "B0" if blocks else None,
    )


def reachable_blocks(cfg: CFG) -> set[str]:
    if cfg.entry is None:
        return set()

    by_name = {
        b.name: b
        for b in cfg.blocks
    }

    seen = set()
    stack = [cfg.entry]

    while stack:
        name = stack.pop()

        if name not in seen:
            seen.add(name)
            stack.extend(
                by_name[name].successors
            )

    return seen


@dataclass
class DominanceReport:
    cfg: CFG
    dominators: dict[str, set[str]]
    immediate_dominator: dict[str, str | None]
    back_edges: list[tuple[str, str]]
    natural_loops: list[dict[str, object]]
    unreachable: list[str]


def analyze_dominance_and_loops(
    code: list[str] | str,
) -> DominanceReport:

    cfg = build_cfg(code)
    reachable = reachable_blocks(cfg)

    names = [
        b.name
        for b in cfg.blocks
        if b.name in reachable
    ]

    by_name = {
        b.name: b
        for b in cfg.blocks
    }

    dom = {
        name: (
            {name}
            if name == cfg.entry
            else set(reachable)
        )
        for name in names
    }

    changed = True

    while changed:
        changed = False

        for name in names:
            if name == cfg.entry:
                continue

            preds = [
                p
                for p in by_name[name].predecessors
                if p in reachable
            ]

            intersection = (
                set.intersection(
                    *(dom[p] for p in preds)
                )
                if preds
                else set()
            )

            new_dom = {name} | intersection

            if new_dom != dom[name]:
                dom[name] = new_dom
                changed = True

    idom = {}

    for name in names:
        strict = dom[name] - {name}

        idom[name] = (
            max(
                strict,
                key=lambda p: len(dom[p]),
            )
            if strict
            else None
        )

    back_edges = []
    loops = []

    for tail in names:
        for header in by_name[tail].successors:

            if header in dom[tail]:
                back_edges.append(
                    (tail, header)
                )

                members = {header, tail}

                stack = (
                    [tail]
                    if tail != header
                    else []
                )

                while stack:
                    node = stack.pop()

                    for pred in (
                        by_name[node].predecessors
                    ):
                        if (
                            pred in reachable
                            and pred not in members
                        ):
                            members.add(pred)

                            if pred != header:
                                stack.append(pred)

                loops.append(
                    {
                        "header": header,
                        "latch": tail,
                        "blocks": sorted(
                            members,
                            key=lambda b: int(b[1:]),
                        ),
                    }
                )

    unreachable = [
        b.name
        for b in cfg.blocks
        if b.name not in reachable
    ]

    return DominanceReport(
        cfg,
        dom,
        idom,
        back_edges,
        loops,
        unreachable,
    )


def dominator_tree_dot(
    report: DominanceReport,
) -> str:

    lines = [
        "digraph Dominators {",
        '  graph [bgcolor="white"];',
        '  node [shape=box,style=filled,'
        'fillcolor="#dbeafe",'
        'fontcolor="#111827"];',
        '  edge [color="#2563eb"];',
    ]

    for name in report.dominators:
        lines.append(
            f'  "{name}";'
        )

    for name, parent in (
        report.immediate_dominator.items()
    ):
        if parent is not None:
            lines.append(
                f'  "{parent}" -> "{name}";'
            )

    lines.append("}")

    return "\n".join(lines)


def instruction_liveness(
    code: list[str] | str,
) -> tuple[
    CFG,
    list[set[str]],
    list[set[str]],
]:

    cfg = build_cfg(code)
    n = len(cfg.instructions)

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
            inst = cfg.instructions[i]

            outgoing = set().union(
                *(
                    live_in[j]
                    for j in (
                        cfg.instruction_successors[i]
                    )
                )
            )

            killed = (
                {inst.defines}
                if inst.defines
                else set()
            )

            incoming = (
                set(inst.uses)
                | (outgoing - killed)
            )

            if (
                incoming != live_in[i]
                or outgoing != live_out[i]
            ):
                live_in[i] = incoming
                live_out[i] = outgoing
                changed = True

    return cfg, live_in, live_out