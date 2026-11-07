# OptiCore - Step 7
# Full Optimization Backend Integration

from cfg_analysis import (
    build_cfg,
    dead_code_elimination_cfg,
    parse_instruction
)

try:
    from control_flow import (
        control_flow_optimize as simplify_flow
    )
except ImportError:
    from control_flow import (
        optimize_control_flow as simplify_flow
    )


# 1. CHECK INTEGER
def is_int(token):
    return token.lstrip("-").isdigit()


# 2. RESOLVE CONSTANT VALUES
def resolve(token, constants):
    return constants.get(token, token)


# 3. COMMON EXPRESSION KEY
def expression_key(a, op, b):
    if op in {"+", "*"}:
        a, b = sorted((a, b))

    return (a, op, b)


# 4. CONSTANT FOLDING + SIMPLIFICATION
def simplify_expression(a, op, b):

    if is_int(a) and is_int(b):
        a_num = int(a)
        b_num = int(b)

        result = {
            "+": a_num + b_num,
            "-": a_num - b_num,
            "*": a_num * b_num
        }[op]

        return str(result)

    if op == "+":
        if a == "0":
            return b
        if b == "0":
            return a

    if op == "-" and b == "0":
        return a

    if op == "*":
        if a == "1":
            return b
        if b == "1":
            return a

    return None


# 5. OPTIMIZE ONE BASIC BLOCK
def optimize_block(lines):

    constants = {}
    expressions = {}
    output = []

    for line in lines:

        inst = parse_instruction(line)
        p = line.split()

        # PRINT STATEMENT
        if inst.kind == "print":
            value = resolve(p[1], constants)
            output.append(f"print {value}")
            continue

        # CONDITIONAL JUMP
        if inst.kind == "if":
            a = resolve(p[1], constants)
            b = resolve(p[3], constants)

            output.append(
                f"if {a} {p[2]} {b} goto {p[5]}"
            )
            continue

        # LABEL OR GOTO
        if inst.kind != "assign":
            output.append(line)
            continue

        name = p[0]
        new_expression = None

        # SIMPLE ASSIGNMENT
        if len(p) == 3:

            rhs = resolve(p[2], constants)
            rewritten = f"{name} = {rhs}"

        # BINARY EXPRESSION
        else:

            a = resolve(p[2], constants)
            op = p[3]
            b = resolve(p[4], constants)

            simple = simplify_expression(a, op, b)

            if simple is not None:

                rhs = simple
                rewritten = f"{name} = {rhs}"

            else:

                key = expression_key(a, op, b)
                previous = expressions.get(key)

                if previous is not None:

                    rhs = previous
                    rewritten = f"{name} = {rhs}"

                else:

                    rhs = None
                    rewritten = f"{name} = {a} {op} {b}"

                    if name != a and name != b:
                        new_expression = key

        # INVALIDATE OLD EXPRESSIONS
        expressions = {
            key: stored_in
            for key, stored_in in expressions.items()
            if stored_in != name
            and name not in (key[0], key[2])
        }

        # UPDATE CONSTANT TABLE
        if rhs is not None and is_int(rhs):
            constants[name] = rhs
        else:
            constants.pop(name, None)

        if new_expression is not None:
            expressions[new_expression] = name

        output.append(rewritten)

    return output


# 6. MAIN OPTIMIZATION ENGINE
def optimize(code, max_rounds=20):

    current = [
        line.strip()
        for line in code
        if line.strip()
    ]

    # Validate TAC
    build_cfg(current)

    for _ in range(max_rounds):

        previous = current[:]

        # Control Flow Optimization
        current = simplify_flow(current)

        # Create Basic Blocks
        blocks = build_cfg(current)

        # Local Optimization
        current = [
            line
            for block in blocks
            for line in optimize_block(block.lines)
        ]

        # Simplify Branches
        current = simplify_flow(current)

        # CFG-based Dead Code Elimination
        current = dead_code_elimination_cfg(current)

        # Final Control Flow Cleanup
        current = simplify_flow(current)

        # Check Convergence
        if current == previous:
            return current

    raise RuntimeError(
        "Optimization did not converge"
    )


# 7. MAIN PROGRAM
if __name__ == "__main__":

    code = [
        "t1 = 10 * 5",
        "t2 = 20 + 10",
        "x = t1 + 0",
        "if 2 > 1 goto YES",
        "print 999",
        "label YES",
        "print x"
    ]

    print("===== ORIGINAL TAC =====")

    for line in code:
        print(line)

    # Run Integrated Optimization
    result = optimize(code)

    print("\n===== OPTIMIZED TAC =====")

    for line in result:
        print(line)

    # Optimization Report
    before = len(code)
    after = len(result)

    percent = (
        100 * (before - after) / before
        if before else 0
    )

    print("\n===== OPTIMIZATION REPORT =====")

    print(f"Original Instructions: {before}")
    print(f"Optimized Instructions: {after}")
    print(f"Reduction: {percent:.1f}%")