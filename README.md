<p align="center"><img src="assets/rig-banner.svg" width="1280" alt="XNODE — RED └•TEAM•┐ lab™"></p>

[Штаб лаборатории](https://github.com/Xnode-sh/RED-TEAM-LAB) · [Профиль XNODE](https://github.com/Xnode-sh)

# sockpuppet-hunter

Авторский детект связанных аккаунтов (sockpuppets). Не ищет «где зарегистрирован» — **сшивает разные идентичности в кластеры** по совокупности сигналов:

- перceptual-hash аватарок (совпавшая картинка = сильный сигнал)
- схожесть display name / варианты никнейма
- пересечение bio (токены, редкие триграммы, стиль, эмодзи)
- взаимные ссылки между профилями

Порог связки: score ≥ 0.55. Веса — в `sockpuppet/signals.py`.

## Установка

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows
# или: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt  # Termux/Linux
```

## Запуск

```bash
# охота: пробить username на ~30 платформах + кластеризация
python -m sockpuppet hunt xnode_sh

# только часть платформ, быстрее
python -m sockpuppet hunt xnode_sh --platforms github gitlab reddit tiktok

# без качания аватарок (медленный нетворк)
python -m sockpuppet hunt xnode_sh --no-avatar

# экспорты
python -m sockpuppet hunt xnode_sh --json out.json --mermaid graph.mmd

# кластеризация готового списка (в т.ч. склейка вывода sherlock/maigret руками)
python -m sockpuppet correlate profiles.json
```

## Формат profiles.json

```json
[
  {
    "platform": "github",
    "username": "xnode_sh",
    "url": "https://github.com/xnode_sh",
    "display_name": "Dima",
    "bio": "OSINT · Termux",
    "avatar_url": "https://…",
    "avatar_hash": 123456,
    "extra_links": ["https://t.me/xnode_sh"]
  }
]
```

`avatar_hash` — целое (8×8 average hash). Если пусто, при экспорте можно не заполнять; при `hunt` считается автоматически.

## Структура

```
sockpuppet/
  models.py    Profile / Edge / Cluster
  discover.py  реестр платформ (regex-экстракция)
  fetch.py     HTTP-проба + парс + avatar hash
  signals.py   скоринг пар (веса и порог тут)
  cluster.py   попарный скор + union-find
  report.py    консоль + JSON + mermaid
  cli.py       argparse
```

## Правовое

Только публичные данные, read-only запросы, без брутфорса и без обхода auth. Не пытайся массово дудосить платформы — `--timeout` и паузы на тебе.

<img src="assets/rig-divider.svg" width="1280" alt="">

## Инженерный процесс лаборатории

`PLAN → ISSUE → BRANCH → WORK → TEST → PR → REVIEW → MERGE`

Команда: **RIG / KAI / NOVA**. NODE — фирменный маскот. [Правила работы](https://github.com/Xnode-sh/RED-TEAM-LAB/blob/main/WORKFLOW.md).
