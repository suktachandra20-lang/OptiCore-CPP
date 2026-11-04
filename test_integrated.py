import unittest

from integrated_optimizer import optimize


class TestIntegratedOptimizer(unittest.TestCase):

    # Test 1: Constant Optimization
    def test_constant_folding_and_dead_code(self):
        code = [
            "t1 = 10 * 5",
            "t2 = 20 + 10",
            "x = t1 + 0",
            "print x"
        ]

        self.assertEqual(
            optimize(code),
            ["print 50"]
        )

    # Test 2: Common Subexpression
    def test_common_subexpression(self):
        code = [
            "t1 = a + b",
            "t2 = a + b",
            "print t2"
        ]

        result = optimize(code)

        self.assertEqual(
            sum(" + " in x for x in result),
            1
        )

    # Test 3: Reassignment Safety
    def test_reassignment_invalidates_expression(self):
        code = [
            "t1 = a + b",
            "a = 7",
            "t2 = a + b",
            "print t2"
        ]

        result = optimize(code)

        self.assertIn("t2 = 7 + b", result)
        self.assertNotIn("t2 = t1", result)

    # Test 4: Branch Safety
    def test_branch_values_not_mixed(self):
        code = [
            "x = 1",
            "if flag > 0 goto POS",
            "x = 2",
            "goto END",
            "label POS",
            "print x",
            "label END",
            "print x"
        ]

        result = optimize(code)

        self.assertIn(
            "if flag > 0 goto POS",
            result
        )

        self.assertIn("x = 1", result)
        self.assertIn("x = 2", result)

        self.assertEqual(
            result.count("print x"),
            2
        )

    # Test 5: Loop Safety
    def test_loop_is_preserved(self):
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
            optimize(code),
            code
        )

    # Test 6: Constant Branch
    def test_constant_branch_removed(self):
        code = [
            "x = 1",
            "if 2 > 3 goto BAD",
            "print x",
            "goto DONE",
            "label BAD",
            "print 999",
            "label DONE"
        ]

        self.assertEqual(
            optimize(code),
            ["print 1"]
        )

    # Test 7: Invalid Jump
    def test_invalid_jump_is_rejected(self):
        with self.assertRaises(ValueError):
            optimize(["goto MISSING"])

    # Test 8: Unsupported Division
    def test_unsupported_division_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "Unsupported TAC"
        ):
            optimize([
                "x = 1 / 0",
                "print 2"
            ])

    # Test 9: CSE Safety
    def test_cse_does_not_reuse_old_value(self):
        code = [
            "t1 = x + y",
            "x = 1",
            "t2 = x + y",
            "print t2"
        ]

        result = optimize(code)

        self.assertNotIn("t2 = t1", result)

    # Test 10: Empty Program
    def test_empty_input(self):
        self.assertEqual(optimize([]), [])


if __name__ == "__main__":
    unittest.main()