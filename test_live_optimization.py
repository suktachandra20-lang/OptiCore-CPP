"""OptiCore Live Optimization Automated Tests."""

import unittest

from dataclasses import dataclass

from live_optimization import (
    lines_of,
    compatible_labels,
    constant_propagation,
    constant_folding,
    dead_assignment_elimination,
    iter_trace,
    instruction_diff,
)


@dataclass
class Result:
    outputs: tuple
    returned: object = None
    halted: bool = False


# Small test-only executor for known safe examples
def mini_execute(code):

    env = {}
    outputs = []

    for line in code:

        if line.startswith("print "):

            outputs.append(
                eval(
                    line[6:],
                    {"__builtins__": {}},
                    env,
                )
            )

        elif " = " in line:

            name, expr = line.split(
                " = ",
                1,
            )

            env[name] = eval(
                expr,
                {"__builtins__": {}},
                env,
            )

        else:

            raise ValueError(
                "Unsupported test TAC"
            )

    return Result(
        tuple(outputs)
    )


class LiveTests(unittest.TestCase):

    CODE = [
        "a = 4",
        "b = 6",
        "c = a + b",
        "print c",
    ]

    def test_01_normalize_text(self):

        self.assertEqual(
            lines_of(
                " a = 1\n\nprint a\n"
            ),
            ["a = 1", "print a"],
        )

    def test_02_normalize_dict(self):

        self.assertEqual(
            lines_of({
                "optimized": ["print 5"]
            }),
            ["print 5"],
        )

    def test_03_normalize_tuple(self):

        result = (
            ["print 5"],
            {"reduction": 1},
        )

        self.assertEqual(
            lines_of(result),
            ["print 5"],
        )

    def test_04_invalid_output(self):

        with self.assertRaises(
            TypeError
        ):
            lines_of(42)

    def test_05_label_compatibility(self):

        self.assertEqual(
            compatible_labels([
                "TOP:",
                "goto TOP",
            ]),
            [
                "label TOP",
                "goto TOP",
            ],
        )

    def test_06_constant_folding(self):

        self.assertEqual(
            constant_folding([
                "x = 2 + 3",
                "print x",
            ]),
            [
                "x = 5",
                "print x",
            ],
        )

    def test_07_constant_propagation(self):

        result = constant_propagation(
            self.CODE
        )

        self.assertEqual(
            result[2],
            "c = 4 + 6",
        )

    def test_08_reassignment(self):

        code = [
            "a = 1",
            "a = a + 1",
            "print a",
        ]

        steps = list(
            iter_trace(
                code,
                executor=mini_execute,
            )
        )

        self.assertTrue(
            all(
                s.verification == "PASS"
                for s in steps
            )
        )

        self.assertEqual(
            mini_execute(
                steps[-1].after
            ).outputs,
            (2,),
        )

    def test_09_dead_assignment(self):

        code = [
            "a = 3",
            "unused = 99",
            "print a",
        ]

        self.assertEqual(
            dead_assignment_elimination(
                code
            ),
            [
                "a = 3",
                "print a",
            ],
        )

    def test_10_branch_safety(self):

        code = [
            "a = 1",
            "if a goto END",
            "END:",
            "print a",
        ]

        for function in (
            constant_propagation,
            constant_folding,
            dead_assignment_elimination,
        ):
            self.assertEqual(
                function(code),
                code,
            )

    def test_11_no_function_evaluation(self):

        self.assertEqual(
            constant_folding([
                "x = dangerous()"
            ]),
            ["x = dangerous()"],
        )

    def test_12_three_live_stages(self):

        steps = list(
            iter_trace(
                self.CODE,
                executor=mini_execute,
            )
        )

        self.assertEqual(
            len(steps),
            3,
        )

        self.assertTrue(
            all(
                s.verification == "PASS"
                for s in steps
            )
        )

        self.assertEqual(
            steps[-1].after,
            ["print 10"],
        )

    def test_13_real_backend_stage(self):

        def backend(code):

            return {
                "optimized": code
            }

        steps = list(
            iter_trace(
                self.CODE,
                backend=backend,
                executor=mini_execute,
            )
        )

        self.assertEqual(
            len(steps),
            4,
        )

        self.assertEqual(
            steps[-1].name,
            "Existing OptiCore integrated optimizer",
        )

        self.assertEqual(
            steps[-1].verification,
            "PASS",
        )

    def test_14_backend_labels(self):

        received = []

        def backend(code):

            received.extend(code)
            return code

        list(
            iter_trace(
                [
                    "TOP:",
                    "print 1",
                ],
                backend=backend,
                educational_passes=False,
            )
        )

        self.assertEqual(
            received[0],
            "label TOP",
        )

    def test_15_wrong_optimizer(self):

        steps = list(
            iter_trace(
                self.CODE,
                backend=lambda code: [
                    "print 999"
                ],
                executor=mini_execute,
            )
        )

        self.assertEqual(
            steps[-1].verification,
            "FAIL",
        )

        self.assertEqual(
            len(steps),
            4,
        )

    def test_16_without_executor(self):

        steps = list(
            iter_trace(self.CODE)
        )

        self.assertTrue(
            all(
                s.verification == "NOT CHECKED"
                for s in steps
            )
        )

    def test_17_instruction_diff(self):

        removed, added = instruction_diff(
            ["a=1", "print a"],
            ["print 1"],
        )

        self.assertEqual(
            removed,
            ["a=1", "print a"],
        )

        self.assertEqual(
            added,
            ["print 1"],
        )

    def test_18_empty_pipeline(self):

        with self.assertRaises(
            ValueError
        ):
            list(
                iter_trace(
                    self.CODE,
                    educational_passes=False,
                )
            )

    def test_19_runtime_error(self):

        steps = list(
            iter_trace(
                self.CODE,
                backend=lambda code: [
                    "print missing"
                ],
                executor=mini_execute,
                educational_passes=False,
            )
        )

        self.assertEqual(
            len(steps),
            1,
        )

        self.assertEqual(
            steps[0].verification,
            "FAIL",
        )

    def test_20_unsupported_execution(self):

        code = [
            "label HERE",
            "goto HERE",
        ]

        steps = list(
            iter_trace(
                code,
                executor=mini_execute,
            )
        )

        self.assertTrue(
            all(
                s.verification == "NOT CHECKED"
                for s in steps
            )
        )


if __name__ == "__main__":

    unittest.main(
        verbosity=2
    )