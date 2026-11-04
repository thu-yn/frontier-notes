#!/usr/bin/env python3
"""校验期刊日期、必需栏目和页面渲染所需的基本结构。"""

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def validate_issue(path: Path, expected_date: str) -> dict:
    date.fromisoformat(expected_date)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("date") != expected_date:
        raise ValueError(f"{path}: date 必须是 {expected_date}")
    for key, kind in (("editor_note", str), ("math_note", dict), ("crossover", dict)):
        if not isinstance(data.get(key), kind) or not data[key]:
            raise ValueError(f"{path}: 缺少或无效的 {key}")
    for key in ("papers", "repos", "news", "research_ideas"):
        if not isinstance(data.get(key), list):
            raise ValueError(f"{path}: {key} 必须是数组")
        if any(not isinstance(item, dict) for item in data[key]):
            raise ValueError(f"{path}: {key} 条目必须是对象")
    if not any(data[key] for key in ("papers", "repos", "news")):
        raise ValueError(f"{path}: 论文、仓库、资讯不能全部为空")

    cx = data["crossover"]
    for key in ("theory", "pc_problem", "bridge", "angles"):
        if not cx.get(key):
            print(f"::warning::crossover 缺 {key}")
    angles = cx.get("angles") or []
    if not isinstance(angles, list) or any(not isinstance(a, dict) for a in angles):
        raise ValueError(f"{path}: crossover.angles 必须是对象数组")
    if not 3 <= len(angles) <= 4:
        print(f"::warning::crossover.angles 有 {len(angles)} 条,规范要求 3-4 条")
    dims = [str(a.get("dim", "")) for a in angles]
    hit = sum(any(core in dim for dim in dims) for core in ("复杂度", "存储", "算法优化"))
    if hit < 2:
        print(f"::warning::crossover.angles 维度 {dims} 只覆盖了 {hit} 个核心维度")
    for i, angle in enumerate(angles, 1):
        if not all(angle.get(key) for key in ("idea", "gain", "cost")):
            print(f"::warning::crossover.angles[{i}] 缺 idea/gain/cost")

    components = {"cobweb", "fourier", "gradient", "vectorfield", "riemann"}
    viz = data["math_note"].get("viz")
    if viz:
        if not isinstance(viz, dict):
            raise ValueError(f"{path}: math_note.viz 必须是对象")
        kind = viz.get("type")
        if kind == "custom":
            if not (viz.get("html") and viz.get("script")):
                print("::warning::math_note.viz 为 custom 但缺 html 或 script")
        elif kind in components:
            if not isinstance(viz.get("params"), dict):
                print(f"::warning::math_note.viz 组件 {kind} 缺 params 字典")
        else:
            print(f"::warning::math_note.viz.type 未知: {kind!r}")
    print(f"✓ 期刊校验通过: {path}")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    today = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    parser.add_argument("--date", default=today)
    args = parser.parse_args()
    validate_issue(ROOT / "data" / "daily" / f"{args.date}.json", args.date)


if __name__ == "__main__":
    main()
