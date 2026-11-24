"""Per-service C-permit coordinator using unchanged v12 lossy/delayed transport.

Static honest authority per service holds up to C_s expiring permits, each with
monotonic fencing token for stale release detection. It has no completion oracle.
No authority crash, split-brain, clock drift, worker fencing or real network.
"""
from collections import Counter
from experiment_common import ExperimentEngine
from v12.distributed_lease import DistributedLeaseEngine,LEASE_TTL

class DistributedCapacitySemaphoreEngine(DistributedLeaseEngine):
    def __init__(self,world,cfg,seed,*,controller='distributed_capacity',**kwargs):
        if controller!='distributed_capacity':raise ValueError(controller)
        super().__init__(world,cfg,seed,controller='distributed_lease',**kwargs)
        self.controller=controller
        self.permits={sid:{} for sid in self.svcs}  # (aid, nonce)->(expiry, token)
        self.serial=Counter();self.action_tokens={}
        self.pending_start={}
        self.stats.update({'permit_issued':0,'permit_peak_issued':0,'permit_expired':0,
            'permit_replayed_grants':0,'permit_stale_releases':0,'permit_capacity_violations':0,
            'permit_wait_sum':0.,'permit_wait_count':0})

    def _prune(self,sid):
        for key,(expiry,token) in list(self.permits[sid].items()):
            if self.now>=expiry:
                del self.permits[sid][key]
                self.stats['permit_expired']+=1

    def _request(self,aid,sid,tid,nonce):
        self.pending_start.setdefault((aid,nonce),self.now)
        return super()._request(aid,sid,tid,nonce)

    def message(self,aid,origin,kind,payload):
        if kind=='lease_request':
            sid,tid,requester,nonce=payload
            if aid!=self._lease_authorities[sid]:return
            self._prune(sid)
            reg=self.permits[sid];key=(requester,nonce)
            current=reg.get(key)
            if current is not None:
                expiry,token=current
                self.stats['permit_replayed_grants']+=1
                self.stats['lease_grants']+=1
                self._send(aid,requester,'lease_grant',(sid,tid,nonce,expiry,token))
            elif len(reg)<self.svcs[sid].spec.capacity:
                self.serial[sid]+=1
                expiry=self.now+LEASE_TTL;token=self.serial[sid]
                reg[key]=(expiry,token)
                self.stats['permit_issued']+=1
                self.stats['lease_grants']+=1
                self.stats['permit_peak_issued']=max(self.stats['permit_peak_issued'],len(reg))
                if len(reg)>self.svcs[sid].spec.capacity:
                    self.stats['permit_capacity_violations']+=1
                    raise AssertionError('capacity permits oversubscribed')
                self._send(aid,requester,'lease_grant',(sid,tid,nonce,expiry,token))
            else:
                self.stats['lease_denials']+=1
                self._send(aid,requester,'lease_busy',(sid,tid,nonce,min(x[0] for x in reg.values())))
            return
        if kind=='lease_grant':
            sid,tid,nonce,expiry,token=payload
            if self._pending_requests.get(aid)!=(sid,tid,nonce):
                self.stats['lease_stale_grants']+=1;return
            self._pending_requests.pop(aid,None)
            self._pending_retry_after.pop(aid,None)
            if self.now+4.4>=expiry:
                self.stats['lease_stale_grants']+=1
                self._send(aid,self._lease_authorities[sid],'lease_release',(sid,aid,nonce,token))
                self.schedule(self.now+.20,'wake',aid)
                return
            self._held[aid]=(sid,tid,nonce,expiry,token)
            t0=self.pending_start.pop((aid,nonce),self.now)
            self.stats['permit_wait_sum']+=self.now-t0
            self.stats['permit_wait_count']+=1
            before=self.action_seq
            self.attempt_action(self.agents[aid],self.tasks[tid])
            if self.action_seq>before:
                self.action_tokens[self.action_seq]=(sid,aid,nonce,token)
            else:
                self._held.pop(aid,None)
                self._send(aid,self._lease_authorities[sid],'lease_release',(sid,aid,nonce,token))
            return
        if kind=='lease_release':
            sid,requester,nonce,token=payload
            if aid!=self._lease_authorities[sid]:return
            reg=self.permits[sid]
            if reg.get((requester,nonce),(None,None))[1]==token:
                del reg[(requester,nonce)]
            else:self.stats['permit_stale_releases']+=1
            return
        return super().message(aid,origin,kind,payload)

    def complete(self,actid):
        act=self.active.get(actid)
        before=set(self.global_done)
        token=self.action_tokens.pop(actid,None)
        ExperimentEngine.complete(self,actid)
        if act and act['task'] in self.global_done and act['task'] not in before:
            self.broadcast(act['agent'],'done',(act['task'],))
            self.stats['task_completion_publications']+=1
        if token:
            sid,aid,nonce,tokenid=token
            self._held.pop(aid,None)
            self.stats['lease_release_messages']+=1
            self._send(aid,self._lease_authorities[sid],'lease_release',(sid,aid,nonce,tokenid))

    def run(self):
        r=super().run()
        for sid in self.permits:
            self._prune(sid)
            assert len(self.permits[sid])<=self.svcs[sid].spec.capacity
        assert self.stats['permit_capacity_violations']==0
        assert r['overcapacity_admissions']==0
        r.update(controller=self.controller,lease_algorithm='C_s concurrent permits; per-service single authority; nonce+token releases',
            permit_mean_acquisition_wait=(self.stats['permit_wait_sum']/self.stats['permit_wait_count'] if self.stats['permit_wait_count'] else 0.),
            capacity_min=min(s.spec.capacity for s in self.svcs.values()),
            capacity_max=max(s.spec.capacity for s in self.svcs.values()),
            capacity_sum=sum(s.spec.capacity for s in self.svcs.values()))
        return r
