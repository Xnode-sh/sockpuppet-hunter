from __future__ import annotations

import json
import re

import requests

from .discover import PLATFORMS
from .models import Profile
from .signals import average_hash_from_bytes, extract_links

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


def _clean(html: str | None) -> str:
    if not html:
        return ""
    t = re.sub(r"<[^>]+>", " ", html)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def _get(url: str, timeout: float) -> requests.Response:
    return requests.get(
        url,
        headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"},
        timeout=timeout,
        allow_redirects=True,
    )


def _dig(obj, path: str):
    cur = obj
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def probe_platform(
    platform: str,
    username: str,
    timeout: float = 10.0,
    fetch_avatar: bool = True,
) -> Profile | None:
    spec = PLATFORMS.get(platform)
    if not spec:
        return None
    url = spec["url"].format(u=username)
    exists_pat = spec["exists"]
    if "{u}" in exists_pat.pattern:
        exists_pat = re.compile(
            exists_pat.pattern.replace("{u}", re.escape(username)), exists_pat.flags
        )
    p = Profile(platform=platform, username=username, url=url)

    try:
        if spec.get("kind") == "json":
            r = _get(url, timeout)
            if r.status_code != 200:
                return None
            data = r.json()
            payload = data.get("data", data)
            if not exists_pat.search(r.text):
                return None
            p.display_name = _dig(payload, spec.get("json_title", "")) or username
            p.bio = _dig(payload, spec.get("json_about", "")) or ""
            p.avatar_url = _dig(payload, spec.get("json_avatar", "")) or ""
            if p.avatar_url.startswith("//"):
                p.avatar_url = "https:" + p.avatar_url
            name = _dig(payload, spec.get("json_name", ""))
            if name:
                p.username = name
        else:
            r = _get(url, timeout)
            if r.status_code in (404, 410, 403, 429):
                return None
            if r.status_code >= 400:
                p.ok = False
                p.error = f"HTTP {r.status_code}"
                return p
            text = r.text
            if not exists_pat.search(text.replace(username, username)):
                if not exists_pat.search(text):
                    return None
            p.display_name = _first(spec.get("name"), text) or username
            p.bio = _clean(_first(spec.get("bio"), text))
            p.avatar_url = _first(spec.get("avatar"), text) or ""
    except requests.Timeout:
        p.ok = False
        p.error = "timeout"
        return p
    except Exception as e:
        p.ok = False
        p.error = str(e)[:120]
        return p

    p.extra_links = extract_links(p.bio)[:10]
    if fetch_avatar and p.avatar_url:
        try:
            ar = requests.get(
                p.avatar_url,
                headers={"User-Agent": UA},
                timeout=timeout,
            )
            if ar.ok:
                p.avatar_hash = average_hash_from_bytes(ar.content)
        except Exception:
            pass
    return p


def _first(pattern, text: str) -> str:
    if not pattern:
        return ""
    m = pattern.search(text)
    return m.group(1).strip() if m else ""


def probe_all(
    username: str,
    timeout: float = 10.0,
    fetch_avatar: bool = True,
    platforms: list[str] | None = None,
    log=None,
) -> list[Profile]:
    found: list[Profile] = []
    names = platforms or list(PLATFORMS.keys())
    for name in names:
        if log:
            log(name)
        p = probe_platform(name, username, timeout=timeout, fetch_avatar=fetch_avatar)
        if p is not None:
            found.append(p)
    return found


def load_profiles_json(path: str) -> list[Profile]:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    out = []
    for item in raw:
        out.append(
            Profile(
                platform=item["platform"],
                username=item["username"],
                url=item.get("url", ""),
                display_name=item.get("display_name", ""),
                bio=item.get("bio", ""),
                avatar_url=item.get("avatar_url", ""),
                avatar_hash=item.get("avatar_hash"),
                extra_links=item.get("extra_links", []),
                ok=item.get("ok", True),
                error=item.get("error", ""),
            )
        )
    return out
