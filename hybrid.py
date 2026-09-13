from collections import deque
from copy import deepcopy
from statistics import median

from workload import analyze_workload


CV_THRESHOLD = 0.5
QUEUE_THRESHOLD = 4
AGING_THRESHOLD = 15
MIN_QUANTUM = 2
MAX_QUANTUM = 8
QUANTUM_CHANGE_THRESHOLD = 2


def _dynamic_quantum(ready_processes, minimum, maximum):
    remaining_times = [p.remaining_time for p in ready_processes]
    median_value = median(remaining_times)
    return max(minimum, min(int(median_value), maximum))


def hybrid(
    processes,
    cv_threshold=CV_THRESHOLD,
    queue_threshold=QUEUE_THRESHOLD,
    aging_threshold=AGING_THRESHOLD,
    min_quantum=MIN_QUANTUM,
    max_quantum=MAX_QUANTUM,
    return_full_log=False,
):
    """Run the workload-aware SJF/RR scheduler.

    The normal three-value return is kept for compatibility. Set
    ``return_full_log=True`` to also receive the detailed execution log.
    """
    if queue_threshold < 1:
        raise ValueError("queue_threshold must be at least 1")
    if aging_threshold < 1:
        raise ValueError("aging_threshold must be at least 1")
    if min_quantum < 1 or max_quantum < min_quantum:
        raise ValueError("quantum limits are invalid")
    if not processes:
        if return_full_log:
            return [], [], [], []
        return [], [], []

    scheduled = deepcopy(processes)
    pending = sorted(scheduled, key=lambda p: p.arrival_time)
    ready_queue = deque()
    next_arrival = 0
    current_time = 0
    completed = 0

    gantt = []
    execution_log = []
    mode_history = []
    last_normal_mode = None
    last_rr_quantum = None

    # A process must accumulate another full threshold of waiting before a
    # second aging override is allowed.
    aging_wait_checkpoint = {id(p): 0 for p in scheduled}

    def add_arrivals(up_to_time):
        nonlocal next_arrival
        while (
            next_arrival < len(pending)
            and pending[next_arrival].arrival_time <= up_to_time
        ):
            ready_queue.append(pending[next_arrival])
            next_arrival += 1

    while completed < len(scheduled):
        add_arrivals(current_time)

        if not ready_queue:
            current_time = pending[next_arrival].arrival_time
            add_arrivals(current_time)

        ready_snapshot = list(ready_queue)
        cv, queue_length = analyze_workload(ready_snapshot)
        normal_mode = (
            "SJF"
            if cv < cv_threshold and queue_length < queue_threshold
            else "RR"
        )
        quantum = None
        if normal_mode == "RR":
            quantum = _dynamic_quantum(
                ready_snapshot, min_quantum, max_quantum
            )

        aging_candidates = []
        for process in ready_snapshot:
            executed = process.burst_time - process.remaining_time
            accumulated_wait = current_time - process.arrival_time - executed
            wait_since_override = (
                accumulated_wait - aging_wait_checkpoint[id(process)]
            )
            if wait_since_override >= aging_threshold:
                aging_candidates.append((accumulated_wait, process))

        aging_override = bool(aging_candidates)
        if aging_override:
            _, selected = max(
                aging_candidates,
                key=lambda item: (item[0], -item[1].arrival_time),
            )
            ready_queue.remove(selected)
        elif normal_mode == "SJF":
            selected = min(
                ready_snapshot,
                key=lambda p: (p.remaining_time, p.arrival_time),
            )
            ready_queue.remove(selected)
        else:
            selected = ready_queue.popleft()

        mode_label = normal_mode
        if aging_override:
            mode_label += " (Aging Override)"

        if normal_mode == "SJF":
            execution_time = selected.remaining_time
        else:
            execution_time = min(quantum, selected.remaining_time)

        if selected.start_time is None:
            selected.start_time = current_time
            selected.response_time = current_time - selected.arrival_time

        start = current_time
        current_time += execution_time
        selected.remaining_time -= execution_time
        gantt.append((selected.pid, start, current_time))

        execution_log.append(
            {
                "Time": start,
                "Process": selected.pid,
                "Mode": mode_label,
                "CV": round(cv, 3),
                "Queue": queue_length,
                "Quantum": quantum if normal_mode == "RR" else None,
                "Start": start,
                "End": current_time,
                "Aging Override": aging_override,
            }
        )

        quantum_changed = (
            normal_mode == "RR"
            and last_rr_quantum is not None
            and abs(quantum - last_rr_quantum) >= QUANTUM_CHANGE_THRESHOLD
        )
        if (
            last_normal_mode is None
            or normal_mode != last_normal_mode
            or aging_override
            or quantum_changed
        ):
            mode_history.append(
                {
                    "Time": start,
                    "Mode": mode_label,
                    "CV": round(cv, 3),
                    "Queue": queue_length,
                    "Quantum": quantum if normal_mode == "RR" else None,
                }
            )

        last_normal_mode = normal_mode
        if normal_mode == "RR":
            last_rr_quantum = quantum

        if aging_override:
            executed = selected.burst_time - selected.remaining_time
            aging_wait_checkpoint[id(selected)] = (
                current_time - selected.arrival_time - executed
            )

        # Processes that arrive during a slice join before the preempted
        # process, preserving FIFO Round Robin rotation.
        add_arrivals(current_time)

        if selected.remaining_time == 0:
            selected.completion_time = current_time
            selected.turnaround_time = current_time - selected.arrival_time
            selected.waiting_time = (
                selected.turnaround_time - selected.burst_time
            )
            completed += 1
        else:
            ready_queue.append(selected)

    if return_full_log:
        return scheduled, gantt, mode_history, execution_log
    return scheduled, gantt, mode_history
