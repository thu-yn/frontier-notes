# 前沿手记 Frontier Notes

每天早晨自动出版的 AI 前沿摘录:论文(HF Daily Papers)、开源仓库(GitHub Trending)、科技资讯(多源 RSS + Hacker News),由 GPT-6.1 Sol(Max 推理)在私有 GitHub Actions 里实时搜索、筛选、总结并写编者按,静态站点发布到 GitHub Pages。

每期还附 2–3 条「今日可做的研究点」——从定向抓取的 arXiv 新论文里提炼单人可完成(1–2 卡量级)的研究切入点,历史点子汇总在「研究方向」页;每张卡片可点 ♥ 收藏,收藏直接写回仓库 `data/likes.json`,在「喜欢」页跨设备查看。

每期另有两个动脑筋的固定栏目:

- **每日一理**——讲透一个经典数学定理(说的是什么、由来、怎么推出来、能用在哪),公式由 KaTeX 排版,多数还配一块能拖着玩的交互图。
- **思想碰撞**——拿一个数学或物理理论去撞点云处理的一个具体痛点,给出 3–4 条带量级估计的可行思路(复杂度、存储、算法优化等维度),附最小验证路径、已有工作核查,以及一句「最可能栽在哪」。理论侧的灵感来自每天定向抓的数学/物理 arXiv 新提交。历史碰撞汇总在「思想碰撞」页。

## 工作原理

```
每天 03:00 (北京时间) 私有出版仓库 GitHub Actions 触发
  └─ scripts/fetch.py        抓取原始数据 → data/raw/<date>.json
  └─ scripts/summarize.py    Codex 订阅登录 + gpt-6.1-sol / max + 实时搜索
                             按 prompts/summarize.md 编辑 → data/daily/<date>.json
  └─ scripts/validate.py     校验日期、必需栏目和内容结构
  └─ scripts/build.py        渲染静态页面 → site/
  └─ 提交 data/daily 到公开仓库 → 触发本仓库构建、部署 GitHub Pages
```

历史每期数据都在 `data/daily/`,git 即归档。

## 首次部署

1. 推送本仓库到 GitHub。
2. 仓库 **Settings → Pages → Source** 选 **GitHub Actions**。
3. 每日抓取和编辑在私有仓库 [`frontier-notes-publisher`](https://github.com/thu-yn/frontier-notes-publisher) 运行,使用独立的 ChatGPT/Codex 订阅登录,无需 OpenAI API key。本公开仓库只负责校验、构建和 Pages 部署,不保存订阅凭证。
4. 私有仓库每次恢复加密的登录状态,由 Codex 自动刷新,再加密回写供下次使用;任务串行执行,与桌面登录分开。凭证被撤销或无法刷新时需重新登录。部署配置和恢复说明见私有仓库 README。
5. 在私有仓库 **Actions** 页手动触发「每日编辑与出版」验证全流程。原 `CLAUDE_CODE_OAUTH_TOKEN` 已不再使用。

## 喜欢按钮(♥)的一次性配置

站点是纯静态页面,点「喜欢」时由浏览器直接调 GitHub API 写 `data/likes.json`,需要一个只授权本仓库的 fine-grained PAT:

1. GitHub → **Settings → Developer settings → Fine-grained personal access tokens → Generate new token**。
2. Repository access 只选本仓库;Permissions 里 **Contents** 给 **Read and write**,其余不动。
3. 打开站点任意页,点任意 ♥(或页脚的 ⚙),把 token 粘进弹出的设置框。token 只存在浏览器 localStorage 里,换浏览器/设备需要重新粘一次(收藏数据本身在仓库里,跨设备一致)。

## 本地调试

```bash
pip install -r requirements.txt
python scripts/fetch.py    # 抓当天原始数据
codex login               # 本地使用自己的订阅登录,不复制私有 CI 的登录
python scripts/summarize.py # Sol 6.1 Max 实时搜索、编辑、校验
python scripts/validate.py  # 独立校验当天期刊
python scripts/build.py    # 生成 site/
open site/index.html
```

## 调口味

- **选题标准 / 文风**:改 `prompts/summarize.md`
- **资讯来源**:改 `scripts/fetch.py` 里的 `NEWS_FEEDS` 和 `HN_KEYWORDS`
- **研究点方向**:改 `scripts/fetch.py` 里的 `RESEARCH_QUERIES`(查询串依据见 `docs/research-radar-2026-07.md`)
- **思想碰撞的理论口味**:改 `scripts/fetch.py` 里的 `THEORY_QUERIES`(数学/物理 arXiv 分支);碰撞怎么写、点云侧靶子有哪些,改 `prompts/summarize.md` 的「思想碰撞」一节
- **页面设计**:改 `scripts/templates/`(base.html 里是全部样式)。每期页与「思想碰撞」归档页共用 `macros.html` 里的 `crossover_block` 宏,改版式只需改那一处
- **发布时间**:改私有出版仓库 `.github/workflows/daily.yml` 里的 cron(注意是 UTC);本仓库在期刊推送后自动部署
