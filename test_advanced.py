# OptiCore - Advanced Automated Tests

import random
import unittest

from advanced_optimizer import (
    analyze_errors,
    run_advanced_pipeline,
    safe_licm,
    strength_reduction
)

from benchmark import benchmark_tac

from correctness_checker import (
    check_equivalence,
    execute_tac
)


class TestAdvancedOptimizer(unittest.TestCase):

    def test_strength_reduction(self):
        result = strength_reduction([
            "x = a * 2",
            "y = 2 * b",
            "z = a * 1"
        ])

        self.assertEqual(result, [
            "x = a + a",
            "y = b + b",
            "z = a"
        ])

    def test_strength_reduction_does_not_delete_undefined_operand(self):
        self.assertEqual(
            strength_reduction(["x = a * 0"]),
            ["x = a * 0"]
        )

    def test_definite_assignment_detects_unknown(self):
        errors = analyze_errors([
            "x = y + 1",
            "print x"
        ])

        self.assertTrue(
            any(
                "y" in err["error"]
                for err in errors
            )
        )

    def test_explicit_external_inputs(self):
        result = analyze_errors(
            ["x = flag + 1", "print x"],
            {"flag"}
        )

        self.assertEqual(result, [])

    def test_branch_merge_detects_undefined(self):
        source = [
            "if flag > 0 goto YES",
            "x = 3",
            "goto END",
            "label YES",
            "print 8",
            "label END",
            "print x"
        ]

        issues = analyze_errors(
            source,
            {"flag"}
        )

        self.assertTrue(
            any(
                "x" in issue["error"]
                for issue in issues
            )
        )

    def test_branch_both_paths_define_x(self):
        source = [
            "if flag > 0 goto YES",
            "x = 3",
            "goto END",
            "label YES",
            "x = 4",
            "label END",
            "print x"
        ]

        self.assertEqual(
            analyze_errors(source, {"flag"}),
            []
        )

    def test_undefined_label(self):
        errors = analyze_errors([
            "goto MISSING"
        ])

        self.assertIn(
            "label",
            errors[0]["error"].lower()
        )

    def test_unsupported_division(self):
        self.assertTrue(
            analyze_errors(["x = 1 / 0"])
        )

    def test_licm_invariant_hoist(self):
        source = [
            "a = 4",
            "b = 6",
            "i = 0",
            "label LOOP",
            "if i >= 3 goto END",
            "t = a * b",
            "print t",
            "i = i + 1",
            "goto LOOP",
            "label END",
            "print i"
        ]

        moved = safe_licm(source)

        self.assertLess(
            moved.index("t = a * b"),
            moved.index("label LOOP")
        )

        self.assertEqual(
            execute_tac(source),
            execute_tac(moved)
        )

    def test_licm_zero_trip_safe(self):
        source = [
            "a = 4",
            "b = 6",
            "i = 3",
            "label LOOP",
            "if i >= 3 goto END",
            "t = a * b",
            "print t",
            "i = i + 1",
            "goto LOOP",
            "label END",
            "print i"
        ]

        result = safe_licm(source)

        self.assertEqual(
            execute_tac(source),
            execute_tac(result)
        )

        self.assertEqual(
            execute_tac(result),
            [3]
        )

    def test_licm_mutated_operand_stays_in_loop(self):
        source = [
            "a = 1",
            "b = 2",
            "i = 0",
            "label LOOP",
            "if i >= 2 goto END",
            "t = a * b",
            "print t",
            "a = a + 1",
            "i = i + 1",
            "goto LOOP",
            "label END"
        ]

        self.assertEqual(
            safe_licm(source),
            source
        )

    def test_licm_used_after_loop_not_hoisted(self):
        source = [
            "a = 4",
            "b = 6",
            "i = 0",
            "label LOOP",
            "if i >= 3 goto END",
            "t = a * b",
            "print t",
            "i = i + 1",
            "goto LOOP",
            "label END",
            "print t"
        ]

        self.assertEqual(
            safe_licm(source),
            source
        )

    def test_interpreter_branch(self):
        source = [
            "if flag > 0 goto YES",
            "print 10",
            "goto END",
            "label YES",
            "print 20",
            "label END"
        ]

        self.assertEqual(
            execute_tac(source, {"flag": 4}),
            [20]
        )

        self.assertEqual(
            execute_tac(source, {"flag": -4}),
            [10]
        )

    def test_interpreter_loop(self):
        source = [
            "i = 0",
            "label AGAIN",
            "if i >= 4 goto END",
            "i = i + 1",
            "goto AGAIN",
            "label END",
            "print i"
        ]

        self.assertEqual(
            execute_tac(source),
            [4]
        )

    def test_checker_detects_wrong_result(self):
        report = check_equivalence(
            ["print 3"],
            ["print 4"],
            [{}]
        )

        self.assertFalse(
            report["all_passed"]
        )

    def test_checker_never_counts_double_runtime_failure_as_pass(self):
        report = check_equivalence(
            ["print unknown"],
            ["print unknown"],
            [{}]
        )

        self.assertFalse(
            report["all_passed"]
        )

    def test_interpreter_execution_limit(self):
        with self.assertRaisesRegex(
            RuntimeError,
            "limit"
        ):
            execute_tac(
                ["label L", "goto L"],
                max_steps=30
            )

    def test_pipeline_and_report(self):
        source = [
            "a = 10",
            "x = a * 2",
            "print x"
        ]

        report = run_advanced_pipeline(source)

        self.assertEqual(
            report["optimized"],
            ["print 20"]
        )

        self.assertEqual(
            len(report["passes"]),
            3
        )

        checked = check_equivalence(
            source,
            report["optimized"],
            [{}]
        )

        self.assertTrue(
            checked["all_passed"]
        )

    def test_pipeline_external_branch(self):
        source = [
            "if flag > 0 goto YES",
            "x = 10",
            "goto END",
            "label YES",
            "x = 20",
            "label END",
            "print x"
        ]

        report = run_advanced_pipeline(
            source,
            {"flag"}
        )

        checked = check_equivalence(
            source,
            report["optimized"],
            [
                {"flag": -3},
                {"flag": 0},
                {"flag": 3}
            ]
        )

        self.assertEqual(
            checked["passed"],
            3
        )

    def test_benchmark(self):
        source = [
            "x = 5 * 2",
            "print x"
        ]

        report = benchmark_tac(
            source,
            ["print 10"],
            repeats=3
        )

        self.assertEqual(
            report["optimized_instructions"],
            1
        )

        self.assertEqual(
            report["repeats"],
            3
        )

    def test_randomized_straight_line_regression(self):
        rng = random.Random(20261103)

        for _ in range(35):
            a, b, c = (
                rng.randint(-10, 10)
                for _ in range(3)
            )

            code = [
                f"a = {a}",
                f"b = {b}",
                "c = a + b",
                "d = c * 2",
                f"e = d - {c}",
                "print e",
                "a = 100",
                "print d"
            ]

            optimized = run_advanced_pipeline(
                code
            )["optimized"]

            self.assertEqual(
                execute_tac(code),
                execute_tac(optimized)
            )


if __name__ == "__main__":
    unittest.main()