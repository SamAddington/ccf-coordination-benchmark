"""Exploratory protocol-fairness controls, 24 Nov 2026.

Derived from the *frozen* v25 source without modifying it. These controls are
study-authored adaptations, not canonical distributed algorithms, and no
network service is executed. See PREDECLARED_DESIGN.md for limitations.
"""
import random
from collections import Counter
from ccf_eventlab.engine import Engine
from experiment_common import ExperimentEngine
from v12.distributed_lease import AccountedDRA,DistributedLeaseEngine
from v14.distributed_capacity import DistributedCapacitySemaphoreEngine

class FallbackCapacity(DistributedCapacitySemaphoreEngine):
    """One-timeout fallback to another service; cancellation and stale replies fenced by nonce.

    The protocol still uses the same lossy transport, service-local manager and
    per-service capacity as the sticky baseline. Only client policy differs.
    """
    def __init__(self,*args,controller='distributed_capacity',fallback_after=1,
                 release_replays=0,**kwargs):
        super().__init__(*args,controller=controller,**kwargs)
        self.fallback_after=fallback_after
        self.release_replays=release_replays
        self.client_retries=Counter()
        self.cancelled={sid:set() for sid in self.svcs}
        self.fallback_stats={'fallback_switches':0,'fallback_busy_switches':0,
           'fallback_timeout_switches':0,'fallback_cancel_messages':0,
           'fallback_late_grant_releases':0,'release_retransmissions':0}

    def _request(self,aid,sid,tid,nonce):
        self.client_retries[(aid,nonce)]+=1
        return super()._request(aid,sid,tid,nonce)

    def _send(self,origin,dest,kind,payload):
        # Explicit best-effort replays for release, each actually enters the lossy transport.
        super()._send(origin,dest,kind,payload)
        if kind=='lease_release' and self.release_replays:
            for i in range(self.release_replays):
                self.schedule(self.now+0.8*(i+1),'message',origin,origin,
                              'local_release_timer',(dest,kind,payload))

    def _switch(self,aid,reason):
        pend=self._pending_requests.pop(aid,None)
        if not pend:return
        sid,tid,nonce=pend
        self._pending_retry_after.pop(aid,None)
        self.pending_start.pop((aid,nonce),None)
        self.agents[aid].delayed_service_until[sid]=self.now+2.5
        self.stats['lease_release_messages']+=1
        self.fallback_stats['fallback_cancel_messages']+=1
        self._send(aid,self._lease_authorities[sid],'lease_cancel',(sid,aid,nonce))
        self.fallback_stats['fallback_switches']+=1
        self.fallback_stats['fallback_'+reason+'_switches']+=1
        self.schedule(self.now+.025,'wake',aid)

    def wake(self,aid):
        a=self.agents[aid]
        if a.busy:return
        p=self._pending_requests.get(aid)
        if p:
            sid,tid,nonce=p
            if self.now+1e-8<self._pending_retry_after.get(aid,0): return
            if self.client_retries[(aid,nonce)] >= self.fallback_after:
                self._switch(aid,'timeout');return
        return super().wake(aid)

    def message(self,aid,origin,kind,payload):
        if kind=='local_release_timer':
            dest,tx_kind,tx_payload=payload
            self.fallback_stats['release_retransmissions']+=1
            return super()._send(aid,dest,tx_kind,tx_payload)
        if kind=='lease_cancel':
            sid,requester,nonce=payload
            if aid!=self._lease_authorities[sid]:return
            self.cancelled[sid].add((requester,nonce))
            self.permits[sid].pop((requester,nonce),None)
            return
        if kind=='lease_request':
            sid,tid,requester,nonce=payload
            if (requester,nonce) in self.cancelled[sid]:return
        if kind=='lease_busy':
            sid,tid,nonce,expiry=payload
            if self._pending_requests.get(aid)==(sid,tid,nonce):
                self._switch(aid,'busy')
                return
        if kind=='lease_grant':
            sid,tid,nonce,expiry,token=payload
            if self._pending_requests.get(aid)!=(sid,tid,nonce):
                self.stats['lease_stale_grants']+=1
                self.fallback_stats['fallback_late_grant_releases']+=1
                self._send(aid,self._lease_authorities[sid],'lease_release',(sid,aid,nonce,token))
                return
        return super().message(aid,origin,kind,payload)

    def run(self):
        r=super().run();r.update(self.fallback_stats);return r

class ColocatedCapacity(DistributedCapacitySemaphoreEngine):
    """Manager <-> client permit transport is locally delivered without loss or delay.
    DONE notifications remain delayed/lossy. This is a placement sensitivity,
    not a claim about remote managers.
    """
    def _send(self,origin,dest,kind,payload):
        if kind in ('lease_request','lease_grant','lease_busy','lease_release'):
            self.message(dest,origin,kind,payload)
        else:super()._send(origin,dest,kind,payload)
    def run(self):
        r=super().run();r['manager_colocated']=True;return r

class RemoteGuardMixin:
    """Optional two-hop guard RPC with same latency/loss distribution as messages.

    No remote node, middleware, or consensus is claimed. The actual atomic
    capacity check is executed on acknowledgement at arrival, never at proposal.
    Each RPC response can be lost, and retry resumes the *whole* candidate path.
    """
    def _init_remote(self):
        self._remote_pending={}
        self._remote_nonce=Counter()
        self._remote_stats={'guard_requests':0,'guard_reply_sent':0,'guard_timeouts':0,
           'guard_delivery_losses':0,'guard_wire_messages':0}
    def _gate_wire(self, aid, origin, kind, payload):
        self.stats['total_messages']+=1
        self._remote_stats['guard_wire_messages']+=1
        if self.rng.random()<self.cfg.message_loss:
            self.stats['delivery_losses']+=1
            self._remote_stats['guard_delivery_losses']+=1
            return
        self.schedule(self.now+self.rng.uniform(self.cfg.delay_min,self.cfg.delay_max),
                      'message',aid,origin,kind,payload)
    def attempt_action(self,a,task):
        if self.cfg.shield!='formal_capacity':
            return super().attempt_action(a,task)
        if a.id in self._remote_pending:return
        self._remote_nonce[a.id]+=1
        n=self._remote_nonce[a.id]
        self._remote_pending[a.id]=(task.id,n)
        self._remote_stats['guard_requests']+=1
        self._gate_wire(a.id,a.id,'gate_request',(a.id,task.id,n))
        self.schedule(self.now+2*self.cfg.delay_max+.4,'message',a.id,a.id,
                      'gate_timeout',(task.id,n))
    def wake(self,aid):
        if aid in self._remote_pending:return
        return super().wake(aid)
    def message(self,aid,origin,kind,payload):
        if kind=='gate_request':
            applicant,tid,n=payload
            self._remote_stats['guard_reply_sent']+=1
            self._gate_wire(applicant,'gate','gate_reply',(tid,n))
            return
        if kind=='gate_reply':
            tid,n=payload
            if self._remote_pending.get(aid)!=(tid,n):return
            self._remote_pending.pop(aid,None)
            # This is the only execution-time atomic admission step.
            return super().attempt_action(self.agents[aid],self.tasks[tid])
        if kind=='gate_timeout':
            tid,n=payload
            if self._remote_pending.get(aid)!=(tid,n):return
            self._remote_pending.pop(aid,None)
            self._remote_stats['guard_timeouts']+=1
            self.agents[aid].delayed_service_until[self.tasks[tid].service]=self.now+.22
            self.schedule(self.now+.03,'wake',aid)
            return
        return super().message(aid,origin,kind,payload)
    def run(self):
        r=super().run();r.update(self._remote_stats);return r

class RemoteGuardDRA(RemoteGuardMixin,AccountedDRA):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self._init_remote()

class RemoteGuardIndependent(RemoteGuardMixin,ExperimentEngine):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,controller='independent',**kwargs);self._init_remote()

class ColocatedFallback(FallbackCapacity):
    """Fallback-capable client with local, lossless manager RPC; DONE still remote."""
    def _send(self,origin,dest,kind,payload):
        if kind in ('lease_request','lease_grant','lease_busy','lease_release','lease_cancel'):
            self.message(dest,origin,kind,payload)
        else:
            return super()._send(origin,dest,kind,payload)
