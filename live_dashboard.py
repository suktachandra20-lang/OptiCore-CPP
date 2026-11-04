"""OptiCore Live Optimization Dashboard.

Run:
python -m streamlit run live_dashboard.py --server.port 8505
"""

from __future__ import annotations

import importlib
import json
import time

from dataclasses import asdict

import pandas as pd
import streamlit as st

from live_optimization import (
    iter_trace,
    instruction_diff,
    lines_of,
)


# ==========================================
# 1. DASHBOARD CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="OptiCore Live Optimization",
    page_icon="⚙️",
    layout="wide",
)

st.title(
    "⚙️ OptiCore — Live Optimization"
)

st.caption(
    "Live Pass Tracking | TAC Comparison | "
    "Correctness | CFG | Register Allocation"
)


# ==========================================
# 2. EXAMPLE PROGRAMS
# ==========================================

EXAMPLES = {

    "Constant optimization": (
        "a = 4\n"
        "b = 6\n"
        "c = a + b\n"
        "d = a - b\n"
        "print c\n"
        "print d"
    ),

    "Dead assignment": (
        "a = 2\n"
        "unused = 99\n"
        "b = a + 3\n"
        "print b"
    ),

    "Loop / CFG": (
        "i = 0\n"
        "TOP:\n"
        "if i >= 3 goto END\n"
        "i = i + 1\n"
        "goto TOP\n"
        "END:\n"
        "print i"
    ),
}


# ==========================================
# 3. OPTIONAL MODULE LOADER
# ==========================================

def load_optional(module, name):

    try:

        imported = importlib.import_module(
            module
        )

        return getattr(
            imported,
            name,
        ), None

    except (
        ImportError,
        AttributeError,
    ) as exc:

        return None, (
            f"{module}.{name}: {exc}"
        )


# ==========================================
# 4. CFG GRAPH GENERATOR
# ==========================================

def graph_for_cfg(code):

    try:

        from v95_analysis import build_cfg

        cfg = build_cfg(code)

        lines = [
            "digraph CFG {",
            "rankdir=TB;",
            'node [shape=box,style=filled,'
            'fillcolor="#dbeafe",'
            'fontcolor="#111827"];',
        ]

        for block in cfg.blocks:

            label = "\\n".join(
                f"{i}: {cfg.instructions[i].raw}"
                for i in range(
                    block.start,
                    block.end + 1,
                )
            )

            label = label.replace(
                '"',
                '\\"',
            )

            lines.append(
                f'"{block.name}" '
                f'[label="{block.name}\\n{label}"];'
            )

            for nxt in block.successors:

                lines.append(
                    f'"{block.name}" -> "{nxt}";'
                )

        lines.append("}")

        return "\n".join(lines), None

    except Exception as exc:

        return None, (
            "CFG preview unavailable: "
            f"{type(exc).__name__}: {exc}"
        )


# ==========================================
# 5. TAC EDITOR
# ==========================================

left, right = st.columns([2, 1])

with left:

    example = st.selectbox(
        "TAC example",
        list(EXAMPLES),
    )

    if (
        st.session_state.get(
            "last_example"
        ) != example
    ):

        st.session_state[
            "tac_editor"
        ] = EXAMPLES[example]

        st.session_state[
            "last_example"
        ] = example

    tac = st.text_area(
        "Input TAC",
        key="tac_editor",
        height=220,
    )


# ==========================================
# 6. EXECUTION OPTIONS
# ==========================================

with right:

    st.subheader(
        "Execution Options"
    )

    use_local = st.checkbox(
        "Built-in educational passes",
        value=True,
    )

    use_backend = st.checkbox(
        "Use existing OptiCore optimizer",
        value=True,
    )

    verify = st.checkbox(
        "Correctness verification",
        value=True,
    )

    delay = st.slider(
        "Stage reveal delay (seconds)",
        0.0,
        1.0,
        0.25,
        0.05,
    )

    st.caption(
        "The existing integrated optimizer "
        "appears as one real stage."
    )


# ==========================================
# 7. LOAD EXISTING BACKEND
# ==========================================

if use_backend:

    backend, backend_error = load_optional(
        "integrated_optimizer",
        "optimize",
    )

else:
    backend, backend_error = None, None


if verify:

    executor, exec_error = load_optional(
        "v95_regression",
        "execute",
    )

else:
    executor, exec_error = None, None


if (
    use_backend
    and backend is None
):

    st.warning(
        "Existing optimizer unavailable: "
        f"{backend_error}. "
        "Uncheck that option to use "
        "the educational passes."
    )


if (
    verify
    and executor is None
):

    st.warning(
        "Correctness verification "
        f"unavailable: {exec_error}"
    )


# ==========================================
# 8. LIVE OPTIMIZATION
# ==========================================

run_disabled = (
    (use_backend and backend is None)
    or (not use_local and not use_backend)
)

if st.button(
    "▶ Run live optimization",
    type="primary",
    disabled=run_disabled,
):

    progress = st.progress(0)

    live_status = st.empty()
    preview = st.empty()

    trace = []

    count = (
        (3 if use_local else 0)
        + (1 if use_backend else 0)
    )

    try:

        generator = iter_trace(
            tac,
            backend=(
                backend
                if use_backend
                else None
            ),
            executor=executor,
            educational_passes=use_local,
        )

        for i, step in enumerate(
            generator,
            start=1,
        ):

            trace.append(step)

            progress.progress(
                i / count
            )

            live_status.info(
                f"Step {i}/{count}: "
                f"{step.name} | "
                f"{step.verification} | "
                f"{step.elapsed_ms:.3f} ms"
            )

            preview.code(
                "\n".join(step.after)
                or "(empty TAC)",
                language="text",
            )

            if delay:
                time.sleep(delay)

            if (
                step.verification
                == "FAIL"
            ):

                st.error(
                    "Correctness mismatch! "
                    "Later stages stopped."
                )

                break

        st.session_state[
            "live_trace"
        ] = trace

        st.session_state[
            "live_source"
        ] = lines_of(tac)

        st.session_state[
            "stage_index"
        ] = max(
            0,
            len(trace) - 1,
        )

        if trace:

            st.success(
                f"Completed {len(trace)} "
                "transformation stage(s)."
            )

    except Exception as exc:

        st.error(
            "Optimization failed: "
            f"{type(exc).__name__}: {exc}"
        )


# ==========================================
# 9. REPLAY PREVIOUS RESULTS
# ==========================================

trace = st.session_state.get(
    "live_trace",
    [],
)

if trace:

    st.divider()

    st.subheader(
        "Step-by-step Optimization Replay"
    )

    if (
        lines_of(tac)
        != st.session_state.get(
            "live_source"
        )
    ):

        st.warning(
            "TAC editor changed. Run again "
            "to update the trace."
        )

    n = len(trace)

    if (
        "stage_index"
        not in st.session_state
    ):

        st.session_state[
            "stage_index"
        ] = 0

    back_col, next_col, _ = st.columns(
        [1, 1, 4]
    )

    with back_col:

        if st.button(
            "◀ Previous",
            disabled=(
                st.session_state[
                    "stage_index"
                ] == 0
            ),
        ):

            st.session_state[
                "stage_index"
            ] -= 1

    with next_col:

        if st.button(
            "Next ▶",
            disabled=(
                st.session_state[
                    "stage_index"
                ] >= n - 1
            ),
        ):

            st.session_state[
                "stage_index"
            ] += 1

    index = st.select_slider(
        "Select stage",
        options=list(range(n)),
        value=st.session_state[
            "stage_index"
        ],
        format_func=lambda i: (
            f"{i + 1}: "
            f"{trace[i].name}"
        ),
    )

    st.session_state[
        "stage_index"
    ] = index

    step = trace[index]

    st.markdown(
        f"**{step.name}** — "
        f"Correctness: "
        f"**{step.verification}**"
    )

    if step.detail:
        st.warning(step.detail)


    # ======================================
    # 10. STATISTICS
    # ======================================

    a, b, c = st.columns(3)

    a.metric(
        "Before instructions",
        len(step.before),
    )

    b.metric(
        "After instructions",
        len(step.after),
    )

    c.metric(
        "Stage time",
        f"{step.elapsed_ms:.3f} ms",
    )


    # ======================================
    # 11. BEFORE / AFTER CODE
    # ======================================

    before_col, after_col = (
        st.columns(2)
    )

    with before_col:

        st.markdown("**Before TAC**")

        st.code(
            "\n".join(step.before)
            or "(empty)",
            language="text",
        )

    with after_col:

        st.markdown("**After TAC**")

        st.code(
            "\n".join(step.after)
            or "(empty)",
            language="text",
        )

    removed, added = instruction_diff(
        step.before,
        step.after,
    )

    with st.expander(
        "Changed Instructions",
        expanded=True,
    ):

        st.write(
            "Removed/replaced:",
            removed if removed else "None",
        )

        st.write(
            "Added/replaced:",
            added if added else "None",
        )


    # ======================================
    # 12. INSTRUCTION CHART
    # ======================================

    st.subheader(
        "Instruction Count Across Passes"
    )

    values = {
        "Input": len(
            st.session_state[
                "live_source"
            ]
        )
    }

    for i, item in enumerate(trace):

        values[
            f"{i + 1}: {item.name}"
        ] = len(item.after)

    chart_data = pd.DataFrame(
        {
            "Instructions": list(
                values.values()
            )
        },
        index=list(
            values.keys()
        ),
    )

    st.bar_chart(chart_data)

    first = len(
        st.session_state[
            "live_source"
        ]
    )

    last = len(
        trace[-1].after
    )

    reduction = (
        100 * (first - last) / first
        if first
        else 0
    )

    st.metric(
        "Final Instruction Reduction",
        f"{reduction:.1f}%",
    )

    if any(
        item.verification == "FAIL"
        for item in trace
    ):

        st.error(
            "Correctness verification FAILED."
        )

    elif (
        executor is not None
        and all(
            item.verification == "PASS"
            for item in trace
        )
    ):

        st.success(
            "All stages preserved observable "
            "behavior for this input."
        )

    else:

        st.info(
            "Correctness has not been "
            "fully verified."
        )


    # ======================================
    # 13. ADVANCED GRAPHS
    # ======================================

    cfg_tab, dom_tab, reg_tab = st.tabs([
        "CFG",
        "Dominator Tree & Loops",
        "Register Allocation",
    ])

    with cfg_tab:

        dot, error = graph_for_cfg(
            step.after
        )

        if dot:
            st.graphviz_chart(dot)
        else:
            st.info(error)

    with dom_tab:

        try:

            from v95_analysis import (
                analyze_dominance_and_loops,
                dominator_tree_dot,
            )

            report = (
                analyze_dominance_and_loops(
                    step.after
                )
            )

            st.graphviz_chart(
                dominator_tree_dot(
                    report
                )
            )

            st.write(
                "Natural loops:",
                report.natural_loops,
            )

            st.write(
                "Back edges:",
                report.back_edges,
            )

        except Exception as exc:

            st.info(
                "Dominator preview "
                f"unavailable: {exc}"
            )

    with reg_tab:

        try:

            from v95_spilling import (
                simulate_spilling,
                interference_dot,
            )

            register_count = st.slider(
                "Available registers",
                min_value=1,
                max_value=8,
                value=3,
            )

            report = simulate_spilling(
                step.after,
                registers=register_count,
            )

            st.graphviz_chart(
                interference_dot(
                    report
                )
            )

            st.write(
                "Assignments:",
                report.assignments,
            )

            st.write(
                "Spill slots:",
                report.slots,
            )

        except Exception as exc:

            st.info(
                "Register preview "
                f"unavailable: {exc}"
            )


    # ======================================
    # 14. DOWNLOAD JSON REPORT
    # ======================================

    report_data = {
        "original": st.session_state[
            "live_source"
        ],
        "steps": [
            asdict(item)
            for item in trace
        ],
        "final": trace[-1].after,
        "final_reduction_percent": round(
            reduction,
            2,
        ),
        "all_stages_verified": (
            bool(executor)
            and all(
                item.verification == "PASS"
                for item in trace
            )
        ),
    }

    st.download_button(
        "⬇ Download Trace Report",
        data=json.dumps(
            report_data,
            indent=2,
        ),
        file_name=(
            "opticore_live_trace.json"
        ),
        mime="application/json",
    )

else:

    st.info(
        "Enter TAC and click "
        "Run live optimization."
    )