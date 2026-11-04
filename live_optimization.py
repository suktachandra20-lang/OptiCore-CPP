"""OptiCore Live Optimization Trace Engine.

Standalone educational passes:
- Constant Propagation
- Constant Folding
- Dead Assignment Elimination

Optional integration:
- integrated_optimizer.optimize

Existing project files remain unchanged.
"""

from __future__ import annotations

import ast
import re
import time

from dataclasses import dataclass
from typing import Callable, Iterator


IDENT = r"[A-Za-z_]\w*"

ASSIGN = re.compile(
    rf"^({IDENT})\s*=\s*(.+)$"
)

LABEL = re.compile(
    rf"^({IDENT}):$"
)

CONTROL = re.compile(
    r"^(?:label\s+|goto\s+|if\b|"
    r"ifFalse\b|ifnot\b|return\b)",
    re.I,
)


# ==========================================
# 1. NORMALIZE TAC
# ==========================================

def lines_of(value) -> list[str]:

    if (
        isinstance(value, tuple)
        and len(value) == 2
    ):
        value = value[0]

    if isinstance(value, dict):

        for key in (
            "optimized",
            "optimized_code",
            "optimized_tac",
            "code",
        ):
            if key in value:
                value = value[key]
                break
        else:
            raise TypeError(
                "Optimizer returned a dict "
                "without a TAC field"
            )

    if isinstance(value, str):
        value = value.splitlines()

    if (
        not isinstance(value, (list, tuple))
        or not all(
            isinstance(x, str)
            for x in value
        )
    ):
        raise TypeError(
            "TAC must be a string or "
            "a sequence of strings"
        )

    return [
        line.strip()
        for line in value
        if line.strip()
    ]


def compatible_labels(
    code: list[str],
) -> list[str]:

    result = []

    for line in code:

        match = LABEL.fullmatch(line)

        if match:
            result.append(
                f"label {match.group(1)}"
            )
        else:
            result.append(line)

    return result


def _straight_line(
    code: list[str],
) -> bool:

    return not any(
        LABEL.fullmatch(line)
        or CONTROL.match(line)
        for line in code
    )


# ==========================================
# 2. SAFE EXPRESSION ANALYSIS
# ==========================================

def _safe_expr(expr: str):

    try:
        tree = ast.parse(
            expr,
            mode="eval",
        )
    except SyntaxError:
        return None

    allowed = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.USub,
        ast.UAdd,
        ast.Name,
        ast.Load,
        ast.Constant,
    )

    for node in ast.walk(tree):

        if not isinstance(node, allowed):
            return None

        if (
            isinstance(node, ast.Constant)
            and type(node.value) is not int
        ):
            return None

    return tree


def _constant_value(node):

    if isinstance(node, ast.Expression):
        return _constant_value(node.body)

    if (
        isinstance(node, ast.Constant)
        and type(node.value) is int
    ):
        return node.value

    if (
        isinstance(node, ast.UnaryOp)
        and isinstance(
            node.op,
            (ast.USub, ast.UAdd),
        )
    ):
        value = _constant_value(
            node.operand
        )

        if value is None:
            return None

        if isinstance(node.op, ast.USub):
            return -value

        return value

    if (
        isinstance(node, ast.BinOp)
        and isinstance(
            node.op,
            (ast.Add, ast.Sub, ast.Mult),
        )
    ):
        a = _constant_value(node.left)
        b = _constant_value(node.right)

        if a is None or b is None:
            return None

        if isinstance(node.op, ast.Add):
            return a + b

        if isinstance(node.op, ast.Sub):
            return a - b

        return a * b

    return None


# ==========================================
# 3. CONSTANT PROPAGATION
# ==========================================

def constant_propagation(
    code: list[str],
) -> list[str]:

    if not _straight_line(code):
        return code.copy()

    constants = {}
    result = []

    class Replace(ast.NodeTransformer):

        def visit_Name(self, node):

            if (
                isinstance(node.ctx, ast.Load)
                and node.id in constants
            ):
                return ast.copy_location(
                    ast.Constant(
                        constants[node.id]
                    ),
                    node,
                )

            return node

    def substitute(expr):

        tree = _safe_expr(expr)

        if tree is None:
            return expr

        updated = ast.fix_missing_locations(
            Replace().visit(tree)
        )

        return ast.unparse(
            updated.body
        )

    for line in code:

        match = ASSIGN.fullmatch(line)

        if match:

            name, expr = match.groups()

            new_expr = substitute(expr)

            tree = _safe_expr(new_expr)

            value = (
                _constant_value(tree)
                if tree is not None
                else None
            )

            constants.pop(name, None)

            if value is not None:
                constants[name] = value

            result.append(
                f"{name} = {new_expr}"
            )

        elif line.startswith("print "):

            result.append(
                "print "
                + substitute(
                    line[6:].strip()
                )
            )

        else:
            return code.copy()

    return result


# ==========================================
# 4. CONSTANT FOLDING
# ==========================================

def constant_folding(
    code: list[str],
) -> list[str]:

    if not _straight_line(code):
        return code.copy()

    result = []

    for line in code:

        match = ASSIGN.fullmatch(line)

        if not match:
            result.append(line)
            continue

        name, expr = match.groups()

        tree = _safe_expr(expr)

        value = (
            _constant_value(tree)
            if tree is not None
            else None
        )

        if value is not None:
            result.append(
                f"{name} = {value}"
            )
        else:
            result.append(line)

    return result


# ==========================================
# 5. DEAD ASSIGNMENT ELIMINATION
# ==========================================

def dead_assignment_elimination(
    code: list[str],
) -> list[str]:

    if not _straight_line(code):
        return code.copy()

    live = set()
    kept = []

    for line in reversed(code):

        match = ASSIGN.fullmatch(line)

        if match:

            name, expr = match.groups()

            tree = _safe_expr(expr)

            if tree is None:
                return code.copy()

            if name not in live:
                continue

            live.discard(name)

            live.update(
                node.id
                for node in ast.walk(tree)
                if isinstance(
                    node, ast.Name
                )
            )

            kept.append(line)

        elif line.startswith("print "):

            tree = _safe_expr(
                line[6:].strip()
            )

            if tree is None:
                return code.copy()

            live.update(
                node.id
                for node in ast.walk(tree)
                if isinstance(
                    node, ast.Name
                )
            )

            kept.append(line)

        else:
            return code.copy()

    return list(reversed(kept))


# ==========================================
# 6. TRACE STEP MODEL
# ==========================================

@dataclass
class TraceStep:

    name: str
    before: list[str]
    after: list[str]
    elapsed_ms: float

    verification: str = "NOT CHECKED"
    detail: str = ""

    @property
    def removed(self) -> int:

        return (
            len(self.before)
            - len(self.after)
        )

    @property
    def changed(self) -> bool:

        return self.before != self.after


def _observable(result):

    return (
        result.outputs,
        result.returned,
        result.halted,
    )


# ==========================================
# 7. LIVE TRACE GENERATOR
# ==========================================

def iter_trace(
    code: list[str] | str,
    backend: Callable | None = None,
    executor: Callable | None = None,
    educational_passes: bool = True,
) -> Iterator[TraceStep]:

    original = lines_of(code)
    current = original.copy()

    reference = None
    reference_error = ""

    # Execute original TAC if possible
    if executor is not None:

        try:
            reference = _observable(
                executor(original)
            )

        except Exception as exc:

            reference_error = (
                "Original execution unsupported: "
                f"{type(exc).__name__}: {exc}"
            )

    # Build pass pipeline
    functions = []

    if educational_passes:

        functions.extend([
            (
                "Built-in: constant propagation",
                constant_propagation,
            ),
            (
                "Built-in: constant folding",
                constant_folding,
            ),
            (
                "Built-in: dead assignment elimination",
                dead_assignment_elimination,
            ),
        ])

    if backend is not None:

        functions.append((
            "Existing OptiCore integrated optimizer",
            backend,
        ))

    if not functions:

        raise ValueError(
            "Select educational passes "
            "or provide an optimizer"
        )

    # Run passes one by one
    for name, function in functions:

        before = current.copy()

        if (
            function is backend
            and backend is not None
        ):
            feed = compatible_labels(
                current
            )
        else:
            feed = current.copy()

        start = time.perf_counter()

        try:

            after = lines_of(
                function(feed.copy())
            )

        except Exception as exc:

            raise RuntimeError(
                f"{name} failed: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        elapsed = (
            time.perf_counter() - start
        ) * 1000

        verification = "NOT CHECKED"
        detail = ""

        # Correctness checking
        if executor is not None:

            if reference is None:

                detail = reference_error

            else:

                try:

                    observed = _observable(
                        executor(after)
                    )

                    if observed == reference:

                        verification = "PASS"

                    else:

                        verification = "FAIL"
                        detail = (
                            "Observable output, "
                            "return, or halt differs"
                        )

                except Exception as exc:

                    verification = "FAIL"

                    detail = (
                        "Optimized TAC execution "
                        f"failed: {type(exc).__name__}: "
                        f"{exc}"
                    )

        step = TraceStep(
            name=name,
            before=before,
            after=after,
            elapsed_ms=elapsed,
            verification=verification,
            detail=detail,
        )

        yield step

        if verification == "FAIL":
            return

        current = after


# ==========================================
# 8. INSTRUCTION DIFFERENCE
# ==========================================

def instruction_diff(
    before: list[str],
    after: list[str],
):

    import difflib

    removed = []
    added = []

    matcher = difflib.SequenceMatcher(
        a=before,
        b=after,
        autojunk=False,
    )

    for op, a1, a2, b1, b2 in (
        matcher.get_opcodes()
    ):

        if op in ("replace", "delete"):
            removed.extend(
                before[a1:a2]
            )

        if op in ("replace", "insert"):
            added.extend(
                after[b1:b2]
            )

    return removed, added