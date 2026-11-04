import unittest

from control_flow import control_flow_optimize


class TestControlFlow(unittest.TestCase):

    # Test 1: Always True Condition
    def test_true_condition(self):
        code = [
            "x = 10",
            "if 5 > 2 goto YES",
            "print 0",
            "goto END",
            "label YES",
            "print x",
            "label END"
        ]

        expected = [
            "x = 10",
            "print x"
        ]

        self.assertEqual(
            control_flow_optimize(code),
            expected
        )

    # Test 2: Always False Condition
    def test_false_condition(self):
        code = [
            "if 1 > 2 goto ELSE",
            "print 10",
            "goto END",
            "label ELSE",
            "print 0",
            "label END"
        ]

        expected = ["print 10"]

        self.assertEqual(
            control_flow_optimize(code),
            expected
        )

    # Test 3: Variable Condition
    def test_variable_condition(self):
        code = [
            "if x > 0 goto POS",
            "print 0",
            "goto END",
            "label POS",
            "print x",
            "label END"
        ]

        result = control_flow_optimize(code)

        self.assertIn(
            "if x > 0 goto POS",
            result
        )

        self.assertIn("label POS", result)
        self.assertIn("print 0", result)
        self.assertIn("print x", result)

    # Test 4: Invalid Jump
    def test_invalid_jump(self):
        code = [
            "goto MISSING",
            "print 1"
        ]

        with self.assertRaises(ValueError):
            control_flow_optimize(code)


if __name__ == "__main__":
    unittest.main()