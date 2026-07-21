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
KANJI_DIGITS = "〇一二三四五六七八九"


def _kanji_md(n: int) -> str:
    """月/日数字转汉字纪年写法(1-31,不带前导零),如 7→七、10→十、21→二十一。"""
    if n < 10:
        return KANJI_DIGITS[n]
    if n == 10:
        return "十"
    tens, ones = divmod(n, 10)
    s = ("十" if tens == 1 else KANJI_DIGITS[tens] + "十")
    return s + (KANJI_DIGITS[ones] if ones else "")

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


# 可视化组件目录:每个条目在 /gallery.html 里渲染一块示例,也是给「每日一理」
# 选型的参考清单。新增一个组件 = 在 viz.js 里实现 + 这里补一条示例。
GALLERY_DEMOS = [
    {
        "id": "cobweb",
        "title": "迭代蛛网图",
        "use": "不动点 / 迭代收敛 / 压缩映射。拖动初始点 x₀ 看 xₙ₊₁=f(xₙ) 收敛到不动点。"
        "参数:fn(表达式)、x0(初值)、xmin/xmax(视窗)、iterations(迭代步数)。",
        "params": {"fn": "cos(x)", "x0": 2.5, "xmin": -0.2, "xmax": 3.3, "iterations": 14},
    },
    {
        "id": "fourier",
        "title": "傅里叶级数逼近",
        "use": "傅里叶级数 / 信号分解 / 收敛与吉布斯现象。拖「项数 N」滑块看部分和如何逼近周期波,"
        "跳变处的过冲永不消失。参数:wave(square/sawtooth/triangle)、terms(初始项数)、maxTerms(滑块上限)。",
        "params": {"wave": "square", "terms": 5, "maxTerms": 30},
    },
    {
        "id": "gradient",
        "title": "梯度下降",
        "use": "优化 / 迭代下山 / 学习率的影响。拖起点或调「学习率 η」滑块看轨迹如何滚向极小值,"
        "η 太大就震荡甚至发散。导数用数值差分,任意 fn 都能跑。"
        "参数:fn、x0(起点)、lr(初始学习率)、maxLr(滑块上限)、xmin/xmax、steps(迭代步数)。",
        "params": {"fn": "0.5*x*x - cos(3*x)", "x0": 2.4, "lr": 0.1, "maxLr": 1.2,
                   "xmin": -3, "xmax": 3, "steps": 24},
    },
    {
        "id": "vectorfield",
        "title": "向量场 / 相图",
        "use": "微分方程 / 动力系统 / 相轨迹。示例是带阻尼的单摆相图,拖动种子点看 RK4 积分出的"
        "流线如何盘旋进平衡点。参数:fx、fy(关于 x,y 的分量)、xmin/xmax/ymin/ymax、density(箭头密度)、"
        "seedX/seedY(种子点)、steps/dt(积分步数与步长)。",
        "params": {"fx": "y", "fy": "-sin(x)-0.3*y", "xmin": -3.6, "xmax": 3.6,
                   "ymin": -3, "ymax": 3, "density": 15, "seedX": -2.5, "seedY": 2.5,
                   "steps": 700, "dt": 0.02},
    },
    {
        "id": "riemann",
        "title": "黎曼和 / 定积分",
        "use": "定积分 / 数值积分 / 极限。拖「矩形数 n」滑块看黎曼和如何逼近曲线下面积,"
        "文本实时对比当前和与真积分。参数:fn、a/b(积分区间)、n(初始矩形数)、maxN(滑块上限)、"
        "rule(left/right/mid 取样)、xmin/xmax(视窗)。",
        "params": {"fn": "0.6*sin(x)+1.4", "a": 0, "b": 5, "n": 6, "maxN": 60,
                   "rule": "left", "xmin": -0.4, "xmax": 5.5},
    },
]


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
        issue["date_cn_kanji"] = (
            "".join(KANJI_DIGITS[int(c)] for c in y)
            + "年" + _kanji_md(int(m)) + "月" + _kanji_md(int(d)) + "日"
        )
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
    gallery_tpl = env.get_template("gallery.html")

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

    # 可视化组件目录(开发/参考页,不挂主导航)
    (SITE / "gallery.html").write_text(
        gallery_tpl.render(demos=GALLERY_DEMOS, root=""), encoding="utf-8"
    )

    # 前端静态资源:build 会 rmtree(SITE),所以每次从 scripts/static 复制进来
    shutil.copy(STATIC / "likes.js", SITE / "likes.js")
    # 每日一理的交互可视化:框架 viz.js + 自托管的 JSXGraph(vendor 整目录)
    shutil.copytree(STATIC / "viz", SITE / "viz")

    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    print(f"[build] {len(issues)} 期已生成 -> {SITE}")


if __name__ == "__main__":
    main()
