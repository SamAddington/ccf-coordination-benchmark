"""Prospective, exploratory service-side admission comparison, 24 Nov 2026.

Uses frozen v27 worlds/engine; DOES NOT alter any historical v27 code/data.
Free-plane completion notifications are repaired to use the declared common
remote DONE channel, independently of the coordinator's control plane.

Two access models:
- local_check: free simulated shared atomic guard (historical control).
- service_admission: claim proposals must traverse lossy request/reply to a
  service-side guard; a permit grant is already a reservation/admission by the
  co-located authority and is *not* charged a redundant second transaction.

All service checks are simulation-model oracle checks (not a live backend).
A claim may settle first and then request admission; this is a deliberate
sequential policy, not a parallel/pipelined implementation.
"""
from __future__ import annotations
from collections import Counter
from symmetry_design import ClaimPlane, RedirectPermit, StickyPermit
from fair_engines import RemoteGuardMixin
from v12.distributed_lease import encoded_payload_bytes

class CommonDoneChannel:
    """Keep completion broadcasts at U(.35,.95), including ideal claim/permit control.
    This fixes the prior implementation's unintended zero-delay DONE at free plane.
    """
    def broadcast(self,origin,kind,payload):
        if kind!='done':
            return super().broadcast(origin,kind,payload)
        for a in self.agents:
            if a.id==origin:continue
            self.stats['total_messages']+=1
            self.stats['done_messages']=self.stats.get('done_messages',0)+1
            self.stats['wire_payload_bytes']=self.stats.get('wire_payload_bytes',0)+encoded_payload_bytes(origin,kind,payload)
            if self.rng.random()<self.cfg.message_loss:
                self.stats['delivery_losses']+=1
                continue
            self.schedule(self.now+self.rng.uniform(.35,.95),'message',a.id,origin,kind,payload)

class ClaimWithCommonDone(CommonDoneChannel,ClaimPlane):
    pass

class ClaimServiceAdmission(RemoteGuardMixin,ClaimWithCommonDone):
    """Claim publication/settlement followed by service-admission request/reply.
    The check occurs at the received reply, not during request delivery;
    there is no remote reservation/transaction or server crash modeled.
    """
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self._init_remote()

class PermitStickyWithCommonDone(CommonDoneChannel,StickyPermit):
    pass

class PermitRedirectWithCommonDone(CommonDoneChannel,RedirectPermit):
    pass
