  OptiCore

Intelligent Optimizing Compiler with Live Visualization

Optimize Smarter. Visualize Better. Verify Every Transformation.

"Python" (https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
"Streamlit" (https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
"Compiler" (https://img.shields.io/badge/Compiler-Optimization-7C3AED?style=for-the-badge)
"Testing" (https://img.shields.io/badge/Testing-Automated-success?style=for-the-badge)

  Overview

OptiCore is a Python-based compiler optimization backend designed to optimize Three-Address Code (TAC), analyze program structures, verify execution correctness, and visualize optimization processes.

It provides an integrated environment for compiler optimization, program analysis, automated testing, and interactive visualization.

This project represents Member 2 — Optimization Backend of a larger Compiler Construction project.

  Key Features

1. Code Optimization

- Constant Folding
- Constant Propagation
- Common Subexpression Elimination (CSE)
- Dead Code Elimination (DCE)
- Control Flow Optimization
- Strength Reduction
- Limited Loop-Invariant Code Motion (experimental)

2. Program Analysis

- Basic Block Detection
- Control Flow Graph (CFG)
- Live Variable Analysis
- Dominator Tree Analysis
- Natural Loop Detection
- Register Interference Graph

3. Register Allocation

- Graph-Coloring Register Allocation Proposal
- Register Pressure Analysis
- Register Spilling Simulation

4. Correctness Verification

- TAC Interpreter
- Original vs Optimized Execution Comparison
- Differential Testing
- Automated Regression Testing
- Optimization Failure Detection

5. Interactive Visualization

- Before-and-After TAC Comparison
- Step-by-Step Optimization Replay
- Instruction Reduction Charts
- CFG Visualization
- Register Allocation Visualization
- Live Optimization Dashboard

6. Automated Bug Minimization

Uses Delta Debugging to reduce failing TAC programs into smaller reproducible test cases.

  System Architecture

flowchart TD
    A[Input TAC] --> B[Original Execution]
    A --> C[Optimization Engine]
    C --> D[Optimized TAC]
    D --> E[Optimized Execution]
    B --> F{Correctness Check}
    E --> F
    F -->|PASS| G[Verified TAC]
    F -->|FAIL| H[Failure Report]
    H --> I[Bug Minimizer]
    A --> J[CFG and Program Analysis]
    A --> K[Register Analysis]
    G --> L[Visualization and Results]
    J --> L
    K --> L

  Optimization Example

Original TAC:

a = 4
b = 6
c = a + b
d = a - b
print c
print d

Optimized TAC:

print 10
print -2

Optimization Results

Metric| Result
Original Instructions| 6
Optimized Instructions| 2
Instruction Reduction| 66.67%
Original Output| 10, -2
Optimized Output| 10, -2
Correctness| PASS

Note: Instruction reduction does not necessarily represent measured runtime speedup.

  Technology Stack

Technology| Purpose
Python| Backend development
Streamlit| Interactive dashboard
Graphviz DOT| Graph visualization
FastAPI| Optional API layer
Uvicorn| Optional API server
Pandas| Data processing
Unittest| Automated testing
Git & GitHub| Version control

  Installation

Requirements

- Python 3.x
- pip
- Git
- Internet connection for package installation

Step 1: Install Dependencies

python -m pip install streamlit pandas fastapi uvicorn requests

Step 2: Run the Backend

python -u auto_backend.py --tests

The backend loads "my_backend_input.tac" if available; otherwise, it uses its built-in TAC example.

Step 3: Run Backend with Dashboard

python -u auto_backend.py --tests --dashboard

Open:

http://127.0.0.1:8507

Step 4: Run Dashboard Separately

python -m streamlit run live_dashboard.py --server.port 8505

Step 5: Run Automated Tests

python -m unittest -v test_v95.py test_live_optimization.py

Step 6: Run Differential Integration Tests

python -u run_v95.py --integration --rounds 100

Step 7: Run Bug Minimizer Demo

python bug_minimizer.py --demo

  Testing Results

Reported local testing results:

Test Category| Result
Combined Backend Tests| 50/50 Passed
Analysis & Regression Tests| 30/30 Passed
Live Visualization Tests| 20/20 Passed
Differential Integration Tests| 100/100 Passed

These results represent tested TAC inputs and do not constitute formal proof of correctness for all possible programs.

  Project Structure

Important backend modules:

OptiCore/
│
├── backend/
│   ├── optimizer.py
│   ├── integrated_optimizer.py
│   ├── control_flow.py
│   ├── cfg_analysis.py
│   ├── register_allocation.py
│   ├── v95_analysis.py
│   ├── v95_spilling.py
│   ├── v95_regression.py
│   ├── bug_minimizer.py
│   ├── live_optimization.py
│   ├── live_dashboard.py
│   ├── auto_backend.py
│   ├── test_v95.py
│   └── test_live_optimization.py
│
├── screenshots/
│
└── README.md

Actual module locations may differ depending on the repository layout.

  Current Limitations

- TAC interpreter supports a defined subset of TAC syntax.
- Register spilling is simulated rather than emitted as machine code.
- SSA is an experimental preview, not a complete SSA conversion pipeline.
- Some optimization passes support limited TAC patterns.
- Full source-code parsing and target-code generation require integration with the other team modules.

  Future Improvements

- Complete source-to-target compiler integration.
- Advanced loop optimization.
- Full SSA conversion and phi-node placement.
- Executable register spilling.
- Expanded TAC language support.
- Continuous Integration (CI/CD).
- More extensive regression and differential testing.

  Academic Project Information

Field| Details
Project Name| OptiCore
Project Type| Compiler Construction
Module| Optimization Backend
Contribution| Member 2
Programming Language| Python
Project Status| Standalone Backend Tested

  Developer Information

Developer: Shamsun Naher
Student ID: 232-115-032
University: Metropolitan University 
Course: Compiler Constraction
Batch: 59th(A)


<div align="center">
    OptiCore

Optimize Smarter. Visualize Better. Verify Every Transformation.

Built with Python for Intelligent Compiler Optimization.

</div>
