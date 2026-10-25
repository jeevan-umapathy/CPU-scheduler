"""Plots from recorded summary.csv. Requires matplotlib."""
import csv
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'figures';OUT.mkdir(exist_ok=True)
rows=list(csv.DictReader(open(ROOT/'results'/'summary.csv',encoding='utf-8')))
family_order=['Similar/sparse','Similar/dense','Mixed/dense','High-variance/staggered','Short+long/batch','Moderate/staggered']
algs=['FCFS','SJF','Round Robin','Adaptive Hybrid']
colors=['#a6adb4','#353e49','#97aabd','#406987']
labels={'Similar/sparse':'Similar\nlight','Similar/dense':'Similar\nheavy','Mixed/dense':'Mixed\nheavy','High-variance/staggered':'Variable\nstaggered','Short+long/batch':'Short/long\nbatch','Moderate/staggered':'Mixed\nstaggered'}
lookup={(r['family'],r['algorithm']):r for r in rows}

def grouped(metric,title,ylabel,filename):
    x=np.arange(len(family_order)); w=.19
    fig,ax=plt.subplots(figsize=(10.5,4.5))
    for j,alg in enumerate(algs):
        val=[float(lookup[(family,alg)][metric]) for family in family_order]
        ax.bar(x+(j-1.5)*w,val,w,label=alg,color=colors[j])
    ax.set_xticks(x, [labels[f] for f in family_order],fontsize=9)
    ax.set_ylabel(ylabel)
    ax.set_title(title,pad=14,fontsize=12,weight='semibold')
    ax.grid(axis='y',alpha=.16)
    ax.set_axisbelow(True)
    ax.legend(frameon=False,ncol=4,fontsize=9,loc='upper center',bbox_to_anchor=(.5,-.17))
    ax.spines[['right','top']].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT/filename,dpi=180,bbox_inches='tight')
    plt.close(fig)

grouped('avg_waiting','Average waiting time across six synthetic workload families','Time units (lower is better)','average_wait_by_family.png')
grouped('max_waiting','Maximum waiting time across six workload families','Time units (lower is better)','maximum_wait_by_family.png')
grouped('context_switches','Context switches per simulation across six workload families','Process changes (lower is generally preferable)','context_switches_by_family.png')

# Sensitivity: CV and queue thresholds, averaged equally across six workload families
srows=list(csv.DictReader(open(ROOT/'results'/'sensitivity.csv',encoding='utf-8')))
fig,ax=plt.subplots(figsize=(7.3,3.7))
qs=[3,4,6];cvs=[.25,.5,.75]
vals=np.array([[np.mean([float(r['max_waiting']) for r in srows if float(r['cv_threshold'])==cv and int(r['queue_threshold'])==q]) for q in qs] for cv in cvs])
im=ax.imshow(vals,cmap='Blues',aspect='auto')
for i in range(len(cvs)):
    for j in range(len(qs)):
        ax.text(j,i,f'{vals[i,j]:.1f}',ha='center',va='center',fontsize=10,color='white' if vals[i,j]>np.quantile(vals,.65) else '#17252f')
ax.set_xticks(range(3),[str(q) for q in qs]); ax.set_yticks(range(3),[str(cv) for cv in cvs]);
ax.set_xlabel('Ready-queue threshold'); ax.set_ylabel('CV threshold')
ax.set_title('Hybrid maximum waiting: threshold sensitivity',fontsize=12,pad=12,weight='semibold')
fig.colorbar(im,ax=ax,label='Mean maximum waiting (time units)',fraction=.05,pad=.03)
fig.tight_layout(); fig.savefig(OUT/'parameter_sensitivity.png',dpi=180,bbox_inches='tight');plt.close(fig)
print('Plots created:',*[p.name for p in sorted(OUT.iterdir())],sep='\n')
