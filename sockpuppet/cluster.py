from __future__ import annotations

from .models import Cluster, Edge, Profile
from .signals import pair_score


def build_edges(profiles: list[Profile]) -> list[Edge]:
    edges: list[Edge] = []
    for i in range(len(profiles)):
        for j in range(i + 1, len(profiles)):
            e = pair_score(profiles[i], profiles[j])
            if e:
                edges.append(e)
    edges.sort(key=lambda e: e.score, reverse=True)
    return edges


def union_find_clusters(
    profiles: list[Profile], edges: list[Edge]
) -> list[Cluster]:
    parent = {p.key: p.key for p in profiles}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    by_key = {p.key: p for p in profiles}
    used_edges: dict[str, list[Edge]] = {}

    for e in edges:
        if e.a in parent and e.b in parent:
            union(e.a, e.b)
            used_edges.setdefault(e.a, []).append(e)
            used_edges.setdefault(e.b, []).append(e)

    groups: dict[str, list[Profile]] = {}
    for p in profiles:
        groups.setdefault(find(p.key), []).append(p)

    clusters: list[Cluster] = []
    for members in groups.values():
        if len(members) < 2:
            continue
        keys = {m.key for m in members}
        cl_edges = [e for e in edges if e.a in keys and e.b in keys]
        if not cl_edges:
            continue
        clusters.append(Cluster(members=members, edges=cl_edges))
    clusters.sort(key=lambda c: (c.score, len(c.members)), reverse=True)
    return clusters
