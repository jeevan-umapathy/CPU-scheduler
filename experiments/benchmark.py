"""Reproducible synthetic workload study for CPU-scheduler (2026-10-25).

Run: python benchmark.py
Python stdlib only; matplotlib needed only for the separate plotting script.
Reference: jeevan-umapathy/CPU-scheduler, default branch, code fetched 2026-10-25.
This is an independent benchmark; do not confuse synthetic workloads with real CPU traces.
"""
import csv
import json
import random
from collections import Counter
from pathlib import Path
from statistics import mean

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from process import Process
from fcfs import fcfs
from sjf import sjf
from rr import round_robin
from hybrid import hybrid
from metrics import calculate_metrics

OUT = Path(__file__).resolve().parent / 'results'
OUT.mkdir(exist_ok=True)
FAMILIES = ['Similar/sparse', 'Similar/dense', 'Mixed/dense', 'High-variance/staggered', 'Short+long/batch', 'Moderate/staggered']
ALGORITHMS = ['FCFS', 'SJF', 'Round Robin', 'Adaptive Hybrid']
METRICS = ['avg_waiting','max_waiting','waiting_stddev','avg_turnaround','avg_response','context_switches','throughput','cpu_utilization']
TRIALS=30


def generate(family, trial):
    """Return (pid, arrival time, burst time) with a fixed seed per trial."""
    rng = random.Random(20261025 + FAMILIES.index(family)*1009 + trial)
    items = []
    t=0
    n=24 if family=='Similar/dense' else 20
    for i in range(n):
        if family=='Similar/sparse':
            t += rng.randint(4, 8)
            arrival=t
            burst=rng.randint(5,7)
        elif family=='Similar/dense':
            arrival=rng.randint(0,6)
            burst=rng.randint(5,7)
        elif family=='Mixed/dense':
            arrival=rng.randint(0,10)
            burst=rng.randint(1,28)
        elif family=='High-variance/staggered':
            t += rng.randint(1,4)
            arrival=t
            burst=rng.randint(1,28)
        elif family=='Short+long/batch':
            arrival=rng.randint(0,12)
            burst=rng.randint(2,5) if rng.random()<.7 else rng.randint(25,45)
        elif family=='Moderate/staggered':
            t += rng.randint(3,10)
            arrival=t
            burst=rng.randint(3,18)
        items.append((f'P{i+1}',arrival,burst))
    return items


def validate(spec,finished,gantt):
    expected={p:burst for p,arrival,burst in spec}
    actual={p:0 for p,_,_ in spec}
    tprev=-1
    for pid,start,end in gantt:
        assert start>=tprev and end>start,(spec,gantt)
        actual[pid]+=end-start
        tprev=end
    assert actual==expected,(actual, expected)
    for p in finished:
        assert p.remaining_time==0
        assert p.waiting_time == p.completion_time-p.arrival_time-p.burst_time
        assert p.response_time == p.start_time-p.arrival_time
        assert p.waiting_time>=0 and p.response_time>=0


def run(spec, algorithm, **hybrid_kwargs):
    processes=[Process(*row) for row in spec]
    if algorithm=='FCFS': finished,gantt=fcfs(processes)
    elif algorithm=='SJF': finished,gantt=sjf(processes)
    elif algorithm=='Round Robin': finished,gantt=round_robin(processes,4)
    elif algorithm=='Adaptive Hybrid': finished,gantt,*_=hybrid(processes,**hybrid_kwargs)
    else: raise KeyError(algorithm)
    validate(spec,finished,gantt)
    return calculate_metrics(finished,gantt)


def dump_csv(path, rows, columns):
    with open(path, 'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=columns)
        w.writeheader()
        w.writerows(rows)


workload_rows=[]
raw=[]
for family in FAMILIES:
    for trial in range(1,TRIALS+1):
        spec=generate(family,trial)
        workload_rows += [dict(family=family,trial=trial,pid=p,arrival=arrival,burst=burst) for p,arrival,burst in spec]
        for algorithm in ALGORITHMS:
            metrics=run(spec,algorithm)
            raw.append(dict(family=family, trial=trial, algorithm=algorithm,**metrics))
dump_csv(OUT/'workloads.csv',workload_rows,['family','trial','pid','arrival','burst'])
dump_csv(OUT/'raw_metrics.csv',raw,['family','trial','algorithm']+METRICS)
summary=[]
for family in FAMILIES + ['ALL (equal trials)']:
    for algorithm in ALGORITHMS:
        filt=[r for r in raw if (r['family']==family or family=='ALL (equal trials)') and r['algorithm']==algorithm]
        summary.append(dict(family=family,algorithm=algorithm,n=len(filt),**{key:mean(r[key] for r in filt) for key in METRICS}))
dump_csv(OUT/'summary.csv',summary,['family','algorithm','n']+METRICS)

# Strict metric comparisons under identical workloads, ties counted separately.
wins=[]
for family in FAMILIES+['ALL (equal trials)']:
    for key in ['avg_waiting','max_waiting','waiting_stddev','avg_response','context_switches']:
        rows=[r for r in raw if r['family']==family or family=='ALL (equal trials)']
        grouped={}
        for r in rows:grouped.setdefault((r['family'],r['trial']),{})[r['algorithm']]=r[key]
        hbetter=sum(1 for case in grouped.values() if case['Adaptive Hybrid']<case['SJF']-1e-9)
        same=sum(1 for case in grouped.values() if abs(case['Adaptive Hybrid']-case['SJF'])<1e-9)
        rbetter=sum(1 for case in grouped.values() if case['Adaptive Hybrid']>case['SJF']+1e-9)
        wins.append(dict(family=family, metric=key, hybrid_better_than_sjf=hbetter,tied=same,sjf_better=rbetter))
dump_csv(OUT/'paired_vs_sjf.csv',wins,['family','metric','hybrid_better_than_sjf','tied','sjf_better'])

# Sensitivity study, holding generated workloads fixed.
sense=[]
for cv in [0.25,0.5,0.75]:
    for queue in [3,4,6]:
        for family in FAMILIES:
            vals=[]
            for trial in range(1,TRIALS+1):
                vals.append(run(generate(family,trial),'Adaptive Hybrid',cv_threshold=cv,queue_threshold=queue))
            sense.append(dict(cv_threshold=cv,queue_threshold=queue,family=family,n=len(vals),**{m:mean(r[m] for r in vals) for m in METRICS}))
dump_csv(OUT/'sensitivity.csv',sense,['cv_threshold','queue_threshold','family','n']+METRICS)

# Verify exact match with the website's demo comparison.
demo=[('P1',0,2),('P2',1,20),('P3',2,3),('P4',3,30),('P5',4,8)]
demo_metrics={a:run(demo,a) for a in ALGORITHMS}
assert [round(demo_metrics[a]['avg_waiting'],2) for a in ALGORITHMS]==[18.80,8.60,15.80,15.00]
assert round(demo_metrics['Adaptive Hybrid']['waiting_stddev'],2)==10.28
meta={'generated_date':'2026-10-25','project':'Adaptive Hybrid CPU Scheduling Using SJF and Round Robin for Dynamic Workloads','source':'GitHub repo jeevan-umapathy/CPU-scheduler, source files read using connected GitHub app','algorithm_settings':{'cv_threshold':0.5,'queue_threshold':4,'aging_threshold':15,'min_quantum':2,'max_quantum':8,'fixed_rr_quantum':4},'trials_per_family':TRIALS,'families':FAMILIES,'seeds':'20261025 + family_index*1009 + trial_number (1..30)','process_count':'24 for Similar/dense, 20 for all others','caveat':'Synthetic deterministic simulations; no measured OS context-switch penalty, scheduling computation overhead, or real application I/O.'}
(OUT/'experiment_settings.json').write_text(json.dumps(meta,indent=2))
print('Done. Total workload cases:',len(workload_rows),'process rows;',len(raw),'algorithm runs,',len(sense)*30,'sensitivity runs')
for s in summary:
    if s['family']=='ALL (equal trials)':
        print(s['algorithm'].ljust(16),'wait',round(s['avg_waiting'],2),'maxwait',round(s['max_waiting'],2),'SD',round(s['waiting_stddev'],2),'response',round(s['avg_response'],2),'switches',round(s['context_switches'],2))
print('Result directory:',OUT)
