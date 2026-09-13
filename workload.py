import statistics

def analyze_workload(ready_queue):
    remaining_times = [
        p.remaining_time
        for p in ready_queue
        if p.remaining_time > 0
    ]

    queue_length = len(remaining_times)

    if queue_length == 0:
        return 0, 0

    mean = statistics.mean(remaining_times)

    if queue_length == 1 or mean == 0:
        cv = 0
    else:
        std = statistics.pstdev(remaining_times)
        cv = std / mean

    return cv, queue_length