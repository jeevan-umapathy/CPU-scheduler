from copy import deepcopy

def fcfs(processes):
    processes = deepcopy(processes)
    processes.sort(key=lambda p: p.arrival_time)

    current_time = 0
    gantt = []

    for p in processes:
        if current_time < p.arrival_time:
            current_time = p.arrival_time

        p.start_time = current_time
        p.response_time = p.start_time - p.arrival_time

        current_time += p.burst_time
        p.remaining_time = 0

        p.completion_time = current_time
        p.turnaround_time = p.completion_time - p.arrival_time
        p.waiting_time = p.turnaround_time - p.burst_time

        gantt.append((p.pid, p.start_time, p.completion_time))

    return processes, gantt
