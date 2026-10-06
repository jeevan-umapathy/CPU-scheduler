// run: .\venv\Scripts\python.exe web_demo\server.py

const scenarios = {
  low: {
    note: "Burst times: 5, 6, 4, 5, 7. Three processes are ready at time 0.",
    rows: [["P1", 0, 5], ["P2", 0, 6], ["P3", 0, 4], ["P4", 4, 5], ["P5", 8, 7]],
  },
  high: {
    note: "Burst times range from 2 to 30.",
    rows: [["P1", 0, 2], ["P2", 1, 20], ["P3", 2, 3], ["P4", 3, 30], ["P5", 4, 8]],
  },
  heavy: {
    note: "Seven processes with equal bursts arrive between time 0 and 3.",
    rows: [["P1", 0, 5], ["P2", 0, 5], ["P3", 1, 5], ["P4", 1, 5], ["P5", 2, 5], ["P6", 2, 5], ["P7", 3, 5]],
  },
  custom: {
    note: "Edit, add, or remove processes.",
    rows: [["P1", 0, 5], ["P2", 1, 3], ["P3", 2, 7]],
  },
};

const metricDescriptions = {
  avg_waiting: "Lower is better · average time ready but not running.",
  avg_turnaround: "Lower is better · average time from arrival to completion.",
  avg_response: "Lower is better · average delay until a process first gets CPU time.",
  throughput: "Higher is better · completed processes per time unit.",
  cpu_utilization: "Higher means less idle time during the observed interval.",
  context_switches: "Process changes between adjacent slices; switching cost is not modeled.",
};

const algorithmOrder = ["FCFS", "SJF", "Round Robin", "Adaptive Hybrid"];
const state = { data: null, step: 0, customRows: scenarios.custom.rows.map(row => [...row]) };
const byId = id => document.getElementById(id);

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = String(text);
  return element;
}

function clear(element) { element.replaceChildren(); }

function addRow(pid = "", arrival = 0, burst = 1) {
  const row = node("tr");
  for (const [value, type, label] of [
    [pid, "text", "PID"], [arrival, "number", "Arrival time"], [burst, "number", "Burst time"],
  ]) {
    const cell = node("td");
    const input = node("input");
    input.type = type;
    input.value = value;
    input.setAttribute("aria-label", label);
    if (type === "number") { input.min = label === "Burst time" ? "1" : "0"; input.step = "1"; }
    input.addEventListener("input", markCustom);
    cell.append(input);
    row.append(cell);
  }
  const removeCell = node("td");
  const remove = node("button", "remove-button", "×");
  remove.type = "button";
  remove.setAttribute("aria-label", `Remove ${pid || "process"}`);
  remove.addEventListener("click", () => { row.remove(); markCustom(); });
  removeCell.append(remove);
  row.append(removeCell);
  byId("process-rows").append(row);
}

function tableValues() {
  return [...byId("process-rows").querySelectorAll("tr")].map(row => {
    const fields = row.querySelectorAll("input");
    return [fields[0].value.trim(), fields[1].value, fields[2].value];
  });
}

function markCustom() {
  state.customRows = tableValues();
  if (byId("preset").value !== "custom") {
    byId("preset").value = "custom";
    byId("preset-note").textContent = scenarios.custom.note;
  }
  markResultsStale();
}

function markResultsStale() {
  if (!state.data) return;
  byId("run-status").textContent = "Inputs changed · rerun";
  byId("run-status").classList.remove("done");
}

function loadScenario(key) {
  const scenario = scenarios[key];
  byId("preset-note").textContent = scenario.note;
  clear(byId("process-rows"));
  const rows = key === "custom" ? state.customRows : scenario.rows;
  rows.forEach(row => addRow(...row));
  markResultsStale();
}

function readWorkload() {
  const rows = tableValues();
  if (rows.length < 1 || rows.length > 30) throw new Error("Enter between 1 and 30 processes.");
  const seen = new Set();
  const processes = rows.map(([pid, arrivalText, burstText], index) => {
    if (!pid) throw new Error(`Row ${index + 1} needs a PID.`);
    if (seen.has(pid)) throw new Error(`Duplicate PID: ${pid}.`);
    seen.add(pid);
    if (arrivalText === "" || burstText === "") throw new Error(`${pid} needs arrival and burst times.`);
    const arrival = Number(arrivalText);
    const burst = Number(burstText);
    if (!Number.isInteger(arrival) || arrival < 0) throw new Error(`${pid} arrival must be a nonnegative integer.`);
    if (!Number.isInteger(burst) || burst <= 0) throw new Error(`${pid} burst must be a positive integer.`);
    return { pid, arrival, burst };
  });
  const readNumber = (id, label) => {
    const value = byId(id).value;
    if (value === "" || !Number.isFinite(Number(value))) throw new Error(`${label} needs a number.`);
    return Number(value);
  };
  const settings = {
    cv_threshold: readNumber("cv-threshold", "CV threshold"),
    queue_threshold: readNumber("queue-threshold", "Queue threshold"),
    aging_threshold: readNumber("aging-threshold", "Aging threshold"),
    min_quantum: readNumber("min-quantum", "Minimum quantum"),
    max_quantum: readNumber("max-quantum", "Maximum quantum"),
  };
  return { processes, settings, rr_quantum: readNumber("rr-quantum", "RR quantum") };
}

async function runSimulation() {
  const error = byId("error-message");
  error.hidden = true;
  const button = byId("run-button");
  try {
    const workload = readWorkload();
    button.disabled = true;
    button.firstChild.textContent = "Running simulation ";
    const response = await fetch("/api/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(workload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Simulation failed.");
    state.data = result;
    state.step = 0;
    byId("run-status").textContent = "Simulation complete";
    byId("run-status").classList.add("done");
    for (const section of ["replay", "timeline", "compare"]) {
      byId(`${section}-empty`).hidden = true;
      byId(`${section}-content`).hidden = false;
    }
    renderReplay();
    renderTimeline();
    renderComparison();
  } catch (problem) {
    error.textContent = problem.message;
    error.hidden = false;
  } finally {
    button.disabled = false;
    button.firstChild.textContent = "Run simulation ";
  }
}

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function decisionReason(entry) {
  const settings = state.data.settings;
  const sjf = entry.Mode.startsWith("SJF");
  const reasons = [];
  if (entry.CV >= settings.cv_threshold) reasons.push("CV reached the variation threshold");
  if (entry.Queue >= settings.queue_threshold) reasons.push("queue length reached the load threshold");
  let result = sjf
    ? "CV and queue length were both below their thresholds. SJF runs the selected process to completion."
    : `${reasons.join(" and ") || "The RR condition was met"}. RR takes the next process from the FIFO queue.`;
  if (entry["Aging Override"]) {
    result += ` Aging selected ${entry.Process} because its accumulated waiting crossed the threshold.`;
  }
  if (!sjf) {
    const middle = median(entry["Ready State"].map(item => item.remaining));
    result += ` Median remaining burst = ${middle}; after clamping, quantum = ${entry.Quantum}.`;
  }
  return result;
}

function renderReplay() {
  if (!state.data) return;
  const log = state.data.hybrid.log;
  const entry = log[state.step];
  const settings = state.data.settings;
  const sjf = entry.Mode.startsWith("SJF");
  byId("step-number").textContent = `${state.step + 1} / ${log.length}`;
  byId("step-range").max = String(log.length - 1);
  byId("step-range").value = String(state.step);
  byId("prev-step").disabled = state.step === 0;
  byId("next-step").disabled = state.step === log.length - 1;
  byId("decision-time").textContent = entry.Time;
  byId("decision-title").textContent = `${sjf ? "SJF" : "RR"} selects ${entry.Process}`;
  byId("mode-badge").textContent = entry.Mode;
  byId("mode-badge").classList.toggle("rr", !sjf);
  byId("decision-cv").textContent = Number(entry.CV).toFixed(3);
  byId("decision-queue").textContent = entry.Queue;
  byId("decision-quantum").textContent = entry.Quantum ?? "—";
  byId("decision-interval").textContent = `${entry.Start} → ${entry.End}`;
  byId("cv-rule").textContent = `threshold ${settings.cv_threshold}`;
  byId("queue-rule").textContent = `RR at ${settings.queue_threshold} or more`;
  byId("decision-reason").textContent = decisionReason(entry);

  const queue = byId("ready-queue");
  clear(queue);
  entry["Ready State"].forEach(item => {
    const card = node("div", `queue-card${item.pid === entry.Process ? " selected" : ""}`);
    card.append(node("strong", "", item.pid));
    card.append(node("span", "", `remaining ${item.remaining}`));
    card.append(node("span", "", `waited ${item.waited}`));
    queue.append(card);
  });

  const history = byId("mode-history");
  clear(history);
  const currentChange = [...state.data.hybrid.history]
    .reverse().find(item => item.Time <= entry.Time);
  state.data.hybrid.history.forEach(item => {
    const row = node("div", `history-item${item === currentChange ? " current" : ""}`);
    row.append(node("strong", "", `t=${item.Time}`));
    row.append(node("span", `mode-name${item.Mode.startsWith("RR") ? " rr" : ""}`, item.Mode));
    row.append(node("span", "", `CV ${Number(item.CV).toFixed(2)}`));
    row.append(node("span", "", `Q ${item.Queue}`));
    row.append(node("span", "", item.Quantum === null ? "q —" : `q ${item.Quantum}`));
    history.append(row);
  });
  if (byId("timeline-algorithm").value === "Adaptive Hybrid") renderTimeline();
}

function renderTimeline() {
  if (!state.data) return;
  const name = byId("timeline-algorithm").value;
  const run = state.data.algorithms[name];
  const chart = byId("timeline-chart");
  clear(chart);
  const endTime = Math.max(...run.gantt.map(item => item.end));
  const pids = run.processes.map(item => item.pid);
  const activeInterval = name === "Adaptive Hybrid" ? state.data.hybrid.log[state.step] : null;
  pids.forEach(pid => {
    const row = node("div", "timeline-row");
    row.append(node("div", "timeline-pid", pid));
    const track = node("div", "timeline-track");
    run.gantt.forEach(interval => {
      if (interval.pid !== pid) return;
      const selected = activeInterval && interval.start === activeInterval.Start && interval.end === activeInterval.End && interval.pid === activeInterval.Process;
      const slice = node("div", `timeline-slice${name === "Adaptive Hybrid" ? " hybrid" : ""}${selected ? " active" : ""}`);
      slice.style.left = `${(interval.start / endTime) * 100}%`;
      slice.style.width = `${((interval.end - interval.start) / endTime) * 100}%`;
      slice.title = `${pid}: ${interval.start}–${interval.end}`;
      track.append(slice);
    });
    row.append(track);
    chart.append(row);
  });
  const axis = node("div", "timeline-axis");
  [0, .25, .5, .75, 1].forEach(fraction => axis.append(node("span", "", Math.round(endTime * fraction))));
  chart.append(axis);

  const results = byId("result-rows");
  clear(results);
  run.processes.forEach(item => {
    const row = node("tr");
    for (const value of [item.pid, item.arrival, item.burst, item.completion, item.waiting, item.turnaround, item.response]) {
      row.append(node("td", "", value));
    }
    results.append(row);
  });
}

function formatMetric(key, value) {
  if (key === "context_switches") return String(value);
  if (key === "cpu_utilization") return `${value.toFixed(1)}%`;
  return value.toFixed(key === "throughput" ? 3 : 2);
}

function renderComparison() {
  if (!state.data) return;
  const metric = byId("compare-metric").value;
  byId("metric-note").textContent = metricDescriptions[metric];
  const data = state.data.algorithms;
  const scale = Math.max(...algorithmOrder.map(name => data[name].metrics[metric]), 0.001);
  const bars = byId("comparison-bars");
  clear(bars);
  algorithmOrder.forEach(name => {
    const value = data[name].metrics[metric];
    const row = node("div", "comparison-bar-row");
    row.append(node("span", "", name));
    const track = node("div", "comparison-track");
    const fill = node("div", `comparison-fill${name === "Adaptive Hybrid" ? " hybrid" : ""}`);
    fill.style.width = `${Math.max(1, value / scale * 100)}%`;
    track.append(fill);
    row.append(track);
    row.append(node("span", "", formatMetric(metric, value)));
    bars.append(row);
  });

  const table = byId("comparison-rows");
  clear(table);
  algorithmOrder.forEach(name => {
    const values = data[name].metrics;
    const row = node("tr");
    row.append(node("td", "", name));
    for (const key of ["avg_waiting", "avg_turnaround", "avg_response", "throughput", "cpu_utilization", "context_switches"]) {
      row.append(node("td", "", formatMetric(key, values[key])));
    }
    table.append(row);
  });
}

function selectView(name) {
  document.querySelectorAll(".tab").forEach(tab => {
    const selected = tab.dataset.view === name;
    tab.classList.toggle("active", selected);
    tab.setAttribute("aria-selected", String(selected));
  });
  document.querySelectorAll(".view").forEach(view => view.classList.toggle("active", view.id === `${name}-view`));
}

byId("preset").addEventListener("change", event => loadScenario(event.target.value));
byId("add-process").addEventListener("click", () => {
  addRow(`P${byId("process-rows").children.length + 1}`, 0, 1);
  markCustom();
});
byId("run-button").addEventListener("click", runSimulation);
byId("prev-step").addEventListener("click", () => { state.step -= 1; renderReplay(); });
byId("next-step").addEventListener("click", () => { state.step += 1; renderReplay(); });
byId("step-range").addEventListener("input", event => { state.step = Number(event.target.value); renderReplay(); });
byId("timeline-algorithm").addEventListener("change", renderTimeline);
byId("compare-metric").addEventListener("change", renderComparison);
document.querySelectorAll(".tab").forEach(tab => tab.addEventListener("click", () => selectView(tab.dataset.view)));
document.querySelectorAll(".settings input").forEach(input => input.addEventListener("input", () => {
  markResultsStale();
}));

loadScenario("low");
runSimulation();
