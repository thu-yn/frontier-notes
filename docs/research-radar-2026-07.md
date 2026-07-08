# 单人可做研究点雷达（2026-07 调研）

服务于每日「研究点」板块的背景调研：各方向单人可完成的活跃子方向、`scripts/fetch.py` 里 `RESEARCH_QUERIES` 各查询串的依据与实测命中量、以及给每日生成 prompt 的写作校准样例。查询串均通过 `https://export.arxiv.org/api/query` 实测（2026-07-01 至 2026-07-08 命中量）。

约束前提：单人独立研究者，算力 1–2 张 GPU（微调/推理量级），排除预训练、大规模标注、真机机器人集群。

---

## 1. 3D 视觉 / 点云处理

**活跃且单人可做的子方向：**

1. **冻结基础模型做下游适配（Adapter/LoRA on VGGT / Sonata）**——VGGT（CVPR2025 最佳论文，前馈式一次性推理相机位姿/点图/深度）和 Sonata（自监督点表征）都已开源权重，冻结主干只训小适配头，单张 A100 几小时内可完成一个下游任务。
2. **点云 + LLM/VLM 空间推理小型化**——PointLLM、Point-3D LLM 已把点云 token 化接入 LLM，但多为 7B 级全量训练；机会在 LoRA/Prompt-tuning 只微调桥接层，蒸馏到小模型做垂类任务。
3. **前馈式 3D 感知的失效模式修补**——综述明确指出 VGGT/AnySplat 类在高重叠视角、细粒度细节、跨域上系统性失效；选定一个具体失效场景做轻量修补即可成文。
4. **开放词汇/小样本点云分割**——用 2D 基础模型（SAM2/Grounding-DINO）反投影生成伪标签，训练轻量 3D 分割头，复用现成 2D 能力。
5. **点云补全的评测 gap**——传统 benchmark（ShapeNet 系）已饱和，「补全用于机器人操作/动力学」是新交叉点，可做小型 benchmark + baseline。

**查询串：**
- 主：`cat:cs.CV AND abs:"point cloud"` — ~3.6 篇/天，覆盖全子任务，需二次过滤。
- 辅：`cat:cs.CV AND abs:"point cloud" AND (abs:LLM OR abs:"large language model" OR abs:"vision-language")` — ~0.3 篇/天，量少但极准。

**校准样例（paper 型）：** VGGT 冻结特征驱动的小样本户外点云开放词汇分割适配器。based_on: VGGT (arXiv:2503.11651, github.com/facebookresearch/vggt) + SAM2 伪标签。why_now: VGGT 2025 年中开源、围绕它的下游适配论文才刚出现，户外开放词汇分割切口尚无专门工作。feasibility: 主干冻结、只训轻量分割头，24GB 消费卡可跑，2–3 周。route: ① VGGT 在 SemanticKITTI/nuScenes 子集上推理并缓存特征与点图；② SAM2+CLIP 生成开放词汇伪标签反投影到点云；③ 训一个 2–3 层 MLP + 跨帧融合的适配头；④ 与从零训练的 3D 分割网络对比；⑤ 失效 case 分析成文。risk: 户外点图精度存疑需先小样本验证；伪标签噪声需置信度过滤;需选窄场景差异化避免撞车。

## 2. 具身智能 / 机器人学习

**活跃且单人可做的子方向：**

1. **训练无关的 VLA 推理加速**——如 "Training-Free Acceleration for VLA with Action Caching and Refinement"（2026-07），无需微调数据，拿开源权重做推理侧改造，LIBERO/SIMPLER 仿真单卡可评测。
2. **面向 VLA 的模仿学习数据筛选/加权（data-centric）**——如 SIEVE（2026-07），用开源 VLA + Open X-Embodiment/DROID 公开子集做数据筛选算法对比，无需采集数据。
3. **LoRA/Adapter 微调开源 VLA 做垂类任务**——Xiaomi-Robotics-0（arXiv:2602.12684）、π0 系列已开源权重，配合 ManiSkill/RoboCasa/Genesis 仿真验证。
4. **VLA 评测/benchmark 工程**——评测碎片化（各论文各用各的环境和 metric），轻量统一评测 harness 是工程空白。
5. **Latent Action Model / 无动作标签信号复用**——如 ALAM，从视频学 latent action 再对齐少量真实标签，低数据需求。

**查询串：**
- 主：`cat:cs.RO AND (abs:"vision-language-action" OR abs:VLA OR abs:"manipulation policy")` — ~6.9 篇/天。
- 辅：`cat:cs.RO AND (abs:"sim-to-real" OR abs:sim2real OR abs:"robot learning benchmark" OR abs:"manipulation benchmark")` — ~2.3 篇/天，聚焦仿真可复现工作。

**校准样例（paper 型）：** 训练无关动作缓存加速方法的复现与跨底座扩展。based_on: "Training-Free Acceleration for VLA with Action Caching and Refinement"（2026-07 新提交）+ OpenVLA-7B / Xiaomi-Robotics-0。why_now: 论文刚提交无跟进工作，开源 VLA 权重齐全，仿真 benchmark 单卡可跑，把方法迁移到另一个底座验证泛化性本身就是可发表的小贡献。feasibility: 单张 A100 40GB，全程仿真，2–3 周。route: ① 部署 LIBERO/SIMPLER + OpenVLA 官方权重跑通基线；② 实现动作缓存+精炼模块并复现原文结果；③ 迁移到架构不同的 Xiaomi-Robotics-0 验证模型无关性；④ 扫描任务复杂度下的加速比-成功率帕累托边界；⑤ 开源代码投 workshop。risk: 原文未开源则复现细节需猜测；跨架构迁移可能非平凡；同期撞车需挑差异化角度（如长程任务）。

## 3. LLM 应用层 / 高效方法

**活跃且单人可做的子方向：**

1. **KV Cache 压缩在 Agent 长程负载上的评测与轻量改进**——关注点正从「通用长文本」转向「agent 多轮工具调用」（如 IntentKV, arXiv:2606.09916），7B–13B 开源模型 + vLLM/SGLang 单卡可跑。
2. **Agent 评测基础设施补位**——HAL（arXiv:2510.11977）指出 agent 评测基础设施缺失，可做聚焦某垂类的轻量评测框架/排行榜。
3. **低秩/稀疏 PEFT 新变体**——如 Localized LoRA-MoE，用现成 PEFT 库做小规模架构消融。
4. **RAG 的检索证据控制/多跳推理**——如 DynaKRAG，基于开源 pipeline 在公开多跳 QA 数据集做算法对比。
5. **Test-Time Scaling 的算力预算效率评测**——固定预算下不同 TTS 策略的系统对比，实用型论文或工具。

**查询串：**
- 主：`cat:cs.CL AND (abs:"retrieval-augmented" OR abs:RAG OR abs:"parameter-efficient" OR abs:LoRA)` — ~5.7 篇/天。
- 辅：`cat:cs.CL AND (abs:"LLM agent" OR abs:"tool use" OR abs:"inference acceleration" OR abs:"KV cache")` — ~4.0 篇/天（两条有重叠，fetch 已按 arxiv_id 去重）。

**校准样例（paper 型）：** 多轮 Agent 负载下 KV Cache 剪枝策略的统一评测与简单改进。based_on: IntentKV (arXiv:2606.09916)，基线 H2O、SnapKV。why_now: 2026 上半年 KV cache 研究重心转向 agent 场景，但各方法在 agent 负载下的公平横向对比是空白。feasibility: 单张 A100 80GB 跑 7B–14B + vLLM，trace 用公开 agent benchmark，约 3 周。route: ① 选 2–3 个多轮 benchmark 统一 trace 格式；② vLLM 复现三种剪枝策略；③ 相同压缩率下统一测成功率/延迟/显存；④ 按任务类型分析敏感性并做启发式改进；⑤ 开源 harness + 短文（harness 本身也是攒 star 的工具）。risk: 部分方法无官方代码需标注复现版本；trace 统一工程量不小；靠「公平评测」定位而非「最优方法」取胜。

## 4. 生成模型 / 3D 重建

**活跃且单人可做的子方向：**

1. **前馈式 3DGS 的细节修补/域适配**——AnySplat（arXiv:2505.23716）等推理快但细节弱，针对具体失效场景做 LoRA 级微调或后处理精修。
2. **前馈 3DGS/NeRF 统一评测（工具向）**——AnySplat/AnchorSplat/VGGT 各用各的评测协议，缺统一 benchmark 工具。
3. **扩散先验修复 3D 重建伪影**——ConFixGS（arXiv:2605.09688，驾驶场景）证明「扩散模型当后处理修复器」可行，换场景复现验证泛化即是贡献。
4. **3DGS/NeRF 在机器人感知的落地**——现成前馈模型直接喂下游任务（抓取位姿、导航建图），做系统集成+评测。
5. **扩散 3D 生成的小样本个性化**——Trellis 系列已开源，做少样本个性化/风格迁移，偏工具/demo 型。

**查询串：**
- 主：`cat:cs.CV AND (abs:"3D Gaussian Splatting" OR abs:"neural radiance field" OR abs:NeRF)` — ~3.6 篇/天。
- 辅：`cat:cs.CV AND abs:diffusion AND (abs:"3D reconstruction" OR abs:"3D generation")` — ~0.6 篇/天，交叉专项。

**校准样例（paper 型）：** 置信度感知扩散先验修复 AnySplat 室内小物体细节（跨域复现 ConFixGS）。based_on: AnySplat (arXiv:2505.23716) + ConFixGS (arXiv:2605.09688)。why_now: ConFixGS 2026-05 才提出且只验证了驾驶场景，室内小物体（反光、薄结构）迁移是空白。feasibility: 24GB 卡可跑（AnySplat 前馈很轻，开销在扩散采样），约 3 周。route: ① AnySplat 在 ScanNet++/Replica 子集跑基线收集失效 case；② 复现置信度估计模块迁移到室内；③ 接开源 inpainting 扩散模型只修低置信度区域；④ 标准协议下三方对比量化增益；⑤ 开源投 3DV/BMVC 短文或技术报告。risk: 跨域先验失配可能需少量 LoRA 域适配；置信度阈值需重标定；增益边际小则转向「系统性失效分析」定位。

## 5. 轻量快产出型（GitHub 工具/库）

**活跃且单人可做的类型：**

1. **统一评测 harness / 排行榜**——历史上最容易攒 star 的类型（类比 lm-evaluation-harness、Chatbot Arena）。
2. **新基座模型的一键推理/微调脚手架**——窗口期是模型发布后 1–4 周。
3. **数据格式转换/清洗 CLI**——机器人与点云数据集格式碎片化严重（OXE、DROID、ScanNet 各一套），有持续需求。
4. **论文追踪/信号提取元工具**。
5. **细分领域的复现状态追踪板**（论文-代码可复现性-实测指标）。

**查询串：** `(cat:cs.CV OR cat:cs.CL OR cat:cs.LG) AND abs:benchmark AND abs:"open-source"` — ~4.4 篇/天。信噪比一般，作为「新数据集/新基座/新基准」信号源使用，建议与 GitHub Trending / HF Papers 交叉验证——工具型机会往往由「模型刚开源但生态没跟上」触发。

**校准样例（repo 型）：** feedforward-3d-bench——前馈式 3D 重建方法统一评测工具。based_on: VGGT / AnySplat / AnchorSplat (arXiv:2604.07053) + 综述 arXiv:2507.14501 指出的评测协议不统一问题。why_now: 前馈 3D 重建日均 ~3.6 篇新论文但各用各的数据切分与 metric，没有 lm-evaluation-harness 式的标准工具，各模型推理代码权重都已公开，做接入层门槛低。feasibility: 核心是写 wrapper 而非训练，消费卡即可，2–4 周出 v0.1。route: ① 列出近一年开源推理代码+权重的方法清单并确认 license；② 设计统一 I/O 接口，逐模型写 wrapper；③ 集成 2–3 个公认数据集与标准 metric 并校验能复现各论文自报数字；④ 脚本定期跑全量评测生成 README 内嵌 leaderboard；⑤ 发布 + 博客/HN 帖引原作者提交接入 PR 形成社区飞轮。risk: 各模型 CUDA/torch 依赖冲突需容器隔离；复现数字对不上需诚实标注「实测 vs 自报」；原作者出官方 leaderboard 会稀释独特性，靠更新频率做护城河。

---

## 每日研究点的选题标准（已同步进 prompts/summarize.md）

**纳入：** 刚开源权重且单卡可推理的新基座；新数据集/新 benchmark 且明示现有方法 gap；training-free / plug-and-play 方法（迁移验证泛化即是低风险扩展）；评测协议不统一/缺 harness/缺开源实现的工程空白；仿真可完整复现的机器人工作；可用 LoRA/Adapter/蒸馏等参数高效方式介入的开源大模型工作。

**排除：** 预训练及其消融（哪怕「小规模」）；多机分布式才成立的效率问题；需真机集群或大规模数据采集；纯理论无实验锚点；核心贡献依赖闭源 API；数据/权重不可获取或 license 禁止复现发布。

**叠加信号：** 「话题热度（arXiv 命中量）」×「摘要提到 code/weights released（复现门槛低）」交叉筛出的候选质量最高。

## 主要来源

- VGGT: arXiv:2503.11651 / github.com/facebookresearch/vggt
- AnySplat: arXiv:2505.23716；AnchorSplat: arXiv:2604.07053；ConFixGS: arXiv:2605.09688
- Feed-Forward 3D 综述: arXiv:2507.14501
- Xiaomi-Robotics-0: arXiv:2602.12684；ALAM: arXiv:2605.10819
- IntentKV: arXiv:2606.09916；HAL: arXiv:2510.11977
- CitySeg: arXiv:2508.09470；Point-3D LLM (Apple ML Research)
