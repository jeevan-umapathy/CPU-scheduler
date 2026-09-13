import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from fcfs import fcfs
from hybrid import (
    AGING_THRESHOLD,
    CV_THRESHOLD,
    MAX_QUANTUM,
    MIN_QUANTUM,
    QUEUE_THRESHOLD,
    hybrid,
)
from metrics import calculate_metrics
from process import Process
from rr import round_robin
from sjf import sjf
from workload import analyze_workload


st.set_page_config(page_title="CPU Scheduling Simulator", layout="wide")
st.title("Adaptive CPU Scheduling Simulator")
st.caption(
    "Compare FCFS, non-preemptive SJF, Round Robin, and a workload-aware "
    "Adaptive Hybrid scheduler."
)


PRESETS = {
    "Custom": pd.DataFrame(
        {
            "PID": ["P1", "P2", "P3"],
            "Arrival Time": [0, 1, 2],
            "Burst Time": [5, 3, 7],
        }
    ),
    "Low Variance": pd.DataFrame(
        {
            "PID": ["P1", "P2", "P3", "P4", "P5"],
            "Arrival Time": [0, 1, 2, 3, 4],
            "Burst Time": [5, 6, 4, 5, 7],
        }
    ),
    "High Variance": pd.DataFrame(
        {
            "PID": ["P1", "P2", "P3", "P4", "P5"],
            "Arrival Time": [0, 1, 2, 3, 4],
            "Burst Time": [2, 20, 3, 30, 8],
        }
    ),
    "Heavy Load": pd.DataFrame(
        {
            "PID": ["P1", "P2", "P3", "P4", "P5", "P6", "P7"],
            "Arrival Time": [0, 0, 1, 1, 2, 2, 3],
            "Burst Time": [4, 15, 3, 18, 5, 20, 7],
        }
    ),
}


def validate_input(data):
    required = ["PID", "Arrival Time", "Burst Time"]
    if data.empty:
        return False, "Please enter at least one process."
    if any(column not in data.columns for column in required):
        return False, "The process table must contain PID, Arrival Time, and Burst Time."

    pids = data["PID"].fillna("").astype(str).str.strip()
    if (pids == "").any():
        return False, "Every process must have a non-empty PID."
    if pids.duplicated().any():
        return False, "PIDs must be unique."

    arrivals = pd.to_numeric(data["Arrival Time"], errors="coerce")
    bursts = pd.to_numeric(data["Burst Time"], errors="coerce")
    if arrivals.isna().any() or bursts.isna().any():
        return False, "Arrival and burst times must be valid integers."
    if ((arrivals % 1) != 0).any() or ((bursts % 1) != 0).any():
        return False, "Arrival and burst times must be whole numbers."
    if (arrivals < 0).any():
        return False, "Arrival time cannot be negative."
    if (bursts <= 0).any():
        return False, "Burst time must be greater than zero."
    return True, ""


def create_processes(data):
    return [
        Process(
            str(row["PID"]).strip(),
            int(row["Arrival Time"]),
            int(row["Burst Time"]),
        )
        for _, row in data.iterrows()
    ]


def create_result_dataframe(result):
    return pd.DataFrame(
        [
            {
                "PID": p.pid,
                "Arrival": p.arrival_time,
                "Burst": p.burst_time,
                "Completion": p.completion_time,
                "Turnaround": p.turnaround_time,
                "Waiting": p.waiting_time,
                "Response": p.response_time,
            }
            for p in sorted(result, key=lambda item: item.pid)
        ]
    )


def plot_compact_gantt(gantt):
    fig, ax = plt.subplots(figsize=(10, 2.2))
    colors = plt.get_cmap("tab20")
    for index, (pid, start, end) in enumerate(gantt):
        ax.barh(0, end - start, left=start, color=colors(index % 20), edgecolor="white")
        ax.text((start + end) / 2, 0, pid, ha="center", va="center", fontsize=9)
    ax.set_yticks([])
    ax.set_xlabel("Time")
    ax.set_title("Execution Gantt Chart")
    fig.tight_layout()
    return fig


def plot_process_timeline(gantt):
    pids = list(dict.fromkeys(pid for pid, _, _ in gantt))
    positions = {pid: index for index, pid in enumerate(pids)}
    total_span = max(end for _, _, end in gantt) if gantt else 1
    fig_height = max(2.8, 0.48 * len(pids) + 1.4)
    fig, ax = plt.subplots(figsize=(11, fig_height))
    colors = plt.get_cmap("tab20")

    for pid, start, end in gantt:
        duration = end - start
        y = positions[pid]
        ax.barh(y, duration, left=start, height=0.58, color=colors(y % 20))
        if duration >= max(1, total_span * 0.04):
            ax.text(
                (start + end) / 2,
                y,
                f"{start}-{end}",
                ha="center",
                va="center",
                fontsize=8,
            )

    ax.set_yticks(range(len(pids)), pids)
    ax.invert_yaxis()
    ax.set_xlabel("Time")
    ax.set_ylabel("Process")
    ax.set_title("Process-Lane Execution Timeline")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    return fig


def show_metrics(values):
    labels = [
        ("Average Waiting Time", "avg_waiting", "{:.2f}"),
        ("Average Turnaround Time", "avg_turnaround", "{:.2f}"),
        ("Average Response Time", "avg_response", "{:.2f}"),
        ("Throughput", "throughput", "{:.3f}"),
        ("CPU Utilization", "cpu_utilization", "{:.2f}%"),
        ("Context Switches", "context_switches", "{}"),
    ]
    for column, (label, key, pattern) in zip(st.columns(6), labels):
        column.metric(label, pattern.format(values[key]))


def hybrid_settings():
    with st.expander("Advanced Settings"):
        col1, col2, col3 = st.columns(3)
        cv_threshold = col1.number_input(
            "CV threshold", min_value=0.0, value=float(CV_THRESHOLD), step=0.05
        )
        queue_threshold = col2.number_input(
            "Queue threshold", min_value=1, value=QUEUE_THRESHOLD, step=1
        )
        aging_threshold = col3.number_input(
            "Aging threshold", min_value=1, value=AGING_THRESHOLD, step=1
        )
        col4, col5 = st.columns(2)
        min_quantum = col4.number_input(
            "Minimum RR quantum", min_value=1, value=MIN_QUANTUM, step=1
        )
        max_quantum = col5.number_input(
            "Maximum RR quantum", min_value=1, value=MAX_QUANTUM, step=1
        )
    return {
        "cv_threshold": float(cv_threshold),
        "queue_threshold": int(queue_threshold),
        "aging_threshold": int(aging_threshold),
        "min_quantum": int(min_quantum),
        "max_quantum": int(max_quantum),
    }


preset = st.selectbox("Workload Preset", list(PRESETS))
if st.session_state.get("active_preset") != preset:
    for result_key in ("simulation_result", "hybrid_analysis", "comparison_result"):
        st.session_state.pop(result_key, None)
    st.session_state["active_preset"] = preset
# A separate editor key per preset prevents one preset's edited rows from
# appearing when another preset is selected.
data = st.data_editor(
    PRESETS[preset].copy(),
    num_rows="dynamic",
    use_container_width=True,
    key=f"process_editor_{preset}",
)

simulator_tab, analysis_tab, comparison_tab = st.tabs(
    ["Simulator", "Hybrid Analysis", "Comparison"]
)

with analysis_tab:
    st.subheader("Hybrid Workload Analysis")
    settings = hybrid_settings()
    st.caption(
        f"Current thresholds: CV < {settings['cv_threshold']:.2f}, "
        f"queue < {settings['queue_threshold']}, aging = {settings['aging_threshold']}, "
        f"RR quantum = {settings['min_quantum']}–{settings['max_quantum']}."
    )
    if settings["max_quantum"] < settings["min_quantum"]:
        st.error("Maximum RR quantum must be at least the minimum RR quantum.")

    valid_for_summary, _ = validate_input(data)
    if valid_for_summary:
        summary_processes = create_processes(data)
        workload_cv, total_queue = analyze_workload(summary_processes)
        initially_ready = sum(p.arrival_time == 0 for p in summary_processes)
        c1, c2, c3 = st.columns(3)
        c1.metric("Configured Workload CV", f"{workload_cv:.3f}")
        c2.metric("Total Processes", total_queue)
        c3.metric("Ready at Time 0", initially_ready)

    if st.button("Run Hybrid Analysis", disabled=settings["max_quantum"] < settings["min_quantum"]):
        valid, message = validate_input(data)
        if not valid:
            st.error(message)
        else:
            result, gantt, history, full_log = hybrid(
                create_processes(data), return_full_log=True, **settings
            )
            st.session_state["hybrid_analysis"] = {
                "result": result,
                "gantt": gantt,
                "history": history,
                "full_log": full_log,
            }

    analysis = st.session_state.get("hybrid_analysis")
    if analysis:
        st.markdown("**Mode-change history**")
        st.dataframe(pd.DataFrame(analysis["history"]), use_container_width=True)
        aging_events = [
            row for row in analysis["full_log"] if row["Aging Override"]
        ]
        st.markdown("**Aging events**")
        if aging_events:
            st.dataframe(pd.DataFrame(aging_events), use_container_width=True)
        else:
            st.info("No process crossed the aging threshold in this run.")
        with st.expander("Full execution log"):
            st.dataframe(pd.DataFrame(analysis["full_log"]), use_container_width=True)

with simulator_tab:
    st.subheader("Run One Algorithm")
    algorithm = st.selectbox(
        "Algorithm", ["FCFS", "SJF", "Round Robin", "Adaptive Hybrid"]
    )
    rr_quantum = 4
    if algorithm == "Round Robin":
        rr_quantum = st.number_input("RR Time Quantum", min_value=1, value=4, step=1)

    if st.button("Run Simulation"):
        valid, message = validate_input(data)
        if not valid:
            st.error(message)
        elif settings["max_quantum"] < settings["min_quantum"]:
            st.error("Correct the hybrid quantum limits in Hybrid Analysis.")
        else:
            processes = create_processes(data)
            history = []
            full_log = []
            if algorithm == "FCFS":
                result, gantt = fcfs(processes)
            elif algorithm == "SJF":
                result, gantt = sjf(processes)
            elif algorithm == "Round Robin":
                result, gantt = round_robin(processes, int(rr_quantum))
            else:
                result, gantt, history, full_log = hybrid(
                    processes, return_full_log=True, **settings
                )
                st.session_state["hybrid_analysis"] = {
                    "result": result,
                    "gantt": gantt,
                    "history": history,
                    "full_log": full_log,
                }
            st.session_state["simulation_result"] = {
                "algorithm": algorithm,
                "result": result,
                "gantt": gantt,
                "metrics": calculate_metrics(result, gantt),
            }

    simulation = st.session_state.get("simulation_result")
    if simulation:
        st.markdown(f"**Latest result: {simulation['algorithm']}**")
        st.dataframe(
            create_result_dataframe(simulation["result"]), use_container_width=True
        )
        show_metrics(simulation["metrics"])
        if simulation["algorithm"] in ("Round Robin", "Adaptive Hybrid"):
            figure = plot_process_timeline(simulation["gantt"])
        else:
            figure = plot_compact_gantt(simulation["gantt"])
        st.pyplot(figure)
        plt.close(figure)

with comparison_tab:
    st.subheader("Same-Workload Comparison")
    comparison_quantum = st.number_input(
        "Round Robin quantum for comparison", min_value=1, value=4, step=1
    )
    if st.button("Compare All Algorithms"):
        valid, message = validate_input(data)
        if not valid:
            st.error(message)
        elif settings["max_quantum"] < settings["min_quantum"]:
            st.error("Correct the hybrid quantum limits in Hybrid Analysis.")
        else:
            processes = create_processes(data)
            runs = {
                "FCFS": fcfs(processes),
                "SJF": sjf(processes),
                "Round Robin": round_robin(processes, int(comparison_quantum)),
            }
            hybrid_result, hybrid_gantt, _ = hybrid(processes, **settings)
            runs["Adaptive Hybrid"] = (hybrid_result, hybrid_gantt)

            rows = []
            for name, (result, gantt) in runs.items():
                values = calculate_metrics(result, gantt)
                rows.append(
                    {
                        "Algorithm": name,
                        "Average Waiting": values["avg_waiting"],
                        "Average Turnaround": values["avg_turnaround"],
                        "Average Response": values["avg_response"],
                        "Throughput": values["throughput"],
                        "CPU Utilization": values["cpu_utilization"],
                        "Context Switches": values["context_switches"],
                    }
                )
            st.session_state["comparison_result"] = pd.DataFrame(rows).round(3)

    comparison = st.session_state.get("comparison_result")
    if comparison is not None:
        st.dataframe(comparison, use_container_width=True, hide_index=True)
        metric = st.selectbox(
            "Metric to chart", [column for column in comparison.columns if column != "Algorithm"]
        )
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(comparison["Algorithm"], comparison[metric])
        ax.set_ylabel(metric)
        ax.tick_params(axis="x", rotation=12)
        ax.set_title(f"{metric} Comparison")
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)
