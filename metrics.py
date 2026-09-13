def calculate_metrics(processes, gantt):
    if not processes:
        return {
            "avg_waiting": 0,
            "avg_turnaround": 0,
            "avg_response": 0,
            "throughput": 0,
            "cpu_utilization": 0,
            "context_switches": 0,
        }

    count = len(processes)
    avg_waiting = sum(p.waiting_time for p in processes) / count
    avg_turnaround = sum(p.turnaround_time for p in processes) / count
    avg_response = sum(p.response_time for p in processes) / count

    # Time zero is the observation point, so initial idle time is represented.
    end_time = max(p.completion_time for p in processes)
    elapsed_time = end_time
    throughput = count / elapsed_time if elapsed_time > 0 else 0
    busy_time = sum(end - start for _, start, end in gantt)
    cpu_utilization = (
        busy_time / elapsed_time * 100 if elapsed_time > 0 else 0
    )

    context_switches = sum(
        1
        for previous, current in zip(gantt, gantt[1:])
        if previous[0] != current[0]
    )

    return {
        "avg_waiting": avg_waiting,
        "avg_turnaround": avg_turnaround,
        "avg_response": avg_response,
        "throughput": throughput,
        "cpu_utilization": cpu_utilization,
        "context_switches": context_switches,
    }
