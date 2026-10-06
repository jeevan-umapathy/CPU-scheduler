import unittest

from web_demo.server import parse_request, run_simulation


class WebsiteServerTests(unittest.TestCase):
    def test_all_algorithms_use_the_same_workload(self):
        payload = {
            "processes": [
                {"pid": "P1", "arrival": 0, "burst": 2},
                {"pid": "P2", "arrival": 1, "burst": 20},
                {"pid": "P3", "arrival": 2, "burst": 3},
            ],
            "rr_quantum": 4,
        }
        result = run_simulation(payload)
        for run in result["algorithms"].values():
            self.assertEqual(
                {process["pid"]: process["burst"] for process in run["processes"]},
                {"P1": 2, "P2": 20, "P3": 3},
            )
            self.assertEqual(sum(block["end"] - block["start"] for block in run["gantt"]), 25)
            self.assertIn("max_waiting", run["metrics"])
            self.assertIn("waiting_stddev", run["metrics"])
        self.assertEqual(result["hybrid"]["log"][0]["Ready State"][0]["pid"], "P1")

    def test_invalid_input_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            parse_request({"processes": [
                {"pid": "P1", "arrival": 0, "burst": 2},
                {"pid": "P1", "arrival": 1, "burst": 3},
            ]})
        with self.assertRaisesRegex(ValueError, "whole number"):
            parse_request({"processes": [{"pid": "P1", "arrival": 0.5, "burst": 2}]})


if __name__ == "__main__":
    unittest.main()
