"""Post-publication prospective symmetric comparison of client policy and control plane.

This extends but does NOT overwrite the archived v26 experiment. Reuse the
v26 generator to permit a matched contrast, but release new source and data.
"""
import random
from collections import Counter
from fair_engines import FallbackCapacity
from experiment_common import ExperimentEngine
from v12.distributed_lease import AccountedDRA
from v14.distributed_capacity import DistributedCapacitySemaphoreEngine
from ccf_eventlab.engine import RunConfig

CTRL = ('lease_request','lease_grant','lease_busy','lease_release','lease_cancel')

class ClaimPlane(AccountedDRA):
    """Advisory service-claim coordinator, with explicit free or remote plane.

    Remote plane is the historical model: independent Bernoulli drops and
    uniform per-hop delays on claim messages, plus max-hop+0.13 settlement.
    Free plane delivers claims instantly, losslessly and with zero settlement.
    DONE notifications remain on the lossy network in both treatments.
    """
    def __init__(self, *args, free_plane=False, sticky=False, sticky_window=2.5, **kwargs):
        super().__init__(*args,controller='dra',**kwargs)
        self.free_plane=free_plane; self.sticky=sticky; self.sticky_window=sticky_window
        self.locked_service={}
        self.plane_stats={'local_claim_deliveries':0,'claim_sticky_block_wakes':0}

    def broadcast(self,origin,kind,payload):
        if self.free_plane and kind=='claim':
            for aid in [a.id for a in self.agents if a.id!=origin]:
                self.plane_stats['local_claim_deliveries']+=1
                self.message(aid,origin,kind,payload)
            return
        return super().broadcast(origin,kind,payload)

    def new_claim(self,a,task,position=0):
        if self.sticky:
            retained=self.locked_service.get(a.id)
            if retained is None or retained[1]<=self.now:
                self.locked_service[a.id]=(task.service,self.now+self.sticky_window)
        return super().new_claim(a,task,position)

    def best_candidates(self, a):
        opts=super().best_candidates(a)
        if not self.sticky:return opts
        retained=self.locked_service.get(a.id)
        if retained is None or retained[1]<=self.now:return opts
        filtered=[t for t in opts if t.service==retained[0]]
        if not filtered and opts:self.plane_stats['claim_sticky_block_wakes']+=1
        return filtered

    def run(self):
        r=super().run(); r.update(self.plane_stats)
        r.update(plane='free' if self.free_plane else 'remote',policy='sticky' if self.sticky else 'redirect')
        return r

class PermitPlaneMixin:
    """Logical remote manager messages are charged even on a home host.

    The historical dispatcher zero-costs a self-send; this experimental arm
    instead applies the SAME loss/delay distribution on every manager RPC.
    Free plane zero-costs every manager RPC. DONE remains remote in both.
    """
    def _init_plane(self,free_plane):
        self.free_plane=free_plane
        self.plane_stats={'local_manager_deliveries':0,'remote_home_manager_messages':0}

    def _send(self,origin,dest,kind,payload):
        if kind not in CTRL:return super()._send(origin,dest,kind,payload)
        if self.free_plane:
            self.plane_stats['local_manager_deliveries']+=1
            return self.message(dest,origin,kind,payload)
        if dest==origin:self.plane_stats['remote_home_manager_messages']+=1
        self.stats['total_messages']+=1
        self.stats[kind+'_messages']=self.stats.get(kind+'_messages',0)+1
        # Respect original approximate wire payload estimator when available
        from v12.distributed_lease import encoded_payload_bytes
        self.stats['wire_payload_bytes']+=encoded_payload_bytes(origin,kind,payload)
        if self.rng.random()<self.cfg.message_loss:
            self.stats['delivery_losses']+=1;return
        delay=self.rng.uniform(self.cfg.delay_min,self.cfg.delay_max)
        self.schedule(self.now+delay,'message',dest,origin,kind,payload)

    def run(self):
        r=super().run(); r.update(self.plane_stats)
        r.update(plane='free' if self.free_plane else 'remote')
        return r

class StickyPermit(PermitPlaneMixin,DistributedCapacitySemaphoreEngine):
    def __init__(self,*args,free_plane=False,**kwargs):
        super().__init__(*args,controller='distributed_capacity',**kwargs)
        self._init_plane(free_plane)
    def run(self):
        r=super().run();r['policy']='sticky';return r

class RedirectPermit(PermitPlaneMixin,FallbackCapacity):
    def __init__(self,*args,free_plane=False,**kwargs):
        super().__init__(*args,controller='distributed_capacity',fallback_after=1,**kwargs)
        self._init_plane(free_plane)
    def run(self):
        r=super().run();r['policy']='redirect';return r
