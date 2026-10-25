# Reproducible CPU Scheduling Experiments

This folder uses the **existing** scheduler implementations from the repository root. It does not replace or duplicate the simulator algorithms.

## Run from repository root (PowerShell)

```powershell
python -m unittest -v test_scheduler.py web_demo.test_server experiments.test_benchmark
python experiments/benchmark.py
python experiments/make_figures.py
```

The last command needs matplotlib and numpy (`python -m pip install matplotlib numpy`). The first two commands require only Python standard library modules.

## Design

Six deterministic synthetic workload families with 30 cases each (180 workloads), shared across FCFS, nonpreemptive SJF, fixed RR quantum 4 and Adaptive Hybrid. Default Hybrid parameters: CV threshold 0.5, queue threshold 4, aging threshold 15, quantum clamped 2–8. Workload seeds and definitions are in `benchmark.py`; generated cases and complete metrics are written under `results/`. CV/queue threshold sweep performs another 1,620 Hybrid executions.

The study assumes known bursts, one CPU, no I/O, and zero modeled scheduling/context-switch overhead. Results support performance trade-off analysis, not universal superiority. Run the script again to regenerate reported results from current source.

Note that `context_switches` counts consecutive execution intervals with different PIDs, not physical OS switches.
