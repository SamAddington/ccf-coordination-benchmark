"""Explicit-state locally synthesized compositional shielding.

This is independent new Python code implementing a simple assume-guarantee
capacity decomposition, NOT the authors' Julia/UPPAAL N-player-Shield tool.

For capacity C and per-agent quota q_i in {0,1}, choose sum(q_i)=min(C,n).
Each local component tracks its own active task count x_i and permits an
admission iff x_i < q_i. Its local safety guarantee is G(0<=x_i<=q_i).
The conjunction of local guarantees implies G(sum_i x_i<=C), without
online shield-to-shield communication. Agents can still communicate to allocate
work but that does not affect safety. Atomic starts and cooperative completions
are required for the induction.
"""
from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from collections import deque

@dataclass(frozen=True)
class CompositionCertificate:
    agents: int
    capacity: int
    quotas: tuple[int,...]
    eligible_agents: tuple[int,...]
    reachable_states: tuple[tuple[int,...],...]
    transitions_checked: int
    local_obligations_hold: bool
    global_invariant_holds: bool
    guarantee: str

@lru_cache(maxsize=None)
def synthesize_local_quota_shields(agents:int,capacity:int,eligible:tuple[int,...]|None=None)->CompositionCertificate:
    if not (agents>0 and capacity>0):raise ValueError('positive agents and capacity')
    capacity=min(capacity,agents)
    if eligible is None: eligible=tuple(range(capacity))
    if len(set(eligible)) != capacity or any(i not in range(agents) for i in eligible):
        raise ValueError('eligible agents must consist of capacity distinct indices')
    q=tuple(int(i in eligible) for i in range(agents))
    # Local game: each component chooses admit or reject, then environment may
    # finish its own task or idle. Keep actions whose every successor stays safe.
    local_actions=[]
    for quota in q:
        safe=set(range(quota+1)); win=set(safe)
        while True:
            new={x for x in win if any(all(
                x+(a=='admit')-int(env=='finish' and x+(a=='admit')>0) in win
                for env in ('idle','finish')) for a in ('admit','reject'))}
            if new==win:break
            win=new
        acts={x:tuple(a for a in ('admit','reject') if all(
            x+(a=='admit')-int(env=='finish' and x+(a=='admit')>0) in win
            for env in ('idle','finish'))) for x in win}
        local_actions.append(acts)
    start=(0,)*agents; seen={start}; todo=deque([start]);edges=0;ok_local=True;ok_global=True
    while todo:
        state=todo.popleft()
        if sum(state)>capacity: ok_global=False
        for i in range(agents):
            for action in local_actions[i].get(state[i],()):
                for env in ('idle','finish'):
                    a=list(state)
                    a[i]=a[i]+int(action=='admit')
                    if env=='finish' and a[i]>0:a[i]-=1
                    nxt=tuple(a);edges+=1
                    if not 0<=nxt[i]<=q[i]:ok_local=False
                    if sum(nxt)>capacity:ok_global=False
                    if nxt not in seen:seen.add(nxt);todo.append(nxt)
    return CompositionCertificate(agents,capacity,q,tuple(eligible),tuple(sorted(seen)),edges,ok_local,ok_global,
                                  'G(x_i<=q_i) for all i entails G(sum(x_i)<=capacity) when sum(q_i)<=capacity')

def certificate_family():
    items=[]
    for n,c in ((2,1),(3,1),(4,2),(6,2),(8,3)):
        obj=synthesize_local_quota_shields(n,c)
        items.append({'agents':n,'capacity':c,'quotas':list(obj.quotas),'reachable_states':len(obj.reachable_states),
                      'edges_checked':obj.transitions_checked,'local_obligations_hold':obj.local_obligations_hold,
                      'global_invariant_holds':obj.global_invariant_holds})
    return {'method':'own finite-state local quota shield (inspired by published compositional shielding but not an execution of the N-player-Shield package)',
            'assumptions':['fixed quotas sum <= capacity','atomic admissions','one active task per agent','local admission checks before execution','service may finish or idle'],
            'excluded':['dynamically negotiated quotas','stress-outage safety','sensor attacks','real-time constraints','UPPAAL/Julia synthesis'],
            'certificates':items}

if __name__=='__main__':
    import json;print(json.dumps(certificate_family(),indent=2))
