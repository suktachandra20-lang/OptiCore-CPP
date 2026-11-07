import streamlit as st
import requests

st.set_page_config(
    page_title="OptiCore",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ OptiCore Compiler")
st.subheader("Intelligent Optimizing Compiler")

st.write("Optimization Backend Dashboard")

code = st.text_area(
    "Enter Three Address Code:",
    value="""t1 = 10 * 5
t2 = 20 + 10
x = t1 + 0
print x""",
    height=180
)

if st.button("Compile & Optimize"):

    try:
        response = requests.post(
            "http://127.0.0.1:8000/optimize",
            json={"code": code.splitlines()},
            timeout=20
        )

        if response.status_code == 200:

            result = response.json()

            st.success("Optimization Successful!")

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Original TAC")
                st.code(
                    "\n".join(result["original"]),
                    language="text"
                )

            with col2:
                st.subheader("Optimized TAC")
                st.code(
                    "\n".join(result["optimized"]),
                    language="text"
                )

            st.subheader("Optimization Report")

            report = result["report"]

            a, b, c = st.columns(3)

            a.metric(
                "Original",
                report["original_instructions"]
            )

            b.metric(
                "Optimized",
                report["optimized_instructions"]
            )

            c.metric(
                "Reduction",
                str(report["reduction_percent"]) + "%"
            )

            st.subheader("Control Flow Blocks")

            for block in result["cfg"]:
                with st.expander(block["id"]):
                    st.write(
                        "Instructions:",
                        block["instructions"]
                    )
                    st.write(
                        "Successors:",
                        block["successors"]
                    )
                    st.write(
                        "Live In:",
                        block["live_in"]
                    )
                    st.write(
                        "Live Out:",
                        block["live_out"]
                    )

        else:
            st.error(response.text)

    except requests.exceptions.RequestException:
        st.error(
            "Backend not connected! "
            "Please start the FastAPI server."
        )