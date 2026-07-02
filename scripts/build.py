#!/usr/bin/env python3
"""把 data/daily/*.json 渲染成静态站点 site/。

- site/index.html          最新一期
- site/issues/<date>.html  每期归档页
- site/archive.html        往期目录
"""

import json
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

WEEKDAYS = "一二三四五六日"


def load_issues() -> list[dict]:
    issues = []
    for f in sorted((ROOT / "data" / "daily").glob("*.json")):
        try:
            issues.append(json.loads(f.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            print(f"[build] 跳过无法解析的 {f.name}")
    issues.sort(key=lambda x: x["date"])
    for no, issue in enumerate(issues, start=1):
        issue["issue_no"] = no
        y, m, d = issue["date"].split("-")
        import datetime

        wd = datetime.date(int(y), int(m), int(d)).weekday()
        issue["date_cn"] = f"{y} 年 {int(m)} 月 {int(d)} 日 · 星期{WEEKDAYS[wd]}"
    return issues


def main() -> None:
    issues = load_issues()
    if not issues:
        raise SystemExit("[build] data/daily/ 里没有任何一期,先生成数据")

    env = Environment(
        loader=FileSystemLoader(ROOT / "scripts" / "templates"),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    issue_tpl = env.get_template("issue.html")
    archive_tpl = env.get_template("archive.html")

    if SITE.exists():
        shutil.rmtree(SITE)
    (SITE / "issues").mkdir(parents=True)

    for i, issue in enumerate(issues):
        html = issue_tpl.render(
            issue=issue,
            prev=issues[i - 1] if i > 0 else None,
            next=issues[i + 1] if i < len(issues) - 1 else None,
            is_latest=(i == len(issues) - 1),
            root="../",
        )
        (SITE / "issues" / f"{issue['date']}.html").write_text(html, encoding="utf-8")

    latest = issues[-1]
    (SITE / "index.html").write_text(
        issue_tpl.render(
            issue=latest,
            prev=issues[-2] if len(issues) > 1 else None,
            next=None,
            is_latest=True,
            root="",
        ),
        encoding="utf-8",
    )
    (SITE / "archive.html").write_text(
        archive_tpl.render(issues=list(reversed(issues)), root=""), encoding="utf-8"
    )
    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    print(f"[build] {len(issues)} 期已生成 -> {SITE}")


if __name__ == "__main__":
    main()
