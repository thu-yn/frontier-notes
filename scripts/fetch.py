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
    ("IEEE Spectrum", "https://spectrum.ieee.org/feeds/feed.rss"),
    ("The Robot Report", "https://www.therobotreport.com/feed/"),
    ("SemiEngineering", "https://semiengineering.com/feed/"),
    ("Fierce Biotech", "https://www.fiercebiotech.com/rss/xml"),
    ("SpaceNews", "https://spacenews.com/feed/"),
    ("Quanta Magazine", "https://www.quantamagazine.org/feed/"),
    ("Ars Technica Science", "https://arstechnica.com/science/feed/"),
]

# 各领域的 arXiv 分类,每天取最新提交,由 Claude 精筛
ARXIV_DOMAINS = {
    "embodied": "cat:cs.RO",
    "quantum": "cat:quant-ph",
    "bio": "cat:q-bio.BM OR cat:q-bio.GN OR cat:q-bio.QM",
    "energy": "cat:cond-mat.mtrl-sci",
    "chip": "cat:cs.AR OR cat:cs.ET",
    "ai4s": "cat:physics.comp-ph OR cat:cs.CE",
}

# 「每日研究点」用的定向 arXiv 查询:面向单人可做的选题,精筛交给 Claude。
# 查询串均已实测(2026-07,注释为近 7 天日均命中量),背景见 docs/research-radar-2026-07.md
RESEARCH_QUERIES = {
    "pointcloud_3d": 'cat:cs.CV AND abs:"point cloud"',  # ~3.6 篇/天
    "pointcloud_llm": (
        'cat:cs.CV AND abs:"point cloud" AND '
        '(abs:LLM OR abs:"large language model" OR abs:"vision-language")'
    ),  # ~0.3 篇/天,量少但极准
    "robot_learning": (
        'cat:cs.RO AND (abs:"vision-language-action" OR abs:VLA OR abs:"manipulation policy")'
    ),  # ~6.9 篇/天
    "robot_sim_bench": (
        'cat:cs.RO AND (abs:"sim-to-real" OR abs:sim2real OR '
        'abs:"robot learning benchmark" OR abs:"manipulation benchmark")'
    ),  # ~2.3 篇/天,聚焦仿真可复现的工作
    "efficient_llm": (
        'cat:cs.CL AND (abs:"retrieval-augmented" OR abs:RAG OR abs:"parameter-efficient" OR abs:LoRA)'
    ),  # ~5.7 篇/天
    "llm_agent_infer": (
        'cat:cs.CL AND (abs:"LLM agent" OR abs:"tool use" OR '
        'abs:"inference acceleration" OR abs:"KV cache")'
    ),  # ~4.0 篇/天,与上一条有重叠,按 arxiv_id 去重
    "generative_3d": (
        'cat:cs.CV AND (abs:"3D Gaussian Splatting" OR abs:"neural radiance field" OR abs:NeRF)'
    ),  # ~3.6 篇/天
    "diffusion_3d": (
        'cat:cs.CV AND abs:diffusion AND (abs:"3D reconstruction" OR abs:"3D generation")'
    ),  # ~0.6 篇/天,扩散×3D 交叉专项
    "tool_signal": (
        '(cat:cs.CV OR cat:cs.CL OR cat:cs.LG) AND abs:benchmark AND abs:"open-source"'
    ),  # ~4.4 篇/天,捕捉"新基准/新开源但生态空缺"的轻量工具型机会
}

# HN 头版粗筛关键词(覆盖全部领域),精筛交给 Claude
HN_KEYWORDS = re.compile(
    r"\b(ai|llm|gpt|claude|gemini|deepseek|qwen|llama|mistral|openai|anthropic|"
    r"model|agent|transformer|diffusion|rag|inference|cuda|open.?source|"
    r"robot|humanoid|drone|autonomous|"
    r"chip|semiconductor|tsmc|nvidia|asml|euv|fab|risc-v|gpu|"
    r"quantum|qubit|"
    r"protein|crispr|drug|genome|biotech|alphafold|"
    r"battery|fusion|solar|nuclear|grid|"
    r"rocket|satellite|spacex|orbit|starship)\b",
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


def _arxiv_search(query: str, max_results: int) -> list[dict]:
    """跑一次 arXiv 查询,按提交时间倒序返回精简后的论文列表。"""
    r = requests.get(
        "https://export.arxiv.org/api/query",
        params={
            "search_query": query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": max_results,
        },
        headers=UA,
        timeout=45,
    )
    r.raise_for_status()
    feed = feedparser.parse(r.text)
    papers = []
    for e in feed.entries:
        arxiv_id = e.get("id", "").rsplit("/", 1)[-1]
        papers.append(
            {
                "arxiv_id": arxiv_id,
                "title": re.sub(r"\s+", " ", e.get("title", "")).strip(),
                "abstract": re.sub(r"\s+", " ", e.get("summary", ""))[:700].strip(),
                "authors": [a.get("name", "") for a in e.get("authors", [])][:6],
                "url": f"https://arxiv.org/abs/{arxiv_id}",
                "published": e.get("published", ""),
            }
        )
    return papers


def fetch_arxiv_domains(per_domain: int = 25) -> dict[str, list[dict]]:
    """各领域 arXiv 最新提交(HF 榜单以 AI 为主,其他领域靠这里补)。"""
    return {domain: _arxiv_search(query, per_domain) for domain, query in ARXIV_DOMAINS.items()}


def fetch_research(per_query: int = 15) -> dict[str, list[dict]]:
    """「每日研究点」候选:按 RESEARCH_QUERIES 抓 arXiv 最新提交,按方向分组,供 Claude 挑选。

    查询之间有意保留重叠(如 efficient_llm 与 llm_agent_infer),这里按 arxiv_id
    全局去重,先出现的方向保留该论文。
    """
    out: dict[str, list[dict]] = {}
    seen: set[str] = set()
    for name, query in RESEARCH_QUERIES.items():
        papers = []
        for p in _arxiv_search(query, per_query):
            pid = p.get("arxiv_id") or p.get("url")
            if pid in seen:
                continue
            seen.add(pid)
            papers.append(p)
        out[name] = papers
    return out


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
    out.parent.mkdir(parents=True, exist_ok=True)  # data/raw 不入库,CI 检出时不存在

    sections, errors = {}, {}
    for key, fn in [
        ("papers", fetch_hf_papers),
        ("domain_papers", fetch_arxiv_domains),
        ("research_papers", fetch_research),
        ("repos", fetch_github_trending),
        ("news", fetch_news),
    ]:
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
    n_domain = sum(len(v) for v in sections["domain_papers"].values()) if sections["domain_papers"] else 0
    n_research = sum(len(v) for v in sections["research_papers"].values()) if sections["research_papers"] else 0
    print(
        f"[fetch] {date}: {len(sections['papers'])} hf papers, {n_domain} domain papers, "
        f"{n_research} research papers, {len(sections['repos'])} repos, {len(sections['news'])} news -> {out}"
    )
    if errors:
        print(f"[fetch] 部分源失败: {errors}", file=sys.stderr)
    if not any(sections.values()):
        sys.exit(1)  # 全部失败才算失败


if __name__ == "__main__":
    main()
