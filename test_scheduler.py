import unittest

from fcfs import fcfs
from hybrid import hybrid
from metrics import calculate_metrics
from process import Process
from rr import round_robin
from sjf import sjf


def make_processes(specification):
    return [Process(pid, arrival, burst) for pid, arrival, burst in specification]


class SchedulerTests(unittest.TestCase):
    def assert_valid_result(self, original, result, gantt):
        self.assertEqual(len(original), len(result))
        self.assertTrue(gantt)
        expected_bursts = {p.pid: p.burst_time for p in original}
        executed = {p.pid: 0 for p in original}
        for pid, start, end in gantt:
            self.assertLess(start, end)
            executed[pid] += end - start
        self.assertEqual(executed, expected_bursts)

        for process in result:
            self.assertEqual(process.remaining_time, 0)
            self.assertGreaterEqual(process.waiting_time, 0)
            self.assertGreaterEqual(process.turnaround_time, process.burst_time)
            self.assertGreaterEqual(process.response_time, 0)
            self.assertGreaterEqual(
                process.completion_time,
                process.arrival_time + process.burst_time,
            )

    def run_all(self, specification):
        original = make_processes(specification)
        results = [
            fcfs(original),
            sjf(original),
            round_robin(original, 3),
            hybrid(original)[:2],
        ]
        for result, gantt in results:
            self.assert_valid_result(original, result, gantt)

    def test_all_processes_arrive_at_zero(self):
        self.run_all([("P1", 0, 5), ("P2", 0, 3), ("P3", 0, 7)])

    def test_cpu_idle_before_first_arrival(self):
        original = make_processes([("P1", 5, 5)])
        for runner in (fcfs, sjf, hybrid):
            result, gantt = runner(original)[:2]
            self.assert_valid_result(original, result, gantt)
            self.assertEqual(gantt[0][1], 5)
            self.assertAlmostEqual(calculate_metrics(result, gantt)["cpu_utilization"], 50)

    def test_low_variance_uses_sjf(self):
        original = make_processes(
            [("P1", 0, 5), ("P2", 0, 6), ("P3", 0, 4), ("P4", 0, 5)]
        )
        result, gantt, history = hybrid(original, queue_threshold=10)
        self.assert_valid_result(original, result, gantt)
        self.assertEqual(history[0]["Mode"], "SJF")

    def test_high_variance_uses_rr(self):
        original = make_processes(
            [("P1", 0, 2), ("P2", 0, 20), ("P3", 0, 3), ("P4", 0, 30)]
        )
        result, gantt, history, log = hybrid(original, return_full_log=True)
        self.assert_valid_result(original, result, gantt)
        self.assertEqual(history[0]["Mode"], "RR")
        self.assertTrue(all(2 <= row["Quantum"] <= 8 for row in log if row["Quantum"] is not None))

    def test_heavy_ready_queue_uses_rr(self):
        original = make_processes([(f"P{i}", 0, 5) for i in range(1, 7)])
        result, gantt, history = hybrid(original, cv_threshold=10, queue_threshold=4)
        self.assert_valid_result(original, result, gantt)
        self.assertEqual(history[0]["Mode"], "RR")

    def test_one_extremely_long_process_clamps_quantum(self):
        original = make_processes(
            [("P1", 0, 2), ("P2", 0, 3), ("P3", 0, 100), ("P4", 0, 4)]
        )
        result, gantt, _, log = hybrid(original, return_full_log=True)
        self.assert_valid_result(original, result, gantt)
        rr_quantums = [row["Quantum"] for row in log if row["Quantum"] is not None]
        self.assertTrue(rr_quantums)
        self.assertLessEqual(max(rr_quantums), 8)

    def test_one_process_only(self):
        self.run_all([("Only", 0, 9)])

    def test_round_robin_arrivals_join_fifo_queue(self):
        original = make_processes(
            [("P1", 0, 5), ("P2", 1, 3), ("P3", 2, 2)]
        )
        result, gantt = round_robin(original, 2)
        self.assert_valid_result(original, result, gantt)
        self.assertEqual([row[0] for row in gantt[:4]], ["P1", "P2", "P3", "P1"])

    def test_aging_override_is_logged_and_not_a_mode(self):
        original = make_processes(
            [("Long", 0, 20), ("S1", 0, 1), ("S2", 0, 1), ("S3", 0, 1)]
        )
        result, gantt, history, log = hybrid(
            original,
            cv_threshold=10,
            queue_threshold=10,
            aging_threshold=2,
            return_full_log=True,
        )
        self.assert_valid_result(original, result, gantt)
        aging_rows = [row for row in log if row["Aging Override"]]
        self.assertTrue(aging_rows)
        self.assertTrue(all(row["Mode"].startswith(("SJF", "RR")) for row in aging_rows))
        self.assertNotIn("STARVATION", {row["Mode"] for row in history})

    def test_hybrid_switches_between_sjf_and_rr(self):
        original = make_processes(
            [("P1", 0, 3), ("P2", 1, 20), ("P3", 1, 2)]
        )
        result, gantt, history = hybrid(original)
        self.assert_valid_result(original, result, gantt)
        normal_modes = [row["Mode"].split(" (")[0] for row in history]
        self.assertIn("SJF", normal_modes)
        self.assertIn("RR", normal_modes)

    def test_context_switches_count_process_changes_only(self):
        original = make_processes([("P1", 0, 4), ("P2", 0, 2)])
        result, _ = round_robin(original, 2)
        artificial_gantt = [("P1", 0, 1), ("P1", 1, 2), ("P2", 2, 4), ("P1", 4, 6)]
        self.assertEqual(calculate_metrics(result, artificial_gantt)["context_switches"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
