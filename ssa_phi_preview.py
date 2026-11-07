"""SSA illustration for a single if/else diamond."""

from cfg_analysis import build_cfg, parse_instruction


def preview_diamond_ssa(
    code: list[str]
) -> list[str]:

    lines = [
        line.strip()
        for line in code
        if line.strip()
    ]

    build_cfg(lines)

    ins = [
        parse_instruction(line)
        for line in lines
    ]

    if_positions = [
        i
        for i, inst in enumerate(ins)
        if inst.kind == "if"
    ]

    gotos = [
        i
        for i, inst in enumerate(ins)
        if inst.kind == "goto"
    ]

    labels = [
        i
        for i, inst in enumerate(ins)
        if inst.kind == "label"
    ]

    if (
        len(if_positions) != 1
        or len(gotos) != 1
        or len(labels) != 2
    ):
        raise ValueError(
            "SSA preview only supports "
            "one canonical if/else diamond"
        )

    cond_i = if_positions[0]
    jump_i = gotos[0]
    then_i, join_i = labels

    if not (
        cond_i < jump_i < then_i < join_i
    ):
        raise ValueError(
            "Expected if, false-body, goto, "
            "then-label, true-body, join-label"
        )

    if (
        ins[cond_i].target != ins[then_i].target
        or ins[jump_i].target != ins[join_i].target
    ):
        raise ValueError(
            "Branch labels do not form a diamond"
        )

    prefix = ins[:cond_i]
    else_arm = ins[cond_i + 1:jump_i]
    then_arm = ins[then_i + 1:join_i]
    suffix = ins[join_i + 1:]

    if any(
        inst.kind not in {"assign", "print"}
        for inst in (
            prefix + else_arm + then_arm + suffix
        )
    ):
        raise ValueError(
            "Nested branches and loops "
            "are not supported"
        )

    versions: dict[str, int] = {}

    def read(
        token: str,
        env: dict[str, str]
    ) -> str:

        if token.lstrip("-").isdigit():
            return token

        return env.get(
            token,
            f"{token}_0"
        )

    def transform(
        segment: list,
        env: dict[str, str]
    ) -> list[str]:

        output = []

        for inst, line in segment:
            p = line.split()

            if inst.kind == "print":
                output.append(
                    "print " + read(p[1], env)
                )
                continue

            rhs = (
                read(p[2], env)
                if len(p) == 3
                else (
                    f"{read(p[2], env)} "
                    f"{p[3]} "
                    f"{read(p[4], env)}"
                )
            )

            name = inst.defines

            versions[name] = (
                versions.get(name, 0) + 1
            )

            updated = (
                f"{name}_{versions[name]}"
            )

            output.append(
                f"{updated} = {rhs}"
            )

            env[name] = updated

        return output

    indexed = list(zip(ins, lines))
    env: dict[str, str] = {}

    result = transform(
        indexed[:cond_i],
        env
    )

    cond = lines[cond_i].split()

    result.append(
        f"if {read(cond[1], env)} "
        f"{cond[2]} "
        f"{read(cond[3], env)} "
        f"goto {cond[5]}"
    )

    else_env = env.copy()

    result.extend(
        transform(
            indexed[cond_i + 1:jump_i],
            else_env
        )
    )

    result.append(lines[jump_i])
    result.append(lines[then_i])

    then_env = env.copy()

    result.extend(
        transform(
            indexed[then_i + 1:join_i],
            then_env
        )
    )

    result.append(lines[join_i])

    for name in sorted(
        set(env) | set(else_env) | set(then_env)
    ):

        else_version = else_env.get(
            name,
            f"{name}_0"
        )

        then_version = then_env.get(
            name,
            f"{name}_0"
        )

        if else_version != then_version:

            versions[name] = (
                versions.get(name, 0) + 1
            )

            merged = (
                f"{name}_{versions[name]}"
            )

            result.append(
                f"{merged} = "
                f"phi({else_version} from ELSE, "
                f"{then_version} from THEN)"
            )

            env[name] = merged

        else:
            env[name] = else_version

    result.extend(
        transform(
            indexed[join_i + 1:],
            env
        )
    )

    return result