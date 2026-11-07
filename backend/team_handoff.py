# OptiCore - Step 12
# Backend API Integration Testing
# Member 2: Optimization Backend

import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

API_URL = "http://127.0.0.1:8000/optimize"


# 1. SEND TAC TO BACKEND API
def send_to_backend(code):

    payload = json.dumps({
        "code": code
    }).encode("utf-8")

    request = Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    with urlopen(request, timeout=10) as response:
        return json.loads(response.read())


# 2. SAMPLE PROGRAMS
examples = {

    "Constant Optimization": [
        "t1 = 10 * 5",
        "t2 = 20 + 10",
        "x = t1 + 0",
        "print x"
    ],

    "Branch Optimization": [
        "if flag > 0 goto POS",
        "x = 10",
        "goto END",
        "label POS",
        "x = 20",
        "label END",
        "print x"
    ],

    "Loop Optimization": [
        "i = 0",
        "label LOOP",
        "if i >= 3 goto END",
        "i = i + 1",
        "goto LOOP",
        "label END",
        "print i"
    ]
}


# 3. TEST BACKEND INTEGRATION
def run_tests():

    results = {}

    print("===== OPTICORE TEAM INTEGRATION =====")

    for name, code in examples.items():

        print(f"\nTesting: {name}")

        data = send_to_backend(code)

        optimized = data["optimized"]

        if name == "Constant Optimization":
            assert optimized == ["print 50"]

        elif name == "Branch Optimization":
            assert "x = 10" in optimized
            assert "x = 20" in optimized

        elif name == "Loop Optimization":
            assert "goto LOOP" in optimized
            assert "i = i + 1" in optimized

        report = data["report"]

        print("Original:", len(code))
        print("Optimized:", len(optimized))
        print(
            "Reduction:",
            report["reduction_percent"],
            "%"
        )

        print("PASS:", name)

        results[name] = data

    # Save API examples for teammates
    output_file = (
        Path(__file__).resolve().parent
        / "team_handoff.json"
    )

    output_file.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8"
    )

    print("\n===== FINAL RESULT =====")
    print("ALL 3 API INTEGRATION TESTS PASSED")
    print("Saved:", output_file.name)


if __name__ == "__main__":

    try:
        run_tests()

    except (URLError, HTTPError) as error:
        print("BACKEND CONNECTION ERROR:", error)
        print("Check if FastAPI is running.")

    except (AssertionError, KeyError) as error:
        print("INTEGRATION TEST FAILED:", error)