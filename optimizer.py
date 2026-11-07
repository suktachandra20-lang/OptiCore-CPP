# OptiCore - Optimization Backend
# Four Optimization Algorithms

def is_number(value):
    return value.lstrip("-").isdigit()


def is_variable(value):
    return value.isidentifier()


# 1. CONSTANT FOLDING
def constant_folding(code):
    optimized = []

    for line in code:
        p = line.split()

        if len(p) == 5 and p[1] == "=":
            name, _, a, op, b = p

            if is_number(a) and is_number(b):
                a, b = int(a), int(b)

                if op == "+":
                    result = a + b
                elif op == "-":
                    result = a - b
                elif op == "*":
                    result = a * b
                else:
                    optimized.append(line)
                    continue

                optimized.append(f"{name} = {result}")
                continue

        optimized.append(line)

    return optimized


# 2. CONSTANT PROPAGATION
def constant_propagation(code):
    values = {}
    optimized = []

    for line in code:
        p = line.split()

        if len(p) == 3 and p[1] == "=":
            name, _, value = p
            value = values.get(value, value)

            optimized.append(f"{name} = {value}")

            if is_number(value):
                values[name] = value
            else:
                values.pop(name, None)

        elif len(p) == 5 and p[1] == "=":
            name, _, a, op, b = p

            a = values.get(a, a)
            b = values.get(b, b)

            optimized.append(
                f"{name} = {a} {op} {b}"
            )
            values.pop(name, None)

        elif len(p) == 2 and p[0] == "print":
            value = values.get(p[1], p[1])
            optimized.append(f"print {value}")

        else:
            raise ValueError(f"Unsupported TAC: {line}")

    return optimized


# 3. COMMON SUBEXPRESSION ELIMINATION
def common_subexpression_elimination(code):
    seen = {}
    optimized = []

    for line in code:
        p = line.split()

        if len(p) in (3, 5) and p[1] == "=":
            name = p[0]

            # Remove expressions invalidated by assignment
            seen = {
                expr: var
                for expr, var in seen.items()
                if name not in (expr[0], expr[2])
                and var != name
            }

            if len(p) == 5 and p[3] in ("+", "-", "*"):
                _, _, a, op, b = p
                expression = (a, op, b)

                if expression in seen:
                    optimized.append(
                        f"{name} = {seen[expression]}"
                    )
                else:
                    optimized.append(line)
                    seen[expression] = name
            else:
                optimized.append(line)
        else:
            optimized.append(line)

    return optimized


# 4. DEAD CODE ELIMINATION
def dead_code_elimination(code):
    live = set()
    optimized = []

    for line in reversed(code):
        p = line.split()

        if len(p) == 2 and p[0] == "print":
            optimized.append(line)

            if is_variable(p[1]):
                live.add(p[1])

        elif len(p) in (3, 5) and p[1] == "=":
            name = p[0]

            if name not in live:
                continue

            live.remove(name)

            operands = (
                [p[2]] if len(p) == 3
                else [p[2], p[4]]
            )

            for value in operands:
                if is_variable(value):
                    live.add(value)

            optimized.append(line)

        else:
            raise ValueError(f"Unsupported TAC: {line}")

    return list(reversed(optimized))


# 5. MAIN OPTIMIZATION ENGINE
def optimize(code):
    current = code[:]

    for _ in range(10):
        updated = constant_propagation(current)
        updated = constant_folding(updated)
        updated = common_subexpression_elimination(updated)
        updated = dead_code_elimination(updated)

        if updated == current:
            break

        current = updated

    return current


# 6. INPUT TAC
code = [
    "t1 = 10 * 5",
    "t2 = 20 + 10",
    "x = t1 + 0",
    "print x"
]


# 7. SHOW ORIGINAL
print("===== ORIGINAL TAC =====")
for line in code:
    print(line)


# 8. RUN OPTIMIZATION
result = optimize(code)


# 9. SHOW OPTIMIZED CODE
print("\n===== OPTIMIZED TAC =====")
for line in result:
    print(line)


# 10. REPORT
original_count = len(code)
optimized_count = len(result)

reduction = (
    (original_count - optimized_count)
    / original_count * 100
    if original_count else 0
)

print("\n===== OPTIMIZATION REPORT =====")
print("Original Instructions:", original_count)
print("Optimized Instructions:", optimized_count)
print(f"Reduction: {reduction:.1f}%")