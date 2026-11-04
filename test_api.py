# OptiCore - Step 8 Automated API Tests

import unittest
from fastapi.testclient import TestClient
from api import app


class TestOptiCoreAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    # TEST 1: API Health
    def test_health(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["status"],
            "ok"
        )

    # TEST 2: Optimization
    def test_constant_optimization(self):
        code = [
            "t1 = 10 * 5",
            "x = t1 + 0",
            "print x"
        ]

        response = self.client.post(
            "/optimize",
            json={"code": code}
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(
            data["optimized"],
            ["print 50"]
        )

        self.assertEqual(
            data["report"]["removed_instructions"],
            2
        )

        self.assertEqual(
            data["cfg"][0]["instructions"],
            ["print 50"]
        )

    # TEST 3: Invalid Label
    def test_invalid_label(self):
        response = self.client.post(
            "/optimize",
            json={"code": ["goto UNKNOWN"]}
        )

        self.assertEqual(response.status_code, 400)

        self.assertIn(
            "label",
            response.json()["detail"].lower()
        )

    # TEST 4: Unsupported Operator
    def test_invalid_operator(self):
        response = self.client.post(
            "/optimize",
            json={
                "code": [
                    "x = 1 / 0",
                    "print 2"
                ]
            }
        )

        self.assertEqual(response.status_code, 400)

    # TEST 5: Empty Program
    def test_empty_program(self):
        response = self.client.post(
            "/optimize",
            json={"code": []}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["optimized"],
            []
        )
        self.assertEqual(
            response.json()["cfg"],
            []
        )

    # TEST 6: Invalid Input Format
    def test_invalid_request(self):
        response = self.client.post(
            "/optimize",
            json={"code": "print 1"}
        )

        self.assertEqual(response.status_code, 422)

    # TEST 7: Preserve Original Input
    def test_input_not_modified(self):
        code = [
            "x = 2",
            "print x"
        ]

        response = self.client.post(
            "/optimize",
            json={"code": code}
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.json()["original"],
            code
        )


if __name__ == "__main__":
    unittest.main()