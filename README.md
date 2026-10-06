# Adaptive CPU Scheduling Simulator

This project compares FCFS, non-preemptive SJF, Round Robin, and an Adaptive
Hybrid CPU Scheduler. The hybrid scheduler measures the current ready queue
and chooses between SJF and RR. The browser interface lets you inspect each
decision, execution interval, and comparison result.

## Run

Python 3.11 or newer is sufficient; the website has no third-party package
dependencies. From the project root:

```powershell
python web_demo\server.py
```

Open <http://127.0.0.1:8502> and keep the terminal open. If using the existing
virtual environment, `.\venv\Scripts\python.exe web_demo\server.py` works too.

## Hybrid logic

At each decision, the scheduler observes the FIFO ready queue and computes
the coefficient of variation (CV) of remaining burst times.

- Use SJF when `CV < CV_THRESHOLD` and the number of ready processes is below
  `QUEUE_THRESHOLD`. The selected process runs to completion.
- Otherwise use FIFO Round Robin. New arrivals join the queue before the
  preempted process is appended again.
- In RR mode, use the median remaining burst time as the quantum, clamped
  between `MIN_QUANTUM` and `MAX_QUANTUM` (2 and 8 by default).
- If a process accumulates at least `AGING_THRESHOLD` waiting time (15 by
  default), give it an execution opportunity. Another full threshold of
  waiting is required before a second override.

The scheduler records every execution event and a shorter history of mode
changes, aging overrides, and significant quantum changes. The website
shows the ready queue before each decision, the selected process, the rule
used, and the resulting CPU interval.

## Files

- `web_demo/index.html`, `style.css`, `app.js`: browser interface.
- `web_demo/server.py`: local HTTP server and input validation; calls the
  Python schedulers below.
- `process.py`: process state.
- `fcfs.py`, `sjf.py`, `rr.py`: baseline scheduling algorithms.
- `hybrid.py`: adaptive mode selection, dynamic quantum, aging, and logs.
- `workload.py`: CV and ready queue length.
- `metrics.py`: common metrics.
- `test_scheduler.py`, `web_demo/test_server.py`: deterministic tests.

## Metrics

Waiting time is turnaround minus CPU burst. Turnaround is completion minus
arrival. Response is first CPU start minus arrival. Throughput is completed
processes per unit of elapsed time from time zero. CPU utilization is busy
time divided by that elapsed time. Context switches count changes from one
process PID to another between adjacent intervals.

## Tests

```powershell
python -m unittest -v test_scheduler.py web_demo.test_server
```

## Demonstration

Run Low Variance to inspect SJF decisions. Run High Variance and step from
the first SJF decision to the CV-driven RR decision. Run Heavy Ready Queue
to show that queue size can trigger RR even when burst times are equal.
Then use the timeline and comparison views on the same workload.

This is a discrete, single-CPU simulator. Burst times are assumed known;
I/O blocking, context-switch cost, and multicore scheduling are not modeled.
Thresholds are experimental rather than claimed optimal values.
