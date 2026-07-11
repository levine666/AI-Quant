#!/usr/bin/env python3
"""从 spec/ai_quant_apps.yaml 生成 AI-Quant/apps/registry.json。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "spec" / "ai_quant_apps.yaml"
OUT = Path(__file__).resolve().parents[1] / "apps" / "registry.json"
MANIFEST = ROOT / "data" / "turtle" / "manifest.json"


def load_manifest_date() -> str | None:
    if not MANIFEST.exists():
        return None
    with MANIFEST.open(encoding="utf-8") as f:
        data = json.load(f)
    return data.get("global", {}).get("refreshed_at")


def main() -> None:
    with SPEC.open(encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    meta = dict(spec.get("meta", {}))
    data_updated = load_manifest_date()
    if data_updated:
        meta["data_updated"] = data_updated

    apps = sorted(spec.get("apps", []), key=lambda a: a.get("order", 999))
    planned = sorted(spec.get("planned_apps", []), key=lambda a: a.get("order", 999))

    payload = {
        "meta": meta,
        "apps": apps,
        "planned_apps": planned,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(apps)} apps, {len(planned)} planned)")


if __name__ == "__main__":
    main()
