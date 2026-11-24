"""EXPLICIT-STATE LOCAL formal admission shield, NOT the external N-player shield.

This independent, small abstract safety game is motivated by the source-audited
work of Brorholt et al. and classical runtime shielding. It does not reuse,
execute, or certify their Julia/UPPAAL implementation. Its guarantee is only
capacity safety for atomic admission and cooperative completion transitions.

Controlled actions: grant one task, reject one task. Environment: either
finish one active task, or do nothing. Invariant: 0 <= load <= capacity.
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
import json
from functools import lru_cache

@dataclass(frozen=True)
class ShieldCertificate:
    capacity: int
    safe_states: tuple[int,...]
    allowed_actions: dict[int,tuple[str,...]]
    reachable_states: tuple[int,...]
    transitions_checked: int
    invariant_holds: bool

ACTIONS=('admit','reject')
ENV=('idle','finish')

def successors(load,capacity,action,env):
    if action=='admit':load += 1
    if env=='finish' and load>0:load -= 1
    return load

def synthesize(capacity:int)->ShieldCertificate:
    if capacity<1:raise ValueError('positive capacity required')
    safe=set(range(capacity+1))
    # Greatest fixed point of states with at least one action whose possible
    # environment responses cannot leave the current safe set.
    winning=set(safe)
    while True:
        nextset={s for s in winning if any(
            all(successors(s,capacity,a,e) in winning for e in ENV)
            for a in ACTIONS)}
        if nextset==winning:break
        winning=nextset
    admissible={s:tuple(a for a in ACTIONS if all(
        successors(s,capacity,a,e) in winning for e in ENV)) for s in sorted(winning)}
    frontier=deque([0]);seen={0};edges=0
    while frontier:
        s=frontier.popleft()
        for action in admissible[s]:
            for e in ENV:
                s2=successors(s,capacity,action,e);edges+=1
                if s2 not in winning:
                    return ShieldCertificate(capacity,tuple(sorted(winning)),admissible,tuple(sorted(seen)),edges,False)
                if s2 not in seen:
                    seen.add(s2);frontier.append(s2)
    return ShieldCertificate(capacity,tuple(sorted(winning)),admissible,tuple(sorted(seen)),edges,True)

@lru_cache(maxsize=None)
def admit_permitted(load:int,capacity:int)->bool:
    # The runtime adapter looks up an action in the synthesized safety game.
    return 'admit' in synthesize(capacity).allowed_actions.get(load,())

def counterexample_reactive_ncp(capacity:int=1):
    """Shortest failure trace in a toy reactive monitor with delayed delivery.

    Before the constraint arrives, unguarded actions may exceed capacity.
    No positive liveness or probabilistic claims follow from this trace.
    """
    # state = (number of active tasks, whether constraint delivered)
    queue=deque([((0,False),[])])
    seen={(0,False)}
    while queue:
        (load,delivered),trace=queue.popleft()
        if load>capacity:return trace,load
        candidates=[('start_before_constraint',(load+1,delivered))] if not delivered else []
        candidates.append(('deliver_constraint',(load,True)))
        if load>0:candidates.append(('finish_one',(load-1,delivered)))
        for event,nxt in candidates:
            if nxt not in seen:
                seen.add(nxt);queue.append((nxt,trace+[event]))
    return [],0

def generate_certificate(capacities=(1,2,3)):
    certs=[synthesize(c) for c in capacities]
    trace,violating_load=counterexample_reactive_ncp(1)
    result={
        'status':'finite-state exhaustiveness for a local atomic admission abstraction, NOT formal verification of NCP or published N-player-Shield',
        'safety_property':'G(load_s <= capacity_s) under atomic guard, one agent task active at a time, environment only finishes or idles',
        'certificates':[
            {'capacity':c.capacity,'safe_states':list(c.safe_states),
             'admissible_actions':{str(k):list(v) for k,v in c.allowed_actions.items()},
             'reachable_states':list(c.reachable_states),'transitions_checked':c.transitions_checked,
             'invariant_holds':c.invariant_holds}
            for c in certs],
        'ncp_reactive_counterexample':{'capacity':1,'sequence':trace,'resulting_active_load':violating_load,'property_violated':violating_load>1},
        'excluded_guarantees':['continuous service-stress thresholds','unknown asynchronous physical actions','Byzantine messages','real networks','unmodeled failure transitions'],
    }
    return result

if __name__=='__main__':
    print(json.dumps(generate_certificate(),indent=2))
