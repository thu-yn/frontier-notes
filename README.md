# 前沿手记 Frontier Notes

每天早晨自动出版的 AI 前沿摘录:论文(HF Daily Papers)、开源仓库(GitHub Trending)、科技资讯(多源 RSS + Hacker News),由 Claude 在 GitHub Actions 里筛选、总结并写编者按,静态站点发布到 GitHub Pages。

## 工作原理

```
每天 06:30 (北京时间) GitHub Actions 触发
  └─ scripts/fetch.py        抓取原始数据 → data/raw/<date>.json
  └─ claude-code-action      按 prompts/summarize.md 编辑 → data/daily/<date>.json
  └─ scripts/build.py        渲染静态页面 → site/
  └─ 提交 data/daily + 部署 GitHub Pages
```

历史每期数据都在 `data/daily/`,git 即归档。

## 首次部署

1. 推送本仓库到 GitHub。
2. 仓库 **Settings → Pages → Source** 选 **GitHub Actions**。
3. 本地终端运行 `claude setup-token`,把生成的 token 存到仓库
   **Settings → Secrets and variables → Actions** 里,名字为 `CLAUDE_CODE_OAUTH_TOKEN`
   (用 Claude Pro/Max 订阅额度;如果想用 API key 计费,改用 secret `ANTHROPIC_API_KEY`
   并把 workflow 里的 `claude_code_oauth_token` 换成 `anthropic_api_key`)。
4. **Actions** 页手动触发一次「每日出版」验证全流程。

## 本地调试

```bash
pip install -r requirements.txt
python scripts/fetch.py    # 抓当天原始数据
# (总结这步平时由 CI 里的 Claude 完成;本地可手动写 data/daily/<date>.json)
python scripts/build.py    # 生成 site/
open site/index.html
```

## 调口味

- **选题标准 / 文风**:改 `prompts/summarize.md`
- **资讯来源**:改 `scripts/fetch.py` 里的 `NEWS_FEEDS` 和 `HN_KEYWORDS`
- **页面设计**:改 `scripts/templates/`(base.html 里是全部样式)
- **发布时间**:改 `.github/workflows/daily.yml` 里的 cron(注意是 UTC)
