from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from .models import Edge, Profile

_SEP_RE = re.compile(r"[\s._\-]+")
_NON_ALNUM = re.compile(r"[^a-z0-9а-яё]")
_URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.I)
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "]+",
    flags=re.UNICODE,
)

WEIGHT_AVATAR = 0.45
WEIGHT_NAME = 0.30
WEIGHT_BIO = 0.25
WEIGHT_LINK = 0.40
WEIGHT_STYLE = 0.20
LINK_THRESHOLD = 0.55


def norm_username(u: str) -> str:
    u = unicodedata.normalize("NFKC", u or "").lower()
    return _SEP_RE.sub("", u)


def username_variant_score(a: str, b: str) -> float:
    na, nb = norm_username(a), norm_username(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    parts_a = set(_SEP_RE.split(a.lower()))
    parts_b = set(_SEP_RE.split(b.lower()))
    if parts_a & parts_b and min(len(na), len(nb)) >= 4:
        return 0.75
    return SequenceMatcher(None, na, nb).ratio()


def text_similarity(a: str, b: str) -> float:
    ta = _tokens(a)
    tb = _tokens(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


def stylometry_score(a: str, b: str) -> float:
    tr_a = _trigrams(a)
    tr_b = _trigrams(b)
    if not tr_a or not tr_b:
        return 0.0
    inter = len(tr_a & tr_b)
    union = len(tr_a | tr_b)
    return inter / union if union else 0.0


def emoji_set_score(a: str, b: str) -> float:
    ea = set(_EMOJI_RE.findall(a or ""))
    eb = set(_EMOJI_RE.findall(b or ""))
    if not ea or not eb:
        return 0.0
    return len(ea & eb) / len(ea | eb)


def avatar_distance(h1: int | None, h2: int | None) -> int | None:
    if h1 is None or h2 is None:
        return None
    return bin(h1 ^ h2).count("1")


def average_hash_from_bytes(data: bytes) -> int | None:
    try:
        from io import BytesIO

        from PIL import Image
    except ImportError:
        return None
    try:
        img = Image.open(BytesIO(data))
        img = img.convert("L").resize((8, 8))
        px = list(img.getdata())
        avg = sum(px) / 64
        bits = 0
        for i, p in enumerate(px):
            if p > avg:
                bits |= 1 << i
        return bits
    except Exception:
        return None


def extract_links(text: str) -> list[str]:
    return _URL_RE.findall(text or "")


def pair_score(p1: Profile, p2: Profile) -> Edge | None:
    if p1.platform == p2.platform and p1.username == p2.username:
        return None
    evidence: list[str] = []
    total = 0.0
    weight_sum = 0.0

    dist = avatar_distance(p1.avatar_hash, p2.avatar_hash)
    if dist is not None:
        weight_sum += WEIGHT_AVATAR
        if dist <= 6:
            total += WEIGHT_AVATAR
            evidence.append(f"аватар совпадает (hamming={dist})")
        elif dist <= 10:
            total += WEIGHT_AVATAR * 0.5
            evidence.append(f"аватар похож (hamming={dist})")

    name_score = SequenceMatcher(
        None,
        (p1.display_name or p1.username).lower(),
        (p2.display_name or p2.username).lower(),
    ).ratio()
    if name_score >= 0.85:
        total += WEIGHT_NAME
        evidence.append(f"имя/ник почти одинаково ({name_score:.2f}): «{p1.display_name or p1.username}» / «{p2.display_name or p2.username}»")
    elif name_score >= 0.7:
        total += WEIGHT_NAME * 0.5
        evidence.append(f"похожее имя ({name_score:.2f})")
    weight_sum += WEIGHT_NAME

    if p1.bio and p2.bio:
        bio_s = text_similarity(p1.bio, p2.bio)
        weight_sum += WEIGHT_BIO
        if bio_s >= 0.5:
            total += WEIGHT_BIO
            evidence.append(f"bio-пересечение токенов ({bio_s:.2f})")
        elif bio_s >= 0.3:
            total += WEIGHT_BIO * 0.5
            evidence.append(f"частичное совпадение bio ({bio_s:.2f})")

    links1 = {norm_username_from_url(u) for u in p1.extra_links}
    links2 = {norm_username_from_url(u) for u in p2.extra_links}
    if links1 and links2:
        cross = any(
            p2.platform.lower() in l and norm_username(p2.username) in l
            for l in links1
        ) or any(
            p1.platform.lower() in l and norm_username(p1.username) in l
            for l in links2
        )
        if cross:
            total += WEIGHT_LINK
            evidence.append("профили ссылаются друг на друга")
        weight_sum += WEIGHT_LINK

    if p1.bio and p2.bio:
        style = stylometry_score(p1.bio, p2.bio)
        emoji = emoji_set_score(p1.bio, p2.bio)
        style_best = max(style, emoji)
        weight_sum += WEIGHT_STYLE
        if style_best >= 0.25:
            total += WEIGHT_STYLE * style_best / 0.25 if style_best else 0
            total = min(total, weight_sum)
            evidence.append(f"стиль речи/эмодзи похожи ({style_best:.2f})")

    if not evidence:
        return None

    score = total / weight_sum if weight_sum else 0.0
    if score < LINK_THRESHOLD:
        return None
    return Edge(a=p1.key, b=p2.key, score=round(score, 3), evidence=evidence)


def norm_username_from_url(url: str) -> str:
    m = re.search(r"https?://(?:www\.)?([^/]+)/.*", url or "", re.I)
    return m.group(1).lower() if m else (url or "").lower()


def _tokens(text: str) -> set[str]:
    t = (text or "").lower()
    t = _NON_ALNUM.sub(" ", t)
    return {w for w in t.split() if len(w) > 2}


def _trigrams(text: str) -> set[str]:
    t = _NON_ALNUM.sub("", (text or "").lower())
    return {t[i : i + 3] for i in range(len(t) - 2)}
