"""Closed-world, synthetic tasks and state; there are no network tools or exploits."""
from __future__ import annotations
from dataclasses import dataclass, field
import hashlib
import random


def draw01(*parts: object) -> float:
    """Stable independent draw keyed to environment, agent, and task, rather than event ordering."""
    payload = '|'.join(map(str, parts)).encode('utf8')
    seed = int.from_bytes(hashlib.blake2b(payload, digest_size=8).digest(), 'big')
    return random.Random(seed).random()

@dataclass(frozen=True)
class ServiceSpec:
    id: str
    capacity: int
    threshold: float
    fragility: float
    recovery: float

@dataclass(frozen=True)
class Task:
    id: str
    service: str
    value: float
    duration: float
    difficulty: float
    allowed: bool = True

@dataclass(frozen=True)
class World:
    id: str
    seed: int
    services: tuple[ServiceSpec, ...]
    tasks: tuple[Task, ...]
    num_agents: int


def world_factory(seed: int, scale: str = 'medium', agent_override: int | None = None) -> World:
    rng = random.Random(seed)
    sizes = {'small': (4,4), 'medium': (6,6), 'large': (8,8)}
    n_svc, n_agents = sizes[scale]
    if agent_override is not None:
        n_agents = agent_override
    services, tasks = [], []
    for s in range(n_svc):
        # Two high-demand bottlenecks, other services vary in capacity.
        cap = 2 if s < 2 else rng.choice([1,2,3])
        services.append(ServiceSpec(f's{s:02}', cap, round(rng.uniform(1.4, 2.15),3),
                                    round(rng.uniform(0.85, 1.25),3), round(rng.uniform(1.6, 2.6),3)))
        for t in range(4):
            # Hot services offer slightly higher task rewards to create contention; all arms see identical data.
            v = rng.uniform(7.5, 12.0) if s < 2 else rng.uniform(4.0, 10.0)
            tasks.append(Task(f's{s:02}-t{t}', f's{s:02}', round(v,3),
                              round(rng.uniform(1.4, 3.4),3), round(rng.uniform(0.1,0.8),3)))
    # Explicit restricted targets exercise the common RoE guard; no engine executes them.
    tasks.append(Task('forbidden-0', 's00', 15, 1.0, 0.2, allowed=False))
    tasks.append(Task('forbidden-1', 's01', 14, 1.0, 0.2, allowed=False))
    return World(f'{scale}-{seed}',seed,tuple(services),tuple(tasks),n_agents)


def agent_skill(world: World, agent: int, task: Task) -> float:
    return 0.45 + 0.55*draw01(world.seed,'skill',agent,task.id)


def bid(world: World, agent: int, task: Task) -> float:
    skill = agent_skill(world,agent,task)
    return task.value*(0.65+0.5*skill)/(task.duration*(1.12-0.28*skill))
