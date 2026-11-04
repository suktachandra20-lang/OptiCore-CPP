import unittest

from cfg_analysis import build_cfg
from integrated_optimizer import optimize

from differential_testing import (
    execute_tac,
    check_program,
    run_differential_tests
)

from optimizer_trace import trace_optimization

from register_allocation import (
    allocate_registers,
    build_interference_graph,
    interference_dot,
    instruction_liveness
)

from ssa_phi_preview import preview_diamond_ssa


class BackendUpgradeTests(unittest.TestCase):

    def test_simple_interpreter(self):
        self.assertEqual(
            execute_tac([
                "a = 2",
                "a = a + 3",
                "print a"
            ]),
            [5]
        )

    def test_reference_interpreter_branch(self):
        source = [
            "if flag > 0 goto T",
            "print 0",
            "goto E",
            "label T",
            "print 1",
            "label E"
        ]

        self.assertEqual(
            execute_tac(source, {"flag": -1}),
            [0]
        )

        self.assertEqual(
            execute_tac(source, {"flag": 1}),
            [1]
        )

    def test_reference_interpreter_loop(self):
        source = [
            "i = 0",
            "label L",
            "if i >= 3 goto E",
            "i = i + 1",
            "goto L",
            "label E",
            "print i"
        ]

        self.assertEqual(
            execute_tac(source),
            [3]
        )

    def test_detect_bad_optimizer(self):
        result = check_program(
            ["print 5"],
            [{}],
            optimizer=lambda _: ["print 4"]
        )

        self.assertFalse(
            result["passed"]
        )

    def test_differential_suite_seeded(self):
        report = run_differential_tests(
            100,
            seed=12,
            failure_file=None
        )

        self.assertTrue(
            report["all_passed"],
            report["first_failure"]
        )

    def test_register_interference(self):
        graph = build_interference_graph([
            "a = 1",
            "b = 2",
            "c = 3",
            "print a",
            "print b",
            "print c"
        ])

        for x, y in [
            ("a", "b"),
            ("a", "c"),
            ("b", "c")
        ]:
            self.assertIn(y, graph[x])
            self.assertIn(x, graph[y])

    def test_color_respects_interference(self):
        program = [
            "a = 1",
            "b = 2",
            "c = a + b",
            "print c",
            "print b"
        ]

        report = allocate_registers(
            program,
            register_count=3
        )

        for a, b in report["edges"]:

            reg_a = report["assignments"][a]
            reg_b = report["assignments"][b]

            if (
                reg_a is not None
                and reg_b is not None
            ):
                self.assertNotEqual(
                    reg_a,
                    reg_b
                )

    def test_spills_when_registers_limited(self):
        report = allocate_registers([
            "a = 1",
            "b = 2",
            "c = 3",
            "print a",
            "print b",
            "print c"
        ], register_count=2)

        self.assertGreaterEqual(
            len(report["spill_candidates"]),
            1
        )

    def test_invalid_register_count(self):
        with self.assertRaises(ValueError):
            allocate_registers(
                ["print 1"],
                register_count=0
            )

    def test_dot_output(self):
        dot = interference_dot([
            "a = 1",
            "print a"
        ])

        self.assertIn(
            "graph Interference",
            dot
        )

        self.assertIn(
            '"a"',
            dot
        )

    def test_instruction_liveness(self):
        data = instruction_liveness([
            "x = 4",
            "print x"
        ])

        self.assertIn(
            "x",
            data["live_out"][0]
        )

        self.assertNotIn(
            "x",
            data["live_in"][0]
        )

    def test_pass_trace_matches_existing_optimizer(self):
        samples = [
            [
                "t1 = 10 * 5",
                "x = t1 + 0",
                "print x"
            ],
            [
                "if flag > 0 goto Y",
                "x = 1",
                "goto E",
                "label Y",
                "x = 2",
                "label E",
                "print x"
            ]
        ]

        for sample in samples:
            report = trace_optimization(sample)

            self.assertEqual(
                report["optimized"],
                optimize(sample)
            )

            self.assertTrue(
                report["passes"]
            )

    def test_ssa_diamond_with_both_arms(self):
        result = preview_diamond_ssa([
            "if flag > 0 goto THEN",
            "x = 10",
            "goto JOIN",
            "label THEN",
            "x = 20",
            "label JOIN",
            "print x"
        ])

        self.assertIn(
            "x_3 = phi(x_1 from ELSE, "
            "x_2 from THEN)",
            result
        )

        self.assertEqual(
            result[-1],
            "print x_3"
        )

    def test_ssa_diamond_with_prefix(self):
        result = preview_diamond_ssa([
            "x = 5",
            "if flag > 0 goto THEN",
            "x = 10",
            "goto JOIN",
            "label THEN",
            "print x",
            "label JOIN",
            "print x"
        ])

        self.assertIn(
            "x_3 = phi(x_2 from ELSE, "
            "x_1 from THEN)",
            result
        )

        self.assertEqual(
            result[-1],
            "print x_3"
        )

    def test_ssa_rejects_loop(self):
        with self.assertRaisesRegex(
            ValueError,
            "diamond"
        ):
            preview_diamond_ssa([
                "label L",
                "goto L"
            ])


if __name__ == "__main__":
    unittest.main()