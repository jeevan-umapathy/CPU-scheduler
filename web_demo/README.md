# CPU Scheduling Simulator website

This is a separate, browser based presentation of the existing Python CPU
schedulers. It does not duplicate the scheduling algorithms in JavaScript.
The local server calls `fcfs.py`, `sjf.py`, `rr.py`, `hybrid.py`, and
`metrics.py` from the parent folder.

## Run

From the project root in PowerShell:

```powershell
cd C:\Users\Jeevan\CPU-scheduler
.\venv\Scripts\python.exe web_demo\server.py
```

Open <http://127.0.0.1:8502> in a browser. Keep PowerShell open while the
website is running. Stop the server with `Ctrl+C`.

This version uses plain HTML, CSS, and JavaScript, with the Python standard
library HTTP server. No npm installation or build step is needed.

## What to show in the review

1. **Low variance:** the hybrid chooses SJF while both measures are below
   their thresholds.
2. **High variance:** step forward to see a switch from SJF to RR. Point to
   the ready queue, measured CV, and median based quantum.
3. **Heavy ready queue:** bursts are equal, so queue length alone can make
   RR necessary.
4. **Execution timeline:** each process has its own lane; the selected hybrid
   slice is highlighted.
5. **Compare algorithms:** all four results come from the same workload.

The website presents the Python scheduling results and lets you inspect each
hybrid decision. The contribution remains the workload aware scheduling logic.

The Hybrid scheduler is not expected to outperform SJF on every metric. SJF is
naturally strong for average waiting time when burst times are known. The
Hybrid approach instead evaluates a trade-off between average performance,
responsiveness, worst-case waiting, and starvation prevention. The comparison
view includes maximum waiting time and waiting-time standard deviation.
