# OptiCore - Advanced Optimization Backend
# Strength Reduction + LICM + Error Detection
# + Optimization Pass Tracking

from cfg_analysis import build_cfg, parse_instruction
from integrated_optimizer import optimize as existing_optimize


# 1. STRENGTH REDUCTION
def strength_reduction(code):
    result = []

    for line in code:
        inst = parse_instruction(line)
        p = line.split()

        if (
            inst.kind == "assign"
            and len(p) == 5
            and p[3] == "*"
        ):
            name, _, a, _, b = p

            if b == "2" and not a.lstrip("-").isdigit():
                line = f"{name} = {a} + {a}"

            elif a == "2" and not b.lstrip("-").isdigit():
                line = f"{name} = {b} + {b}"

            elif b == "1":
                line = f"{name} = {a}"

            elif a == "1":
                line = f"{name} = {b}"

        result.append(line)

    return result


def _numeric(s):
    return s.lstrip("-").isdigit()


# 2. CONSERVATIVE LOOP-INVARIANT CODE MOTION
def safe_licm(code):
    lines = [
        line.strip()
        for line in code
        if line.strip()
    ]

    instructions = [
        parse_instruction(x)
        for x in lines
    ]

    build_cfg(lines)

    for header, h in enumerate(instructions):

        if (
            h.kind != "label"
            or header + 3 >= len(lines)
        ):
            continue

        guard = instructions[header + 1]

        if guard.kind != "if":
            continue

        loop_label = h.target
        exit_label = guard.target
        guard_p = lines[header + 1].split()

        if not _numeric(guard_p[3]):
            continue

        # Require a simple preheader
        prefix = instructions[:header]

        if (
            not prefix
            or any(
                i.kind != "assign"
                for i in prefix
            )
        ):
            continue

        # Identify constants defined before loop
        constant_defs = set()

        for line in lines[:header]:
            p = line.split()

            if (
                len(p) == 3
                and _numeric(p[2])
            ):
                constant_defs.add(p[0])

            else:
                constant_defs.discard(p[0])

        # Find unique backedge
        backedges = [
            i
            for i in range(
                header + 2,
                len(lines)
            )
            if (
                instructions[i].kind == "goto"
                and instructions[i].target
                == loop_label
            )
        ]

        if len(backedges) != 1:
            continue

        back = backedges[0]

        if (
            back + 1 >= len(lines)
            or lines[back + 1]
            != f"label {exit_label}"
        ):
            continue

        # Reject additional entries to loop
        if any(
            i.kind in {"goto", "if"}
            and i.target == loop_label
            for j, i in enumerate(instructions)
            if j != back
        ):
            continue

        body = instructions[header + 2:back]

        # Only pure assignments and print
        if any(
            i.kind not in {"assign", "print"}
            for i in body
        ):
            continue

        # Reject extra exits
        if any(
            i.kind in {"goto", "if"}
            and i.target == exit_label
            for j, i in enumerate(instructions)
            if j != header + 1
        ):
            continue

        all_defs = [
            i.defines
            for i in body
            if i.defines is not None
        ]

        # Find an invariant expression
        for candidate in range(
            header + 2,
            back
        ):
            p = lines[candidate].split()
            inst = instructions[candidate]

            if (
                inst.kind != "assign"
                or len(p) != 5
            ):
                continue

            dest, _, a, op, b = p

            if (
                all_defs.count(dest) != 1
                or dest in {a, b}
            ):
                continue

            # Operands must be known before loop
            if not all(
                _numeric(x)
                or x in constant_defs
                for x in (a, b)
            ):
                continue

            # Operands cannot change in loop
            if any(
                x in all_defs
                for x in (a, b)
                if not _numeric(x)
            ):
                continue

            # Destination cannot be used outside body
            if any(
                dest in i.uses
                or i.defines == dest
                for j, i in enumerate(instructions)
                if not (
                    header + 2 <= j < back
                )
            ):
                continue

            # Destination cannot be read before assignment
            if any(
                dest in i.uses
                for i in instructions[
                    header + 2:candidate
                ]
            ):
                continue

            # Move invariant assignment to preheader
            rewritten = (
                lines[:header]
                + [lines[candidate]]
                + lines[header:candidate]
            )

            rewritten += lines[candidate + 1:]

            return rewritten

    return lines


# 3. ADVANCED ERROR DETECTION
def analyze_errors(code, initial_variables=()):
    lines = [
        x.strip()
        for x in code
        if x.strip()
    ]

    try:
        blocks = build_cfg(lines)

    except ValueError as exc:
        return [{
            "line": None,
            "error": str(exc)
        }]

    if not blocks:
        return []

    by_name = {
        b.name: b
        for b in blocks
    }

    # Find reachable basic blocks
    reachable = set()
    pending = [blocks[0].name]

    while pending:
        name = pending.pop()

        if name in reachable:
            continue

        reachable.add(name)
        pending.extend(
            by_name[name].successors
        )

    # Collect possible definitions
    definitions = set(initial_variables)

    for block in blocks:
        for line in block.lines:
            inst = parse_instruction(line)

            if inst.defines is not None:
                definitions.add(inst.defines)

    assigned_in = {
        b.name: set(definitions)
        for b in blocks
    }

    assigned_out = {
        b.name: set(definitions)
        for b in blocks
    }

    assigned_in[blocks[0].name] = set(
        initial_variables
    )

    # Forward must-defined data-flow analysis
    changed = True

    while changed:
        changed = False

        for block in blocks:

            if block.name not in reachable:
                continue

            if block.name == blocks[0].name:
                incoming = set(initial_variables)

            else:
                predecessors = [
                    p
                    for p in block.predecessors
                    if p in reachable
                ]

                if not predecessors:
                    continue

                incoming = set.intersection(
                    *(
                        assigned_out[p]
                        for p in predecessors
                    )
                )

            outgoing = set(incoming)

            for line in block.lines:
                inst = parse_instruction(line)

                if inst.defines is not None:
                    outgoing.add(inst.defines)

            if (
                incoming != assigned_in[block.name]
                or outgoing != assigned_out[block.name]
            ):
                assigned_in[block.name] = incoming
                assigned_out[block.name] = outgoing
                changed = True

    # Report potentially uninitialized reads
    errors = []

    for block in blocks:

        if block.name not in reachable:
            continue

        assigned = set(
            assigned_in[block.name]
        )

        for offset, line in enumerate(block.lines):
            inst = parse_instruction(line)

            for var in sorted(
                inst.uses - assigned
            ):
                errors.append({
                    "line": block.start + offset + 1,
                    "error": (
                        f"Variable '{var}' "
                        "may be uninitialized"
                    )
                })

            if inst.defines is not None:
                assigned.add(inst.defines)

    return errors


# 4. INTEGRATED ADVANCED PIPELINE
def run_advanced_pipeline(
    code,
    initial_variables=()
):
    original = [
        line.strip()
        for line in code
        if line.strip()
    ]

    errors = analyze_errors(
        original,
        initial_variables
    )

    if errors:
        raise ValueError(
            f"TAC validation failed: {errors}"
        )

    steps = []
    current = original

    passes = [
        (
            "Strength Reduction",
            strength_reduction
        ),
        (
            "Conservative LICM",
            safe_licm
        ),
        (
            "Existing Integrated Optimizer",
            existing_optimize
        )
    ]

    for name, fn in passes:
        updated = fn(current)

        steps.append({
            "pass": name,
            "changed": updated != current,
            "before_count": len(current),
            "after_count": len(updated),
            "before": list(current),
            "after": list(updated)
        })

        current = updated

    return {
        "original": original,
        "optimized": current,
        "passes": steps,
        "instruction_reduction": (
            len(original) - len(current)
        )
    }