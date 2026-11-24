"""Per-service sharded lease manager under exactly the CCF message scheduler.

Conventional comparison, not a new consensus protocol. A static manager for each
service receives requests, manages only that service's lease, and grants one
exclusive holder. It has no global task-completion oracle, task queue, or other
agent's skill/bids. Packets face the same delay/loss law as DRA claims/done.

Message loss can cause temporary deadlock until lease expiry. Network partitions,
manager crashes, clock skew, durable fencing and Byzantine safety are NOT modeled.
Mutual exclusion in this model depends on a single non-Byzantine authority per
service and a lease TTL longer than maximum request/response+action duration.
"""
from __future__ import annotations
from dataclasses import dataclass
import json
from experiment_common import ExperimentEngine

LEASE_TTL = 8.0
LEASE_RETRY_MIN = 0.22


def encoded_payload_bytes(origin,kind,payload):
    return len(json.dumps({'sender':origin,'kind':kind,'data':payload},separators=(',',':'),sort_keys=True).encode('utf8'))


class WireAccountingMixin:
    """Only adds byte accounting; must not change the source DRA event stream."""
    def broadcast(self,origin,kind,payload):
        count=sum(a.id != origin for a in self.agents)
        self.stats['wire_payload_bytes']=self.stats.get('wire_payload_bytes',0)+count*encoded_payload_bytes(origin,kind,payload)
        super().broadcast(origin,kind,payload)


class AccountedDRA(WireAccountingMixin,ExperimentEngine):
    pass


class DistributedLeaseEngine(WireAccountingMixin,ExperimentEngine):
    """All owners see only locally known task completions; manager sees leases only."""
    def __init__(self,world,cfg,seed,*,controller='distributed_lease',**kwargs):
        if controller!='distributed_lease':raise ValueError(controller)
        if cfg.coordination!='independent':raise ValueError('distributed lease must use independent task-selection core')
        # Reuse unmodified v11 engine without broadening its controller enum.
        super().__init__(world,cfg,seed,controller="independent",**kwargs)
        self.controller=controller
        self._lease_authorities={sid:i%world.num_agents for i,sid in enumerate(sorted(self.svcs))}
        self._lease_register={} # sid -> (owner, request_nonce, expires_at)
        self._pending_requests={} # aid -> (sid,tid,nonce)
        self._held={} # aid -> (sid,tid,nonce,expires_at)
        self._agent_nonce={aid:0 for aid in range(world.num_agents)}
        self._pending_retry_after={}
        self._pending_action_leases={} # actid -> (sid,aid,nonce)
        self.stats.update({'lease_requests':0,'lease_grants':0,'lease_denials':0,
                           'lease_request_retries':0,'lease_release_messages':0,
                           'lease_expired':0,'lease_stale_grants':0,
                           'lease_authority_conflicts':0,'wire_payload_bytes':0,
                           'task_completion_publications':0})

    def _send(self,origin,dest,kind,payload):
        # Single recipient transmission, same Bernoulli-loss and bounded-delay
        # distributions as Engine.broadcast. Send-to-self is local dispatch.
        if dest==origin:
            self.message(dest,origin,kind,payload)
            return
        self.stats['total_messages']+=1
        self.stats[kind+'_messages']=self.stats.get(kind+'_messages',0)+1
        self.stats['wire_payload_bytes']+=encoded_payload_bytes(origin,kind,payload)
        if self.rng.random()<self.cfg.message_loss:
            self.stats['delivery_losses']+=1
            return
        latency=self.rng.uniform(self.cfg.delay_min,self.cfg.delay_max)
        self.schedule(self.now+latency,'message',dest,origin,kind,payload)

    def _clear_expired(self,sid):
        current=self._lease_register.get(sid)
        if current and self.now>=current[2]:
            self._lease_register.pop(sid,None)
            self.stats['lease_expired']+=1

    def _request(self,aid,sid,tid,nonce):
        self.stats['lease_requests']+=1
        self._pending_retry_after[aid]=self.now+max(LEASE_RETRY_MIN,2*self.cfg.delay_max+.22)
        self._send(aid,self._lease_authorities[sid],'lease_request',(sid,tid,aid,nonce))

    def wake(self,aid):
        a=self.agents[aid]
        if a.busy:return
        pending=self._pending_requests.get(aid)
        if pending:
            sid,tid,nonce=pending
            ready=self._pending_retry_after.get(aid,0.0)
            if self.now+1e-8<ready:
                # A timeout is already scheduled by the pending request or BUSY response.
                # Stale wake events must not schedule duplicate retries.
                return
            # Retry the SAME request id; manager re-grants if owner still holds.
            self.stats['lease_request_retries']+=1
            self._request(aid,sid,tid,nonce)
            self.schedule(self.now+max(LEASE_RETRY_MIN,2*self.cfg.delay_max+.22),'wake',aid)
            return
        options=self.best_candidates(a) # local, not global completion state
        if not options:
            self.schedule(self.now+.54,'wake',aid)
            return
        task=options[0]
        self._agent_nonce[aid]+=1
        nonce=self._agent_nonce[aid]
        self._pending_requests[aid]=(task.service,task.id,nonce)
        self._request(aid,task.service,task.id,nonce)
        self.schedule(self.now+max(LEASE_RETRY_MIN,2*self.cfg.delay_max+.22),'wake',aid)

    def message(self,aid,origin,kind,payload):
        if kind=='lease_request':
            sid,tid,requester,nonce=payload
            if aid!=self._lease_authorities[sid]:return
            self._clear_expired(sid)
            held=self._lease_register.get(sid)
            if held is None:
                expiry=self.now+LEASE_TTL
                self._lease_register[sid]=(requester,nonce,expiry)
                self.stats['lease_grants']+=1
                self._send(aid,requester,'lease_grant',(sid,tid,nonce,expiry))
            elif held[0]==requester and held[1]==nonce:
                self.stats['lease_grants']+=1
                self._send(aid,requester,'lease_grant',(sid,tid,nonce,held[2]))
            else:
                self.stats['lease_denials']+=1
                self._send(aid,requester,'lease_busy',(sid,tid,nonce,held[2]))
            return
        if kind=='lease_grant':
            sid,tid,nonce,expiry=payload
            if self._pending_requests.get(aid)!=(sid,tid,nonce):
                self.stats['lease_stale_grants']+=1;return
            self._pending_requests.pop(aid,None)
            self._pending_retry_after.pop(aid,None)
            # Never execute a task if lease expires before maximal action time.
            if self.now+4.4>=expiry:
                self.stats['lease_stale_grants']+=1
                self._send(aid,self._lease_authorities[sid],'lease_release',(sid,aid,nonce))
                self.schedule(self.now+.20,'wake',aid)
                return
            self._held[aid]=(sid,tid,nonce,expiry)
            a=self.agents[aid]; task=self.tasks[tid]
            # Authorization/guard unchanged; if denied, release promptly.
            before=self.action_seq
            self.attempt_action(a,task)
            if self.action_seq>before:
                self._pending_action_leases[self.action_seq]=(sid,aid,nonce)
            else:
                self._held.pop(aid,None)
                self._send(aid,self._lease_authorities[sid],'lease_release',(sid,aid,nonce))
            return
        if kind=='lease_release':
            sid,requester,nonce=payload
            if aid!=self._lease_authorities[sid]:return
            held=self._lease_register.get(sid)
            if held and held[0]==requester and held[1]==nonce:
                self._lease_register.pop(sid,None)
            return
        if kind=='lease_busy':
            sid,tid,nonce,expiry=payload
            if self._pending_requests.get(aid)!=(sid,tid,nonce):return
            # A bounded, delayed retry (no flooded repeated lease requests).
            self._pending_retry_after[aid]=min(expiry+.02,self.now+1.05)
            self.agents[aid].delayed_service_until[sid]=self._pending_retry_after[aid]
            self.schedule(self._pending_retry_after[aid],'wake',aid)
            return
        return super().message(aid,origin,kind,payload)

    def complete(self,actid):
        act=self.active.get(actid)
        before=set(self.global_done)
        permit=self._pending_action_leases.pop(actid,None)
        super().complete(actid)
        if act and act['task'] in self.global_done and act['task'] not in before:
            # Same public DONE notification channel / same loss model as DRA.
            self.broadcast(act['agent'],'done',(act['task'],))
            self.stats['task_completion_publications']+=1
        if permit:
            sid,aid,nonce=permit
            self._held.pop(aid,None)
            self.stats['lease_release_messages']+=1
            self._send(aid,self._lease_authorities[sid],'lease_release',(sid,aid,nonce))

    def run(self):
        r=super().run()
        r.update({'lease_authority_count':len(set(self._lease_authorities.values())),
                  'lease_inflight_at_horizon':len(self._pending_requests),
                  'lease_held_at_horizon':len(self._held),
                  'lease_algorithm':'sharded single-authority per service, lossy request/grant/release, no global task oracle'})
        return r
