# OptiCore - Control Flow Optimization
# Member 2: Optimization Backend

COMPARISONS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
}


# 1. FIND ALL LABELS
def get_labels(code):
    labels = {}

    for index, line in enumerate(code):
        parts = line.split()

        if parts and parts[0] == "label":
            if len(parts) != 2:
                raise ValueError(f"Invalid label: {line}")

            if parts[1] in labels:
                raise ValueError(
                    f"Duplicate label: {parts[1]}"
                )

            labels[parts[1]] = index

    return labels


# 2. FIND JUMP TARGET
def jump_target(line):
    p = line.split()

    if not p:
        return None

    if p[0] == "goto":
        if len(p) != 2:
            raise ValueError(f"Invalid goto: {line}")
        return p[1]

    if p[0] == "if":
        if (
            len(p) != 6
            or p[2] not in COMPARISONS
            or p[4] != "goto"
        ):
            raise ValueError(
                f"Invalid if statement: {line}"
            )

        return p[5]

    return None


# 3. VALIDATE ALL JUMPS
def validate_jumps(code):
    labels = get_labels(code)

    for line in code:
        target = jump_target(line)

        if target is not None and target not in labels:
            raise ValueError(
                f"Undefined jump label: {target}"
            )


# 4. CONSTANT CONDITION OPTIMIZATION
def fold_conditions(code):
    result = []

    for line in code:
        p = line.split()

        if (
            p
            and p[0] == "if"
            and p[1].lstrip("-").isdigit()
            and p[3].lstrip("-").isdigit()
        ):
            a = int(p[1])
            b = int(p[3])

            if COMPARISONS[p[2]](a, b):
                result.append(f"goto {p[5]}")

            # False condition: remove the jump.
        else:
            result.append(line)

    return result


# 5. UNREACHABLE CODE ELIMINATION
def remove_unreachable(code):
    if not code:
        return []

    labels = get_labels(code)

    visited = set()
    pending = [0]

    while pending:
        i = pending.pop()

        if i in visited or i < 0 or i >= len(code):
            continue

        visited.add(i)
        p = code[i].split()

        if p[0] == "goto":
            pending.append(labels[p[1]])

        elif p[0] == "if":
            pending.extend([
                i + 1,
                labels[p[5]]
            ])

        else:
            pending.append(i + 1)

    return [
        line
        for i, line in enumerate(code)
        if i in visited
    ]


# 6. REMOVE REDUNDANT GOTO
def remove_redundant_gotos(code):
    labels = get_labels(code)
    result = []

    for i, line in enumerate(code):
        p = line.split()

        if p and p[0] == "goto":
            target_i = labels[p[1]]

            if target_i > i and all(
                code[j].startswith("label ")
                for j in range(i + 1, target_i + 1)
            ):
                continue

        result.append(line)

    return result


# 7. REMOVE UNUSED LABELS
def remove_unused_labels(code):
    targets = {
        t
        for line in code
        if (t := jump_target(line)) is not None
    }

    return [
        line
        for line in code
        if (
            not line.startswith("label ")
            or line.split()[1] in targets
        )
    ]


# 8. MAIN CONTROL FLOW OPTIMIZER
def control_flow_optimize(code):
    lines = [
        line.strip()
        for line in code
        if line.strip()
    ]

    validate_jumps(lines)

    lines = fold_conditions(lines)
    lines = remove_unreachable(lines)
    lines = remove_redundant_gotos(lines)
    lines = remove_unused_labels(lines)

    return lines


# 9. TEST INPUT
if __name__ == "__main__":

    code = [
        "x = 10",
        "if 5 > 2 goto YES",
        "print 0",
        "goto END",
        "label YES",
        "print x",
        "label END"
    ]

    result = control_flow_optimize(code)

    print("===== ORIGINAL TAC =====")

    for line in code:
        print(line)

    print("\n===== OPTIMIZED TAC =====")

    for line in result:
        print(line)

    print(
        "\nRemoved instructions:",
        len(code) - len(result)
    )