from copy import deepcopy

def sjf(processes):
    processes = deepcopy(processes)

    current_time = 0
    completed = 0
    n = len(processes)

    gantt = []

    while completed < n:
        ready = [
            p for p in processes
            if p.arrival_time <= current_time and p.completion_time is None
        ]

        if not ready:
            current_time = min(
                p.arrival_time
                for p in processes
                if p.completion_time is None
            )
            continue

        p = min(ready, key=lambda x: x.burst_time)

        p.start_time = current_time
        p.response_time = p.start_time - p.arrival_time

        current_time += p.burst_time
        p.remaining_time = 0

        p.completion_time = current_time
        p.turnaround_time = p.completion_time - p.arrival_time
        p.waiting_time = p.turnaround_time - p.burst_time

        gantt.append((p.pid, p.start_time, p.completion_time))

        completed += 1

    return processes, gantt
