from __future__ import annotations

import argparse
import sys


def _utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


from .cluster import build_edges, union_find_clusters
from .discover import PLATFORMS
from .fetch import load_profiles_json, probe_all
from .report import export_json, export_mermaid, print_report


def main(argv: list[str] | None = None) -> int:
    _utf8_stdio()
    ap = argparse.ArgumentParser(
        prog="sockpuppet",
        description="sockpuppet-hunter — детект связанных аккаунтов",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    hunt = sub.add_parser("hunt", help="искать username на платформах и кластеризовать")
    hunt.add_argument("username")
    hunt.add_argument("--timeout", type=float, default=10.0)
    hunt.add_argument("--no-avatar", action="store_true", help="не качать аватарки")
    hunt.add_argument(
        "--platforms",
        nargs="*",
        help=f"только эти платформы (доступно: {', '.join(PLATFORMS)})",
    )
    hunt.add_argument("--json", help="путь для экспорта JSON")
    hunt.add_argument("--mermaid", help="путь для экспорта mermaid-графа")
    hunt.add_argument("--no-singles", action="store_true", help="не показывать одинокие")

    corr = sub.add_parser("correlate", help="кластьеризовать готовый JSON профилей")
    corr.add_argument("file", help="profiles.json")
    corr.add_argument("--json", help="путь для экспорта JSON")
    corr.add_argument("--mermaid", help="путь для экспорта mermaid-графа")
    corr.add_argument("--no-singles", action="store_true")

    args = ap.parse_args(argv)

    if args.cmd == "hunt":
        if args.platforms:
            unknown = [p for p in args.platforms if p not in PLATFORMS]
            if unknown:
                print(f"нет платформ: {', '.join(unknown)}", file=sys.stderr)
                return 2

        def log(name: str) -> None:
            print(f"  probe {name}…", flush=True)

        print(f"hunt: @{args.username}")
        profiles = probe_all(
            args.username,
            timeout=args.timeout,
            fetch_avatar=not args.no_avatar,
            platforms=args.platforms,
            log=log,
        )
    else:
        profiles = load_profiles_json(args.file)
        print(f"correlate: {len(profiles)} профилей из {args.file}")

    edges = build_edges(profiles)
    clusters = union_find_clusters(profiles, edges)
    print_report(profiles, clusters, show_singles=not args.no_singles)

    if getattr(args, "json", None):
        export_json(args.json, profiles, clusters)
    if getattr(args, "mermaid", None):
        export_mermaid(args.mermaid, clusters)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
