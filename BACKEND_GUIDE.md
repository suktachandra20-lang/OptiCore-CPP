# OptiCore - Optimization Backend

## Project
Intelligent Optimizing Compiler with Live Visualization

## Backend Developer
Member 2 - Optimization Backend

## Technologies
Python, FastAPI, Uvicorn, Streamlit

## Optimization Algorithms
1. Constant Folding
2. Constant Propagation
3. Common Subexpression Elimination
4. Dead Code Elimination
5. Control Flow Optimization
6. CFG-Based Liveness Analysis

## Install Dependencies
python -m pip install -r requirements.txt

## Run Backend
python -m uvicorn api:app --host 127.0.0.1 --port 8000

## API Endpoint
POST http://127.0.0.1:8000/optimize

## Request Example
{
  "code": [
    "t1 = 10 * 5",
    "x = t1 + 0",
    "print x"
  ]
}

## Expected Optimized TAC
print 50

## API Response
- Original TAC
- Optimized TAC
- Optimization Report
- Control Flow Blocks
- Liveness Information

## Testing
python -m unittest discover -s . -p "test_*.py" -v

## Current Limitations
- Accepts supported TAC, not full C source code
- No function call support
- No division support
- Limited to integer expressions
- Additional correctness testing required

## Team Integration
Member 1: Generate TAC from source code
Member 2: Optimize TAC through this API
Member 3: Display results in the dashboard