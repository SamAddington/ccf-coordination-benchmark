"""Exploratory pipelined claim admission (no physical server or consensus).

A claim's *service-admission request* is sent at the same event as claim
publication.  Actual action execution is blocked until BOTH the original
settlement deadline and a successful two-hop service response have occurred.
The response is not a capacity reservation; capacity is checked only at
execution, as with the frozen sequential experiment. The model permits overlap
between publication/settlement and the RPC, and cancels stale requests on
claim deferral, completion, or timeout. A lost reply cannot start an action.

Study-authored variation of the published CCF engine. Not a new protocol claim.
"""
from __future__ import annotations
from collections import Counter
from admission_symmetric import ClaimServiceAdmission
from fair_engines import RemoteGuardMixin


class PipelinedClaimAdmission(ClaimServiceAdmission):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self._pipeline = {}
        self._pipeline_nonce = Counter()
        self._pipeline_metrics = Counter()

    def new_claim(self,a,task,position=0):
        super().new_claim(a,task,position)
        if self.cfg.shield != 'formal_capacity':
            return
        if a.id in self._pipeline:
            self._pipeline.pop(a.id,None)
            self._pipeline_metrics['pipeline_superseded']+=1
        self._pipeline_nonce[a.id]+=1
        n=self._pipeline_nonce[a.id]
        self._pipeline[a.id]={'task_id':task.id,'nonce':n,'ack':False,'settled':False,
                              'started_at':self.now}
        self._remote_stats['guard_requests']+=1
        # Starts concurrently with claim settlement; no premature execution.
        self._gate_wire(a.id,a.id,'pipe_guard_request',(a.id,task.id,n))
        self.schedule(self.now+2*self.cfg.delay_max+0.4,'message',a.id,a.id,
                      'pipe_guard_timeout',(task.id,n))

    def _start_if_ready(self,aid):
        p=self._pipeline.get(aid)
        if not p or not(p['ack'] and p['settled']):return
        a=self.agents[aid]
        self._pipeline.pop(aid,None)
        if p['task_id'] in a.local_done:
            self._pipeline_metrics['pipeline_obsolete_task']+=1
            self.schedule(self.now+0.03,'wake',aid)
            return
        t=self.tasks[p['task_id']]
        # Authoritative capacity check at *start*, not at RPC transmission.
        self._pipeline_metrics['pipeline_completed']+=1
        return super(RemoteGuardMixin,self).attempt_action(a,t)

    def wake(self,aid):
        p=self._pipeline.get(aid)
        if not p:return super().wake(aid)
        a=self.agents[aid]
        if a.busy:
            return
        if a.pending is not None:
            if self.now < a.pending_at-1e-7:return
            task=self.tasks[a.pending]
            winner=a.views.get('svc:'+task.service)
            if winner and winner[0]!=aid and winner[2]>self.now:
                self._pipeline.pop(aid,None)
                self._pipeline_metrics['pipeline_claim_preemptions']+=1
                return super().wake(aid)
            a.pending=None
            p['settled']=True
            return self._start_if_ready(aid)
        if not p['settled']:
            # A DONE or superior claim canceled the proposal before settlement.
            self._pipeline.pop(aid,None)
            self._pipeline_metrics['pipeline_cancelled']+=1
            return super().wake(aid)
        return self._start_if_ready(aid)

    def message(self,aid,origin,kind,payload):
        if kind=='pipe_guard_request':
            requestor,task_id,n=payload
            self._remote_stats['guard_reply_sent']+=1
            self._gate_wire(requestor,'gate','pipe_guard_reply',(task_id,n))
            return
        if kind=='pipe_guard_reply':
            task_id,n=payload
            p=self._pipeline.get(aid)
            if not p or (p['task_id'],p['nonce'])!=(task_id,n):return
            p['ack']=True
            if not p['settled']:
                self._pipeline_metrics['pipeline_early_replies']+=1
            return self._start_if_ready(aid)
        if kind=='pipe_guard_timeout':
            task_id,n=payload
            p=self._pipeline.get(aid)
            if not p or (p['task_id'],p['nonce'])!=(task_id,n):return
            self._pipeline.pop(aid,None)
            self._remote_stats['guard_timeouts']+=1
            self._pipeline_metrics['pipeline_timeouts']+=1
            a=self.agents[aid]
            if a.pending==task_id:a.pending=None
            a.delayed_service_until[self.tasks[task_id].service]=self.now+0.22
            self.schedule(self.now+0.03,'wake',aid)
            return
        if kind=='done':
            task_id,=payload
            p=self._pipeline.get(aid)
            if p and p['task_id']==task_id:
                self._pipeline.pop(aid,None)
                self._pipeline_metrics['pipeline_done_cancel']+=1
        return super().message(aid,origin,kind,payload)

    def run(self):
        out=super().run()
        out.update(self._pipeline_metrics)
        return out
