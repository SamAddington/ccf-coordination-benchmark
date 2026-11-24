#!/usr/bin/env python3
"""Sensitivity experiments using the frozen v26 clients and v25 event engine.
The experiments are synthetic post-review exploration; no production traffic.
"""
import csv, json, random, sys, time, statistics
from pathlib import Path
from itertools import product
from collections import defaultdict
ROOT=Path(__file__).resolve().parent
SRC=ROOT.parent/'v25'/'source'/'CCF_v15_Reproduction_Candidate_20261123'
sys.path.insert(0,str(SRC));sys.path.insert(0,str(ROOT))
from ccf_eventlab.model import world_factory
from ccf_eventlab.engine import RunConfig
from v12.distributed_lease import AccountedDRA, encoded_payload_bytes
from v14.distributed_capacity import DistributedCapacitySemaphoreEngine
import v14.distributed_capacity as capmod
import v12.distributed_lease as leasemod
from fair_engines import FallbackCapacity,ColocatedFallback

# One global two-state channel, rather than independent link-by-link bursts.
# Bad state arrives probability .05 from good; good arrives probability .18
# from bad; in bad state a packet drops with 0.9 probability, in good 0.
class BurstyChannel:
    def _burst_init(self):
        self._bad=False
        self._burst_stats={'burst_bad_packets':0,'burst_total_packets':0}
    def _bursty_drop(self):
        self._bad=(self.rng.random()>=.18) if self._bad else (self.rng.random()<.05)
        self._burst_stats['burst_total_packets']+=1
        if self._bad:self._burst_stats['burst_bad_packets']+=1
        return self._bad and self.rng.random()<.90
    def broadcast(self,origin,kind,payload):
        for a in self.agents:
            if a.id==origin:continue
            self.stats['total_messages']+=1
            self.stats[kind+'_messages']=self.stats.get(kind+'_messages',0)+1
            self.stats['wire_payload_bytes']=self.stats.get('wire_payload_bytes',0)+encoded_payload_bytes(origin,kind,payload)
            if self._bursty_drop():
                self.stats['delivery_losses']+=1;continue
            self.schedule(self.now+self.rng.uniform(self.cfg.delay_min,self.cfg.delay_max),'message',a.id,origin,kind,payload)
    def _send(self,origin,dest,kind,payload):
        if dest==origin:return self.message(dest,origin,kind,payload)
        self.stats['total_messages']+=1
        self.stats[kind+'_messages']=self.stats.get(kind+'_messages',0)+1
        self.stats['wire_payload_bytes']=self.stats.get('wire_payload_bytes',0)+encoded_payload_bytes(origin,kind,payload)
        if self._bursty_drop():
            self.stats['delivery_losses']+=1;return
        self.schedule(self.now+self.rng.uniform(self.cfg.delay_min,self.cfg.delay_max),'message',dest,origin,kind,payload)
    def run(self):
        r=super().run();r.update(self._burst_stats);return r

class BurstyDRA(BurstyChannel,AccountedDRA):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self._burst_init()
class BurstyPermit(BurstyChannel,DistributedCapacitySemaphoreEngine):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self._burst_init()
class BurstyFallback(BurstyChannel,FallbackCapacity):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self._burst_init()

def evaluate(w,seed,loss,horizon,arm,ttl=8.0,claim_ttl=5.0,settle_extra=.13,burst=False):
    cfg=RunConfig('dra' if arm=='claim_local' else 'independent','formal_capacity',horizon=horizon,
                  delay_min=.35,delay_max=.95,message_loss=loss,claim_ttl=claim_ttl,settle_extra=settle_extra)
    c=dict(physics='reference',release_profile='all_at_start')
    leasemod.LEASE_TTL=ttl
    capmod.LEASE_TTL=ttl
    if arm=='claim_local':k=BurstyDRA if burst else AccountedDRA;return k(w,cfg,seed,controller='dra',**c).run()
    if arm=='permit_sticky':k=BurstyPermit if burst else DistributedCapacitySemaphoreEngine;return k(w,cfg,seed,controller='distributed_capacity',**c).run()
    if arm=='permit_fallback':k=BurstyFallback if burst else FallbackCapacity;return k(w,cfg,seed,controller='distributed_capacity',fallback_after=1,**c).run()
    if arm=='permit_retx':return FallbackCapacity(w,cfg,seed,controller='distributed_capacity',fallback_after=1,release_replays=2,**c).run()
    if arm=='permit_colocated_fallback':return ColocatedFallback(w,cfg,seed,controller='distributed_capacity',fallback_after=1,**c).run()
    raise ValueError(arm)

def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    rows=[];t0=time.time();problem=[]
    def attempt(study,wi,w,seed,loss,horizon,arm,**kwargs):
        rec=dict(study=study,world_seed=w.seed,world_id=w.id,world_idx=wi,agents=w.num_agents,seed=seed,
                  loss=loss,horizon=horizon,arm=arm,**kwargs)
        try:
            d=evaluate(w,seed,loss,horizon,arm,**kwargs)
            rec.update(status='completed',completion_fraction=d['completion_fraction'],overcapacity_admissions=d['overcapacity_admissions'],
                       total_messages=d['total_messages'],delivery_losses=d['delivery_losses'],disruptions=d['disruptions'],
                       lease_requests=d.get('lease_requests',0),lease_stale_grants=d.get('lease_stale_grants',0),
                       fallback_switches=d.get('fallback_switches',0),burst_bad_packets=d.get('burst_bad_packets',0),
                       burst_total_packets=d.get('burst_total_packets',0),error='')
        except Exception as e:
            rec.update(status='failed',error=type(e).__name__+':'+str(e));problem.append(rec)
        rows.append(rec)
    # Low-loss cells 1% and 3%, with same 12 new worlds and three trials
    for wi,seed,loss,horizon,arm in product(range(220,232),(71011,71012,71013),(.01,.03),(16.0,54.0),
                    ('claim_local','permit_sticky','permit_fallback','permit_colocated_fallback')):
        w=world_factory(170123+wi*23,('small','medium','large')[wi%3]);attempt('low_loss',wi,w,seed,loss,horizon,arm,ttl=8.0)
    print('low_loss complete',len(rows),time.time()-t0,flush=True)
    # TTL perturbation from initial 8.0 baseline (6/12) on six other worlds
    for wi,seed,loss,horizon,ttl,arm in product(range(300,306),(72011,72012),(.05,.20),(16.0,54.0),(6.0,8.0,12.0),
                             ('permit_sticky','permit_fallback')):
        w=world_factory(170123+wi*23,('small','medium','large')[wi%3]);attempt('ttl',wi,w,seed,loss,horizon,arm,ttl=ttl)
    print('ttl complete',len(rows),time.time()-t0,flush=True)
    # Claim settlement and claim duration sensitivity
    for wi,seed,loss,horizon,settle,claimttl in product(range(300,306),(72011,72012),(.05,.20),(16.0,54.0),(.13,.60),(3.0,5.0,8.0)):
        w=world_factory(170123+wi*23,('small','medium','large')[wi%3])
        attempt('claim_timer',wi,w,seed,loss,horizon,'claim_local',settle_extra=settle,claim_ttl=claimttl)
    print('claim_timer complete',len(rows),time.time()-t0,flush=True)
    # New bigger 16-agent worlds with 8 shared services, not 16 services.
    for wi,seed,loss,horizon,arm in product(range(330,336),(73011,73012),(.0,.05,.20),(16.,54.),
                                       ('claim_local','permit_sticky','permit_fallback','permit_colocated_fallback')):
        w=world_factory(170123+wi*23,'large',agent_override=16)
        attempt('scale_16agents',wi,w,seed,loss,horizon,arm,ttl=8.)
    print('large complete',len(rows),time.time()-t0,flush=True)
    # 0.2 Bernoulli vs 2-state bursty expected long-run ~0.195 on ten worlds
    for wi,seed,horizon,arm,burst in product(range(350,360),(74011,74012),(16.,54.),
                                          ('claim_local','permit_sticky','permit_fallback'),(False,True)):
        w=world_factory(170123+wi*23,('small','medium','large')[wi%3])
        attempt('bursty_loss',wi,w,seed,.20,horizon,arm,ttl=8.,burst=burst)
    print('bursty complete',len(rows),time.time()-t0,flush=True)
    cols=sorted(set().union(*(x.keys() for x in rows)))
    with open(out/'episodes.csv','w',newline='') as f:
        d=csv.DictWriter(f,cols);d.writeheader();d.writerows(rows)
    (out/'failures.json').write_text(json.dumps(problem,indent=2))
    bycond=defaultdict(list)
    for r in rows:
        if r['status']=='completed':
            key=tuple((k,r.get(k)) for k in ['study','arm','loss','horizon','ttl','settle_extra','claim_ttl','burst'] if k in r)
            bycond[key].append(r)
    aggs=[]
    for key,rr in bycond.items():
        sr=dict(key)
        sr.update(n=len(rr),completion=statistics.mean(float(r['completion_fraction']) for r in rr),
          messages=statistics.mean(float(r['total_messages']) for r in rr),
          delivery_losses=statistics.mean(float(r['delivery_losses']) for r in rr),
          overcapacity=sum(float(r['overcapacity_admissions']) for r in rr))
        if any(r.get('burst_total_packets',0) for r in rr):
          sr['observed_drop_ratio']=sum(float(r['delivery_losses']) for r in rr)/max(1,sum(float(r['total_messages']) for r in rr))
        aggs.append(sr)
    (out/'summary.json').write_text(json.dumps(aggs,indent=2))
    stat={'episodes':len(rows),'failures':len(problem),'studies':{z:sum(x['study']==z for x in rows) for z in sorted({x['study'] for x in rows})}}
    (out/'audit.json').write_text(json.dumps(stat,indent=2));print('DONE',stat,flush=True)

if __name__=='__main__':run(sys.argv[1] if len(sys.argv)>1 else ROOT/'sensitivity_results')
