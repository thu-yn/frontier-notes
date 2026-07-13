# Design — 前沿手记 Frontier Notes

A locked design system for this site. Every page redesign reads this file before
emitting code. Do not regenerate per page — extend or amend this file when the
system needs to grow.

产出方式：Hallmark `redesign`（multi-page）。实现载体是 `scripts/templates/base.html`
内联 CSS（`:root` token 块为 live copy），`tokens.css`（项目根）为可移植副本，两处必须同步。

## Genre

modern-minimal（自 editorial/newsprint 切换而来；旧版的网格纸背景、红边线、楷体、
黄荧光笔、波浪下划线全部移除，不得回流）。

## Macrostructure family

- 每期页（index.html / issues/*.html）：**Ecosystem Index** — 栏目即 rail
  （今日研究点 / 论文 / 开源 / 资讯），每个 rail 一条 rail-titled band；无 display 大字 hero，
  报头收敛为一行 stamp + 期号。
- 索引页（archive.html）：**Index-First** — 页面即链接列表，hairline 分行。
- 汇总页（research.html / likes.html）：**Index-First** 变体 — 按日期分组的条目列表。

## Theme — Cobalt（CJK 内容站改编）

- `--color-paper`      oklch(98.5% 0.004 250)   冷调工程近白，永不 #fff
- `--color-paper-2`    oklch(96.5% 0.006 250)   次级底（chip hover、代码底）
- `--color-ink`        oklch(24% 0.02 258)      标题墨，永不 #000
- `--color-ink-2`      oklch(34% 0.018 257)     正文墨
- `--color-muted`      oklch(50% 0.015 257)     元数据/次要文字
- `--color-rule`       oklch(91% 0.008 255)     hairline
- `--color-rule-2`     oklch(85% 0.01 255)      重一档的边线（nav 底线可用）
- `--color-accent`     oklch(58% 0.20 256)      唯一钴蓝信号色，<5% 视口
- `--color-accent-ink` oklch(98.5% 0.004 250)   钴蓝底上的文字
- `--color-graphite`   oklch(22% 0.016 260)     石墨深带（编者按专用）
- `--color-graphite-ink` oklch(90% 0.01 255)    石墨带上的正文
- `--color-focus`      = accent
- `--mark-wash`        oklch(93% 0.045 256)     `<mark>` 一句话摘要底纹（低饱和钴蓝，非黄）

信号色纪律：钴蓝只出现在——链接 hover 下划线、filter 激活态、编者按标签、
focus ring、领域 chip 激活、极少量 meta 强调。领域体系 8 色（build.py DOMAINS）
降级为：chip 本体中性（mono 小字 + hairline 边框 + muted 墨），领域色仅用于 chip 内
6px 圆点与 filter 激活态背景。禁止 8 色文字满页跑。

## Typography（CJK 约束：中文走系统栈，webfont 只加载 Latin）

- Display: "Space Grotesk"(500/600) + PingFang SC / Noto Sans SC / Microsoft YaHei, weight 600
- Body:    "Inter"(400/500) + PingFang SC / Noto Sans SC / Microsoft YaHei, weight 400
- Mono:    "JetBrains Mono" + ui-monospace + 中文回落体，weight 400/500
- Google Fonts 一条 link（Space Grotesk 500;600 · Inter 400;500 · JetBrains Mono 400;500），
  `display=swap`。
- Letter-spacing：负 tracking（-0.01em~-0.02em）只允许用在纯 Latin 元素（wordmark、mono meta）；
  中文/混排元素 tracking 为 0。mono 标签 UPPERCASE + .06em 只用于纯 Latin 小标。
- 正文 16px / line-height 1.75（中文），meta 0.78rem mono，行长 ≤ 42rem。

## Spacing

4-point named scale（--space-3xs 0.25rem … --space-3xl 7rem，见 tokens.css）。
页面主列 max-width 44rem 居中，与旧版一致；栏目间距 --space-2xl 起。
只准用命名 token，不准写裸值。

## Radii

按钮/输入/chip 6px；卡片（编者按石墨带、token 面板）10px。无 pill，无 0px 直角砖。

## Motion

- Easing: cubic-bezier(0.16, 1, 0.3, 1) 命名 --ease-out；--dur-short: 180ms。
- 无滚动 reveal（阅读页保持排定状态，删除旧版 settle 动画）。
- 保留：♥ heart-pop（一次性 scale）、toast 淡入位移、filter 切换即时无动画。
- prefers-reduced-motion: reduce → 全部静态。

## Microinteractions stance

- 静默成功（♥ 点亮即反馈，toast 只报同步失败/需要配置）。
- hover 提示延迟不做 tooltip 系统；title 属性即可。
- focus-visible：2px 钴蓝 ring，offset 2px，出现无动画。

## CTA voice

本站无营销 CTA。唯一实心钴蓝按钮 = token 面板「保存」；次级按钮 = hairline 边框
transparent 底。链接：正文链接墨色 + hover 钴蓝下划线（underline-offset 3px）。

## 各页固定要素

- Nav（Cobalt 签名条）：通栏贴边，底部 1px --color-rule-2，wordmark「前沿手记」
  Space Grotesk/系统黑体 600 居左，右侧 4 个文字链接（本期 · 研究方向 · 喜欢 · 归档），
  当前页链接钴蓝。移动端允许换行为两行。无 ⌘K（静态站不引入命令面板）。
- 期号 stamp：mono 小字（第 N 期 · 日期 · 星期），置于内容列顶部。
- 编者按：石墨深带卡（--color-graphite 底，10px 圆角），mono 钴蓝小标
  「编者按 EDITOR'S NOTE」，正文 --color-graphite-ink，每页至多一处（页面唯一深色节拍）。
- Footer（Ft2）：hairline rule 之上留 --space-2xl，两行 colophon 小字 + ⚙ 喜欢设置入口，
  mono，muted 墨。

## What pages MUST share

- Nav / Footer / stamp 结构与全部 token。
- 条目卡语法：无边框、hairline 分隔（1px solid --color-rule，不再用 dashed）、
  标题 600、摘要 400、meta mono muted。
- ♥ 按钮、toast、token 面板样式。
- 领域 chip 与 filter-bar 语法。

## What pages MAY differ on

- 每期页有编者按石墨带与 filter-bar；归档页是纯链接列表；研究/喜欢页按日期分组
  （日期组头 = mono 小标 + hairline）。
- 研究点条目允许更结构化的行内标签（为什么现在/可行性/路线/风险），
  风险行用 muted 墨 + 前置「风险」mono 标签，不再用红色斜体。

## 禁止事项（本项目 slop 清单）

- 背景纹理/网格纸、双色边线装饰、楷体/宋体混排、黄色荧光 mark、波浪下划线。
- 渐变文字、玻璃拟态、卡中卡、pill 渐变按钮、纯黑纯白、bounce 动效。
- 斜体标题（含 .orig 原文题名——改 mono 小字，不用 italic）。
- 除钴蓝外的第二信号色（领域色圆点除外）。

## 充实层（2026-07-13 增补：科技感 × 现代中式）

第一版过素，经用户确认增补以下模块。原则：视觉元素必须有真实数据或真实语义做锚点，
科技感来自仪表盘语汇（mono 读数、刻度、状态点），中国审美来自印章/竖排/汉字纪年，
两者都不得引入新颜色（仍只有钴蓝一个信号色）。

1. **方印站标**：钴蓝方形印章（--color-accent 底 + --color-accent-ink 文字，
   「前沿手记」2×2 排布，--radius-xs，约 2.75rem 见方），置于报头；印章即署名，
   页脚可复用小号。这是全站唯一的大面积钴蓝，计入 <5% 预算。
2. **大号报头**（issue 页）：印章 + 「前沿手记」display 大字 + mono 仪表行
   （ISSUE 009 · 2026-07-10 · 星期五，前置 6px 钴蓝状态点）+ 汉字纪年行
   （二〇二六年七月十日，muted）+ tagline。h1 语义落在报头。
   次级页（归档/研究/喜欢）用紧凑版：印章小号 + 页名 display + mono 读数行。
3. **本期速览仪表条**：hairline 边框条（--radius-control），mono 读数：
   研究点 03 · 论文 06 · 开源 03 · 资讯 04 + 本期领域彩点；四角 aria-hidden 的
   「+」蓝图刻度（mono，muted）。数字全部来自当期数据，禁止编造。
4. **条目序号与 hover**：每栏目内 CSS counter 01/02/03 mono muted 前缀于标题；
   .entry:hover 整条切 --color-paper-2 底（负外边距外扩补偿），左缘 2px 钴蓝
   竖标（inset box-shadow 或 ::before）。触屏无 hover 不受影响。
5. **栏目头升级**：中文标题 + 大写 mono Latin 小标（论文 PAPERS/06）+
   向右延伸至列缘的通栏 hairline（flex + 伪元素 flex:1）。
6. **竖排编者按标签**：石墨带内「编者按」竖排（writing-mode: vertical-rl，
   --color-accent-bright），与正文分栏（label 竖栏 + 正文），移动端可回横排。
7. **页脚 statement**：Ft2 之上加一行 statement（如「明早六点半，下一期照常出版。」），
   font-display 稍大字号，ink 墨色。
8. **汉字纪年**：build.py 增加 date_cn_kanji 字段（数字→〇一二三四五六七八九），
   仅报头使用。

仍然禁止：红色印泥色（印章用钴蓝，不引入第二信号色）、仿宣纸纹理、楷体、
任何背景纹理。竖排只用于短标签（≤4 字），正文永不竖排。

## Exports

本项目为无框架静态 Jinja 站点，只维护 tokens.css 一种导出（Tailwind/DTCG/shadcn
格式对本仓库无消费方，刻意省略；将来需要时按 export-formats.md 补）。

### tokens.css

见项目根 `tokens.css`（与 base.html `:root` 同步）。
