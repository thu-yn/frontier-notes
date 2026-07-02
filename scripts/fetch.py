#!/usr/bin/env python3
"""每日抓取原始数据:HF 论文榜、GitHub trending、科技资讯 RSS。

产出 data/raw/YYYY-MM-DD.json,供 Claude 总结成 data/daily/YYYY-MM-DD.json。
日期一律使用北京时间。
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import requests

ROOT = Path(__file__).resolve().parent.parent
CST = timezone(timedelta(hours=8))

UA = {"User-Agent": "frontier-notes-bot (personal daily digest; contact: repo issues)"}

NEWS_FEEDS = [
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("Ars Technica AI", "https://arstechnica.com/ai/feed/"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
]

# HN 上和 AI/系统/开源相关的关键词,用于粗筛,精筛交给 Claude
HN_KEYWORDS = re.compile(
    r"\b(ai|llm|gpt|claude|gemini|deepseek|qwen|llama|mistral|openai|anthropic|"
    r"model|agent|transformer|diffusion|rag|inference|cuda|open.?source)\b",
    re.I,
)


def today_cst() -> str:
    return datetime.now(CST).strftime("%Y-%m-%d")


def fetch_hf_papers(limit: int = 40) -> list[dict]:
    """Hugging Face daily papers 榜单,社区投票筛过,信噪比高。"""
    r = requests.get(
        "https://huggingface.co/api/daily_papers",
        params={"limit": limit},
        headers=UA,
        timeout=30,
    )
    r.raise_for_status()
    papers = []
    for item in r.json():
        p = item.get("paper") or {}
        arxiv_id = p.get("id", "")
        papers.append(
            {
                "arxiv_id": arxiv_id,
                "title": (p.get("title") or "").strip(),
                "abstract": (p.get("summary") or "").strip(),
                "upvotes": p.get("upvotes", 0),
                "authors": [a.get("name", "") for a in (p.get("authors") or [])][:8],
                "url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "",
                "hf_url": f"https://huggingface.co/papers/{arxiv_id}" if arxiv_id else "",
            }
        )
    papers.sort(key=lambda x: x["upvotes"], reverse=True)
    return papers


def fetch_github_trending(top_n: int = 20) -> list[dict]:
    """解析 trending 页面拿仓库名和今日新增 star,再用 API 补齐详情。"""
    r = requests.get("https://github.com/trending?since=daily", headers=UA, timeout=30)
    r.raise_for_status()
    html = r.text

    # 每个条目形如 <h2 class="h3 lh-condensed"> ... <a href="/owner/repo" ...>
    names = re.findall(r'<h2 class="h3 lh-condensed">\s*<a\s[^>]*href="/([^/"]+/[^/"]+)"', html)
    stars_today = dict(
        zip(names, re.findall(r"([\d,]+) stars? today", html))
    )  # 顺序与条目一致,数量可能略少,缺了不致命

    token = os.environ.get("GITHUB_TOKEN", "")
    api_headers = {**UA, "Accept": "application/vnd.github+json"}
    if token:
        api_headers["Authorization"] = f"Bearer {token}"

    repos = []
    for name in names[:top_n]:
        entry = {"name": name, "url": f"https://github.com/{name}", "stars_today": stars_today.get(name, "")}
        try:
            d = requests.get(f"https://api.github.com/repos/{name}", headers=api_headers, timeout=20).json()
            entry.update(
                {
                    "description": d.get("description") or "",
                    "stars": d.get("stargazers_count", 0),
                    "language": d.get("language") or "",
                    "topics": (d.get("topics") or [])[:6],
                }
            )
        except requests.RequestException:
            pass  # 详情拿不到就只留名字和链接
        repos.append(entry)
    return repos


def fetch_news(hours: int = 36) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    items = []

    for source, url in NEWS_FEEDS:
        try:
            feed = feedparser.parse(url, request_headers=UA)
        except Exception:
            continue
        for e in feed.entries[:15]:
            published = None
            for key in ("published_parsed", "updated_parsed"):
                if getattr(e, key, None):
                    published = datetime(*getattr(e, key)[:6], tzinfo=timezone.utc)
                    break
            if published and published < cutoff:
                continue
            summary = re.sub(r"<[^>]+>", "", getattr(e, "summary", ""))[:600]
            items.append(
                {
                    "source": source,
                    "title": getattr(e, "title", "").strip(),
                    "url": getattr(e, "link", ""),
                    "published": published.isoformat() if published else "",
                    "summary": summary.strip(),
                }
            )

    # Hacker News 头版里 AI 相关的高分帖
    try:
        r = requests.get(
            "https://hn.algolia.com/api/v1/search",
            params={"tags": "front_page", "hitsPerPage": 60},
            headers=UA,
            timeout=30,
        )
        for hit in r.json().get("hits", []):
            title = hit.get("title") or ""
            if not HN_KEYWORDS.search(title):
                continue
            items.append(
                {
                    "source": "Hacker News",
                    "title": title,
                    "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                    "published": hit.get("created_at", ""),
                    "summary": f"HN {hit.get('points', 0)} 分 / {hit.get('num_comments', 0)} 评论",
                    "hn_url": f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                }
            )
    except requests.RequestException:
        pass

    return items


def main() -> None:
    date = today_cst()
    out = ROOT / "data" / "raw" / f"{date}.json"

    sections, errors = {}, {}
    for key, fn in [("papers", fetch_hf_papers), ("repos", fetch_github_trending), ("news", fetch_news)]:
        try:
            sections[key] = fn()
        except Exception as exc:  # 单个源挂掉不阻塞整期
            sections[key] = []
            errors[key] = f"{type(exc).__name__}: {exc}"

    payload = {
        "date": date,
        "fetched_at": datetime.now(CST).isoformat(),
        "errors": errors,
        **sections,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"[fetch] {date}: {len(sections['papers'])} papers, "
        f"{len(sections['repos'])} repos, {len(sections['news'])} news -> {out}"
    )
    if errors:
        print(f"[fetch] 部分源失败: {errors}", file=sys.stderr)
    if not any(sections.values()):
        sys.exit(1)  # 全部失败才算失败


if __name__ == "__main__":
    main()
