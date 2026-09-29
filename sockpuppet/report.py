from __future__ import annotations

import json
from pathlib import Path

from .models import Cluster, Profile


def print_report(
    profiles: list[Profile],
    clusters: list[Cluster],
    show_singles: bool = True,
) -> None:
    ok = [p for p in profiles if p.ok]
    print(f"\nПроверено платформ: {len(profiles)} · найдено профилей: {len(ok)}")
    fails = [p for p in profiles if not p.ok]
    if fails:
        print(f"Ошибки/лимиты: {len(fails)}")

    if not clusters:
        print("\nСвязанных кластеров не найдено.")
    else:
        print(f"\n=== Кластеры связанных аккаунтов: {len(clusters)} ===")
        for i, cl in enumerate(clusters, 1):
            print(f"\n[{i}] участников={len(cl.members)} score={cl.score:.2f}")
            for p in cl.members:
                name = p.display_name or "—"
                print(f"  • {p.platform:16} @{p.username:20} «{name}»")
                print(f"    {p.url}")
                if p.bio:
                    bio = p.bio[:100] + ("…" if len(p.bio) > 100 else "")
                    print(f"    bio: {bio}")
            print("  evidence:")
            for e in cl.edges:
                for line in e.evidence:
                    print(f"    - [{e.score:.2f}] {line}")

    if show_singles:
        clustered_keys = set()
        for cl in clusters:
            for m in cl.members:
                clustered_keys.add(m.key)
        singles = [p for p in ok if p.key not in clustered_keys]
        if singles:
            print(f"\n--- Одинокие профили ({len(singles)}) ---")
            for p in singles:
                print(f"  {p.platform:16} @{p.username:20} {p.url}")


def export_json(path: str, profiles: list[Profile], clusters: list[Cluster]) -> None:
    data = {
        "profiles": [
            {
                "platform": p.platform,
                "username": p.username,
                "url": p.url,
                "display_name": p.display_name,
                "bio": p.bio,
                "avatar_url": p.avatar_url,
                "avatar_hash": p.avatar_hash,
                "extra_links": p.extra_links,
                "ok": p.ok,
                "error": p.error,
            }
            for p in profiles
        ],
        "clusters": [
            {
                "score": c.score,
                "members": [m.key for m in c.members],
                "edges": [
                    {"a": e.a, "b": e.b, "score": e.score, "evidence": e.evidence}
                    for e in c.edges
                ],
            }
            for c in clusters
        ],
    }
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"JSON → {path}")


def export_mermaid(path: str, clusters: list[Cluster]) -> None:
    lines = ["graph LR"]
    for i, cl in enumerate(clusters, 1):
        lines.append(f"  subgraph cluster{i}")
        for m in cl.members:
            node = m.key.replace(":", "_").replace("-", "_")
            label = f"{m.platform}\\n@{m.username}"
            lines.append(f'    {node}["{label}"]')
        for e in cl.edges:
            a = e.a.replace(":", "_").replace("-", "_")
            b = e.b.replace(":", "_").replace("-", "_")
            lines.append(f"    {a} ---|{e.score:.2f}| {b}")
        lines.append("  end")
    Path(path).write_text("\n".join(lines), encoding="utf-8")
    print(f"Mermaid → {path}")
