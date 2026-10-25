"""Sanity checks for copied repository algorithms and benchmark reproduction."""
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from process import Process
from hybrid import hybrid
from fcfs import fcfs
from rr import round_robin
from metrics import calculate_metrics

class BenchmarkChecks(unittest.TestCase):
    def test_website_example_matches(self):
        p=[Process('P1',0,2),Process('P2',1,20),Process('P3',2,3),Process('P4',3,30),Process('P5',4,8)]
        cases={'FCFS':fcfs(p), 'Round Robin':round_robin(p,4)}
        ps,g,*_=hybrid(p,return_full_log=True)
        cases['Hybrid']=(ps,g)
        self.assertAlmostEqual(calculate_metrics(*cases['FCFS'])['avg_waiting'],18.8)
        self.assertAlmostEqual(calculate_metrics(*cases['Round Robin'])['avg_response'],4)
        self.assertAlmostEqual(calculate_metrics(*cases['Hybrid'])['waiting_stddev'],10.2761860629)
        self.assertEqual(calculate_metrics(*cases['Hybrid'])['context_switches'],6)
    def test_mode_switch_from_sjf_to_rr(self):
        p=[Process('P1',0,2),Process('P2',1,20),Process('P3',2,3),Process('P4',3,30),Process('P5',4,8)]
        _,_,log,history=hybrid(p,return_full_log=True)
        self.assertEqual(history[0]['Mode'],'SJF')
        self.assertEqual(history[1]['Mode'],'RR')
        self.assertEqual(history[1]['Quantum'],8)
    def test_aging_has_override(self):
        p=[Process('Long',0,20),Process('S1',0,1),Process('S2',0,1),Process('S3',0,1)]
        _,_,_,log=hybrid(p,cv_threshold=10,queue_threshold=10,aging_threshold=2,return_full_log=True)
        self.assertTrue(any(x['Aging Override'] for x in log))
    def test_process_metrics_identity(self):
        p=[Process('P1',0,5),Process('P2',0,3),Process('P3',2,11)]
        ps,g,*_=hybrid(p)
        for x in ps:
            self.assertEqual(x.waiting_time,x.completion_time-x.arrival_time-x.burst_time)
            self.assertEqual(x.response_time,x.start_time-x.arrival_time)
        self.assertEqual(sum(e-s for _,s,e in g),19)

if __name__=='__main__':unittest.main(verbosity=2)
