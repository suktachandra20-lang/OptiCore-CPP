"""
OptiCore v9.5
Advanced Automated Regression Testing

30 Tests:
- CFG Analysis
- Dominator Tree
- Natural Loop Detection
- Liveness Analysis
- Register Spilling Simulation
- TAC Execution
- Differential Testing

Run:
python -m unittest -v test_v95.py
"""

import unittest

from v95_analysis import (
    build_cfg,
    parse_instruction,
    analyze_dominance_and_loops,
    dominator_tree_dot,
    instruction_liveness,
)

from v95_spilling import (
    simulate_spilling,
    interference_dot,
)

from v95_regression import (
    execute,
    differential_test,
    evaluate,
)


# ============================================
# PART 1: CFG AND DOMINATOR TESTS
# ============================================

class CFGTests(unittest.TestCase):

    LOOP = [
        "i = 0",
        "TOP:",
        "if i >= 3 goto END",
        "i = i + 1",
        "goto TOP",
        "END:",
        "print i",
    ]

    def test_01_basic_blocks(self):

        cfg = build_cfg(self.LOOP)

        self.assertGreaterEqual(
            len(cfg.blocks), 3
        )

        self.assertEqual(
            cfg.entry, "B0"
        )

    def test_02_predecessors_successors(self):

        cfg = build_cfg(self.LOOP)

        blocks = {
            block.name: block
            for block in cfg.blocks
        }

        for block in cfg.blocks:

            for nxt in block.successors:

                self.assertIn(
                    block.name,
                    blocks[nxt].predecessors
                )

    def test_03_duplicate_labels(self):

        with self.assertRaisesRegex(
            ValueError,
            "Duplicate label"
        ):

            build_cfg([
                "X:",
                "X:"
            ])

    def test_04_unknown_label(self):

        with self.assertRaisesRegex(
            ValueError,
            "Unknown label"
        ):

            build_cfg([
                "goto MISSING"
            ])

    def test_05_unsafe_expression(self):

        with self.assertRaises(ValueError):

            parse_instruction(
                "x = __import__('os').system('echo hi')"
            )

    def test_06_unreachable_block(self):

        report = analyze_dominance_and_loops([
            "goto END",
            "dead = 9",
            "END:",
            "print 1",
        ])

        self.assertTrue(
            report.unreachable
        )

        self.assertNotIn(
            report.unreachable[0],
            report.dominators
        )

    def test_07_natural_loop(self):

        report = analyze_dominance_and_loops(
            self.LOOP
        )

        self.assertEqual(
            len(report.natural_loops), 1
        )

        loop = report.natural_loops[0]

        self.assertIn(
            loop["header"],
            loop["blocks"]
        )

        self.assertIn(
            loop["latch"],
            loop["blocks"]
        )

    def test_08_diamond_no_loop(self):

        code = [
            "a = 1",
            "if a > 0 goto YES",
            "b = 2",
            "goto END",
            "YES:",
            "b = 3",
            "END:",
            "print b",
        ]

        report = analyze_dominance_and_loops(
            code
        )

        self.assertEqual(
            report.natural_loops,
            []
        )

    def test_09_dominator_tree(self):

        report = analyze_dominance_and_loops(
            self.LOOP
        )

        self.assertIsNone(
            report.immediate_dominator["B0"]
        )

        for block, parent in (
            report.immediate_dominator.items()
        ):

            if block != "B0":

                self.assertIn(
                    parent,
                    report.dominators[block]
                )

        dot = dominator_tree_dot(report)

        self.assertIn(
            "digraph Dominators",
            dot
        )

    def test_10_nested_loops(self):

        code = [
            "i = 0",
            "OUTER:",
            "if i >= 2 goto DONE",
            "j = 0",
            "INNER:",
            "if j >= 2 goto NEXT",
            "j = j + 1",
            "goto INNER",
            "NEXT:",
            "i = i + 1",
            "goto OUTER",
            "DONE:",
            "print i",
        ]

        report = analyze_dominance_and_loops(
            code
        )

        self.assertEqual(
            len(report.back_edges), 2
        )

        self.assertEqual(
            len(report.natural_loops), 2
        )

        self.assertEqual(
            execute(code).outputs,
            (2,)
        )

    def test_11_self_loop(self):

        code = [
            "HERE:",
            "goto HERE",
        ]

        report = analyze_dominance_and_loops(
            code
        )

        self.assertEqual(
            len(report.natural_loops), 1
        )

        self.assertEqual(
            len(
                report.natural_loops[0]["blocks"]
            ),
            1
        )

    def test_12_if_false_cfg(self):

        code = [
            "x = 0",
            "ifFalse x goto ALT",
            "print 2",
            "ALT:",
            "print 3",
        ]

        cfg = build_cfg(code)

        self.assertEqual(
            len(
                cfg.instruction_successors[1]
            ),
            2
        )

    def test_13_liveness_analysis(self):

        code = [
            "a = 1",
            "b = 2",
            "print a",
        ]

        cfg, live_in, live_out = (
            instruction_liveness(code)
        )

        self.assertIn(
            "a",
            live_out[0]
        )

        self.assertNotIn(
            "b",
            live_in[2]
        )


# ============================================
# PART 2: REGISTER SPILLING TESTS
# ============================================

class SpillTests(unittest.TestCase):

    PROGRAM = [
        "a = 1",
        "b = 2",
        "c = 3",
        "print a",
        "print b",
        "print c",
    ]

    def test_14_forced_register_spill(self):

        report = simulate_spilling(
            self.PROGRAM,
            2
        )

        self.assertGreaterEqual(
            len(report.slots), 1
        )

        self.assertGreater(
            report.loads, 0
        )

        self.assertGreater(
            report.stores, 0
        )

    def test_15_no_spill_with_three_registers(self):

        report = simulate_spilling(
            self.PROGRAM,
            3
        )

        self.assertEqual(
            report.slots,
            {}
        )

    def test_16_interference_conflict(self):

        report = simulate_spilling(
            self.PROGRAM,
            3
        )

        for name, neighbors in (
            report.graph.items()
        ):

            for other in neighbors:

                a = report.assignments[name]
                b = report.assignments[other]

                if (
                    a is not None
                    and b is not None
                ):

                    self.assertNotEqual(
                        a, b
                    )

    def test_17_valid_register_names(self):

        for count in (1, 2, 3, 4):

            report = simulate_spilling(
                self.PROGRAM,
                count
            )

            allowed = {
                f"R{i}"
                for i in range(count)
            }

            allowed.add(None)

            self.assertTrue(
                set(
                    report.assignments.values()
                ) <= allowed
            )

    def test_18_invalid_register_count(self):

        invalid = [
            0,
            -1,
            33,
            True,
            1.5
        ]

        for count in invalid:

            with self.assertRaises(
                ValueError
            ):

                simulate_spilling(
                    self.PROGRAM,
                    count
                )

    def test_19_original_code_unchanged(self):

        original = self.PROGRAM.copy()

        before = execute(
            original
        ).outputs

        simulate_spilling(
            original,
            1
        )

        after = execute(
            original
        ).outputs

        self.assertEqual(
            original,
            self.PROGRAM
        )

        self.assertEqual(
            before,
            after
        )

    def test_20_spill_memory_events(self):

        report = simulate_spilling(
            self.PROGRAM,
            2
        )

        events = " ".join(
            " ".join(
                event["before"]
                + event["after"]
            )
            for event in report.events
        )

        for slot in report.slots.values():

            self.assertIn(
                slot,
                events
            )

        graph = interference_dot(
            report
        )

        self.assertIn(
            "graph Interference",
            graph
        )


# ============================================
# PART 3: ADVANCED REGRESSION TESTS
# ============================================

class RegressionTests(unittest.TestCase):

    def test_21_branch_true(self):

        code = [
            "x = 3",
            "if x > 2 goto GOOD",
            "print 0",
            "goto END",
            "GOOD:",
            "print 1",
            "END:",
        ]

        result = execute(code)

        self.assertEqual(
            result.outputs,
            (1,)
        )

    def test_22_branch_false(self):

        code = [
            "x = 0",
            "ifFalse x goto ZERO",
            "print 1",
            "ZERO:",
            "print 0",
        ]

        result = execute(code)

        self.assertEqual(
            result.outputs,
            (0,)
        )

    def test_23_loop_execution(self):

        code = [
            "i = 0",
            "sum = 0",
            "L:",
            "if i >= 5 goto DONE",
            "sum = sum + i",
            "i = i + 1",
            "goto L",
            "DONE:",
            "print sum",
        ]

        result = execute(code)

        self.assertEqual(
            result.outputs,
            (10,)
        )

    def test_24_return_statement(self):

        code = [
            "return 42",
            "print 0",
        ]

        result = execute(code)

        self.assertTrue(
            result.halted
        )

        self.assertEqual(
            result.returned,
            42
        )

        self.assertEqual(
            result.outputs,
            ()
        )

    def test_25_undefined_variable(self):

        with self.assertRaisesRegex(
            ValueError,
            "Read before assignment"
        ):

            execute([
                "print missing"
            ])

    def test_26_infinite_loop_protection(self):

        code = [
            "L:",
            "goto L",
        ]

        with self.assertRaisesRegex(
            RuntimeError,
            "step limit"
        ):

            execute(
                code,
                max_steps=50
            )

    def test_27_randomized_identity(self):

        report = differential_test(
            lambda code: code,
            rounds=120,
            seed=2026
        )

        self.assertEqual(
            report["failed"],
            0
        )

        self.assertEqual(
            report["passed"],
            120
        )

    def test_28_detect_wrong_optimizer(self):

        def wrong_optimizer(code):

            return [
                "print 999"
            ]

        report = differential_test(
            wrong_optimizer,
            rounds=20,
            seed=2026
        )

        self.assertGreater(
            report["failed"],
            0
        )

    def test_29_deterministic_seed(self):

        wrong = lambda code: [
            "print 999"
        ]

        report1 = differential_test(
            wrong,
            rounds=5,
            seed=321
        )

        report2 = differential_test(
            wrong,
            rounds=5,
            seed=321
        )

        self.assertEqual(
            report1,
            report2
        )

    def test_30_expression_evaluation(self):

        result = evaluate(
            "(a + 2) * 3",
            {"a": 2}
        )

        self.assertEqual(
            result,
            12
        )


# ============================================
# RUN ALL TESTS
# ============================================

if __name__ == "__main__":

    unittest.main(
        verbosity=2
    )