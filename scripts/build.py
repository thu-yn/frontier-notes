#!/usr/bin/env python3
"""把 data/daily/*.json 渲染成静态站点 site/。

- site/index.html          最新一期
- site/issues/<date>.html  每期归档页
- site/archive.html        往期目录
"""

import hashlib
import json
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
STATIC = ROOT / "scripts" / "static"

WEEKDAYS = "一二三四五六日"

# 领域 id → (显示名, 标签色)。与 prompts/summarize.md 的领域体系保持一致
DOMAINS = {
    "ai": ("AI·大模型", "#2440b3"),
    "embodied": ("具身智能", "#0d7a68"),
    "chip": ("半导体", "#8a5a12"),
    "bio": ("生物医学", "#a83a52"),
    "quantum": ("量子计算", "#6b3fa0"),
    "ai4s": ("AI4Science", "#0b6f8a"),
    "energy": ("新能源", "#3f7d20"),
    "space": ("商业航天", "#4a5a8a"),
}


def issue_domains(issue: dict) -> list[str]:
    """本期实际出现过的领域,按 DOMAINS 定义顺序排,供筛选条使用。"""
    seen = {
        item.get("domain", "ai")
        for key in ("papers", "repos", "news", "research_ideas")
        for item in issue.get(key, [])
    }
    return [d for d in DOMAINS if d in seen]


def item_id(item: dict, section: str, date: str) -> str:
    """给每条内容生成稳定 ID:{date}:{section}:{url 的 sha1 前 10 位}(url 缺失时用标题)。"""
    key = (
        item.get("url")
        or item.get("title")
        or item.get("title_zh")
        or item.get("name")
        or ""
    )
    h = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
    return f"{date}:{section}:{h}"


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
    env.globals["DOMAINS"] = DOMAINS
    env.globals["issue_domains"] = issue_domains
    env.globals["item_id"] = item_id
    issue_tpl = env.get_template("issue.html")
    archive_tpl = env.get_template("archive.html")
    likes_tpl = env.get_template("likes.html")
    research_tpl = env.get_template("research.html")

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

    # 「我的喜欢」页:静态壳,内容由 likes.js 客户端实时拉 likes.json 渲染
    (SITE / "likes.html").write_text(
        likes_tpl.render(root=""), encoding="utf-8"
    )

    # 研究方向归档页:汇总所有期的 research_ideas,按日期倒序分组
    idea_issues = [i for i in reversed(issues) if i.get("research_ideas")]
    seen = {
        idea.get("domain", "ai")
        for i in idea_issues
        for idea in i["research_ideas"]
    }
    idea_domains = [d for d in DOMAINS if d in seen]
    (SITE / "research.html").write_text(
        research_tpl.render(
            idea_issues=idea_issues, idea_domains=idea_domains, root=""
        ),
        encoding="utf-8",
    )

    # 前端静态资源:build 会 rmtree(SITE),所以每次从 scripts/static 复制进来
    shutil.copy(STATIC / "likes.js", SITE / "likes.js")

    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    print(f"[build] {len(issues)} 期已生成 -> {SITE}")


if __name__ == "__main__":
    main()
