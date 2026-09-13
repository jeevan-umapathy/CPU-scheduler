from copy import deepcopy
from collections import deque

def round_robin(processes, quantum):
    if quantum <= 0:
        raise ValueError("quantum must be greater than zero")

    processes = deepcopy(processes)
    processes.sort(key=lambda p: p.arrival_time)

    queue = deque()
    gantt = []

    current_time = 0
    i = 0
    n = len(processes)

    while i < n or queue:
        while i < n and processes[i].arrival_time <= current_time:
            queue.append(processes[i])
            i += 1

        if not queue:
            current_time = processes[i].arrival_time
            continue

        p = queue.popleft()

        if p.start_time is None:
            p.start_time = current_time
            p.response_time = p.start_time - p.arrival_time

        execution_time = min(quantum, p.remaining_time)

        start = current_time
        current_time += execution_time
        p.remaining_time -= execution_time

        gantt.append((p.pid, start, current_time))

        while i < n and processes[i].arrival_time <= current_time:
            queue.append(processes[i])
            i += 1

        if p.remaining_time > 0:
            queue.append(p)
        else:
            p.completion_time = current_time
            p.turnaround_time = p.completion_time - p.arrival_time
            p.waiting_time = p.turnaround_time - p.burst_time

    return processes, gantt
