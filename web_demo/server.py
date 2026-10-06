"""Local website for the existing Python scheduling algorithms."""

import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
sys.path.insert(0, str(PROJECT))

from fcfs import fcfs
from hybrid import AGING_THRESHOLD, CV_THRESHOLD, MAX_QUANTUM, MIN_QUANTUM, QUEUE_THRESHOLD, hybrid
from metrics import calculate_metrics
from process import Process
from rr import round_robin
from sjf import sjf


def integer(value, label, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be a whole number.")
    if not minimum <= value <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}.")
    return value


def parse_request(payload):
    if not isinstance(payload, dict):
        raise ValueError("Send a workload and settings as a JSON object.")
    rows = payload.get("processes")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 30:
        raise ValueError("Enter between 1 and 30 processes.")

    processes = []
    seen = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"Process {index} is invalid.")
        pid = row.get("pid")
        if not isinstance(pid, str) or not pid.strip():
            raise ValueError(f"Process {index} needs a PID.")
        pid = pid.strip()
        if len(pid) > 20 or pid in seen:
            raise ValueError("PIDs must be unique and at most 20 characters.")
        seen.add(pid)
        arrival = integer(row.get("arrival"), f"{pid} arrival", 0, 1000)
        burst = integer(row.get("burst"), f"{pid} burst", 1, 1000)
        processes.append(Process(pid, arrival, burst))

    if sum(process.burst_time for process in processes) > 3000:
        raise ValueError("Total burst time must be at most 3000 for a readable demo.")

    settings = payload.get("settings", {})
    if not isinstance(settings, dict):
        raise ValueError("Settings are invalid.")
    cv_threshold = settings.get("cv_threshold", CV_THRESHOLD)
    if isinstance(cv_threshold, bool) or not isinstance(cv_threshold, (int, float)):
        raise ValueError("CV threshold must be a number.")
    if not 0 <= cv_threshold <= 5:
        raise ValueError("CV threshold must be between 0 and 5.")

    options = {
        "cv_threshold": float(cv_threshold),
        "queue_threshold": integer(settings.get("queue_threshold", QUEUE_THRESHOLD), "Queue threshold", 1, 30),
        "aging_threshold": integer(settings.get("aging_threshold", AGING_THRESHOLD), "Aging threshold", 1, 1000),
        "min_quantum": integer(settings.get("min_quantum", MIN_QUANTUM), "Minimum quantum", 1, 1000),
        "max_quantum": integer(settings.get("max_quantum", MAX_QUANTUM), "Maximum quantum", 1, 1000),
    }
    if options["min_quantum"] > options["max_quantum"]:
        raise ValueError("Minimum quantum cannot exceed maximum quantum.")
    rr_quantum = integer(payload.get("rr_quantum", 4), "RR quantum", 1, 1000)
    return processes, options, rr_quantum


def process_data(process):
    return {
        "pid": process.pid,
        "arrival": process.arrival_time,
        "burst": process.burst_time,
        "start": process.start_time,
        "completion": process.completion_time,
        "waiting": process.waiting_time,
        "turnaround": process.turnaround_time,
        "response": process.response_time,
    }


def run_simulation(payload):
    processes, settings, rr_quantum = parse_request(payload)
    runs = {
        "FCFS": fcfs(processes),
        "SJF": sjf(processes),
        "Round Robin": round_robin(processes, rr_quantum),
    }
    result, gantt, history, log = hybrid(
        processes, return_full_log=True, **settings
    )
    runs["Adaptive Hybrid"] = result, gantt

    algorithms = {}
    for name, (finished, intervals) in runs.items():
        algorithms[name] = {
            "processes": [process_data(process) for process in finished],
            "gantt": [
                {"pid": pid, "start": start, "end": end}
                for pid, start, end in intervals
            ],
            "metrics": calculate_metrics(finished, intervals),
        }
    return {
        "algorithms": algorithms,
        "hybrid": {"history": history, "log": log},
        "settings": settings,
    }


class DemoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(HERE), **kwargs)

    def do_POST(self):
        if self.path != "/api/simulate":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 65536:
                raise ValueError("Request is too large or empty.")
            payload = json.loads(self.rfile.read(length))
            response = run_simulation(payload)
            status = 200
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            response = {"error": str(error)}
            status = 400

        body = json.dumps(response).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    address = ("127.0.0.1", 8502)
    print(f"CPU Scheduling Simulator: http://{address[0]}:{address[1]}")
    ThreadingHTTPServer(address, DemoHandler).serve_forever()
