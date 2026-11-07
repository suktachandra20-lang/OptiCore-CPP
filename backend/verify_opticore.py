# OptiCore - Step 10
# Original vs Optimized TAC Verification

from cfg_analysis import build_cfg, parse_instruction
from integrated_optimizer import optimize


COMPARE = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
}


# 1. EXECUTE THREE-ADDRESS CODE
def execute_tac(code, inputs=None, max_steps=10000):

    build_cfg(code)

    labels = {
        parts[1]: index
        for index, line in enumerate(code)
        if (parts := line.split())[0] == "label"
    }

    variables = dict(inputs or {})
    output = []
    pc = 0
    steps = 0

    def value(token):
        if token.lstrip("-").isdigit():
            return int(token)

        if token not in variables:
            raise ValueError(
                f"Undefined variable: {token}"
            )

        return variables[token]

    while pc < len(code):

        steps += 1

        if steps > max_steps:
            raise RuntimeError(
                "Execution limit exceeded"
            )

        line = code[pc]
        instruction = parse_instruction(line)
        parts = line.split()

        if instruction.kind == "label":
            pc += 1

        elif instruction.kind == "goto":
            pc = labels[instruction.target]

        elif instruction.kind == "if":
            matched = COMPARE[parts[2]](
                value(parts[1]),
                value(parts[3])
            )

            pc = (
                labels[instruction.target]
                if matched else pc + 1
            )

        elif instruction.kind == "print":
            output.append(value(parts[1]))
            pc += 1

        elif instruction.kind == "assign":

            if len(parts) == 3:
                new_value = value(parts[2])

            else:
                a = value(parts[2])
                b = value(parts[4])

                new_value = {
                    "+": lambda: a + b,
                    "-": lambda: a - b,
                    "*": lambda: a * b,
                }[parts[3]]()

            variables[parts[0]] = new_value
            pc += 1

    return output


# 2. ORIGINAL VS OPTIMIZED VERIFICATION
def verify_program(name, source, input_cases):

    optimized = optimize(source)

    print(f"\n=== {name} ===")

    print(
        "Original TAC:",
        len(source),
        "instructions"
    )

    print(
        "Optimized TAC:",
        len(optimized),
        "instructions"
    )

    print("Optimized code:")

    for line in optimized:
        print("  ", line)

    for inputs in input_cases:

        before = execute_tac(source, inputs)
        after = execute_tac(optimized, inputs)

        if before != after:
            raise AssertionError(
                f"FAILED for {inputs}: "
                f"original={before}, "
                f"optimized={after}"
            )

        print(
            f"PASS | inputs={inputs} | "
            f"output={after}"
        )

    return optimized


# 3. AUTOMATED TEST PROGRAMS
if __name__ == "__main__":

    # TEST 1: CONSTANT OPTIMIZATION
    verify_program(
        "CONSTANT OPTIMIZATION",
        [
            "t1 = 10 * 5",
            "t2 = 20 + 10",
            "x = t1 + 0",
            "print x",
        ],
        [{}],
    )

    # TEST 2: BRANCH OPTIMIZATION
    verify_program(
        "BRANCH OPTIMIZATION",
        [
            "if flag > 0 goto POS",
            "x = 10",
            "goto END",
            "label POS",
            "x = 20",
            "label END",
            "print x",
        ],
        [
            {"flag": -1},
            {"flag": 0},
            {"flag": 5}
        ],
    )

    # TEST 3: LOOP OPTIMIZATION
    verify_program(
        "LOOP OPTIMIZATION",
        [
            "i = 0",
            "label LOOP",
            "if i >= 3 goto END",
            "i = i + 1",
            "goto LOOP",
            "label END",
            "print i",
        ],
        [{}],
    )

    print(
        "\nALL 5 EXECUTION CASES PASSED"
    )