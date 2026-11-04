# OptiCore - Step 6 Automated Tests

import unittest

from cfg_analysis import (
    build_cfg,
    analyze_liveness,
    dead_code_elimination_cfg
)


class TestCFG(unittest.TestCase):

    # TEST 1: CFG Blocks and Edges
    def test_basic_blocks_and_edges(self):
        code = [
            "x = 1",
            "if x > 0 goto YES",
            "print 0",
            "goto END",
            "label YES",
            "print x",
            "label END",
            "print 1"
        ]

        blocks = build_cfg(code)

        self.assertEqual(len(blocks), 4)

        self.assertEqual(
            set(blocks[0].successors),
            {"B2", "B3"}
        )

        self.assertEqual(
            blocks[1].successors,
            ["B4"]
        )

        self.assertEqual(
            blocks[2].successors,
            ["B4"]
        )

    # TEST 2: Remove Unused Variables
    def test_unused_assignments_removed(self):
        code = [
            "a = 10",
            "unused = 99",
            "print a"
        ]

        expected = [
            "a = 10",
            "print a"
        ]

        self.assertEqual(
            dead_code_elimination_cfg(code),
            expected
        )

    # TEST 3: Overwritten Assignment
    def test_overwritten_assignment_removed(self):
        code = [
            "x = 1",
            "x = 2",
            "print x"
        ]

        expected = [
            "x = 2",
            "print x"
        ]

        self.assertEqual(
            dead_code_elimination_cfg(code),
            expected
        )

    # TEST 4: Preserve Branch Variables
    def test_branch_definitions_preserved(self):
        code = [
            "if flag > 0 goto YES",
            "x = 10",
            "goto END",
            "label YES",
            "x = 20",
            "label END",
            "print x"
        ]

        result = dead_code_elimination_cfg(code)

        self.assertIn("x = 10", result)
        self.assertIn("x = 20", result)

    # TEST 5: Loop Safety
    def test_loop_carried_variable_preserved(self):
        code = [
            "i = 0",
            "label LOOP",
            "if i >= 3 goto END",
            "i = i + 1",
            "goto LOOP",
            "label END",
            "print i"
        ]

        self.assertEqual(
            dead_code_elimination_cfg(code),
            code
        )

    # TEST 6: Cross-Block Optimization
    def test_cross_block_fixed_point(self):
        code = [
            "x = 1",
            "goto NEXT",
            "label NEXT",
            "unused = x + 1",
            "print 8"
        ]

        expected = [
            "goto NEXT",
            "label NEXT",
            "print 8"
        ]

        self.assertEqual(
            dead_code_elimination_cfg(code),
            expected
        )

    # TEST 7: Liveness Through Branch
    def test_live_out_through_branch(self):
        code = [
            "x = 10",
            "if flag > 0 goto YES",
            "print x",
            "goto END",
            "label YES",
            "print x",
            "label END"
        ]

        blocks = analyze_liveness(
            build_cfg(code)
        )

        self.assertIn(
            "x",
            blocks[0].live_out
        )

    # TEST 8: Undefined Label
    def test_undefined_jump_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "Undefined jump label"
        ):
            build_cfg(["goto MISSING"])

    # TEST 9: Duplicate Label
    def test_duplicate_label_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "Duplicate label"
        ):
            build_cfg([
                "label X",
                "label X"
            ])

    # TEST 10: Unsupported Operation
    def test_unsupported_division_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "Unsupported TAC"
        ):
            dead_code_elimination_cfg([
                "x = 1 / 0",
                "print 2"
            ])


if __name__ == "__main__":
    unittest.main()