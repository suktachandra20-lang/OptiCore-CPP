# OptiCore - Step 6
# CFG + Liveness Analysis + Safe DCE

from dataclasses import dataclass, field
import re

IDENT = re.compile(r"[A-Za-z_][A-Za-z_0-9]*\Z")
NUMBER = re.compile(r"-?\d+\Z")

OPERATORS = {"+", "-", "*"}
COMPARISONS = {"==", "!=", "<", ">", "<=", ">="}


def is_variable(token):
    return IDENT.fullmatch(token) is not None


def is_operand(token):
    return (
        is_variable(token)
        or NUMBER.fullmatch(token) is not None
    )


def operand_uses(*operands):
    return frozenset(
        x for x in operands if is_variable(x)
    )


@dataclass(frozen=True)
class Instruction:
    kind: str
    uses: frozenset = frozenset()
    defines: str | None = None
    target: str | None = None


# 1. PARSE TAC INSTRUCTIONS
def parse_instruction(line):
    p = line.strip().split()

    if not p:
        raise ValueError("Empty instruction")

    if (
        p[0] == "label"
        and len(p) == 2
        and is_variable(p[1])
    ):
        return Instruction("label", target=p[1])

    if (
        p[0] == "goto"
        and len(p) == 2
        and is_variable(p[1])
    ):
        return Instruction("goto", target=p[1])

    if (
        len(p) == 6
        and p[0] == "if"
        and is_operand(p[1])
        and p[2] in COMPARISONS
        and is_operand(p[3])
        and p[4] == "goto"
        and is_variable(p[5])
    ):
        return Instruction(
            "if",
            uses=operand_uses(p[1], p[3]),
            target=p[5]
        )

    if (
        len(p) == 2
        and p[0] == "print"
        and is_operand(p[1])
    ):
        return Instruction(
            "print",
            uses=operand_uses(p[1])
        )

    if (
        len(p) == 3
        and is_variable(p[0])
        and p[1] == "="
        and is_operand(p[2])
    ):
        return Instruction(
            "assign",
            uses=operand_uses(p[2]),
            defines=p[0]
        )

    if (
        len(p) == 5
        and is_variable(p[0])
        and p[1] == "="
        and is_operand(p[2])
        and p[3] in OPERATORS
        and is_operand(p[4])
    ):
        return Instruction(
            "assign",
            uses=operand_uses(p[2], p[4]),
            defines=p[0]
        )

    raise ValueError(
        f"Unsupported TAC instruction: {line!r}"
    )


# 2. BASIC BLOCK STRUCTURE
@dataclass
class BasicBlock:
    name: str
    lines: list[str]
    start: int

    successors: list[str] = field(
        default_factory=list
    )
    predecessors: list[str] = field(
        default_factory=list
    )

    use: set[str] = field(default_factory=set)
    defs: set[str] = field(default_factory=set)
    live_in: set[str] = field(default_factory=set)
    live_out: set[str] = field(default_factory=set)


# 3. BUILD CONTROL FLOW GRAPH
def build_cfg(code):
    lines = [
        line.strip()
        for line in code
        if line.strip()
    ]

    if not lines:
        return []

    ins = [
        parse_instruction(line)
        for line in lines
    ]

    label_positions = {}

    for i, inst in enumerate(ins):
        if inst.kind == "label":
            if inst.target in label_positions:
                raise ValueError(
                    f"Duplicate label: {inst.target}"
                )

            label_positions[inst.target] = i

    for inst in ins:
        if inst.kind in {"goto", "if"}:
            if inst.target not in label_positions:
                raise ValueError(
                    f"Undefined jump label: {inst.target}"
                )

    leaders = {0, *label_positions.values()}

    for i, inst in enumerate(ins):
        if inst.kind in {"goto", "if"}:
            if i + 1 < len(lines):
                leaders.add(i + 1)

    starts = sorted(leaders)
    blocks = []

    for j, start in enumerate(starts):
        end = (
            starts[j + 1]
            if j + 1 < len(starts)
            else len(lines)
        )

        blocks.append(
            BasicBlock(
                f"B{j + 1}",
                lines[start:end],
                start
            )
        )

    index_to_block = {}

    for block in blocks:
        for i in range(
            block.start,
            block.start + len(block.lines)
        ):
            index_to_block[i] = block.name

    label_to_block = {
        label: index_to_block[pos]
        for label, pos in label_positions.items()
    }

    names = {
        block.name: block
        for block in blocks
    }

    for j, block in enumerate(blocks):
        last = parse_instruction(
            block.lines[-1]
        )

        next_block = (
            blocks[j + 1].name
            if j + 1 < len(blocks)
            else None
        )

        destinations = []

        if last.kind in {"goto", "if"}:
            destinations.append(
                label_to_block[last.target]
            )

        if (
            last.kind != "goto"
            and next_block is not None
        ):
            destinations.append(next_block)

        block.successors = list(
            dict.fromkeys(destinations)
        )

        for target in block.successors:
            names[target].predecessors.append(
                block.name
            )

    return blocks


# 4. LIVENESS ANALYSIS
def analyze_liveness(blocks):
    by_name = {
        block.name: block
        for block in blocks
    }

    for block in blocks:
        block.use.clear()
        block.defs.clear()
        block.live_in.clear()
        block.live_out.clear()

        for line in block.lines:
            inst = parse_instruction(line)

            block.use.update(
                inst.uses - block.defs
            )

            if inst.defines is not None:
                block.defs.add(inst.defines)

    changed = True

    while changed:
        changed = False

        for block in reversed(blocks):
            live_out = set().union(
                *(
                    by_name[s].live_in
                    for s in block.successors
                )
            )

            live_in = (
                block.use
                | (live_out - block.defs)
            )

            if (
                live_in != block.live_in
                or live_out != block.live_out
            ):
                block.live_in = live_in
                block.live_out = live_out
                changed = True

    return blocks


# 5. CFG-BASED DEAD CODE ELIMINATION
def dead_code_elimination_cfg(code):
    current = [
        line.strip()
        for line in code
        if line.strip()
    ]

    for _ in range(len(current) + 1):
        blocks = analyze_liveness(
            build_cfg(current)
        )

        result = []

        for block in blocks:
            live = set(block.live_out)
            kept = []

            for line in reversed(block.lines):
                inst = parse_instruction(line)

                if (
                    inst.kind == "assign"
                    and inst.defines not in live
                ):
                    continue

                if inst.defines is not None:
                    live.discard(inst.defines)

                live.update(inst.uses)
                kept.append(line)

            result.extend(reversed(kept))

        if result == current:
            return result

        current = result

    raise RuntimeError(
        "Dead-code elimination did not converge"
    )


# 6. PRINT CFG INFORMATION
def print_cfg(blocks):
    for block in blocks:
        print(
            f"\n{block.name}: {block.lines}"
        )
        print(
            "  Successors:",
            block.successors
        )
        print(
            "  LIVE_IN:",
            sorted(block.live_in)
        )
        print(
            "  LIVE_OUT:",
            sorted(block.live_out)
        )


# 7. DEMO PROGRAM
if __name__ == "__main__":
    code = [
        "x = 5",
        "unused = 99",
        "if x > 0 goto POS",
        "y = 100",
        "print y",
        "goto END",
        "label POS",
        "t1 = x + 1",
        "t2 = 25",
        "print t1",
        "label END",
        "print x"
    ]

    print("===== ORIGINAL TAC =====")
    print("\n".join(code))

    print("\n===== CFG + LIVENESS =====")

    blocks = analyze_liveness(
        build_cfg(code)
    )

    print_cfg(blocks)

    result = dead_code_elimination_cfg(code)

    print("\n===== OPTIMIZED TAC =====")
    print("\n".join(result))

    print(
        "\nRemoved instructions:",
        len(code) - len(result)
    )