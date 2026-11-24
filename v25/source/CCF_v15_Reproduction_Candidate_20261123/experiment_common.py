"""CCF v11 falsification experiments using the unchanged v8 CCF engine core.

Research-only code. External workload comprises synthetic tasks; no exploit tools.
The two conventional controls are *centralized* and deliberately privileged:
  (1) FCFS exclusive service lease, single service holder;
  (2) FCFS capacity-C semaphore, with a central permit count.
Neither is a claim to a decentralized lease implementation. They receive
central completion information and hence make deliberately strong baselines.
"""
from __future__ import annotations
from dataclasses import replace
from dataclasses import dataclass
from collections import Counter
import json
from ccf_eventlab.engine import Engine, RunConfig
from ccf_eventlab.model import World, ServiceSpec

CONTROLLERS = ("dra", "service_lease", "capacity_semaphore", "independent")
PHYSICS = ("reference", "no_overcapacity_penalty", "smooth_convex", "strong_overcapacity")
RELEASES = ("all_at_start", "waves", "hot_burst")
CAPACITY_VARIANTS = ("original", "one_per_service", "at_least_three")


def adjusted_world(world:World, capacity_variant:str, fragility_multiplier:float=1.0)->World:
    if capacity_variant not in CAPACITY_VARIANTS: raise ValueError(capacity_variant)
    svcs=[]
    for svc in world.services:
        cap = svc.capacity
        if capacity_variant == "one_per_service": cap=1
        if capacity_variant == "at_least_three": cap=max(3,cap)
        svcs.append(replace(svc,capacity=cap, fragility=round(svc.fragility*fragility_multiplier,8)))
    return replace(world,services=tuple(svcs),id=world.id)  # preserve seeded task/difficulty draws


def task_release_times(world:World, release_profile:str)->dict[str,float]:
    if release_profile not in RELEASES: raise ValueError(release_profile)
    out={}
    for t in world.tasks:
        if not t.allowed:
            out[t.id]=0.0; continue
        i=int(t.id.split('-t')[-1])
        if release_profile=="all_at_start": out[t.id]=0.0
        elif release_profile=="waves": out[t.id]=(0.0,9.0,23.0,38.0)[i]
        elif release_profile=="hot_burst":
            out[t.id]=0.0 if t.service in ("s00","s01") else (0.0,0.0,20.0,32.0)[i]
    return out


class ExperimentEngine(Engine):
    """Subclass changes workload and conventional comparator; original DRA code reused."""
    def __init__(self, world:World, cfg:RunConfig, seed:int, *, controller:str,
                 physics:str="reference", release_profile:str="all_at_start"):
        if controller not in CONTROLLERS:raise ValueError(controller)
        if physics not in PHYSICS:raise ValueError(physics)
        if cfg.coordination!=("dra" if controller=="dra" else "independent"):
            raise ValueError("Wrong core coordination flag for chosen controller")
        super().__init__(world,cfg,seed)
        self.controller=controller
        self.physics=physics
        self.release_profile=release_profile
        self.release_at=task_release_times(world,release_profile)
        self.leases:dict[str,tuple[int,float]]={}
        self.tokens:Counter[str]=Counter()
        self.action_permits:dict[int,tuple[str,int]]={}
        self.control_stats={"admission_acquires":0,"admission_releases":0,
                            "controller_busy_deferrals":0,"controller_lease_expirations":0,
                            "controller_shared_state_reads":0,
                            "peak_controller_tokens":0}

    def update_service(self,state):
        if self.physics=="reference": return super().update_service(state)
        dt=self.now-state.updated
        if dt<=0:return
        load=state.load;cap=state.spec.capacity
        if self.physics=="no_overcapacity_penalty": drift=0.19*load-0.36
        elif self.physics=="strong_overcapacity": drift=0.19*load+3.04*max(0,load-cap)-0.36
        elif self.physics=="smooth_convex": drift=0.14*load*load-0.34
        else:raise ValueError(self.physics)
        if self.now >= state.outage_until:
            state.stress=max(0.0,state.stress+dt*drift*state.spec.fragility)
            if state.stress>=state.spec.threshold:
                self.stats["disruptions"]+=1
                state.outage_until=self.now+state.spec.recovery
                state.stress=0.0
                for action in self.active.values():
                    if action["service"]==state.spec.id:
                        action["failed_outage"]=True
                self.log("DISRUPTION",service=state.spec.id,details=f"physics={self.physics};recovery_until={state.outage_until:.2f}")
        else:state.stress=0.0
        state.updated=self.now

    def best_candidates(self,agent):
        allc=super().best_candidates(agent)
        ready=[t for t in allc if self.now+1e-8>=self.release_at[t.id]]
        if self.controller in ("service_lease", "capacity_semaphore"):
            # Strong centralized comparator: shared completion and task-in-progress list.
            self.control_stats["controller_shared_state_reads"]+=1
            ready=[t for t in ready if t.id not in self.global_done and
                   not any(action["task"]==t.id for action in self.active.values())]
        return ready

    def wake(self,aid:int):
        if self.controller in ("dra", "independent"):return super().wake(aid)
        a=self.agents[aid]
        if a.busy:return
        for task in self.best_candidates(a):
            sid=task.service
            if self.controller=="service_lease":
                old=self.leases.get(sid)
                if old and old[1]<=self.now:
                    self.leases.pop(sid,None)
                    self.control_stats["controller_lease_expirations"]+=1
                if sid in self.leases:continue
                # Lease exceeds maximal admissible task duration, no background renewals.
                self.leases[sid]=(aid,self.now+8.0)
            else:
                if self.tokens[sid]>=self.svcs[sid].spec.capacity:continue
                self.tokens[sid]+=1
                self.control_stats["peak_controller_tokens"]=max(
                    self.control_stats["peak_controller_tokens"],self.tokens[sid])
            self.control_stats["admission_acquires"]+=1
            before=self.action_seq
            self.attempt_action(a,task)  # dynamic dispatch; measured adapter must see the admitted action
            if self.action_seq>before:
                self.action_permits[self.action_seq]=(sid,aid)
                self.log("CONTROL_ACQUIRE",aid,task.id,sid,self.controller)
                return
            self._release(sid,aid)
            return  # one denied operation per wake; base engine has already queued retry
        self.control_stats["controller_busy_deferrals"]+=1
        self.schedule(self.now+0.18,"wake",aid)

    def _release(self,sid:str,aid:int):
        if self.controller=="service_lease":
            if self.leases.get(sid,(None,))[0]==aid:self.leases.pop(sid,None)
        elif self.controller=="capacity_semaphore":
            assert self.tokens[sid]>=1,"Semaphore release without acquisition"
            self.tokens[sid]-=1
        self.control_stats["admission_releases"]+=1

    def complete(self,actid:int):
        permit=self.action_permits.pop(actid,None)
        super().complete(actid)
        if permit:
            sid,aid=permit
            self._release(sid,aid)

    def run(self):
        r=super().run()
        if self.controller in ("service_lease","capacity_semaphore"):
            # Horizon-censored active tasks retain their permits; report, don't fake release.
            assert all(v<=self.svcs[k].spec.capacity for k,v in self.tokens.items())
        r.update({"controller":self.controller,"physics":self.physics,
                  "release_profile":self.release_profile,**self.control_stats,
                  "censored_active_actions":len(self.active)})
        return r


def make_engine(world,seed,controller,shield,*,horizon=54.0,network="nominal",
                physics="reference",release_profile="all_at_start",trace=False):
    from ccf_eventlab.engine import RunConfig
    if network=="nominal":net={"delay_min":0.04,"delay_max":0.23,"message_loss":0.0}
    elif network=="loss20":net={"delay_min":0.35,"delay_max":0.95,"message_loss":0.20}
    else:raise ValueError(network)
    cfg=RunConfig("dra" if controller=="dra" else "independent",shield,
                  horizon=float(horizon),trace=trace,**net)
    return ExperimentEngine(world,cfg,seed,controller=controller,physics=physics,
                            release_profile=release_profile)
