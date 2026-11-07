"""OptiCore Backend Upgrade Dashboard."""

import streamlit as st

from integrated_optimizer import optimize

from optimizer_trace import trace_optimization

from register_allocation import (
    allocate_registers,
    interference_dot
)

from ssa_phi_preview import preview_diamond_ssa

from differential_testing import run_differential_tests


st.set_page_config(
    page_title="OptiCore - Backend Upgrade",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ OptiCore — Optimization Backend Upgrade")

st.caption(
    "Register Allocation | Pass Tracker | "
    "SSA Preview | Differential Testing"
)


EXAMPLES = {
    "Register allocation": (
        "a = 4\n"
        "b = 6\n"
        "c = a + b\n"
        "d = a - b\n"
        "print c\n"
        "print d"
    ),

    "Constant optimization": (
        "t1 = 10 * 5\n"
        "x = t1 + 0\n"
        "print x"
    ),

    "If/else SSA": (
        "if flag > 0 goto THEN\n"
        "x = 10\n"
        "goto JOIN\n"
        "label THEN\n"
        "x = 20\n"
        "label JOIN\n"
        "print x"
    )
}


# 1. USER INPUT
example = st.selectbox(
    "Choose sample",
    list(EXAMPLES)
)

code_string = st.text_area(
    "TAC source code",
    value=EXAMPLES[example],
    height=210,
    key=example
)

register_count = st.slider(
    "Available registers",
    1,
    8,
    3
)


# 2. ANALYZE BUTTON
if st.button(
    "Analyze backend",
    type="primary"
):

    code = [
        line.strip()
        for line in code_string.splitlines()
        if line.strip()
    ]

    try:

        trace = trace_optimization(code)

        st.success(
            "Analysis completed for supported TAC"
        )

        left, right = st.columns(2)

        left.subheader("Original TAC")

        left.code(
            "\n".join(trace["original"])
            or "(empty)",
            language="text"
        )

        right.subheader("Optimized TAC")

        right.code(
            "\n".join(trace["optimized"])
            or "(empty)",
            language="text"
        )

        st.metric(
            "Instruction reduction",
            len(code) - len(trace["optimized"])
        )

        # 3. OPTIMIZATION PASS TRACKER
        st.subheader(
            "Optimization Pass Tracker"
        )

        for stage in trace["passes"]:

            with st.expander(
                f"Round {stage['round']}: "
                f"{stage['pass']} — "
                f"{'changed' if stage['changed'] else 'no change'}"
            ):

                a, b = st.columns(2)

                a.code(
                    "\n".join(stage["before"])
                    or "(empty)",
                    language="text"
                )

                b.code(
                    "\n".join(stage["after"])
                    or "(empty)",
                    language="text"
                )

        # 4. INTERFERENCE GRAPH
        st.subheader(
            "Interference Graph & Register Allocation"
        )

        selected = st.radio(
            "Graph input",
            [
                "Original TAC",
                "Optimized TAC"
            ],
            horizontal=True
        )

        graph_source = (
            code
            if selected == "Original TAC"
            else trace["optimized"]
        )

        registers = allocate_registers(
            graph_source,
            register_count
        )

        st.graphviz_chart(
            interference_dot(
                graph_source,
                register_count
            )
        )

        st.write(
            "Assignments:",
            registers["assignments"]
        )

        st.write(
            "Potential spills:",
            registers["spill_candidates"]
        )

        st.caption(
            registers["note"]
        )

        # 5. SSA PHI PREVIEW
        st.subheader(
            "SSA Phi-node Preview"
        )

        try:

            st.code(
                "\n".join(
                    preview_diamond_ssa(code)
                ),
                language="text"
            )

        except ValueError as exc:
            st.info(str(exc))

    except (
        ValueError,
        RuntimeError,
        KeyError
    ) as exc:

        st.error(
            f"Analysis error: {exc}"
        )


# 6. DIFFERENTIAL TESTING
st.divider()

st.subheader(
    "Reproducible Differential Testing"
)

count = st.slider(
    "Random programs",
    20,
    500,
    100,
    step=20
)

if st.button("Run differential tests"):

    result = run_differential_tests(
        count=count
    )

    if result["all_passed"]:

        st.success(
            f"{result['programs']} programs, "
            f"{result['input_executions']} "
            "input checks: all matched"
        )

    else:

        st.error(
            f"{result['failures']} failing "
            "programs. Inspect "
            "opticore_failures.json"
        )

        st.json(
            result["first_failure"]
        )

st.caption(
    "These checks are sampled testing, "
    "not a proof of full semantic equivalence."
)