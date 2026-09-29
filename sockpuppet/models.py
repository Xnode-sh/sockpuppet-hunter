from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Profile:
    platform: str
    username: str
    url: str
    display_name: str = ""
    bio: str = ""
    avatar_url: str = ""
    avatar_hash: int | None = None
    extra_links: list[str] = field(default_factory=list)
    ok: bool = True
    error: str = ""

    @property
    def key(self) -> str:
        return f"{self.platform}:{self.username}"


@dataclass
class Edge:
    a: str
    b: str
    score: float
    evidence: list[str] = field(default_factory=list)


@dataclass
class Cluster:
    members: list[Profile]
    edges: list[Edge]

    @property
    def score(self) -> float:
        if not self.edges:
            return 0.0
        return max(e.score for e in self.edges)
