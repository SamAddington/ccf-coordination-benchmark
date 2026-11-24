"""Event-driven DRA, auctions, and NCP in a synthetic task world.

No reward, coverage, disruption, or redundancy profile multipliers exist here.
All algorithms act in the SAME workload, service physics and outcome rules.
Auction baselines are independently coded operational adaptations, not reference ports.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import heapq
import random
from typing import Any
from .model import World, Task, ServiceSpec, agent_skill, bid, draw01

COORDINATORS = ('independent','shared_board','dra','cbaa','cbba_lite')
SHIELDS = ('none','local','partitioned','oracle','ncp','formal_capacity','compositional')

@dataclass
class RunConfig:
    coordination: str
    shield: str
    horizon: float = 27.0
    delay_min: float = 0.04
    delay_max: float = 0.23
    message_loss: float = 0.0
    monitor_period: float = 0.30
    settle_extra: float = 0.13
    claim_ttl: float = 5.0
    ncp_ttl: float = 1.35
    ncp_rebroadcast: float = 0.80
    stress_warn_ratio: float = 0.52
    trace: bool = False

    def __post_init__(self):
        if self.coordination not in COORDINATORS or self.shield not in SHIELDS:
            raise ValueError('Unknown coordinator/shield')
        if not (0 <= self.message_loss < 1) or self.delay_max < self.delay_min:
            raise ValueError('Invalid network settings')

@dataclass
class SvcState:
    spec: ServiceSpec
    load: int = 0
    stress: float = 0.0
    updated: float = 0.0
    outage_until: float = 0.0
    ncp_version: int = 0
    ncp_broadcast_after: float = 0.0

@dataclass
class AgState:
    id: int
    busy: bool = False
    pending: str | None = None
    pending_at: float = 0.0
    bundle: list[str] = field(default_factory=list)
    local_done: set[str] = field(default_factory=set)
    views: dict[str, tuple[int,float,float]] = field(default_factory=dict)  # task -> (winner, bid, expiry)
    constraints: dict[str, tuple[int,float]] = field(default_factory=dict)  # service -> (version, expiry)
    delayed_service_until: dict[str,float] = field(default_factory=dict)
    last_start: dict[str,float] = field(default_factory=dict)
    attempts: dict[str,int] = field(default_factory=dict)
    busy_task: str | None = None

class Engine:
    def __init__(self, world: World, config: RunConfig, seed: int):
        self.world, self.cfg, self.seed = world, config, seed
        self.rng = random.Random(seed + 9187)
        self.now = 0.0
        self.counter = 0
        self.queue: list[tuple[float,int,str,tuple[Any,...]]] = []
        self.tasks = {t.id:t for t in world.tasks}
        self.svcs = {s.id:SvcState(s) for s in world.services}
        self.agents = [AgState(i) for i in range(world.num_agents)]
        self.bids = {(a.id,t.id):bid(world,a.id,t) for a in self.agents for t in world.tasks if t.allowed}
        self.skills = {(a.id,t.id):agent_skill(world,a.id,t) for a in self.agents for t in world.tasks if t.allowed}
        self.partition_grants = {s.id:set(sorted(range(world.num_agents), key=lambda a:draw01(world.seed,'grant',s.id,a))[:s.capacity]) for s in world.services}
        if config.shield=='compositional':
            from compositional_shield import synthesize_local_quota_shields
            self.partition_grants = {s.id:set(synthesize_local_quota_shields(world.num_agents,s.capacity,tuple(sorted(self.partition_grants[s.id]))).eligible_agents) for s in world.services}
        self.global_done: set[str] = set()
        self.reservations: dict[str,int] = {}
        self.active: dict[int,dict[str,Any]] = {}
        self.action_seq = 0
        self.trace_rows: list[dict[str,Any]] = []
        self.stats = {'completed_tasks':0,'earned_value':0.0,'executed_actions':0,
                      'failed_actions':0,'duplicate_starts':0,'overcapacity_admissions':0,
                      'disruptions':0,'denied_ncp':0,'denied_oracle':0,'denied_partitioned':0,'denied_formal_capacity':0,
                      'denied_local':0,'denied_roe':0,'claim_messages':0,'bid_messages':0,
                      'constraint_messages':0,'done_messages':0,'delivery_losses':0,
                      'defer_events':0,'first_completion_time':None,'peak_overcapacity':0,
                      'ncp_issued':0,'ncp_received':0,'total_messages':0,'retries':0}
        self.ncp_received_versions: set[tuple[int,str,int]] = set()
        for a in self.agents:
            self.schedule(0.02*a.id,'wake',a.id)
        self.schedule(config.monitor_period,'monitor')

    def log(self, name: str, agent: int | str = '-', task: str = '-', service: str = '-', details: str = ''):
        if self.cfg.trace:
            self.trace_rows.append({'time':round(self.now,4),'event':name,'agent':agent,
                                    'task':task,'service':service,'detail':details})

    def schedule(self, t: float, event: str, *args: Any):
        if t>self.cfg.horizon+1e-9:
            return
        self.counter += 1
        heapq.heappush(self.queue,(round(t,7),self.counter,event,args))

    def broadcast(self, origin: int | str, kind: str, payload: tuple[Any,...]):
        recipients = [a.id for a in self.agents if a.id != origin]
        for aid in recipients:
            self.stats['total_messages']+=1
            self.stats[f'{kind}_messages']+=1
            if self.rng.random() < self.cfg.message_loss:
                self.stats['delivery_losses']+=1
                continue
            latency=self.rng.uniform(self.cfg.delay_min,self.cfg.delay_max)
            self.schedule(self.now+latency,'message',aid,origin,kind,payload)

    def update_service(self, state: SvcState):
        dt = self.now-state.updated
        if dt<=0:
            return
        # Shared physical dynamics, not influenced by the algorithm label.
        drift=(0.19*state.load+1.52*max(0,state.load-state.spec.capacity)-0.36)*state.spec.fragility
        if self.now >= state.outage_until:
            state.stress=max(0.0,state.stress + dt*drift)
            if state.stress>=state.spec.threshold:
                self.stats['disruptions']+=1
                state.outage_until=self.now+state.spec.recovery
                state.stress=0.0
                for action in self.active.values():
                    if action['service']==state.spec.id:
                        action['failed_outage']=True
                self.log('DISRUPTION',service=state.spec.id,details=f'recovery_until={state.outage_until:.2f}')
        else:
            state.stress=0.0
        state.updated=self.now

    def best_candidates(self, agent: AgState) -> list[Task]:
        res=[]
        for task in self.world.tasks:
            if not task.allowed or task.id in agent.local_done:
                continue
            if agent.attempts.get(task.id,0)>=2:
                continue
            if agent.delayed_service_until.get(task.service,0)>self.now:
                continue
            if self.cfg.shield in ('partitioned','compositional') and not self.has_partition_grant(agent.id,task.service):
                continue
            if self.cfg.coordination=='shared_board' and (task.id in self.global_done or task.id in self.reservations):
                continue
            if self.cfg.coordination in ('dra','cbaa','cbba_lite'):
                known=agent.views.get(('svc:'+task.service) if self.cfg.coordination=='dra' else task.id)
                if known and known[0]!=agent.id and known[2]>self.now:
                    continue
            res.append(task)
        res.sort(key=lambda t:(-self.bids[(agent.id,t.id)], t.id))
        return res

    def has_partition_grant(self, agent_id: int, service: str) -> bool:
        # A conservative, static per-service ownership shield: no more than capacity agents may work simultaneously.
        return agent_id in self.partition_grants[service]

    def new_claim(self, a: AgState, task: Task, position: int = 0):
        # Shared task utility, with small bundle-position penalty in CBBA-lite.
        score=self.bids[(a.id,task.id)]*(1.0 if position==0 else 0.89)
        # DRA prioritizes task suitability and a local stability estimate (no global state).
        if self.cfg.coordination=='dra':
            score=0.80*score + 0.20*(0.5+self.skills[(a.id,task.id)])
        claim_key='svc:'+task.service if self.cfg.coordination=='dra' else task.id
        a.views[claim_key]=(a.id,score,self.now+self.cfg.claim_ttl)
        message_kind='claim' if self.cfg.coordination=='dra' else 'bid'
        self.broadcast(a.id,message_kind,(claim_key,a.id,score,self.now+self.cfg.claim_ttl))
        self.log('CLAIM' if message_kind=='claim' else 'BID',a.id,task.id,task.service,f'score={score:.3f}; position={position}')

    def wake(self, aid: int):
        a=self.agents[aid]
        if a.busy:
            return
        if a.pending is not None:
            if self.now<a.pending_at-1e-7:
                return
            task=self.tasks[a.pending]
            if self.cfg.coordination in ('dra','cbaa','cbba_lite'):
                winner=a.views.get(('svc:'+task.service) if self.cfg.coordination=='dra' else task.id)
                if winner and winner[0]!=a.id and winner[2]>self.now:
                    a.pending=None
                    self.stats['defer_events']+=1
                    self.log('DEFER',aid,task.id,task.service,f'winner={winner[0]}')
                    self.schedule(self.now+0.12,'wake',aid)
                    return
            a.pending=None
            self.attempt_action(a,task)
            return
        options=self.best_candidates(a)
        if not options:
            self.schedule(self.now+0.54,'wake',aid)
            return
        coord=self.cfg.coordination
        if coord=='independent':
            self.attempt_action(a,options[0]);return
        if coord=='shared_board':
            task=options[0]
            self.reservations[task.id]=aid
            self.log('RESERVE',aid,task.id,task.service)
            self.attempt_action(a,task);return
        if coord=='cbba_lite':
            if not a.bundle or a.bundle[0] not in [t.id for t in options]:
                a.bundle=[t.id for t in options[:2]]
            for pos,tid in enumerate(a.bundle):
                self.new_claim(a,self.tasks[tid],pos)
            task=self.tasks[a.bundle[0]]
        else:
            task=options[0]
            self.new_claim(a,task)
        a.pending=task.id
        a.pending_at=self.now+self.cfg.delay_max+self.cfg.settle_extra
        self.schedule(a.pending_at,'wake',aid)

    @staticmethod
    def formal_admission_allowed(load:int, capacity:int) -> bool:
        # Run the action selected by the finite-state synthesized guard, not a
        # hardcoded value inferred from the experimental arm label.
        from formal_shield import admit_permitted
        return admit_permitted(load,capacity)

    def attempt_action(self, a: AgState, task: Task):
        svc=self.svcs[task.service]
        self.update_service(svc)
        if not task.allowed:
            self.stats['denied_roe']+=1
            self.log('DENY_ROE',a.id,task.id,task.service)
            self.schedule(self.now+0.3,'wake',a.id);return
        reason=None
        if self.now<svc.outage_until:
            reason='outage'
        elif self.cfg.shield=='ncp' and a.constraints.get(task.service,(0,0.0))[1]>self.now:
            reason='ncp'
        elif self.cfg.shield=='formal_capacity' and not self.formal_admission_allowed(svc.load,svc.spec.capacity):
            reason='formal_capacity'
        elif self.cfg.shield=='oracle' and (svc.load>=svc.spec.capacity or svc.stress>=svc.spec.threshold*0.58):
            reason='oracle'
        elif self.cfg.shield in ('partitioned','compositional') and not self.has_partition_grant(a.id,task.service):
            reason='partitioned'
        elif self.cfg.shield=='local' and self.now-a.last_start.get(task.service,-100)<4.20:
            reason='local'
        if reason:
            k='denied_'+reason
            if k in self.stats:self.stats[k]+=1
            a.delayed_service_until[task.service]=self.now+(0.48 if reason!='outage' else max(0.48,svc.outage_until-self.now))
            self.log('DENY_'+reason.upper(),a.id,task.id,task.service)
            if self.cfg.coordination=='shared_board' and self.reservations.get(task.id)==a.id:
                del self.reservations[task.id]
            self.schedule(self.now+0.22,'wake',a.id)
            return
        # A rejected/blocked proposal is not counted as an executed unsafe action.
        duplicate=(task.id in self.global_done or any(act['task']==task.id for act in self.active.values()))
        if duplicate:self.stats['duplicate_starts']+=1
        if svc.load>=svc.spec.capacity:
            self.stats['overcapacity_admissions']+=1
        a.busy=True
        a.busy_task=task.id
        a.last_start[task.service]=self.now
        a.attempts[task.id]=a.attempts.get(task.id,0)+1
        self.stats['executed_actions']+=1
        svc.load+=1
        self.stats['peak_overcapacity']=max(self.stats['peak_overcapacity'],svc.load-svc.spec.capacity)
        self.action_seq+=1
        actid=self.action_seq
        duration=task.duration*(1.10-0.25*self.skills[(a.id,task.id)])
        self.active[actid]={'agent':a.id,'task':task.id,'service':task.service,'failed_outage':False}
        self.schedule(self.now+duration,'complete',actid)
        self.log('ACTION_START',a.id,task.id,task.service,f'load={svc.load}/{svc.spec.capacity}; duplicate={duplicate}')

    def complete(self, actid: int):
        act=self.active.pop(actid,None)
        if not act:return
        agent=self.agents[act['agent']]
        task=self.tasks[act['task']]
        svc=self.svcs[task.service]
        self.update_service(svc)
        svc.load=max(0,svc.load-1)
        agent.busy=False
        agent.busy_task=None
        p=0.56+0.38*self.skills[(agent.id,task.id)]-0.12*task.difficulty
        good=draw01(self.world.seed,self.seed,'success',agent.id,task.id,agent.attempts[task.id])<p
        success=good and not act['failed_outage'] and self.now>=svc.outage_until
        if success and task.id not in self.global_done:
            self.global_done.add(task.id)
            self.stats['completed_tasks']+=1
            self.stats['earned_value']+=task.value
            if self.stats['first_completion_time'] is None:
                self.stats['first_completion_time']=self.now
            self.log('TASK_COMPLETE',agent.id,task.id,task.service)
            if self.cfg.coordination not in ('independent','shared_board'):
                self.broadcast(agent.id,'done',(task.id,))
        else:
            self.stats['failed_actions']+=1
            self.log('ACTION_FAIL',agent.id,task.id,task.service,
                     f'outage={act["failed_outage"]}; sampled_success={good}; already_done={task.id in self.global_done}')
        agent.local_done.add(task.id) if task.id in self.global_done else None
        if self.reservations.get(task.id)==agent.id:
            del self.reservations[task.id]
        if task.id in agent.bundle:
            agent.bundle.remove(task.id)
        self.schedule(self.now+0.04,'wake',agent.id)

    def message(self, aid: int, origin: Any, kind: str, payload: tuple[Any,...]):
        a=self.agents[aid]
        if kind=='constraint':
            sid,ver,expiry=payload
            old_ver=a.constraints.get(sid,(0,0))[0]
            if ver>=old_ver and expiry>self.now:
                a.constraints[sid]=(ver,expiry)
                self.stats['ncp_received']+=1
                self.log('CONSTRAINT_RECEIVE',aid,service=sid,details=f'v{ver} expiry={expiry:.2f}')
                if not a.busy:
                    self.schedule(self.now+0.01,'wake',aid)
            return
        if kind=='done':
            task_id,=payload
            a.local_done.add(task_id)
            if task_id==a.pending:
                a.pending=None
                self.schedule(self.now+0.03,'wake',aid)
            if task_id in a.bundle:
                a.bundle.remove(task_id)
            return
        if kind not in ('claim','bid'):return
        task_id,winner,score,expiry=payload
        if expiry<=self.now:return
        current=a.views.get(task_id)
        superior= current is None or current[2]<=self.now or score>current[1]+1e-10 or (abs(score-current[1])<1e-10 and winner<current[0])
        if superior:
            a.views[task_id]=(winner,score,expiry)
            pending_key=('svc:'+self.tasks[a.pending].service) if a.pending and self.cfg.coordination=='dra' else a.pending
            if pending_key==task_id and winner!=aid:
                losing_task=a.pending
                a.pending=None
                self.stats['defer_events']+=1
                self.log('DEFER',aid,losing_task or '-',task_id[4:] if task_id.startswith('svc:') else self.tasks[task_id].service,f'winner={winner}')
                if self.cfg.coordination=='cbba_lite' and task_id in a.bundle:
                    # CBBA-style suffix release upon outbid. No formal canonical CBBA claim made.
                    ix=a.bundle.index(task_id)
                    a.bundle=a.bundle[:ix]
                self.schedule(self.now+0.05,'wake',aid)

    def monitor(self):
        for sid,svc in self.svcs.items():
            self.update_service(svc)
            if self.cfg.shield!='ncp' or self.now<svc.outage_until:
                continue
            if (svc.load>=svc.spec.capacity or svc.stress>=svc.spec.threshold*self.cfg.stress_warn_ratio) and self.now>=svc.ncp_broadcast_after:
                svc.ncp_version+=1
                expiry=self.now+self.cfg.ncp_ttl
                svc.ncp_broadcast_after=self.now+self.cfg.ncp_rebroadcast
                self.stats['ncp_issued']+=1
                self.broadcast('monitor','constraint',(sid,svc.ncp_version,expiry))
                self.log('CONSTRAINT_ISSUE',service=sid,details=f'v{svc.ncp_version}; load={svc.load}; stress={svc.stress:.2f}')
        self.schedule(self.now+self.cfg.monitor_period,'monitor')

    def run(self) -> dict[str, Any]:
        while self.queue:
            t,_,kind,args=heapq.heappop(self.queue)
            self.now=t
            if kind=='wake':self.wake(*args)
            elif kind=='message':self.message(*args)
            elif kind=='monitor':self.monitor()
            elif kind=='complete':self.complete(*args)
            elif kind=='acbba_flush':
                # Optional original-source ACBBA adapter outbound poll. DRA never
                # schedules this event; all physical/guard logic stays common.
                self._flush_event(*args)
        result={'env_id':self.world.id,'world_seed':self.world.seed,'run_seed':self.seed,
                'scale':self.world.id.split('-')[0],'agents':self.world.num_agents,
                'coordination':self.cfg.coordination,'shield':self.cfg.shield,
                'message_loss':self.cfg.message_loss,'delay_max':self.cfg.delay_max,
                'horizon':self.cfg.horizon,'task_total':sum(t.allowed for t in self.world.tasks),
                'max_value':sum(t.value for t in self.world.tasks if t.allowed),
                **self.stats}
        result['completion_fraction']=result['completed_tasks']/max(1,result['task_total'])
        result['value_fraction']=result['earned_value']/max(1,result['max_value'])
        result['duplication_rate']=result['duplicate_starts']/max(1,result['executed_actions'])
        result['overcapacity_rate']=result['overcapacity_admissions']/max(1,result['executed_actions'])
        if self.stats['first_completion_time'] is None:
            result['first_completion_time']=self.cfg.horizon
        return result
