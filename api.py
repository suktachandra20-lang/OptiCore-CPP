# OptiCore - Step 8
# Backend API Integration

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from integrated_optimizer import optimize
from cfg_analysis import build_cfg, analyze_liveness


# 1. CREATE API APPLICATION
app = FastAPI(
    title="OptiCore Compiler API",
    version="0.1.0"
)


# 2. FRONTEND CONNECTION
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# 3. INPUT DATA MODEL
class OptimizeRequest(BaseModel):
    code: list[str] = Field(max_length=250)


# 4. HEALTH CHECK
@app.get("/health")
def health():
    return {
        "status": "ok",
        "project": "OptiCore"
    }


# 5. MAIN OPTIMIZATION API
@app.post("/optimize")
def optimize_program(request: OptimizeRequest):

    lines = [
        line.strip()
        for line in request.code
        if line.strip()
    ]

    if any(len(line) > 300 for line in lines):
        raise HTTPException(
            status_code=400,
            detail="A TAC line is too long"
        )

    try:
        # Run Integrated Optimizer
        optimized = optimize(lines)

        # Generate Optimized CFG
        blocks = analyze_liveness(
            build_cfg(optimized)
        )

    except (ValueError, RuntimeError) as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        ) from error

    # Optimization Statistics
    original_count = len(lines)
    optimized_count = len(optimized)

    removed = original_count - optimized_count

    reduction = (
        round(100 * removed / original_count, 1)
        if original_count else 0.0
    )

    # Response For Frontend
    return {
        "original": lines,
        "optimized": optimized,

        "report": {
            "original_instructions": original_count,
            "optimized_instructions": optimized_count,
            "removed_instructions": removed,
            "reduction_percent": reduction
        },

        "cfg": [
            {
                "id": block.name,
                "instructions": block.lines,
                "successors": block.successors,
                "predecessors": block.predecessors,
                "live_in": sorted(block.live_in),
                "live_out": sorted(block.live_out)
            }
            for block in blocks
        ]
    }