# Adaptive CPU Scheduling Simulator

This undergraduate Operating Systems project simulates and compares FCFS,
non-preemptive SJF, Round Robin, and an Adaptive Hybrid CPU Scheduler. The
hybrid contribution is workload awareness: it observes the ready queue and
chooses an established scheduling policy that fits the current state.

## Hybrid scheduling logic

At every scheduling decision, the hybrid scheduler updates a FIFO ready queue,
computes the coefficient of variation (CV) of remaining burst times, and checks
the number of ready processes.

- **SJF** is selected when `CV < CV_THRESHOLD` and
  `queue length < QUEUE_THRESHOLD`. A selected SJF process runs to completion.
- **Round Robin** is selected when variation is high or the queue is heavily
  loaded. It uses true FIFO rotation, including processes that arrive during a
  time slice.
- **Dynamic quantum** is the median remaining burst time of ready processes,
  clamped to `MIN_QUANTUM` and `MAX_QUANTUM` (defaults: 2 and 8).
- **Aging protection** checks actual accumulated waiting time
  (`current time - arrival time - CPU time already received`). A process that
  crosses the experimental threshold (default: 15) receives one opportunity.
  It cannot immediately retrigger; it must accumulate another threshold of
  waiting first. Aging is logged as an override of SJF or RR, not as a separate
  algorithm.

The simulator keeps a full per-execution log for debugging and a smaller
history containing only initial state, mode changes, aging overrides, and RR
quantum changes of at least two time units.

## Run the application

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

The interface contains three tabs:

1. **Simulator** runs one selected algorithm and shows its process results,
   metrics, and visualization.
2. **Hybrid Analysis** exposes threshold settings and shows workload state,
   clean mode history, aging events, and the expandable full log.
3. **Comparison** runs all four algorithms on exactly the same workload and
   charts one selected metric.

FCFS and SJF use a compact Gantt chart. RR and Adaptive Hybrid use process-lane
timelines so that many time slices remain readable.

## Modules

- `process.py`: process state used by every scheduler.
- `fcfs.py`: First Come First Served.
- `sjf.py`: non-preemptive Shortest Job First.
- `rr.py`: fixed-quantum FIFO Round Robin.
- `hybrid.py`: adaptive selection, dynamic quantum, aging, and logs.
- `workload.py`: remaining-burst CV and ready-queue length calculation.
- `metrics.py`: common evaluation metrics.
- `app.py`: Streamlit interface and charts.
- `test_scheduler.py`: deterministic scheduler and invariant tests.

## Evaluation metrics

- **Waiting time:** turnaround time minus CPU burst time.
- **Turnaround time:** completion time minus arrival time.
- **Response time:** first CPU start time minus arrival time.
- **Throughput:** completed processes divided by elapsed time from time zero.
- **CPU utilization:** busy CPU time divided by elapsed time from time zero.
- **Context switches:** changes from one process PID to a different PID between
  adjacent execution intervals. Consecutive slices of the same process do not
  add a switch.

## Tests

```bash
python -m unittest -v test_scheduler.py
```

The test workloads cover simultaneous arrivals, initial CPU idle time, low and
high variance, heavy load, a very long process, a single process, RR arrivals,
aging, hybrid mode switching, metric behavior, and completion invariants.

## Scope and limitations

This is a discrete, single-CPU educational simulator. Burst times are known in
advance, scheduling overhead is assumed to be zero, and context-switch cost and
I/O blocking are not modeled. Threshold defaults are experimental parameters,
not claimed optimal values. Combining SJF and RR is not itself presented as a
novel algorithm.
