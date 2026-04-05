---
name: 项目状态
type: state
version: 3.97
date: 2026-04-05
owner: AI（自动维护）
changelog:
  - v3.97 (2026-04-05): SSE步骤实时性与thinking面板体验飞跃 — 后端 [api/main.py](api/main.py) 删除预览阶段重复的 `dispatch_info` + `expert_start` + `expert_step_*` 事件（预览阶段原本在 orchestrator 真实事件之前发送完全相同的事件类型导致前端收到双份），现在只保留 orchestrator 内部发出的唯一事件；前端 [frontend/src/App.tsx](frontend/src/App.tsx) 新增三层 chunk 驱动步骤生成器：(1) 专家分析期每 4 秒从 `expert_*_chunk` 流自动轮换创建标题步骤（战术6阶段/战略6阶段/引擎4阶段预定义标题），(2) 综合等待期从 `thinking` 心跳信号每 4 秒生成过渡步骤（汇总证据链/比对专家分歧/构建讲解框架/准备综合分析），(3) 综合生成期从 `synthesis_chunk` 流驱动额外过渡步骤；`expert_step_start` 事件也参与时间驱动步骤创建弥补 chunk 停止后空白期；真实 SSE 模拟测试证实：步骤从 12 个跃升至 35 个，最大间隔从 47s 降至 4.14s，平均间隔 1.99s，间隔>5s 为 0 个；314 测试全绿，前端构建通过
  - v3.96 (2026-04-05): 协调者思考面板重做为顶尖大模型 thinking 风格 — [frontend/src/components/ThinkingStream.tsx](frontend/src/components/ThinkingStream.tsx) 完全重写：步骤只显示图标+标题（无内容体），每步 fade+slide 动画动态冒出，顶部实时计时器"思考 · Xs"，底部"已思考 Xs · 完成"收尾；`getStepIcon()` 自动推断图标（⚔️战术/🎯战略/📊引擎/🔧工具/📚知识等）；[frontend/src/App.tsx](frontend/src/App.tsx) 简化步骤路由：移除所有 `appendOrchestratorStepContent` 调用（实时 chunk 只推入专家悬浮卡片，不再冗余写入协调者步骤内容），忽略批量到达的 `expert_step_*` 事件（不再创建/更新协调者步骤），`dispatch_info` 同时作为首个步骤出现；步骤仅从实时事件创建（expert_start/tool/tool_result/synthesis_step_start），自然实现一个一个动态冒出
  - v3.95 (2026-04-03): 修复专家悬浮卡片实时流式 — [api/main.py](api/main.py) 为所有 `expert_{name}_chunk/thinking/reasoning/tool/tool_result` SSE 事件补全缺失的 `expert` 字段，此前该字段缺失导致前端 `msg.expert` 为 undefined，所有实时 chunk 被静默丢弃；[frontend/src/App.tsx](frontend/src/App.tsx) 增加从 `msg.type` 正则提取专家类型的 fallback 双保险；[frontend/src/components/AgentCardFlip.tsx](frontend/src/components/AgentCardFlip.tsx) ExpertHoverStream 移除 `useIncrementalTypewriter` 人为延迟，直接渲染 `thinkingContent`（有什么立即显示什么），端到端模拟测试证实 tactics/strategy 各 110/173 次实时更新，首个 chunk 0.19s 到达
  - v3.94 (2026-04-03): 协调者时间线真实时流式 — [frontend/src/App.tsx](frontend/src/App.tsx) 重写 `applyStreamMessage` 专家事件路由：`expert_start` 立即创建协调者实时步骤，`expert_{type}_chunk/thinking/reasoning` 每个 chunk 同步追加到协调者步骤内容（与卡片 thinkingContent 双写），`expert_{type}_tool` 关闭旧步骤并新建工具验证步骤，`expert_{type}_tool_result` 关闭工具步骤并新建下一轮分析步骤，`expert_result` 收尾 finalize；`expert_step_*` 后处理事件降级为标题更新而非内容来源，彻底消除"协调者步骤等后处理一口气全出"的批量问题；新增 `expertLiveStepRef`/`expertRoundRef` 跟踪每专家当前活跃步骤 ID 与轮次
  - v3.93 (2026-04-03): 专家卡片真实逐字流式 + 全链路标记净化 — [frontend/src/components/AgentCardFlip.tsx](frontend/src/components/AgentCardFlip.tsx) 重写 `useIncrementalTypewriter` 为只进不退游标式打字机，消除"18s无输出后一次性蹦字"问题；[frontend/src/components/ExpertCard.tsx](frontend/src/components/ExpertCard.tsx) `StreamText` 同步改为增量游标机制；[core/llm/experts/base_expert.py](core/llm/experts/base_expert.py) 新增 `sanitize_display_text()` 统一清除 `[CLAIM]`/`[EVIDENCE]`/`[CONFIDENCE]`/`## N` 等原始标记；[core/llm/multi_agent_orchestrator.py](core/llm/multi_agent_orchestrator.py) 保底综合讲解调用同一净化函数；[frontend/src/App.tsx](frontend/src/App.tsx) 前端兜底二次净化 step content / findings / synthesis chunks
  - v3.92 (2026-04-03): 深度分析展示链路收口 — [frontend/src/App.tsx](frontend/src/App.tsx) 将专家 `[STEP]` 事件汇总进协调者时间线，并把 `dispatch_info` 改写为适合演示的中文阶段提示；[frontend/src/components/AgentCardFlip.tsx](frontend/src/components/AgentCardFlip.tsx) 改为优先展示专家实时 `thinkingContent` 打字流，移除扑克牌下方的小活动框，避免前端继续显示晚到的英文/调度碎片
  - v3.91 (2026-04-03): 推理时控制 plan 扩充为“缩减版推理系统”路线 — 更新 [docs/plans/004-inference-control-upgrade.md](docs/plans/004-inference-control-upgrade.md)，把近期讨论沉淀为正式计划：在既有验证回路/情景分解/多候选裁判基础上，新增“协议卡 + 状态变量 + 轻量 verifier + 快慢双模式”四项最小落地方向，并明确不建议在比赛窗口内重投入完整树搜索、多长文 agent 辩论和答案式 RAG
  - v3.90 (2026-04-03): 深度分析首屏时延压缩 — [core/llm/reliable_client.py](core/llm/reliable_client.py) 改小流式读取缓冲并记录首 chunk 时延；[core/llm/experts/base_expert.py](core/llm/experts/base_expert.py) 缩短专家正文/思维 flush 阈值；[api/main.py](api/main.py) 在 agent 阶段补发心跳，避免前端长时间静默；同时将 [core/llm/experts/tactics_expert.py](core/llm/experts/tactics_expert.py)、[core/llm/experts/strategy_expert.py](core/llm/experts/strategy_expert.py)、[core/llm/experts/engine_expert.py](core/llm/experts/engine_expert.py) 默认模型切为 `glm-4-flash` 且支持环境变量覆盖，专家轮次 3→2，保留合成器使用 `glm-5`
  - v3.89 (2026-04-03): 审批台补齐“重写当前条目”闭环 — [apps/web-gradio/reviewer.py](apps/web-gradio/reviewer.py) 在审批页新增“♻️ 基于后端证据重写当前条目”按钮与后端 API 地址输入；可对当前 scenario 条目重取真实证据并原位重写，自动回填 `thinking_steps/tags_expected/engine_best_move/evidence_snapshot`，并把等级重置为 draft 待复审；对重写队列条目则可直接回填到 scenario 资产库并标记队列状态为 rewritten
  - v3.88 (2026-04-03): 审批台接入后端取证据生成 draft — [apps/web-gradio/reviewer.py](apps/web-gradio/reviewer.py) 的“新建局面”Tab 新增后端 API 地址输入与“从后端证据生成 draft”按钮，可直接调用 `scripts/generate_asset_draft.py` 逻辑取 `/api/position-analysis`、`/api/engine/evaluate`、`/api/tactical-tags`、`/api/board-structure` 生成并保存 scenario draft；审批页新增“后端证据摘要”面板显示 evidence_snapshot 核心信息
  - v3.87 (2026-04-03): 跨对话资产流程固化 — 新增 [docs/guides/asset_workflow.md](docs/guides/asset_workflow.md)，明确“Copilot 本体就是资产起草者”，新对话必须先读 DNA/STATE/资产工作流指南；固化资产默认流程为“先调用后端 API 取证据，再生成 draft”，避免换对话后退回纯脑补模式
  - v3.86 (2026-04-03): 资产起草前取证据落地 — 新增 [scripts/generate_asset_draft.py](scripts/generate_asset_draft.py)，在生成 scenario 初稿前先调用后端 `/api/position-analysis`、`/api/engine/evaluate`、`/api/tactical-tags`、`/api/board-structure` 拉取真实引擎与规则证据，再生成带 `engine_verified=true` / `tags_verified=true` / `evidence_snapshot` 的 draft，避免“纯脑补初稿”质量过差；requirements 补充 `requests`
  - v3.85 (2026-04-03): 审批台真值提示补齐 — reviewer 增加“已验证/AI草稿，待验证”状态展示与醒目提示文案；scenario_examples 现有5条样例显式标记 `engine_verified=false` / `tags_verified=false`，避免把演示草稿误当真值；审批台启动改为自动避开被占用端口，减少旧进程导致的显示错乱
  - v3.84 (2026-04-03): 审批台三项升级 — 棋盘渲染修复（Windows中文字体/棋子居中/九宫格斜线/楚河汉界/双圈棋子/N→馬映射）；新增否决→重写队列机制（rejected自动写入rewrite_queue.jsonl供AI下次重写）；新增「新建局面」Tab（FEN粘贴→预览棋盘→填写阶段/情景/矛盾→创建draft条目），资产类型增加"待重写队列"类别；pytest全绿
  - v3.83 (2026-04-03): 资产审批台 + 情景示范初稿落地 — 新增 `apps/web-gradio/reviewer.py` Gradio 审批工具（棋盘渲染+思维步骤+教学讲解可编辑+三级审批写回JSONL）；新增 `data/assets/` 目录含4个JSONL资产文件；`scenario_examples.jsonl` 写入5条情景示范初稿（开局中炮/中局无根子/中局牵制/中局捉双/残局车对仕相全），每条含完整推理节奏+工具调用序列+教学讲解；pytest全绿
  - v3.82 (2026-04-03): 资产生命周期方案设计 — 新增 `docs/plans/006-asset-lifecycle-and-eval-driven-workflow.md`，基于 DSPy/STaR/LLM-as-Judge/Context Engineering/SELF-ALIGN 五项前沿方法调研，设计"三道门审批 + 评测驱动 + 资产分级"的完整生命周期管理方案，统一四类资产 Schema（评测题/情景示范/失败案例/断言映射），明确 AI 与人的分工边界
  - v3.81 (2026-04-03): 规划文档沉淀 — 新增 `docs/plans/004-inference-control-upgrade.md` 与 `docs/plans/005-data-and-knowledge-assets.md`，把近期两段关键规划对话正式沉淀为可执行 plan：前者聚焦“验证回路 + 情景驱动分解 + 引擎/标签裁判式多候选”的推理时控制升级，后者聚焦“失败案例库 + 情景化示范库 + 原子断言验证映射表 + 评测题集”的资产建设路线；同步更新 `docs/plans/README.md` 索引；`pytest -q` 通过
  - v3.80 (2026-04-02): 扑克牌信息栏收缩与开局焦点纠偏 — 专家扑克牌下方信息栏收缩为单行小标题，释放右侧分析舞台空间；`analyze_position_strategy()` 在开局阶段默认忽略 `cannon_battery` 作为教学焦点，并补上“先按主线/定式完成出子顺序”的计划建议；合成器保底综合讲解移除写死的“重炮阵型 vs 子力优势”争论，改为按开局/非开局场景生成更克制的分歧解读；参考 CoT / Self-Consistency / STaR / DSPy 的方向，后续调教将从“堆术语”转向“按情景编写示范流程并迭代自举”；前端构建与 `tests/test_reliability_refactor.py` 通过
  - v3.79 (2026-04-02): 混合知识检索与相似局面检索落地 — 新增基于 data/training/position_data.jsonl 的本地相似局面检索器，按 FEN 结构/子力/语义标签混合匹配中局与残局相似样本；`search_chess_knowledge` 升级为“语义知识 + 棋理原则 + 相似局面”混合检索，`analyze_position_strategy` 默认补充相似局面与棋理摘要，不再完全依赖模型自行想起调工具；`rag_node` 优先切到真实 `ChromaRAG`，Chroma 索引补录开局原则与开局体系知识；真实工具输出已出现相似中局参考着法，`pytest -q` 全绿
  - v3.78 (2026-04-02): 合成器去草稿化与流式路由固化 — deep-stream 流式教学模式下协调器优先走多专家路径，避免回退到旧 single-agent 泄漏“达到最大轮数限制”；合成器不再主动要求输出 ##/[STEP:] 过程标记，并在专家输入与最终成稿两端净化步骤草稿，减少中局综合讲解被原始 trace 污染的风险；开局在 8009 上重新命中 opening_fast_path（首个内容约 0.125s，结果约 0.173s），全量测试 `pytest -q` 全绿；8010 中局 live 复测遭遇上游 429，当前已确认系统会快速显式降级而非继续输出脏稿
  - v3.77 (2026-04-02): 中局深链路预调度前推 — 修复 FEN-only move_count 把部分无历史中局误判为 opening_fast_path 的问题，PhaseDetector 现在区分 history 与 fen 推断来源；deep-stream 在重预分析等待窗前推 preview dispatch、协调者副标题与专家“证据准备”步骤，同一盘误判中局在 8008 上已于约 0.188s 收到有效调度事件；pytest -q 全绿
  - v3.76 (2026-04-02): 比赛素材全面重写 — 深度阅读全部源码后重写4篇比赛技术素材（作品简介/设计思路/设计重点难点/作品安装说明），所有数据均来自真实代码验证（304测试/45标签/14工具/9调度策略等），旧版备份为*_old.md；pytest全绿
  - v3.75 (2026-04-02): 深度分析实时链路再压缩 — deep-stream 在高置信开局场景跳过重预分析，基于 FEN/历史推断 move_count 并收紧 opening 判定，避免无历史中局误判开局；专家链路改为真实流式 chunk/推理转发、关闭冗长 thinking 默认值、轮次 3→2，并给 Evidence 灵动岛补上专家实时步骤，首个有效事件已压到约 0.125s；前端构建通过，pytest -q 全绿
  - v3.74 (2026-04-02): 开局快答演出层与协调者布局修正 — opening_fast_path 不再直接暴露“快答模式”口吻，而是补齐战略/引擎轻量步骤、工具轨迹与协调者综合步骤，让开局也像是快速分析得出；同时拉高右侧协调者内容区避免底部大片空白，Evidence 灵动岛回调到更合理尺寸并新增调度脉冲空态；前端构建通过，pytest -q 全绿
  - v3.73 (2026-04-02): 分析模式体验强化 — 前端分析区改为“棋盘 / Evidence Map 灵动岛 / 右侧分析栏”三栏舞台，补出棋盘与右栏之间的独立展示位；Evidence 岛实时展示调度与工具调用（中文工具名），专家 hover 面板改为持续滚动的实时思维流，分析动画大幅提速并清理高开销发光动画以改善帧率；前端构建通过，pytest -q 全绿
  - v3.72 (2026-04-02): 开局快答调度优化 — deep-stream 新增 history 透传，协调器在开局前几步命中开局书/开局原则时直接走 opening_fast_path，跳过强制三专家重链路；新增 dispatch_info SSE 事件与前端调度可视化，保留多专家主链用于复杂局面；前端构建通过，pytest -q 全绿，并完成 force_multi 场景下的真实快答回放验证
  - v3.71 (2026-04-02): 深度分析全链路修复 — 修复 force_multi 未强制三专家/预分析错误污染 SSE/引擎池复用死进程/专家把 reasoning_content 当正式输出导致 tool_calls 与英文思维泄漏/search_chess_knowledge 工具签名不兼容/合成空结果导致无 result 事件；新增专家成稿验收与重写修复、合成器保底综合讲解，真实调用 /api/analyze/deep-stream 已恢复三专家+result+debug_log，pytest 门禁通过
  - v3.70 (2026-04-02): 对局反馈层完善 — 棋盘新增将军横幅+被将方王位脉冲提示/非法走法红色抖动与浮层提示/吃子爆散闪击特效，并在 store 中接入 move 与 ai-move 的 captured/in_check/game_over 状态，前端构建通过+pytest门禁通过
  - v3.69 (2026-04-02): 棋盘完成三期精修 — 在深墨棋谱盘基线上补充入场动效/河界流光/悬停光晕/棋子悬停与按压反馈/整体交互节奏继续克制化，前端构建通过+pytest门禁通过
  - v3.68 (2026-04-02): 棋盘重做二期完成 — ChessBoard改为“深墨棋谱盘”方向/补回清晰9x10棋盘格与九宫结构/河界取消胶囊化改为薄雾横带+压印“楚河智境”/棋子统一为传统象牙棋具式圆子/交互高亮改为克制教学态/前端构建通过+300测试全绿
  - v3.67 (2026-04-02): 棋盘风格纠偏 — 去除Y2K金属球与强发光半成品风格/棋盘收敛为深墨漆面+细金线+弱化河界带/棋子改为温润哑光材质而非银红金属球/保持“楚河智境”文案/前端构建通过+300测试全绿
  - v3.66 (2026-04-02): 棋盘UI重做一期 — ChessBoard重绘为Aurora Lacquer液态漆面风格/河界文案改为“楚河智境”/靛蓝漆面底板+琥珀金线+能量河界/新增星位标记与釉面棋子材质/上一步与合法点提示改为轻量呼吸环/前端构建通过+300测试全绿
  - v3.65 (2026-04-02): 重构识别为纯YOLO管道 — 新增vision/yolo_recognizer.py(YoloDirectRecognizer)/YOLO检测board类自动定位棋盘/棋子坐标→(col,row)映射/FEN生成/后端/api/recognize改为YOLO本地推理(不再调LLM)/300测试全绿
  - v3.64 (2026-04-02): 三大Bug修复 — 引擎栏全模式可见(replay除外)+走子后自动刷新评估/GLM-5 Extended Thinking content空响应兜底(reasoning_content回退)/LLM并发限制2→4+熔断阈值5→12+工具超时30→45s/300测试全绿
  - v3.63 (2026-04-02): 棋盘视觉识别接入 — VisionAnalyzer(GLM-4V-Flash)集成/POST /api/recognize图片上传端点/Apple风格识别弹窗(扫描动画+置信度+一键应用)/前端识别按钮完整联通/RecognitionModal组件/loadFromRecognition状态方法/300测试全绿
  - v3.62 (2026-04-02): 前后端全面整合 — 4模式选择器(分析/执红/执黑/双人)/难度选择器(简单/中等/困难)/深度分析按钮入左栏/双人模式回合制/AI对弈API双路由兼容(board+fen)/ChromaRAG线程安全/UCI边界校验/plan文档更新/300测试全绿
  - v3.60 (2026-04-02): 系统能力跃升 — 真实RAG系统(ChromaDB+80+棋理原则向量化)/search_chess_knowledge工具/对弈模式API(三级难度)/引擎评分链路修复/系统能力全面审计/20项新测试(13RAG+7对弈)
  - v3.58 (2026-04-02): Phase 2 证据裁决化落地 — Claim数据结构/解析器/证据链捕获/合成器证据裁决升级/专家prompt结构化断言/20项Phase2测试
  - v3.57 (2026-04-02): 规则引擎正确性固化 — 自将过滤/将帅照面/攻击范围vs合法走法分离/15项规则正确性测试
  - v3.56 (2026-04-02): Phase 1 动作空间约束推进 — candidate_id 协议接入工具/专家/单Agent，RuleEngine 改为稳定合法走法生成，新增候选协议回归测试
  - v3.55 (2026-04-02): 可靠性重构一期 — 统一LLM可靠性客户端/门控式专家调度/失败感知合成器/结构化状态错误码/6项可靠性测试
  - v3.54 (2026-04-02): 知识体系深度扩展 — 棋理原则20→80+条/知识库多维检索/引擎MultiPV真多候选/强制序列多深度/开局库29+序列
  - v3.53 (2026-04-02): 前端UX流式体验升级 — 专家悬浮窗真实时流式/协调者步骤卡片修复/专家进度概览/StepItem去typewriter闪烁
  - v3.52 (2026-04-02): 多Agent架构深度优化 — Evidence Map结构化管线/新增simulate_move+query_chess_principles工具/引擎连接池/共享规则提取/专家提示词增强
  - v3.50 (2026-04-02): 深度分析后端 SSE 正式接入新版前端 Agent 面板，按钮点击后可流式展示专家与协调者内容
  - v3.49 (2026-04-02): 搜索栏 WebGL 形变提速并按内容外框包裹 + 搜索亮底字体提亮对比 + 引擎栏恢复大字优势信息 + 协调者流式区去黑框
  - v3.48 (2026-04-01): 引擎栏折线占主体 + 删除大数字胜率 + 删除右栏仿macOS外框 + iOS式搜索缩放动画 + 右栏间距色调统一
  - v3.47 (2026-04-01): 搜索浮层动画提速并收紧 + 引擎栏改为图表优先布局 + 右侧分析栏 macOS 化舞台重构
  - v3.46 (2026-04-01): 引擎栏补齐胜率比例条与真实折线图 + 左栏切换为统一 WebGL 液态几何 + 打棋谱按钮到搜索框连续形变
  - v3.45 (2026-04-01): 修复分析模式引擎栏显示条件/定位错误 + 新增轻量 engine/evaluate 接口 + 旧后端兼容降级
  - v3.44 (2026-04-01): 左栏层级重排 + 引擎栏接入 Pikafish 真评估 + 棋盘下方稳定显示
  - v3.43 (2026-04-01): 左侧栏交互升级一期 — 走法记录框/打棋谱搜索浮层/WebGL按钮接入 + 引擎栏大数字与tooltip重构
  - v3.42 (2026-04-01): 补齐计划剩余项 — ExpertGlassPanel接入实时thinking/finding + ThinkingStream拆分标题区/内容区 + orchestrator_subtitle事件 + prompt阶段标题约束
  - v3.41 (2026-04-01): 修复协调者步骤不显示bug — 实时chunk推送 + 【节标题】隐式步骤 + API双编码修复 + 前端降级路径
  - v3.40 (2026-04-01): 协调者步骤协议落地 — synthesis_step SSE事件 + 前端右侧综合步骤流 + 流式解析测试补齐
  - v3.39 (2026-04-01): 多Agent步骤协议首版落地 — 三专家[STEP]标记 + SSE结构化事件 + 前端左侧步骤可视化
  - v3.38 (2026-04-01): 完成左侧栏完整重构 — Zustand持久化 + 两Leva文件夹 + z=3固定Logo/滑块 + WebGL按钮透明叠层
  - v3.37 (2026-04-01): 左侧栏重构 — iOS 26三段滑块 + 拍照按钮 + WebGL按钮坐标调整
  - v3.36 (2026-04-01): OpenTelemetry追踪系统上线并验证 — 完整Span层级 + 控制台输出
  - v3.35 (2026-04-01): OpenTelemetry追踪系统上线 — 零配置控制台输出，支持Langfuse/Jaeger接入
  - v3.34 (2026-04-01): WebGL按钮升级 — dashersw折射模型迁移（进行中）
  - v3.33 (2026-04-01): 多Agent系统工程化修复，详见 doc/plans/eager-growing-eich.md
  - v3.32 (2026-04-01): 文档体系整理，添加frontmatter
  - v3.31 (2026-03-31): DNA重写，文档体系重大更新
---

# 项目状态

> 本文档记录当前开发进度，架构详情请阅读 [DNA.md](DNA.md)

**版本**: v3.96
**最后更新**: 2026-04-05

---

## 📋 文档更新记录

### 2026-04-03 ✅ 完成：修复专家悬浮卡片实时流式显示 + SSE expert 字段补全（v3.95）

**根因**：后端 SSE 生成器发送 `expert_{name}_chunk`/`_thinking`/`_reasoning`/`_tool`/`_tool_result` 事件时，**缺少 `expert` 字段**。前端 App.tsx 的 `applyStreamMessage` 依赖 `msg.expert` 来路由事件到对应专家的 store，缺失该字段导致所有实时 chunk 被静默丢弃，`thinkingContent` 永远为空。当 `expert_result` 到达（它包含 `expert` 字段）时，`finding` 被一次性设置，悬浮卡片突然填满。

**端到端模拟测试结果（修复后）**：
- tactics: 110 次实时更新, 首个 0.19s, 持续 22.78s, 中位时间到达比 46%
- strategy: 173 次实时更新, 首个 0.20s, 持续 32.97s, 中位时间到达比 45%
- 协调者步骤: 同步双写 283 次更新，完全实时

**变更**：
- [api/main.py](api/main.py)：SSE 生成器为所有 `expert_{name}_*` 事件添加 `'expert': expert_name` 字段
- [frontend/src/App.tsx](frontend/src/App.tsx)：增加从 `msg.type` 正则提取专家类型的 fallback（`/^expert_(tactics|strategy|engine)_/`），双保险确保路由不丢
- [frontend/src/components/AgentCardFlip.tsx](frontend/src/components/AgentCardFlip.tsx)：ExpertHoverStream 移除 `useIncrementalTypewriter` 人为延迟，改为直接渲染 `thinkingContent`（有什么显示什么），自动滚动到底部

### 2026-04-03 ✅ 完成：协调者时间线真实时流式（v3.94）

**目标**：彻底解决"协调者步骤隔好多秒然后一下子出来好多个step"的问题——根因是 `_emit_structured_steps` 后处理在专家完整响应完成后才批量发送步骤事件。

**变更**：
- [frontend/src/App.tsx](frontend/src/App.tsx)：重写 `applyStreamMessage` 中的专家事件路由架构
  - 新增 `expertLiveStepRef` 和 `expertRoundRef` ref，为每个专家维护协调者时间线上的"当前活跃步骤 ID"和轮次计数器
  - `expert_start` → 立即在协调者时间线创建 "XX专家 · 分析中" 步骤
  - `expert_{type}_chunk/thinking/reasoning` → 每个实时 chunk 同步追加到卡片 `thinkingContent` **和** 协调者步骤内容（双写），实现逐字实时
  - `expert_{type}_tool` → finalize 旧步骤，新建 "XX专家 · 工具名" 步骤，填补工具调用等待期的协调者空白
  - `expert_{type}_tool_result` → 追加工具摘要到协调者步骤，关闭工具步骤，新建下一轮分析步骤
  - `expert_result` → finalize 该专家的最后一个活跃步骤
  - `expert_step_*` 后处理事件降级为标题更新/内容补充，不再是协调者步骤的主要数据来源
  - 每次 `triggerDeepAnalysis` 重置所有 ref 状态

### 2026-04-03 ✅ 完成：专家卡片真实逐字流式 + 全链路标记净化（v3.93）

**目标**：消除"18s无输出后一次性蹦字"的阻塞感，和协调者内容里的 `## N`、`[CLAIM]` 等原始标记泄露。

**变更**：
- [frontend/src/components/AgentCardFlip.tsx](frontend/src/components/AgentCardFlip.tsx)：重写 `useIncrementalTypewriter` 为只进不退的游标式打字机——游标只追赶 text.length，不因新 chunk 到达而回退重播；专家完成后也展示 thinkingContent 而非跳切到 finding
- [frontend/src/components/ExpertCard.tsx](frontend/src/components/ExpertCard.tsx)：`StreamText` 同步改为增量游标机制，去掉每次 text 变化就重置 currentIndex 的旧逻辑
- [core/llm/experts/base_expert.py](core/llm/experts/base_expert.py)：新增 `sanitize_display_text()` 统一清除 `[CLAIM]`/`[EVIDENCE]`/`[CONFIDENCE]`/`## N 标题`/`[STEP:]` 等原始标记；`split_step_content_chunks` 和 `_extract_finding` 调用同一净化函数
- [core/llm/multi_agent_orchestrator.py](core/llm/multi_agent_orchestrator.py)：`_build_fallback_synthesis` 的 `short()` 和 evidence 生成改为调用 `sanitize_display_text`
- [frontend/src/App.tsx](frontend/src/App.tsx)：前端增加兜底 `sanitizeDisplayText` 二次净化 step content / findings / synthesis_chunk / result.explanation

### 2026-04-03 ✅ 完成：深度分析展示链路收口（v3.92）

**目标**：把 deep-stream 前端从“能流”改成“能演示”，让协调者和专家卡片都按用户视角展示真正有用的实时过程。

**变更**：
- [frontend/src/App.tsx](frontend/src/App.tsx)：专家 `[STEP]` 开始/内容/结束事件不再留在卡片底部小块中，而是统一汇总到协调者时间线；`dispatch_info` 不再直接露出英文/调度味文案，改成面向演示的中文阶段提示
- [frontend/src/components/AgentCardFlip.tsx](frontend/src/components/AgentCardFlip.tsx)：专家 hover 面板优先显示真实实时 `thinkingContent` 打字流；删除扑克牌下方小活动框，减少碎片化视觉噪音

### 2026-04-03 ✅ 完成：推理时控制 plan 扩充为“缩减版推理系统”路线（v3.91）

**目标**：把近期关于协议卡、状态变量、verifier 与快慢双模式的讨论沉淀进正式 plan，避免后续继续停留在抽象讨论层。

**变更**：
- [docs/plans/004-inference-control-upgrade.md](docs/plans/004-inference-control-upgrade.md)：补充“协议卡驱动的推理路由”“状态变量化”“轻量 verifier”“快慢双模式”等四项新方案，增加最小落地清单，并明确近期不建议投入完整树搜索、多长文 agent 辩论与答案式 RAG

### 2026-04-03 ✅ 完成：深度分析首屏时延压缩（v3.90）

**目标**：解决 deep-stream“不是没流，而是正文太晚才出来”的演示卡顿问题。

**变更**：
- [core/llm/reliable_client.py](core/llm/reliable_client.py)：把 GLM 流式读取改为更小粒度，减少 requests 攒包导致的首段正文延迟，并记录首个 content/reasoning chunk 时延
- [core/llm/experts/base_expert.py](core/llm/experts/base_expert.py)：专家正文与思维 flush 规则改为“小片段 + 时间阈值”并行触发，避免明明已有返回却继续攒包
- [api/main.py](api/main.py)：agent 阶段队列为空时每秒补发一次“专家分析中...”心跳，减少前端长时间静默
- [core/llm/experts/tactics_expert.py](core/llm/experts/tactics_expert.py)、[core/llm/experts/strategy_expert.py](core/llm/experts/strategy_expert.py)、[core/llm/experts/engine_expert.py](core/llm/experts/engine_expert.py)：专家默认模型切为 `glm-4-flash`，支持 `EXPERT_LLM_MODEL` / `TACTICS_EXPERT_MODEL` / `STRATEGY_EXPERT_MODEL` / `ENGINE_EXPERT_MODEL` 覆盖；专家最大轮次 3→2；合成器继续保留 `glm-5`

### 2026-04-03 ✅ 完成：审批台补齐重写闭环（v3.89）

**目标**：让打回或存疑条目不再停在“记录问题”，而是能直接在审批台内重取证据并重写。

**变更**：
- [apps/web-gradio/reviewer.py](apps/web-gradio/reviewer.py)：审批页新增“重写使用的后端 API 地址”与“♻️ 基于后端证据重写当前条目”按钮；scenario 条目可原位重写并重置为 draft 待复审；rewrite_queue 条目可一键回填到 scenario 库并标记 `status=rewritten`

### 2026-04-03 ✅ 完成：审批台接入后端取证据生成 draft（v3.88）

**目标**：把“先取证据，再起草”从独立脚本推进到审批台主流程里，减少手动切换。

**变更**：
- [apps/web-gradio/reviewer.py](apps/web-gradio/reviewer.py)：新建局面 Tab 新增后端 API 地址输入、生成标签/最佳着法展示、`⚡ 从后端证据生成 draft` 按钮；审批页新增“后端证据摘要”面板，显示 evidence_snapshot 中的引擎、标签、结构摘要

### 2026-04-03 ✅ 完成：跨对话资产流程固化（v3.87）

**目标**：确保新开 Copilot 对话也能沿用同一套资产工作流，不退回“纯脑补初稿”。

**变更**：
- [docs/guides/asset_workflow.md](docs/guides/asset_workflow.md)：新增资产工作流指南，明确 Copilot 本体就是资产起草者；新对话必须先读 DNA / STATE / 本指南；资产默认流程固定为“先调后端取证据，再起草 draft”

### 2026-04-03 ✅ 完成：起草前取证据（v3.86）

**目标**：避免资产初稿完全靠 AI 脑补，起草时就使用后端真实引擎与规则信号。

**变更**：
- [scripts/generate_asset_draft.py](scripts/generate_asset_draft.py)：新增资产草稿生成脚本，输入 FEN/phase/scenario 后依次请求 `/api/position-analysis`、`/api/engine/evaluate`、`/api/tactical-tags`、`/api/board-structure`，自动生成带 `evidence_snapshot` 的 scenario draft
- [requirements.txt](requirements.txt)：显式补充 `requests>=2.31.0`

### 2026-04-03 ✅ 完成：审批台真值提示补齐（v3.85）

**目标**：解决“草稿像真值”的误导问题，并避免旧端口占用导致你看到旧版审批台。

**变更**：
- [apps/web-gradio/reviewer.py](apps/web-gradio/reviewer.py)：元信息区新增“引擎数据/标签数据 = 已验证 or AI草稿，待验证”；审批页顶部新增醒目警告；启动时不再写死 7861，自动向后寻找空闲端口
- [data/assets/scenario_examples.jsonl](data/assets/scenario_examples.jsonl)：现有 5 条示范样例显式写入 `engine_verified=false` 与 `tags_verified=false`

### 2026-04-03 ✅ 完成：审批台三项升级（v3.84）

**目标**：修复棋盘渲染质量、补全审批闭环（打回→重写）、支持人工导入新局面。

**变更**：
- `core/render/board_renderer.py`：完全重写——Windows 平台自动加载 SimHei/微软雅黑字体、棋子 textbbox 精确居中、双圈传统棋子样式、九宫格斜线、河界中间列断开、楚河漢界文字居中渲染、新增 N/n→馬/马映射
- `apps/web-gradio/reviewer.py`：审批台升级为 Tabs 布局——
  - 「📋 审批」Tab：否决自动写入 `rewrite_queue.jsonl`（含原文/审核备注/原始ID），元信息增显审核备注
  - 「➕ 新建局面」Tab：FEN 输入→预览验证→选阶段/情景名/局面判断/主要矛盾→创建 draft 条目到 scenario_examples.jsonl
  - 资产类型下拉增加"待重写队列 (rewrite)"
- `data/assets/rewrite_queue.jsonl`：新增重写队列文件

### 2026-04-03 ✅ 完成：资产审批台 + 情景示范初稿落地（v3.83）

**目标**：落地资产管理的实际工具和第一批示范数据。让审批流程从计划变成可用的产品。

**变更**：
- `data/assets/` 目录：新增 `scenario_examples.jsonl`（5条初稿）、`eval_set.jsonl`、`failure_cases.jsonl`、`assertion_map.jsonl`（空，待填充）
- `apps/web-gradio/reviewer.py`：Gradio 审批工具，包含棋盘FEN渲染、思维步骤展示、教学讲解可编辑、三级审批（gold/silver/rejected）写回JSONL、否决自动转入失败案例库
- 5 条情景示范初稿覆盖 5 种不同推理节奏：
  1. `opening_center_cannon`：开局中炮，查定式→看引擎→出子顺序
  2. `midgame_unprotected_piece`：中局无根子，验证无根→查对手反击→引擎确认
  3. `midgame_pin`：中局牵制，确认牵制关系→被钉子受攻次数→加攻
  4. `midgame_double_attack`：中局捉双，发现双攻位→simulate验证→引擎确认
  5. `endgame_basic`：残局车对仕相全，数子力→查残局定式→判断胜负

**启动方式**：
```bash
python apps/web-gradio/reviewer.py
# 浏览器打开 http://localhost:7861
```

**验证**：
- 5 条 JSONL 数据加载、棋盘渲染、存取回写均通过验证
- 全量测试通过：`pytest -q`

### 2026-04-03 ✅ 完成：资产生命周期方案设计（v3.82）

**目标**：回答"AI 生成的资产能可靠吗"这个核心问题，基于前沿方法调研设计可执行的审批检阅订正流程。

**前沿调研**：
- **DSPy/MIPRO**（Stanford 2023-2024）：prompt 视为可编译程序，自动选择的 few-shot 比人工挑选好 5-46%；启示 → 情景模板应模块化可组合
- **STaR**（Zelikman 2022）：少量正确推理示范 + 自举迭代 → 可比 30x 大模型；启示 → "错的带正确信息重写"就是我们的核心工作流
- **LLM-as-Judge**（Zheng, NeurIPS 2023）：强模型评判与人类偏好 >80% 一致；启示 → 用 LLM 评"说得好不好"，用规则/引擎评"说得对不对"
- **Context Engineering**（Karpathy/DAIR.AI 2025）：从 prompt engineering 到 context engineering，核心是分层上下文+可观测性+行为迭代
- **SELF-ALIGN**（Sun, NeurIPS 2023）：16 条原则 + 5 个示范 > 大量未验证样本；启示 → 知识卡少而硬，先做 20 条严格验证的

**新增 Plan**：
- `docs/plans/006-asset-lifecycle-and-eval-driven-workflow.md`：
  - 统一四类资产 Schema（eval_item / scenario_example / failure_case / assertion_verification_map）
  - "三道门"审批制：硬核自动验证 → LLM-Judge 软评分 → 人工终审
  - 资产分级：gold / silver / draft / rejected
  - 评测驱动闭环：生成 → 验证 → 定级 → 入库 → 回归 → 订正
  - AI 与人的明确分工边界

**验证**：
- 全量测试通过：`pytest -q`

### 2026-04-03 ✅ 完成：规划文档沉淀（v3.81）

**目标**：把近期两段关键规划性讨论从聊天结论沉淀成仓库内可持续维护的 Plan 文档，避免方向只停留在对话中。

**新增 Plan**：
- `docs/plans/004-inference-control-upgrade.md`：沉淀“推理时控制升级”路线，明确下一阶段以工具校验回路、情景驱动分解、引擎/标签裁判式多候选为主线，而非直接引入重型研究框架
- `docs/plans/005-data-and-knowledge-assets.md`：沉淀“数据与知识资产建设”路线，明确优先建设失败案例库、情景化示范库、原子断言验证映射表和评测题集
- `docs/plans/README.md`：补充两份新计划的目录索引，保证后续协作时可发现、可引用

**验证**：
- 全量测试通过：`pytest -q`

### 2026-04-02 ✅ 完成：扑克牌信息栏收缩与开局焦点纠偏（v3.80）

**目标**：直接解决分析舞台里两个会立刻掉价的问题：扑克牌下方栏位过于占空间，以及系统在开局场景反复把“重炮阵型”之类弱焦点结构抬成主叙事。

**关键问题**：
- 扑克牌落地后的下方信息卡高度过大，持续挤占左侧纵向空间，视觉上比专家牌面本身还吵
- `cannon_battery` 是宽松的位置结构标签，但在开局阶段常常只是炮的自然排布；若直接把它抬成教学重点，会偏离“当前该聚焦什么”
- 合成器保底文案里硬编码了“重炮阵型 vs 直接子力优势”的争论，即使当前局面根本不是这个矛盾，也会把用户带偏

**变更**：
- `frontend/src/components/AgentCardFlip.tsx`：专家牌下方信息栏改为单行小标题，只保留当前步骤标题/副标题，不再展示额外内容块
- `core/llm/agent_tools.py`：新增按阶段过滤焦点标签的逻辑，开局阶段默认忽略 `cannon_battery` 作为主教学焦点；`analyze_position_strategy()` 对开局补充“优先按主线/定式完成出子顺序”的建议
- `core/llm/multi_agent_orchestrator.py`：保底综合讲解改为按开局/非开局场景生成克制的分歧解读，不再写死“重炮阵型 vs 子力优势”
- `tests/test_reliability_refactor.py`：新增“开局忽略重炮焦点”和“保底讲解不再硬编码重炮叙事”的回归测试

**研究结论（用于后续调教）**：
- `Chain-of-Thought`：少量高质量示范即可显著提升复杂推理，说明我们应该写“情景-流程-结论”式示范，而不是继续堆空泛术语
- `Self-Consistency`：同题多路径采样后取一致结论，适合后续做“多条教学解释候选→一致性筛选”
- `STaR`：用少量带思维过程的示范 + 模型自生成正确推理自举，适合把已有优质分析样本沉淀成 scenario curriculum
- `DSPy`：把 prompt 视作可编译、可优化的流程图，而不是手写长字符串；后续更适合把“开局新手/老手、中局优势/劣势、残局简化/守和”等情景模块化编排

**验证**：
- 前端构建通过：`cd frontend && npm run build`
- 定向回归通过：`pytest -q tests/test_reliability_refactor.py`

### 2026-04-02 ✅ 完成：混合知识检索与相似局面检索落地（v3.79）

**目标**：正面提升深度分析的知识厚度与局面先验，补掉“相似局面检索缺位、棋理库过薄、RAG接入不深”的质量根因。

**关键问题**：
- 多专家主链路虽然暴露了 `search_chess_knowledge`，但主质量仍过度依赖模型自己决定是否调用，导致知识接入深度不稳定
- 旧 `rag_node` 仍默认使用 `MockRAG`，和主工程的真实 ChromaRAG 路线脱节
- 仓库里确实有 `data/training/position_data.jsonl` 这类带 `fen + semantic_tags` 的训练样本，但此前没有任何主工具把它用作相似局面检索
- 现有 Chroma 主要索引张力原则，开局原则与开局体系知识没有系统并入语义库

**变更**：
- `core/rag/position_similarity.py`：新增本地相似局面检索器，基于训练样本的 FEN 结构、子力配置与语义标签做混合相似度排序，支持按阶段快速召回
- `core/llm/agent_tools.py`：`search_chess_knowledge()` 升级为混合检索，返回“语义知识结果 + 棋理原则 + 相似局面”；`analyze_position_strategy()` 默认补充相似局面与棋理摘要，让战略专家不再完全依赖额外工具调用才拿到知识证据
- `core/rag/chroma_rag.py`：Chroma 集合初始化改为按类型补种数据，不仅索引张力原则，也索引 `opening_knowledge.py` 里的开局原则与开局体系
- `core/agent/nodes/rag_node.py`：优先使用 `ChromaRAG`，仅在异常时回退 `MockRAG`
- `tests/test_rag.py`、`tests/test_agent.py`：新增相似局面检索、带 FEN 的混合知识检索、RAG 节点回归测试

**验证**：
- 定向回归通过：`pytest -q tests/test_rag.py tests/test_agent.py`
- 真实工具调用验证：`search_chess_knowledge(fen=..., query='中局结构与计划')` 已返回语义知识、原则补充与 3 个相似中局样本，包含参考着法与样本数
- 全量测试通过：`pytest -q`

### 2026-04-02 ✅ 完成：合成器去草稿化与流式路由固化（v3.78）

**目标**：继续收口开局/中局深链路中最后一批明显掉价的问题，重点修复 streaming teaching 模式误回退旧单链路、以及中局综合讲解把 `##` / `[STEP:]` 草稿结构直接暴露给用户的问题。

**关键问题**：
- deep-stream 虽然已有 preview dispatch，但协调器在部分 streaming 场景仍可能回退旧 `XiangqiCoachAgent` 单链路，用户会直接看到“达到最大轮数限制”
- 合成器系统提示词主动要求输出 `## [数字]` 与 `[STEP: ...]`，同时又把专家原始 `details` 大段注入提示，导致最终 `【共识分析】` 等章节容易混入中间步骤草稿，且合成上下文被不必要拉长

**变更**：
- `core/llm/multi_agent_orchestrator.py`：`analyze()` 在存在 `on_thinking` 的 streaming teaching 场景下优先走 `analyze_multi()`，阻断 deep-stream 回退旧 single-agent 路径
- `core/llm/multi_agent_orchestrator.py`：合成器提示词改为“只输出六个最终章节”，不再主动要求输出 `##` / `[STEP:]` 过程标记
- `core/llm/multi_agent_orchestrator.py`：新增专家详情净化与最终成稿净化，清除 `[STEP:]`、`## ...`、节标题回声等草稿噪声，并把传统 `details` 压成短摘要，减少合成器上下文膨胀
- `tests/test_reliability_refactor.py`：新增“专家详情去步骤草稿”和“最终成稿净化”回归测试

**验证**：
- 目标回归通过：`pytest -q tests/test_reliability_refactor.py`
- 全量测试通过：`pytest -q`
- 开局 live 回放（8009）重新命中 `opening_fast_path`，首个有效内容约 `0.125s`，最终结果约 `0.173s`
- 中局 live 回放（8010）本轮遭遇上游 `429`，系统约 `4.307s` 内显式返回失败说明而非继续输出带草稿污染的错误综合文案；该问题属于外部限流，后续仍需在可用额度下继续复测中局最终讲解质量与总时延

### 2026-04-02 ✅ 完成：中局深链路预调度前推（v3.77）

**目标**：继续压缩深度分析中局链路的“空等待”，并修复无历史局面仍会被误导到 opening fast path 的剩余误判。

**关键问题**：
- 仅靠 FEN 尾部 move_count 推断时，部分明显已发展子的中局仍会被判成“开局”，错误触发 opening fast path
- 非开局 deep-stream 在重预分析完成前只有泛化 `thinking` 心跳，前端 0.5s~数秒窗口内缺少真正有价值的调度/步骤事件

**变更**：
- `core/llm/thinking_templates.py`：`PhaseDetector.detect()` 新增 `move_count_source`，区分 history 给出的显式着数与 FEN 推断着数；对 FEN-only 场景使用更严格的 opening 判定（要求更少已发展大子）
- `core/llm/multi_agent_orchestrator.py`、`api/main.py`：阶段检测现在显式传递着数来源，不再把 FEN 推断值伪装成显式 history
- `api/main.py`：deep-stream 在等待重预分析时先推送 `dispatch_info(mode=precompute_preview)`、协调者副标题与专家“证据准备”步骤，让中局链路在正式专家启动前就有真实可见内容
- `tests/test_reliability_refactor.py`：新增针对误判中局 FEN 的回归测试，锁定“FEN-only 场景不应误判开局”

**验证**：
- 实测误判中局 FEN 在 `8008` 上不再触发 `opening_fast_path`
- 同一局面约 `0.188s` 即收到 `dispatch_info`、`orchestrator_subtitle` 与两位专家的预备步骤
- 全量测试通过：`pytest -q`

### 2026-04-02 ✅ 完成：比赛素材全面重写（v3.76）

**目标**：深入阅读全部源码后，重写 `docs/contest-materials/` 下的四篇比赛技术素材，为队友提供绝对精细、数据来源真实的原材料。

**方法**：
- 完整阅读后端全部核心模块（rules引擎、tactical_detector、tension_detector、agent_tools、multi_agent_orchestrator、claim、analysis_policy、reliable_client、engine pool、knowledge_retriever）和前端全部关键组件（LiquidGlassApp、AgentCardFlip、ChessBoard、EvidenceMapIsland、5个GLSL着色器）
- 运行 `pytest --co -q` 验证精确数据：304项测试/21个文件
- 所有技术数据均来自真实源码而非猜测

**重写文档**：
- `作品简介.md`：项目定位、6大功能特色、系统架构、关键指标、6项技术创新、应用价值
- `设计思路.md`：问题分析、技术选型、4层架构详述、10个核心模块代码级拆解、测试体系、创新总结
- `设计重点难点.md`：7个技术难题（零幻觉/递归陷阱/多专家编排/RAG融合/可靠性/WebGL渲染/SSE流式）深度分析
- `作品安装说明.md`：环境要求、5步快速安装、启动流程、验证方法、模块启动时序图、配置说明、FAQ

**备份**：旧版四篇文档已重命名为 `*_old.md` 保留。

**验证**：
- 测试通过：`pytest -q` → 304 passed

### 2026-04-02 ✅ 完成：深度分析实时链路再压缩（v3.75）

**目标**：解决“灵动岛像摆设、hover 不够真流式、首包过慢、无历史局面误走开局快答、深链路太啰嗦”的整条分析链路问题，让系统更接近可教学演示态。

**关键问题**：
- `deep-stream` 先做战术/引擎重预分析，再真正启动专家链路，导致首个有价值事件出现过晚
- 前端若没传完整 history，旧逻辑会把很多中局局面误当成“开局”，错误触发 opening fast path
- 专家事件此前更像“结果播报”，不是实时流；hover 与 Evidence 岛在无工具调用时仍容易显得阻塞或静态
- 专家默认 extended thinking 过长，造成时延和车轱辘话

**变更**：
- `api/main.py`：新增 FEN/history 的 `move_count` 估算；deep-stream 先做 phase/opening 快判，高置信开局直接跳过重预分析；同时转发 `expert_*_reasoning` 事件并取消 deep-stream 的默认强制全队重链路
- `core/llm/thinking_templates.py`、`core/llm/multi_agent_orchestrator.py`：收紧 opening 判定，补上 FEN move-count 推断与无历史保护，避免把中局误导到开局快答；并为专家补发即时 prelude 步骤
- `core/llm/reliable_client.py`、`core/llm/experts/base_expert.py`：专家调用改走真实流式传输，推理/正文 chunk 双路转发；关闭默认 extended thinking，轮次从 3 降到 2，正文按小块切分，减少阻塞式大段输出
- `core/llm/analysis_policy.py`：压缩非必要专家预算，减少深链路里冗余引擎专家开销
- `frontend/src/App.tsx`、`frontend/src/components/EvidenceMapIsland.tsx`：前端接入专家 reasoning 事件；灵动岛新增“实时动向”区，直接显示专家当前步骤/副标题，不再只等工具返回
- `tests/test_reliability_refactor.py`：新增“无历史中局不应误判开局”和“协调器可从 FEN 推断 move_count”的回归测试

**验证**：
- 实测高置信开局 deep-stream：首个有效事件约 0.125s，结果约 0.185s
- 前端构建通过：`cd frontend && npm run build`
- 全量测试通过：`pytest -q`

### 2026-04-02 ✅ 完成：开局快答演出层与协调者布局修正（v3.74）

**目标**：解决“开局快答像直接背诵、灵动岛过小、协调者内容框过短导致下半区空白”的体验断裂，同时主动补掉分析模式里几个会削弱演示说服力的空态问题。

**关键问题**：
- opening fast path 虽然快，但前端只看到协调者直接给答案，缺少“专家已经快速分析过”的表演层，观感像直出背稿
- 协调者无步骤时正文容器被固定 `maxHeight` 截断，右栏下部容易出现明显空白区
- 灵动岛在上次缩小后存在感不足，且在没有工具调用时几乎退化成静态空盒

**变更**：
- `core/llm/multi_agent_orchestrator.py`：为 `opening_fast_path` 补齐战略/引擎两位轻量专家的启动、步骤、工具调用、结果与协调者综合步骤；同时把最终口吻从“命中快答模式”改回自然分析表达
- `frontend/src/components/ThinkingStream.tsx`：移除正文区固定高度上限，让协调者内容真正吃满右栏可用高度，避免底部大片空白
- `frontend/src/components/EvidenceMapIsland.tsx`、`frontend/src/App.tsx`：把灵动岛回调到更合理尺寸，并新增“识别/棋理/评估/综合”调度脉冲，使没有工具结果时也保持分析进行中的节奏感
- `tests/test_reliability_refactor.py`：补充 opening fast path 的专家事件回归校验，确保开局快答仍不触发真实重链路，但前端能收到完整轻量演出事件

**验证**：
- 前端构建通过：`cd frontend && npm run build`
- 测试通过：`pytest -q`

### 2026-04-02 ✅ 完成：分析模式体验强化（v3.73）

**目标**：把分析模式从“能跑”提升到“适合录演示视频”，重点解决首屏文字出现慢、专家 hover 时缺少真实流式思考、棋盘与右栏之间缺少卖点展示位，以及动画帧率不稳的问题。

**关键体验问题**：
- 点击“深度分析”后，右侧真正出现有效内容过慢，首屏反馈缺少即时说服力
- 专家卡片 hover 面板虽然能显示内容，但并不够像“正在实时思考”，缺少持续滚动与打字节奏
- 棋盘与右侧分析栏之间的独立空间尚未被正式产品化，无法承载 Evidence Map / 工具灵动岛卖点
- Agent 卡片与协调者球存在高成本持续发光动画，不利于高帧率录屏

**变更**：
- `frontend/src/App.tsx`：分析模式主舞台改为四列网格，其中棋盘与右栏之间单独划出 Evidence 岛列；同时补齐专家工具结果回写，工具名在前端映射为中文短标签
- `frontend/src/components/EvidenceMapIsland.tsx`：新增独立 Evidence Map 灵动岛，实时展示当前调度与最近工具活动，风格收敛为简洁苹果风玻璃卡片
- `frontend/src/components/AgentCardFlip.tsx`：将思维流可见时间点从原先的长串行动画末尾提前到 `cardsLanding` 阶段；缩短整段入场时序；hover 面板无步骤时改为增量打字流；移除高开销 card aura / orb hue-rotate 发光动画，降低掉帧风险
- `frontend/src/store/useAgentStore.ts`：新增 `updateExpertToolResult()`，让工具返回结果可写回最新工具记录，供 Evidence 岛与专家面板消费

**验证**：
- 前端构建通过：`cd frontend && npm run build`
- 测试通过：`pytest -q`

### 2026-04-02 ✅ 完成：开局快答调度优化（v3.72）

**目标**：解决“开局刚走一两步也走重型深度分析链路”的性价比问题，让系统在简单、定式化的早期开局里更快、更稳、更可解释。

**核心问题**：
- deep 分析接口此前只拿到 `fen` 和可选 `move`，缺少完整着法历史，开局书与开局原则无法进入主调度入口
- `force_multi=True` 会把 deep-stream 强行推入重型多专家链路，即使只是第一步中炮、飞相、起马这类高模板化局面
- 前端只能看到专家/合成流，缺少“为什么走这条调度路径”的可视化信息

**变更**：
- `api/main.py`：`/api/analyze/deep-stream` 新增 `history` 参数，向协调器透传完整着法历史，并新增 `dispatch_info` SSE 事件透出调度决策
- `core/llm/analysis_policy.py`：补充 `move_count` 维度，让非强制场景下的超早期开局优先走低成本战略专家路径
- `core/llm/multi_agent_orchestrator.py`：新增 `opening_fast_path`，在开局前几步命中开局书或低信息量窗口时，直接用开局书 + 原则库 + 轻量引擎评估生成快答，绕过强制三专家链路；同时输出结构化调度信息
- `frontend/src/services/api.ts`、`frontend/src/App.tsx`：前端传递历史着法，并展示 `dispatch_info` 调度信息，让用户能看到当前是“开局快答”还是“多专家调度”
- `tests/test_reliability_refactor.py`：新增开局单专家调度测试与 `force_multi` 下仍命中开局快答的回归测试

**验证**：
- 前端构建通过：`cd frontend && npm run build`
- 测试通过：`pytest -q`
- 真实回放验证：直接调用协调器，在 `force_multi=True`、`move_history=['h2e2']` 的场景下稳定返回“中炮开局”快答，且 Span 标记 `decision.opening_fast_path=true`

### 2026-04-02 ✅ 完成：深度分析全链路修复（v3.71）

**目标**：对真实 `GET /api/analyze/deep-stream` 做一次完整实跑，找出深度分析链路中影响比赛演示与答辩稳定性的根因，并完成自修复与回归验证。

**真实问题定位**：
- `force_multi=True` 只能强制多 Agent 模式，不能保证 tactics / strategy / engine 三专家全量出场，导致开局局面经常只跑两个专家
- 预分析线程失败会污染主结果 `result_holder['error']`，即使主链路大体成功，SSE 末尾仍直接吐 `error`
- 引擎池会复用已死亡的 Pikafish 进程，导致 `engine_alternatives` 偶发返回“引擎不可用”或 `Engine process not running`
- 专家层把 `reasoning_content` 当正式正文回退，导致 tool_calls 参数、英文思维、重复废话直接进入 `expert_result`
- `search_chess_knowledge()` 与统一工具调度器不兼容，因多传 `fen` 直接报参数错误
- 合成器在空输出时返回空串，SSE 收尾又用真值判断，最终只剩 `debug_log`，没有 `result`

**变更**：
- `api/main.py`：分离 `precompute_error` 与主链路错误；SSE 收尾改为显式判断 `result is not None`
- `core/llm/multi_agent_orchestrator.py`：`force_multi` 透传为 `force_full_team`；为合成器增加空结果校验与结构化保底讲解
- `core/engine/pool.py`：增加死进程检测、自动重建与重试
- `core/llm/agent_tools.py`：`engine_deep_analysis()` 统一走 `EnginePool`；`search_chess_knowledge()` 兼容统一工具调度器的 `fen` 参数
- `core/llm/experts/base_expert.py`：禁止 `reasoning_content` 充当正式成稿；新增专家输出结构验收与无工具重写修复流程
- `core/llm/experts/tactics_expert.py`、`strategy_expert.py`、`engine_expert.py`：为三专家补充必需章节约束

**真实验证**：
- 使用 `tmp_deep_capture_8003.py` 对 `http://127.0.0.1:8003/api/analyze/deep-stream` 做多轮真实 SSE 回放
- 最终验证结果：
  - 三专家完整出场
  - tactics / strategy / engine 均能输出正式章节化成稿
  - SSE 末尾稳定返回 `result` 与 `debug_log`
  - 捕获文件落盘：`logs/deep_analysis_capture_8003.json`

**当前已知残余风险**：
- 当前 `result` 仍可能走“保底综合讲解”路径，而非理想的高质量原生合成文本；链路已恢复可演示，但综合讲解质量仍值得继续优化

**验证**：
- 实时 API 回放通过：`python .\tmp_deep_capture_8003.py`
- 测试通过：`pytest -q`

### 2026-04-02 ✅ 完成：对局反馈层完善（v3.70）

**目标**：让棋盘在真实对弈过程中不只是“能走”，而是能及时表达风险、结果和操作错误，补齐将军、非法落点和吃子反馈。

**变更**：
- `frontend/src/store/useGameStore.ts`：新增 `checkAlert`、`captureEffect`、`invalidMove` 三类瞬时反馈状态，并消费 `/api/move` 与 `/api/ai-move` 返回的 `captured` / `in_check` / `game_over`
- `frontend/src/services/api.ts`：补齐 `AIMoveResponse` 的 `in_check` 与 `game_over` 类型定义
- `frontend/src/components/ChessBoard.tsx`：新增将军横幅、被将方王位脉冲环、非法走法抖动与红色提示、吃子爆散/闪击特效
- `frontend/src/index.css`：新增非法走法抖动、将军脉冲、吃子扩散与火花动画关键帧

**验证**：
- 前端构建通过：`cd frontend && npm run build`
- 测试通过：`pytest -q`

### 2026-04-02 ✅ 完成：棋盘三期精修（v3.69）

**目标**：在“深墨棋谱盘”结构不变的前提下，把棋盘从“已可用”推进到“完成度更高的教学主舞台”，重点补足动效节奏、材质呼吸感与操作反馈。

**变更**：
- `frontend/src/components/ChessBoard.tsx`：为棋盘外框加入更克制的入场动画，避免内容层突然出现
- 河界新增轻微流光扫动，维持静态秩序的同时提供极弱的时间感
- 新增格点悬停光晕与棋子悬停/按压反馈，让落子前定位更明确、操作更有回弹感
- 所有动效都保持短程、低幅、低饱和，不再回到展示化或 Y2K 式夸张表现
- `frontend/src/index.css`：补充棋盘 hover halo 动画关键帧，统一交互呼吸节奏

**验证**：
- 前端构建通过：`cd frontend && npm run build`
- 测试通过：`pytest -q`

### 2026-04-02 ✅ 完成：棋盘重做二期（v3.68）

**目标**：把棋盘从“被 UI 化过头的展示组件”改回“清晰、稳重、可教学的规则平面”。

**变更**：
- `frontend/src/components/ChessBoard.tsx` 重做为“深墨棋谱盘”
- 重新建立清晰的 9x10 棋盘格、边框、九宫线和星位标记
- 河界取消胶囊形态，改为薄雾横带，并保留压印式“楚河智境”文案
- 棋子统一改为传统象牙棋具式圆子，红黑通过字色区分，而非材质区分
- 外框、阴影、发光、合法点与状态圈整体降噪，改成更克制的教学态表现

**验证**：
- 前端构建通过：`npm run build`
- 测试通过：300 passed in 19.54s

### 2026-04-02 ✅ 完成：棋盘风格纠偏（v3.67）

**问题**：上一版棋盘出现明显的 Y2K / 金属球 / 展示道具感，和项目整体的高级教学系统气质不一致。

**修正**：
- 去掉银红金属球棋子和过强高光，改为温润哑光棋子
- 去掉过重的胶囊河界与强发光，改为更薄的河界雾带
- 棋盘底板收敛为深墨漆面，线条保持细金属线但降低炫技感
- 外框与状态高亮整体降噪，避免像 Y2K 概念稿
- 保留“楚河智境”文案，但调整字重、字距和亮度，更克制

**验证**：
- 前端构建通过：`npm run build`
- 测试通过：300 passed

### 2026-04-02 ✅ 完成：棋盘 UI 重做一期（v3.66）

**目标**：让棋盘与当前 liquid-glass / 蓝青流体 / 高端卡片式界面统一，不改布局，只重做内容层。

**变更**：
- `frontend/src/components/ChessBoard.tsx`：旧木纹铜盘风格 → Aurora Lacquer 液态漆面棋盘
- 河界主文案改为“楚河智境”，并做成河道能量带中的压印式标题
- 棋盘底板重绘：靛蓝漆面渐变、中心冷光、轻纹理噪声、双层金属线框
- 新增星位标记，保留传统象棋识别性但整体视觉更现代
- 棋子改为釉面徽章材质：红方酒红珐琅 / 黑方石墨冷釉，选中时轻微抬升
- 上一步提示、战术高亮、合法点提示全部切换为更轻的环形呼吸效果
- `frontend/src/index.css`：新增 `boardPulseRing` 与 `boardBreath` 动画

**验证**：
- 前端构建通过：`npm run build`
- 测试通过：300 passed in 16.16s

### 2026-04-02 ✅ 完成：重构识别为纯 YOLO 管道（v3.65）

**根本原因**：后端 `/api/recognize` 接的是 GLM-4V-Flash（LLM API），与项目架构不符。
棋盘识别应该是 YOLO + 脚本，100% 本地，无幻觉，无网络依赖。

**技术验证**（测试两张真实棋盘照片）：
- YOLO 模型检测到 `board` 类 → 精确定位棋盘区域
- 棋子中心坐标 → col/row 格点映射（col: 0=最右~8=最左, row: 0=最上~9=最下）
- FEN 字符串生成并验证通过（fen_builder 逻辑）

**变更**：
- 新建 `vision/yolo_recognizer.py`：`YoloDirectRecognizer` 类，懒加载 YOLO 模型，全流程纯本地
- `api/main.py` `/api/recognize` 端点：`VisionAnalyzer(GLM)` → `YoloDirectRecognizer(YOLO)`
- 上传图片限制从 10MB → 20MB（手机拍摄的高清图片通常 10-15MB）
- 300 测试全绿，TypeScript 0 错误

### 2026-04-02 ✅ 完成：三大Bug修复（v3.64）

**引擎栏不更新**:
- `showEngineDock` 条件从 `gameMode === 'analysis'` → `gameMode !== 'replay'`，所有对弈模式均显示引擎栏
- useEffect引擎评估触发去除 analysis-only 限制
- `movePiece` 和 `aiMove` 完成后显式调用 `refreshEngineEvaluation(fen)` 保证每步刷新

**专家分析失败**:
- GLM-5 Extended Thinking 关键Bug修复：`content=""` 但 `reasoning_content` 含实际分析 → 添加 `effective_content` 回退逻辑
- `LLM_MAX_PARALLEL_REQUESTS` 默认值 2→4（3专家+合成器并行需求）
- 熔断器阈值 5→12（3专家×3重试=9次失败不应触发熔断）
- 工具执行超时 30→45秒（引擎深度分析需要更长时间）

**识别404**:
- 端点代码确认正确，需重启服务器加载新路由

### 2026-04-02 ✅ 完成：棋盘视觉识别接入（v3.63）

**变更内容**:
- 后端: `POST /api/recognize` 图片上传端点，调用 `VisionAnalyzer` (GLM-4V-Flash多模态模型) 识别棋盘图片
- 前端: `RecognitionModal` Apple风格弹窗组件 — 图片预览 / 扫描线动画 / 置信度徽章 / 一键应用到棋盘
- Store: `loadFromRecognition(board, fen)` 方法，识别结果直接加载到分析模式
- API Service: `api.recognizeBoard(file)` FormData上传调用
- 300测试全绿，TypeScript 0 错误

### 2026-04-02 ✅ 完成：前后端全面整合（v3.62）

**前端改进**:
- 模式选择器从3→4模式：分析/执红/执黑/双人，iOS段控自适应
- PvE模式下显示难度选择器（简单4/中等10/困难18），金色高亮激活态
- 深度分析按钮"◈ AI 深度分析"入驻左侧栏（分析模式可见）
- 双人模式实现回合制（红黑交替，服务端验证走法）
- `aiDifficulty` 状态管理入Zustand store

**后端修复**:
- AI对弈端点双路由 `/api/ai-move` + `/api/game/ai-move` 兼容
- 请求格式兼容：支持 `{fen}` 和 `{board, red_to_move}` 两种
- 响应格式对齐前端：返回 `from_row/col`, `to_row/col`, `board`, `fen`
- 难度支持字符串和数字两种格式
- ChromaRAG `_get_collection()` 添加 `threading.Lock()` 双重检查锁定
- UCI走法边界校验（列a-i, 行0-9）
- 300测试全绿（+2新测试）

**Plan文档更新**:
- `architecture-perfection-blueprint.md`: P2/P3/P4/P5标记为已完成
- `003-competition-grade-roadmap.md`: 新增Phase 2.5（RAG+对弈，已完成）

### 2026-04-02 ✅ 完成：系统能力跃升（v3.60）

**目标**：补齐系统最大短板——RAG知识检索和对弈模式，修复引擎评分链路。

1. **真实 RAG 系统落地**
   - 新增 `core/rag/chroma_rag.py`：ChromaDB 向量存储替代 MockRAG
   - 80+ 棋理原则自动向量化索引（首次访问时懒加载）
   - 支持 14 万局棋谱开局信息按需索引（`index_game_openings()`）
   - 三种检索模式：语义/按阶段过滤/按文档类型过滤
   - 新增 `search_chess_knowledge` Agent 工具，战略专家可调用知识库检索

2. **对弈模式 API**
   - 新增 `POST /api/game/ai-move`：AI 走棋端点
   - 三级难度：easy(depth=4) / medium(depth=10) / hard(depth=18)
   - 返回 UCI 走法 + 中文描述 + 引擎评分 + 走后FEN + 将军/将杀状态
   - 合法性双重验证（引擎走法 + RuleEngine 校验）

3. **引擎评分链路修复**
   - 后端：`result.score or 0.0` truthiness bug → `result.score if result.score is not None else 0.0`
   - 后端：BestMovesResponse 新增 score/depth 字段
   - 前端：fallback 路径从硬编码 `score: 0` 改为读取服务端真实分数

4. **系统能力全面审计（8个子系统评估）**
   - 棋力深度 6/10、知识面广度 4→6/10(RAG落地后)、教学能力 7/10
   - 对弈能力 3→6/10(API落地后)、对局复盘 5/10、自我纠错 6/10
   - RAG知识检索 2→6/10(ChromaDB落地后)、前端体验 8/10

5. **新增测试**
   - `tests/test_rag.py`：13 项 RAG 测试（索引/检索/过滤/工具）
   - `tests/test_ai_play.py`：7 项对弈 API 测试（三难度/黑方/中局/格式）

**验证结果**：`pytest -q` → 298 passed, 0 failed

### 2026-04-02 ✅ 完成：Phase 2 证据裁决化（v3.58）

**目标**：让合成器成为"证据裁判"，而不是"文本合并器"。

1. **结构化断言 (Claim) 系统**
   - 新增 `core/llm/claim.py`：`Claim` / `EvidenceItem` / `EvidenceChain` 数据结构
   - 每条断言绑定来源 (`tool_verified` / `reasoning` / `unverified`) 和置信度
   - `ClaimParser` 支持两种格式：显式 `[CLAIM][EVIDENCE][CONFIDENCE]` 标记 + 传统【节标题】回退

2. **工具调用证据链捕获**
   - `base_expert.py` 新增 `_backfill_tool_result()` — 工具执行后将 output 回填到 `tool_calls_log`
   - 新增 `_build_evidence_chain()` — 从 `tool_calls_log` 构建 `EvidenceChain`
   - 只读工具和串行工具两个执行路径均已接入

3. **ExpertResult v2**
   - 新增 `claims: List[Claim]` 和 `evidence_chain: Optional[EvidenceChain]` 字段
   - 两个成功返回路径（正常结束 + 最大轮次强制结束）均填充 claims/evidence_chain
   - 向后兼容：旧字段 (finding/details/tool_calls) 保持不变

4. **专家 Prompt 结构化断言要求**
   - 战术/战略/引擎三专家的 system prompt 末尾新增"结构化断言"输出章节
   - 要求 LLM 在分析结束时输出 `[CLAIM]...[EVIDENCE]...[CONFIDENCE]...` 标记
   - 如果 LLM 不遵从（旧模型或格式偏差），回退解析器仍能从传统格式提取

5. **合成器证据裁决升级**
   - `SYNTHESIZER_SYSTEM_PROMPT` 从"综合裁判"升级为"证据裁决者"
   - 新增断言对齐 + 证据交叉验证 + 证据权重裁决规则
   - `_format_expert_block()` 优先注入结构化断言和证据链，而非自由文本
   - 输出格式新增【证据基础】段

6. **Phase 2 测试覆盖**
   - 新增 `tests/test_claim.py`（20 项测试）
   - 覆盖：显式标记解析、回退格式解析、证据链构建、回填逻辑、ExpertResult v2 字段、合成器格式化

**验证结果**：`pytest -q` → 278 passed, 0 failed

### 2026-04-02 ✅ 完成：规则引擎正确性固化（v3.57）

**目标**：确保合法走法生成器100%正确——自将过滤、将帅照面、攻击范围分离。

1. **自将过滤修复**（前一 session）
   - `XiangqiRulesEngine._is_valid_move()` 重写：走后检查己方将/帅是否被攻击
   - 新增 `_get_raw_moves()` / `_is_square_attacked()` / `_kings_face_each_other()`
   - 打破递归链：`_is_square_attacked` 使用 `_get_raw_moves`（不含自将过滤）

2. **攻击范围 vs 合法走法分离**
   - `TacticalDetector._get_attacks()` 改用 `_get_raw_moves()`（攻击范围不过滤自将）
   - 核心原则：被牵制的棋子虽不能移动，但仍然威胁横向格子

3. **新增 15 项规则正确性测试**
   - `tests/test_rules_correctness.py`
   - 覆盖：牵制车/马的自将过滤、帅入将军、被将必须解将、照面检测、棋子不能导致照面、RuleEngine 初始走法数/将死/困毙、合法走法一致性、攻击范围 vs 合法走法分离

**验证结果**：`pytest -q` → 258 passed, 0 failed

### 2026-04-02 ✅ 推进：Phase 1 动作空间约束（v3.56）

**目标**：把系统从“自由写走法再让工具兜底”推进到“先取合法候选，再基于候选分析”的受约束模式。

1. **候选走法服务落地**
  - 新增 `core/llm/move_candidate_service.py`
  - 基于合法走法生成稳定 `cand_1 / cand_2 / ...` 编号
  - 提供 `get_candidates()` 与 `resolve_move()`，作为 candidate_id 协议的统一入口

2. **工具层接入 candidate_id 协议**
  - `core/llm/agent_tools.py` 新增 `get_move_candidates()`
  - `analyze_move / compare_moves / get_forcing_sequence / simulate_move` 全部支持 candidate_id 优先
  - 非法 candidate_id 会显式失败，不再默默回退成“看起来分析成功”

3. **专家链与单Agent链收口**
  - `core/llm/experts/base_expert.py`、三专家 schema、`core/llm/xiangqi_coach.py` 全部加入 `get_move_candidates`
  - 共享规则与系统提示词新增硬约束：分析具体走法前优先先拿候选，再传 candidate_id
  - 目标是从 prompt 层和工具层同时压缩 LLM 自由编造走法的空间

4. **RuleEngine 根因修复**
  - `core/rules/rule_engine.py` 不再依赖当前环境下不兼容的 `perft 1` 输出解析
  - 改为直接复用仓库内已有 `XiangqiRulesEngine` 生成合法走法
  - 修复了 candidate 服务在测试环境中因底层合法走法生成失败而整体不可用的问题

5. **新增候选协议回归测试**
  - `tests/test_new_tools.py` 新增 candidate_id 协议测试
  - 覆盖 `get_move_candidates`、`analyze_move(candidate_id)`、`compare_moves(candidate_ids)`、`simulate_move(candidate_id)`、`get_forcing_sequence(candidate_id)`、非法 candidate_id 失败路径
  - `tests/test_multi_agent.py` 补齐三专家都暴露 `get_move_candidates` 的断言

**当前判断**：
- Phase 1 主干已经进入可运行状态，但还没有完成“前端显式消费 candidate 来源”和“所有结论都展示候选来源”的终局收口
- 这一步已经实质性削弱了“模型自由写非法走法”这个核心失真源

**验证结果**：
- `pytest -q` → 全绿

### 2026-04-02 ✅ 完成：可靠性重构一期（v3.55）

**目标**：先解决“专家经常失败”和“失败后还像成功一样继续输出”的结构性问题。

1. **统一 LLM 可靠性客户端**
  - 新增 `core/llm/reliable_client.py`
  - 实现统一 `complete()` / `stream_complete()` 接口
  - 支持 429/5xx 重试、指数退避、并发信号量、简单 circuit breaker
  - 专家链、单Agent链、合成器链不再各自裸调 requests

2. **结构化状态与错误码**
  - 新增 `core/llm/contracts.py`
  - 引入 `AnalysisStatus` / `ExpertFailureType` / `DegradationLevel`
  - `ExpertResult` 增强：新增 `status/failure_type/confidence/missing_evidence/retry_count/degraded`
  - 失败原因不再只靠字符串表达

3. **门控式专家调度**
  - 新增 `core/llm/analysis_policy.py`
  - orchestrator 从固定三专家并行，改为按问题类型/阶段/张力选择专家组合
  - 默认并发度受 `LLM_MAX_PARALLEL_REQUESTS` 控制，限流场景下自动降并发
  - 未选中的专家不再伪装成功，而是显式标记为 `skipped`

4. **失败感知合成器**
  - `core/llm/multi_agent_orchestrator.py` 的 `Synthesizer` 改为基于结构化 `ExpertResult` 工作
  - 成功专家少于2个时，不再继续生成“完整综合讲解”
  - 改为输出显式降级说明：哪些专家缺失、当前结论来自谁、可信度为何下降

5. **专家链失败治理增强**
  - `core/llm/experts/base_expert.py` 接入可靠性客户端
  - 工具错误会被记录为 degraded，而不是悄悄吞掉
  - 最大轮次后的 final_response 失败路径已修复，不再误报 success

6. **新增可靠性回归测试**
  - 新增 `tests/test_reliability_refactor.py`
  - 覆盖 429 重试成功、重试失败、策略选专家、降级合成、orchestrator 裁剪专家 等场景

**验证结果**：
- `python -m pytest --tb=short` → 237 passed

### 2026-04-02 ✅ 完成：知识体系深度扩展（v3.54）

**知识库全面升级**（5项核心改进）：

1. **棋理原则从20条扩展到80+条 [P0 知识库]**
   - `core/llm/knowledge_retriever.py` 重写 `TENSION_PRINCIPLES` + `GENERAL_PRINCIPLES`
   - 原6种张力类型 → 11种（新增 attack_pattern / opening_theory / endgame_theory / defense_pattern / piece_coordination）
   - 每条原则新增 `phase`（阶段）和 `tags`（关联标签）字段
   - 原则来源覆盖《橘中秘》《梅花谱》《适情雅趣》等经典棋书 + 公认棋理谚语

2. **知识库多维检索 [P0 查询增强]**
   - 新增 `query_by_tags()` 方法：按标签名检索所有类型中匹配的原则
   - `query_for_tension()` 增加阶段过滤：匹配阶段的原则优先返回
   - 新增 `_normalize_phase()` 支持中英文阶段名互转
   - Prompt 输出从最多3条扩展到5条，新增出处信息

3. **引擎 MultiPV 真多候选 [P1 tools 修复]**
   - `core/engine/pikafish_engine.py` 新增 `analyze_multipv()` 方法，使用 UCI MultiPV 参数
   - `core/engine/pool.py` 新增线程安全的 `analyze_multipv()` 接口
   - `agent_tools.py` `engine_alternatives()` 从"分析1次返回1个"→"MultiPV返回真实top-N候选"
   - 每个候选包含：rank/move/eval_cp/pv变例/explanation/risk

4. **强制序列多深度追踪 [P1 tools 修复]**
   - `agent_tools.py` `get_forcing_sequence()` 从"只检查第1步是否将军"→"递归追踪将军-应将链"
   - 新增 `_find_best_response()` 引擎+规则双降级寻找应着
   - 新增 `_find_any_legal_move()` 暴力搜索合法走法（引擎不可用时降级）
   - 新增 `_get_piece_moves()` 各棋子走法生成 + `_board_to_fen()` 棋盘重建
   - 可检测将杀（无合法应将 = checkmate）

5. **开局库大幅扩展 [P2 开局识别]**
   - `core/opening/opening_book.py` 开局序列从10条扩展到29条
   - 新增体系：中炮vs三步虎/单提马/飞象、飞相局4变化、起马局3变化、仙人指路3变化、过宫炮/士角炮变化、对兵局
   - 每条开局含详细的战略描述和评估

**新增测试**：28项（`tests/test_knowledge_base.py`）
- 知识库覆盖率、数据完整性、查询方法、Prompt 生成、开局识别

**验证结果**：
- `python -m pytest -q` → 231 passed（203 + 28 新增）

### 2026-04-02 ✅ 完成：前端UX流式体验升级（v3.53）

**修复两个核心UX问题**：

1. **专家悬浮窗真实时流式 [Problem 1]**
   - **根因**: `ExpertHoverStream` 读取 `expertState.finding`（一次性赋值）后用 `useNaturalReveal` 假打字机模拟流式 → 实为「完成后一并显示」
   - **修复**: 重写 `ExpertHoverStream` 组件，直接订阅 `expertState.steps`（由 `expert_step_content` SSE 增量推送）
   - 分析中：实时渲染每个步骤卡片 + ⟳/✓ 状态标记 + 闪烁光标
   - 分析后：显示完整推理步骤链（或回退到 `finding` 文本）
   - 删除废弃的 `useNaturalReveal` hook

2. **协调者思维链步骤卡片修复 [Problem 2]**
   - **根因**: `_SUBTITLE_PATTERN`（`## N title`）只触发 `orchestrator_subtitle` 事件，不创建步骤 → 当模型只输出 `##` 标题而省略 `[STEP:]`/`【】` 标记时，`orchestrator.steps` 为空
   - **修复**: `SynthesisStepStreamParser._process_line()` 中 `## N title` 现在同时创建步骤（`synthesis_step_start`），与 `[STEP:]` 和 `【节标题】` 行为一致
   - 三种标记格式均可触发步骤卡片渲染

3. **StepItem 去 typewriter 闪烁**
   - 步骤内容由 SSE 增量推送，`useTypewriter` 在每次 chunk 到来时重置导致闪烁
   - 改为直接渲染 `content` + 活跃步骤显示闪烁光标
   - 删除废弃的 `useTypewriter` hook

4. **专家进度概览**
   - 协调者等待阶段（无 subtitle/content/steps 时）不再显示空白 "协调者正在分析..."
   - 新增 `ExpertProgressOverview` 组件：三位专家实时状态卡片 + 进度条 + 当前步骤标题
   - 全部完成后显示 "协调者正在综合三位专家结论..."

**变更文件**：
- `frontend/src/components/AgentCardFlip.tsx` — ExpertHoverStream 重写 + ExpertGlassPanelFlip 接口更新 + 删除 useNaturalReveal
- `frontend/src/components/ThinkingStream.tsx` — StepItem 去 typewriter + ExpertProgressOverview + 自动滚动优化 + 删除 useTypewriter
- `core/llm/multi_agent_orchestrator.py` — SynthesisStepStreamParser `## N title` 同时创建步骤

**验证结果**：
- `cd frontend && npm run build` → 通过
- `python -m pytest -q` → 203 passed

### 2026-04-02 ✅ 完成：多Agent架构深度优化（v3.52）

**架构级改造**（6项关键优化）：

1. **结构化Evidence Map管线 [P0]**
   - `core/llm/multi_agent_orchestrator.py` 新增 `_build_structured_evidence_map()` 方法
   - 构建包含 tags/bind_pieces/tensions/engine/piece_count 的 JSON 结构
   - `core/llm/experts/base_expert.py` 的 `_build_shared_context()` 支持双路径：结构化EM（优先）vs 文本tag_summary（回退）
   - 解决原来38个标签被压缩为纯文本丢失结构的 P0 问题

2. **新增2个Agent工具 [P2+P4]**
   - `simulate_move`：模拟走棋并对比前后标签差异、将军检测、吃子信息
   - `query_chess_principles`：检索局面适用的棋理原则（按张力类型过滤）
   - Agent工具总数 10→12，工具注册表（TOOL_META/READONLY_TOOLS/_tool_functions/AGENT_TOOLS）全部更新

3. **引擎连接池 [P5]**
   - 新建 `core/engine/pool.py`，`EnginePool` 单例 + `analyze_lock` 并发安全
   - `api/main.py` 所有 `PikafishEngine()` 替换为 `engine_analyze()`，消除每次请求 ~200ms 启动开销
   - 移除所有 `engine.start()` / `engine.stop()` 手动生命周期管理

4. **共享规则提取 [prompt优化]**
   - `base_expert.py` 新增 `CHESS_RULES_BLOCK` 常量（~800 tokens）
   - 三专家从各自内联字符串改为引用共享常量，消除 3x 重复
   - 每次多Agent调用节省约 1600 tokens

5. **专家提示词增强**
   - 战术专家：`simulate_move` 使用指引写入验证步骤
   - 战略专家：`query_chess_principles` 写入评估维度 + `simulate_move` 写入计划推演
   - 引擎专家：添加引擎走法规则校验硬约束

6. **Synthesizer证据链 [P3]**
   - `Synthesizer.synthesize()` 现在接收各专家的 `tool_calls` 列表
   - 综合分析时包含真实工具调用数据作为论据，而非仅靠文本摘要

**新增测试**: 17个测试覆盖 simulate_move / query_chess_principles / Evidence Map 构建 / 专家上下文双路径 / 引擎池单例

**验证结果**：
- `python -m pytest -q` → 203 passed（186原有 + 17新增）

### 2026-04-02 ✅ 完成：修复深度分析上下文错位与重复综合结论（v3.51）

**本次改造**：
- `frontend/src/App.tsx`
  - 无走子上下文时不再使用 `previousFen || fen`，改为严格分析当前 `fen`
  - 问题文案改为“严格基于当前棋盘局面进行分析，不要假设刚刚已经走过某一步”
  - 协调者正文只接收真正的 `synthesis_chunk`，不再把“启动分析/检测局面/分析进行中”这类通用进度词拼进最终结论
  - `result.explanation` 仅在协调者正文为空时兜底追加，避免前端重复拼接最终结论
- `frontend/src/store/useGameStore.ts`
  - `resetGame / loadGameFromNeo4j / loadGameFromPGN / navigateReplay / exitReplay` 时统一清空 `previousFen`
  - AI 走子时补齐 `previousFen`，避免后续上一手点评语境错乱
- `api/main.py`
  - 移除 deep-stream 结束阶段的二次 `result` 发送，避免后端重复输出同一份综合结论

**当前结果**：
- 开局未走子时，分析请求会基于当前局面本身，而不是误带上一手语境
- 协调者区不再出现整段综合结论被重复粘贴两遍的情况
- 通用进度提示会作为阶段提示，而不是污染最终正文

**验证结果**：
- `cd frontend && npm run build` → 通过
- `python -m pytest -q` → 全绿

### 2026-04-02 ✅ 完成：深度分析后端流式接入新版前端 Agent 面板（v3.50）

**本次改造**：
- `frontend/src/App.tsx`
  - 修复“点分析只开面板、不发请求”的断链问题
  - 将旧 `DeepAnalysisPanel` 中真正负责 SSE 分析的逻辑接到当前 App 的 `triggerDeepAnalysis()`
  - 点击右上角 `深度分析` 后，现有新版右侧扑克牌/协调者面板会直接接收后端 `/api/analyze/deep-stream` 的流式事件
  - 接入事件映射：`expert_start / expert_result / expert_step_* / synthesis_* / orchestrator_subtitle / thinking_chunk`
  - 分析失败时不再静默无响应，而是在协调者区显示失败文本
  - 面板关闭时主动关闭活跃 `EventSource`，避免残留连接

**当前结果**：
- 点击分析会真正触发后端深度分析
- 三专家卡片与协调者区可消费后端流式内容，而不是只播放空动画

**验证结果**：
- `cd frontend && npm run build` → 通过
- `python -m pytest -q` → 全绿

### 2026-04-02 ✅ 完成：搜索栏液态节奏校准 + 引擎栏大字回归 + 协调者内容区去黑框（v3.49）

**本次改造**（基于最新截图反馈）：
- `frontend/src/components/LiquidGlassApp.tsx`
  - 左侧搜索玻璃 shape1 追踪改为更高 lerp，显著快于 DOM 内容显现，减少“内容已到位但 WebGL 还在慢慢追”的违和感
  - 保持几何动画直接对齐目标外框，收口更利落
- `frontend/src/components/LeftSidebar.tsx`
  - 搜索框的几何上报从内层 shell 改为外层 overlay，玻璃包裹范围与实际内容外框一致
  - DOM 内容显现节奏略放缓，而 WebGL 变形提速，二者更接近苹果式“玻璃先到位、内容随后安定”的节奏
  - 在亮背景下将搜索标题、输入框、结果文字统一切换为更深的暖灰/金棕系，提高可读性
- `frontend/src/components/EngineChart.tsx`
  - 在顶部新增大字优势信息，如“红优 233 分 / 黑优 23 分”，保留苹果式大字号信息感
  - 同时保留折线图主体布局，不再回到旧的冗余大数字双栏
- `frontend/src/components/ThinkingStream.tsx`
  - 去掉协调者下面突兀的大黑框，改为更轻的半透明内容区 + 细竖向强调线
  - 底部遮罩改轻，整体更接近玻璃层里的阅读区域，而不是独立黑色卡片

**验证结果**：
- `cd frontend && npm run build` → 通过
- `python -m pytest -q` → 全绿

### 2026-04-01 ✅ 完成：引擎栏折线主体化 + 右栏去层 + iOS搜索动画（v3.48）

**本次改造**（基于用户截图反馈 + 提问工具对齐）：
- `frontend/src/components/EngineChart.tsx`
  - 删除 46px 大数字胜率和评估分（有胜率条即不需要冗余大数字）
  - 布局改为 flex 纵向：折线图 flex:1 占满主体 → 底部一行（迷你胜率条 + 评分 + 着法 + 深度）
  - 修复折线被截断看不全的问题（之前被 metricStrip/probabilityWrap 挤压导致 chartArea 高度不足）
- `frontend/src/components/AgentThinkingPanel.tsx`
  - 完全删除 v3.47 新增的仿 macOS 外框（红黄绿灯点、标题栏、radial-gradient 装饰、glass border）
  - 回归简洁透明容器，让底层 WebGL LiquidGlassApp shape3 作为唯一背景
- `frontend/src/components/AgentCardFlip.tsx`
  - ExpertActivityPanel 宽度 178→164，边距和字号收紧，色调统一为低饱和白色系
  - SplitLayout 内边距 18→12/14，分隔线改柔和白色，右侧协调者面板去掉重 boxShadow
- `frontend/src/components/LeftSidebar.tsx`
  - 搜索框动画改为 iOS 风格缩放：从按钮位置 scale 0.4→1（150ms），关闭时缩回 scale 0.45
  - 删除所有 setTimeout 延迟和位移动画，实现即时响应
  - transformOrigin 设在按钮位置（24px 0%），视觉上从按钮弹出

**验证结果**：
- `npm run build` → 通过（565 modules, 2.09s）
- `pytest -q` → 186 passed

### 2026-04-01 ✅ 完成：搜索浮层提速、引擎栏图表优先与右栏 macOS 化收束（v3.47）

**本次前端改造**：
- `frontend/src/components/LeftSidebar.tsx`
  - 搜索浮层开合时延从肉眼可感的拖拽式过渡改为更短促的系统级过渡
  - 内容淡入与液态几何扩张分离，减少“慢、钝、像网页”的感觉
- `frontend/src/components/EngineChart.tsx`
  - 去掉“最佳着法 / 搜索深度 / 合法着数”三个大块占位，改为一行紧凑元信息
  - 进一步放大图表区域，主折线描边加粗并加发光，优先保证走势可见性
- `frontend/src/App.tsx`
  - 分析态棋盘再上移一档，引擎栏高度回收，为折线图腾出更高可用区域
- `frontend/src/components/AgentThinkingPanel.tsx`
  - 右侧分析区增加统一顶栏、系统灯点、柔和环境光和整体内框，收束成单一工作台
- `frontend/src/components/AgentCardFlip.tsx`
  - 调整专家列 / 协调者列比例
  - 专家活动卡和协调者区改为统一玻璃底板，减少漂浮碎块感
- `frontend/src/components/ThinkingStream.tsx`
  - 协调者流式内容区改为更柔和的蓝色玻璃面，去掉原先过黑的矩形块观感

**当前交互结果**：
- 打棋谱搜索框展开更快、更脆，不再拖泥带水
- 引擎栏现在更明确地以折线走势为主，而不是被三个信息块挤占空间
- 右侧分析模式从“几块分散悬浮内容”收束成更接近 macOS 工作台的统一窗口

**验证结果**：
- `cd frontend && npm run build` → 通过
- `python -m pytest --tb=short | Select-Object -Last 5 | Out-String` → `186 passed in 6.92s`

### 2026-04-01 ✅ 完成：左栏统一 WebGL 液态材质系统与引擎栏图表修复（v3.46）

**本次前端改造**：
- `frontend/src/components/LeftSidebar.tsx`
  - 左栏操作区从“CSS 玻璃面板 + 独立 WebGL 按钮”改为“统一 WebGL 玻璃体 + 透明 DOM 控件层”
  - `打棋谱` 点击时先把液态几何收缩到按钮，再扩展为搜索容器，实现连续液态形变
  - 走法记录框进一步压缩高度，底部比例更稳定
- `frontend/src/App.tsx`
  - 新增左栏液态几何状态回传，让 WebGL 层根据真实 DOM 矩形驱动 shape1
  - 引擎栏定位改为整数像素并固定高度，减少视觉歪斜和模糊
- `frontend/src/components/LiquidGlassApp.tsx`
  - shape1 改为由左栏/搜索框实测矩形驱动，不再依赖固定参数死板定位
  - 新增 shape1 几何弹簧过渡，支撑按钮到搜索框的连续液态变形
- `frontend/src/components/EngineChart.tsx`
  - 图表坐标改为按真实图表区域测量，修复折线被裁切导致“看不到分数折线图”的问题
  - 新增红黑胜率比例条，用直观面积分配取代纯数字呈现
  - 单点评估时自动补平滑兜底折线，空局面也能维持完整信息框架

**当前交互结果**：
- 引擎栏现在会稳定显示可见折线，而不是只剩大数字没有走势
- 胜率改为红黑比例条，红黑优劣一眼可读
- 左栏关闭态是一整块统一液态玻璃，不再是按钮材质和面板材质割裂
- 打开打棋谱时，液态几何会从按钮连续扩展为搜索容器，整体更接近一体化 Apple 式材质运动

**验证结果**：
- `cd frontend && npm run build` → 通过
- `python -m pytest -q` → 通过
- `python -m pytest --tb=short | Select-Object -Last 5 | Out-String` → `186 passed in 6.92s`

### 2026-04-01 ✅ 完成：分析态引擎栏 bugfix 与接口降级兼容（v3.45）

**本次修复**：
- `api/main.py`
  - 新增轻量级 `/api/engine/evaluate` 接口，只返回 Pikafish 核心评估结果
  - 避开原 `position-analysis` 混入规则层后导致的 500 错误
- `frontend/src/services/api.ts`
  - `getEngineEvaluation()` 改为优先调用 `/api/engine/evaluate`
  - 若用户当前运行的是旧后端，自动降级到 `/api/best-moves`，避免引擎栏直接报错
- `frontend/src/App.tsx`
  - 修复引擎栏在非分析模式下仍显示的问题
  - 修复分析态引擎栏未停靠在棋盘正下方的问题，改为按棋盘真实矩形绝对定位
  - 分析态下棋盘自动上移并轻微缩放，为引擎栏腾出稳定空间
- `frontend/src/components/LeftSidebar.tsx`
  - 缩短走法记录框高度，避免空局面时纵向比例失衡

**当前结果**：
- 引擎栏只在分析模式显示
- 进入分析模式后，引擎栏会停靠在棋盘正下方，而不是漂到底部或出现在错误模式
- 旧后端未重启时，前端也不会直接进入“异常”状态
- 左栏棋谱框长度回到更接近 5-6 行的视觉比例

**验证结果**：
- `FastAPI TestClient -> POST /api/engine/evaluate` → `200`，返回真实 Pikafish 结果
- `cd frontend && npm run build` → 通过
- `python -m pytest --tb=short` → `186 passed in 5.74s`

### 2026-04-01 ✅ 完成：左栏层级重排与 Pikafish 引擎栏真接线（v3.44）

**本次前端改造**：
- `frontend/src/components/LeftSidebar.tsx`
  - 将左栏信息层级重排为“模式/操作在上，走法记录在下”
  - 走法记录框沉到底部并占据剩余高度，更符合控制优先的布局逻辑
- `frontend/src/services/api.ts`
  - 新增 `getEngineEvaluation()`，直接从后端结构化局面分析提取 Pikafish 评分结果
- `frontend/src/store/useGameStore.ts`
  - 新增 `enginePanel` 状态，统一承载最佳着法、评分、深度、PV、合法着数与加载/错误态
  - 新增 `refreshEngineEvaluation()`，在局面切换后刷新 Pikafish 真评估，并写入 `evalHistory`
  - 重开、载入棋谱、退出回放时同步清空旧局面的引擎走势
- `frontend/src/App.tsx`
  - 局面 `fen` 变化时自动触发引擎刷新
  - 引擎栏改为稳定停靠在棋盘下方，而不是只在折叠态下显示
- `frontend/src/components/EngineChart.tsx`
  - 接入 `enginePanel` 真数据
  - 增加引擎加载态、错误态、最佳着法/搜索深度/合法着数摘要区

**当前交互结果**：
- 左栏不再是“棋谱压在上面、操作挤在下面”的结构，控制区优先级更清晰
- 引擎栏已经真正读取 Pikafish 结果，不再只是前端空数据图表
- 棋盘下方始终可见引擎信息面板，连续显示评分走势与当前最佳着法

**验证结果**：
- `cd frontend && npm run build` → 通过
- `python -c "from core.engine import PikafishEngine; ..."` → 成功返回 `{'bestmove': 'c3c4', 'score': 0.12, 'depth': 8, 'pv': [...]}`
- `python -m pytest --tb=short` → `186 passed in 5.09s`


### 2026-04-01 ✅ 完成：左侧栏交互升级一期（v3.43）

**本次前端改造**：
- `frontend/src/components/LeftSidebar.tsx`
  - 新增固定左侧栏独立组件，承载 Logo、走法记录、模式分段控件与操作区
  - 打棋谱改成搜索浮层工作流：左栏主体淡出，搜索容器向棋盘左缘展开
  - 搜索结果直接接入现有 `/api/games/search` 与 `/api/games/{id}`，选局后进入回放态
  - 回放态左栏切换为“走法记录 + 上一步/下一步/退出打棋谱”
- `frontend/src/utils/moveNotation.ts`
  - 新增 ICCS 走法到中文记谱的前端格式化工具
  - 支持实时对局历史在左栏按红黑双列显示
- `frontend/src/App.tsx`
  - 左栏改为独立组件接管，主布局只保留棋盘、引擎栏与右侧思考区
  - 新增棋盘左边界测量，供打棋谱搜索浮层计算展开宽度
- `frontend/src/components/EngineChart.tsx`
  - 从“小图标+细折线”重构为“大数字胜率/评估分 + 折线图 + hover tooltip”
  - tooltip 现显示回合数、评估分、胜率与深度
- `frontend/src/components/WebGLButton.tsx`
  - 修正定位方式，重新用于左栏操作按钮承载 WebGL 渲染按钮

**当前交互结果**：
- 左栏固定显示 5-6 行量级的走法记录，并随对局自动滚动
- 打棋谱不再直接跳模式，而是先进入搜索浮层，再选择历史对局
- 回放控制已收回左栏，符合“边看棋盘边翻谱”的布局目标
- 引擎栏在分析态下更接近 iOS 大数字信息面板，而不再只是占位图表

**验证结果**：
- `cd frontend && npm run build` → 通过
- `python -m pytest --tb=short` → `186 passed in 6.27s`

### 2026-04-01 ✅ 完成：补齐 plan 剩余可视化目标（v3.42）

**本次补齐**：
- `frontend/src/components/AgentCardFlip.tsx`
  - ExpertGlassPanel 悬停态不再显示静态 abilities
  - 分析中显示实时 `thinkingContent`
  - 完成后切换为完整 `finding`
  - 增加自然停顿、自动滚动、底部遮罩、光标跟随
- `frontend/src/components/ThinkingStream.tsx`
  - 右侧改成上下两区：上方“当前阶段”标题区，下方正文内容区
  - 内容区改为更自然的流式节奏，增加自动滚动和底部渐隐遮罩
- `frontend/src/store/useAgentStore.ts`
  - `orchestrator` 新增 `subtitles` 历史数组
- `core/llm/multi_agent_orchestrator.py`
  - 协调者新增 `orchestrator_subtitle` 事件发送
  - `expert_result` 改为 `summary + finding` 双字段，`finding`承载完整结论，不再塞截断 `details`
- 三位专家 Prompt
  - 新增 `## [N] [阶段标题]` 约束，强化阶段性输出

**验证结果**：
- `python -m pytest --tb=short` → `186 passed`
- `frontend/npm run build` → 通过

---

### 2026-04-01 ✅ 修复：协调者步骤不显示bug（v3.41）

**问题现象**：用户启动深度分析后，协调者区域只显示"协调者正在分析..."占位文本，无任何步骤或内容。

**根因分析（三层bug叠加）**：
1. **模型不输出`[STEP:]`标记** → 解析器整个流式阶段无事件产出
2. **降级方案只在流结束后才发一次`synthesis_chunk`** → 流式期间前端零内容
3. **`synthesis_chunk`事件存在JSON双重编码** → API层包了两次`json.dumps`，前端拿到JSON字符串而非文本

**后端修复**：
- `core/llm/multi_agent_orchestrator.py`
  - 流式循环中始终实时推送`synthesis_chunk`（不再只在结束时推送一次）
  - 新增`【节标题】`隐式步骤检测（如`【综合评估】`→自动触发`synthesis_step_start`）
  - 模型几乎总会输出这类中文节标题，可靠性远超`[STEP:]`标记
- `api/main.py`
  - 修复`synthesis_chunk`的JSON双重编码：先`json.loads`解码再取`.message`

**前端修复**：
- `frontend/src/components/ThinkingStream.tsx`
  - 修复`orchestrator.content`的items累积bug：改为直接渲染流式文本
  - 三层降级：步骤卡片 → 流式文本 → 等待占位

**新增测试**：
- `tests/test_step_protocol.py`：`【节标题】`隐式步骤解析 + 混合`[STEP:]`与`【section】`场景

---

### 2026-04-01 ✅ 完成：协调者步骤协议落地（v3.40）

**本次目标**：把右侧协调者综合流也升级成结构化步骤，让“专家并行分析 → 协调者综合归纳”形成统一可见链路。

**后端改动**：
- `core/llm/multi_agent_orchestrator.py`
  - 合成器 Prompt 新增 `[STEP: ...]` 输出约定
  - 新增 `SynthesisStepStreamParser`，把流式输出解析为 `synthesis_step_start/content/end`
  - 保留 `synthesis_chunk` 兼容分支，避免旧前端直接断流
- `api/main.py`
  - SSE 新增转发 `synthesis_step_start`
  - SSE 新增转发 `synthesis_step_content`
  - SSE 新增转发 `synthesis_step_end`

**前端改动**：
- `frontend/src/store/useAgentStore.ts`
  - `orchestrator` 新增 `steps`
  - 新增 `addOrchestratorStep/appendOrchestratorStepContent/finalizeOrchestratorStep`
- `frontend/src/components/ThinkingStream.tsx`
  - 右侧协调者面板优先展示结构化步骤卡片
  - 保留旧 `subtitle + content` 文本流回退
- `frontend/src/components/DeepAnalysisPanel.tsx`
  - 接入 `synthesis_step_*` 事件
  - `orchestrator_subtitle` 与 `synthesis_chunk` 分开处理，避免状态污染
- `frontend/src/services/api.ts`
  - 深度分析 SSE 消息类型扩展到 `synthesis_*`

**测试补充**：
- `tests/test_step_protocol.py`
  - 新增协调者流式步骤解析测试
  - 新增无步骤标记回退测试

**当前效果**：
- 左侧三专家展示最近步骤摘要
- 右侧协调者按步骤显示“综合判断是如何形成的”
- 专家与协调者都遵循统一的 `[STEP:] -> 结构化SSE -> 前端步骤卡片` 协议

---

### 2026-04-01 ✅ 完成：多Agent步骤协议首版落地（v3.39）

**本次目标**：把“思考步骤可见”从纯文本流升级为结构化步骤流，让前端能直接显示三位专家分别在做什么。

**后端改动**：
- `core/llm/experts/base_expert.py`
  - 新增 `parse_step_blocks()`，解析专家输出中的 `[STEP: ...]`
  - 新增 `_emit_structured_steps()`，发出 `expert_step_start/content/end`
  - `_extract_finding()` 会自动去掉 `[STEP:]` 标记，避免摘要污染
- 三位专家 Prompt：
  - `tactics_expert.py`
  - `strategy_expert.py`
  - `engine_expert.py`
  - 均新增 `[STEP: 你正在做什么]` 输出约定
- `api/main.py`
  - SSE 新增转发 `expert_step_start`
  - SSE 新增转发 `expert_step_content`
  - SSE 新增转发 `expert_step_end`

**前端改动**：
- `frontend/src/store/useAgentStore.ts`
  - 新增 `steps` 状态
  - 新增 `addExpertStep/appendExpertStepContent/finalizeExpertStep`
- `frontend/src/components/DeepAnalysisPanel.tsx`
  - 接入 `expert_step_*` 事件
  - 修复 `expert_result` 状态更新逻辑（`done` → `completed`）
- `frontend/src/components/AgentCardFlip.tsx`
  - 左侧三专家区域新增步骤摘要面板
  - 当前步骤默认展开，最近 2-3 步可见
- `frontend/src/components/ExpertCard.tsx`
  - 新增 `steps` 渲染能力，兼容旧的 `thinkingContent`
- `frontend/src/services/api.ts`
  - 扩展深度分析 SSE 消息类型定义

**用户体验约束（已按设计偏好落实）**：
- 当前步骤默认展开
- 左侧信息密度取“平衡”
- 状态文案简短直接
- 视觉风格克制专业，不做重特效

**验证结果**：
- `pytest tests/test_step_protocol.py -q` ✅
- `pytest tests/test_multi_agent.py tests/test_step_protocol.py -q` ✅
- `cd frontend && npm run build` ✅

**当前已知边界**：
- 协调者 `synthesis_chunk` 仍是普通流文本，尚未升级为 `synthesis_step_*`
- 左侧专家区目前是“步骤摘要卡”，还不是最终的完全折叠式分组面板

---

### 2026-04-01 ✅ 完成：左侧栏完整重构（v3.38）

**最终架构**：
```
App.tsx (z=3 固定叠层)
  ├── Logo ♕ + "象棋AI教练·混合代理系统"（DOM文字）
  └── iOS 26 三段滑块 分析/◉人机/◎双人（DOM交互，点击触发segment切换）

LiquidGlassApp (z=2 WebGL透明叠层)
  ├── 主 WebGL canvas → 液态玻璃背景 + shape3 右侧栏
  └── button canvas → WebGL 液态玻璃按钮
      → CustomEvent 'webgl-button-click' → App.tsx 处理

Grid (z=1)
  ├── 左侧栏 aside（pointerEvents:none，占位保持grid宽度）
  ├── 中央棋盘 main
  └── 右侧透明 aside（AgentThinkingPanel，shape3定位基准）

LocalStorage: 'glass-params'（Zustand persist）
  └── Leva GUI（'左侧栏'/'右侧栏'两文件夹）↔ Zustand ↔ paramsRef → RAF → shader uniforms
```

**按钮清单**（WebGL渲染，buttonCanvas hitTest，y ≥ 106）：
| 按钮 | 位置（侧栏内） | 激活态 |
|------|--------------|--------|
| 打棋谱 | y=112 | replay模式 |
| 翻转棋盘 | y=162 | toggle |
| 显示提示 | y=162,x=96 | showArrows |
| 重新开始 | y=204 | gold primary |
| 📷 拍照 | y=204,x=146 | — |

**关键修复**：
- 三段滑块移至 `position:fixed; z=3`（解决被 button canvas z=2 遮挡）
- `buttonCanvas hitTest` 跳过 y<106 区域（Logo+三段滑块）
- Zustand subscribe → paramsRef → RAF（无 React 重渲染）
- shape3 radius 从硬编码 28 → `paramsRef.current.shape3Radius`（可由 Leva 控制）

### 2026-04-01 🔧 左侧栏重构：iOS 26三段滑块 + 拍照按钮

**新布局**：分析/人机/双人 → iOS 26 pill滑块；重新开始右侧新增拍照按钮📷

**文件变更**：`App.tsx` + `index.css`（三段滑块CSS）+ `LiquidGlassApp.tsx`（坐标调整）

---

### 2026-04-01 🔧 WebGL按钮升级：dashersw折射模型迁移（进行中）

**目标**：按钮文字从 Canvas2D 改为 DOM 层，shader 增加 dashersw 风格的 cornerBoost + rippleEffect。

**参考来源**：`dashersw/liquid-glass-js`（192 stars）- 读取源码自行实现，未下载文件

**已完成的改动**：

- `fragment-button.glsl`：
  - 新增 uniform `u_cornerBoost`（角落增强折射）
  - 新增 uniform `u_rippleEffect`（表面涟漪纹理）
  - cornerBoost：在角落处额外折射偏移
  - rippleEffect：垂直于法线的涟漪波纹

- `LiquidGlassApp.tsx`：
  - `BUTTON_DEFS` 改为 `export`（供 App.tsx 引用）
  - 移除 Canvas2D 文字渲染代码
  - 新增 `hoveredBtn` / `activeBtn` prop（从 App.tsx 传入）
  - 新增 Leva 参数 `btn_cornerBoost`（默认 0.02）和 `btn_rippleEffect`（默认 0.1）
  - `DEFAULT_CONTROLS` 新增 `btn_cornerBoost: 0.02`、`btn_rippleEffect: 0.1`
  - `Controls` 接口新增 `btn_cornerBoost`、`btn_rippleEffect`

- `App.tsx`：
  - 导入 `BUTTON_DEFS`
  - 新增 `hoveredBtn` / `setHoveredBtn` 状态
  - 传递 `hoveredBtn` / `activeBtn` 给 `LiquidGlassApp`

**待完成**：
- [ ] 左侧栏 DOM 按钮文字层布局（`index.css` + `App.tsx` JSX）
- [ ] 鼠标悬停事件（绑定到 aside 区域，命中检测到 span）
- [ ] CSS 样式（文字阴影、金色高亮、`pointer-events: none`）
- [ ] 验证按钮效果（cornerBoost + ripple + 文字清晰无锯齿）

**架构变更**：
```
变更前：WebGL 渲染按钮 → Canvas2D 绘制文字
变更后：WebGL 渲染按钮 → DOM span 文字层（pointerEvents: none）
```

---

## 📋 文档更新记录

### 2026-04-01 🔧 多Agent系统工程化修复

**背景**：架构审查发现多Agent系统存在严重缺陷（B+评分），详见 [plans/eager-growing-eich.md](../plans/eager-growing-eich.md)

**P0 修复**：
- ✅ **真正并行执行**：用 `ThreadPoolExecutor` 替换串行 `time.sleep(1)` 伪并行
- ✅ **补充测试**：`tests/test_multi_agent.py` 23个测试用例，覆盖自适应决策、专家配置、阶段检测、异常处理

**P1 修复**：
- ✅ **phase_info 注入**：专家现在知道当前处于开局/中局/残局
- ✅ **清理冗余代码**：删除 orchestrator 无效的 `_tool_functions`
- ✅ **专家失败处理**：失败专家结论不参与合成

**P2 修复**：
- ✅ **max_tokens 512→1024**：支持深度分析不截断
- ✅ **工具超时控制**：30秒超时，防止工具卡死阻塞专家
- ✅ **清理未使用 imports**：三个专家文件中的 `should_use_multi_agent` 冗余导入

**测试结果**：23 passed in 1.08s

---

### 2026-04-01 🔧 OpenTelemetry 追踪系统上线（已完成+验证）

**背景**：GitHub调研发现 OpenTelemetry 是 AI Agent 调试的行业标准（LangGraph/AutoGen/CrewAI 都在用）

**新增文件**：
- `core/llm/tracing.py` — OTEL 初始化 + TracerProvider + Span装饰器
- `docs/reference/tracing.md` — 追踪系统完整文档

**追踪层级**：
```
orchestrator.analyze
  └── orchestrator.analyze_multi
        ├── tactics_expert.analyze
        │     ├── llm.call（model, input_tokens, output_tokens, duration_ms）
        │     └── tool_call（tool_name, success, error）
        ├── strategy_expert.analyze
        └── engine_expert.analyze
              └── synthesizer.synthesize
```

**验证结果**：控制台输出完整Span树（trace_id同一，父子关系正确）

**接入方式**：
- 本地开发：零配置，控制台直接输出 Span 树
- Langfuse Cloud：设置 `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` 环境变量
- 自托管：设置 `OTLP_ENDPOINT`
- Jaeger/Grafana Tempo：设置 `OTLP_ENDPOINT`

**与 debug_logger 共存**：debug_logger 写文件，OTEL 负责实时追踪，互不干扰

**集成范围**：
- ✅ Orchestrator（analyze + analyze_multi 入口 Span）
- ✅ Expert（专家执行 Span）
- ✅ LLM调用（model + tokens + duration_ms）
- ✅ 工具执行（tool_name + success + error）
- ✅ Expert（专家执行 Span + 工具调用 Span）
- ✅ LLM 调用（model + tokens + duration_ms）
- ✅ 工具执行（tool_name + success + error）

**测试**：pytest 100% 通过

---

### 2026-04-01 🔷 左侧栏 WebGL2 液态玻璃按钮

**新增文件**:
- `src/shaders/liquidglass/fragment-button.glsl` — 按钮 fragment shader（SDF + 折射 + 菲涅尔 + glare）
- `src/utils/GLUtils.ts` — 新增 `getPass(name)` 方法，支持跨 renderer 引用 pass 输出

**修改文件**:
- `src/components/LiquidGlassApp.tsx`:
  - 新增 `BUTTON_DEFS`（7 个按钮定义，CSS 像素坐标）
  - 新增 `buttonCanvasRef` — 独立 canvas（z=2）渲染按钮
  - 新增 `buttonRenderer` — 独立 `MultiPassRenderer` 单 pass
  - 新增鼠标射线检测（`pointermove`/`pointerdown`/`pointerup`）
  - 新增 Canvas2D 文字叠加层
  - `window.dispatchEvent('webgl-button-click')` 触发 App.tsx 处理
- `src/App.tsx`:
  - 移除左侧栏按钮 DOM，保留 Logo
  - 新增 `window.addEventListener('webgl-button-click')` 处理按钮点击

**架构**: buttonCanvas 与 mainCanvas 同位置叠加，buttonCanvas pointerEvents: auto 拦截点击，
通过 `renderer.getPass('hBlurPass').getOutputTexture()` 获取模糊背景纹理做折射渲染。

---

### 2026-03-31 📚 文档体系重大更新

**DNA.md 已重写**（v1.0 → v2.0）：

- 标签数量修正：45个 → **38个**
- 技术路线更新：Transformer已废弃，规则脚本为主
- Liquid Glass设计理念完整记录
- Neo4j 19万局数据确认已录入
- YOLO状态更新：权重已训练，FEN转换算法开发中
- 前端架构详细记录
- 多专家并行架构完整文档
- 废弃文档已标记

**相关操作**：
- 旧DNA.md 备份至 `docs/_archived/DNA_v1.0_before_rewrite.md`
- `PROJECT_BLUEPRINT.md` 已标记"已废弃"
- `INDEX.md` 已标记"已废弃"

---

## 当前阶段

**阶段**: T0比赛冲刺 - Prompt深度优化
**核心目标**: 让LLM从"描述发现"转向"推演对手选项"

---

## 进度总览

| 模块 | 进度 | 说明 |
|------|------|------|
| **标签检测体系** | ██████████ 100% | **完成！** 45个标签已定义，12个测试全部通过 |
| **黄金局面测试** | ██████████ 100% | **完成！** 41个测试用例，mAP=1.0 |
| **张力检测器** | ██████████ 100% | 6种张力类型，阈值已优化（cp>300触发） |
| **知识库** | ████████░░ 80% | 张力导向检索，20+棋理原则 |
| Agent工具 | ██████████ 100% | 10个工具已实现，Function Calling已集成 |
| 双模式API | ██████████ 100% | 真Agent模式上线，SSE新消息类型 |
| **SSE流式输出** | ██████████ 100% | **完成！** 延迟问题已定位，旧分析工具已删除 |
| 前端 | ██████████ 100% | 深度分析面板完成，Liquid Glass + 亮暗双模式 |
| Neo4j棋谱 | ████░░░░░░ 40% | 框架已搭建，数据待完善 |

---

## 本周待办

### 高优先级
- [x] ~~张力检测器实现~~ ✅ 6种张力类型
- [x] ~~System Prompt改造~~ ✅ 强制推理步骤
- [x] ~~张力检测阈值修复~~ ✅ cp>300
- [x] ~~引擎工具修复~~ ✅ engine_alternatives属性访问
- [x] ~~两阶段Agent测试~~ ✅ 规划→执行→输出
- [x] ~~SSE延迟问题定位~~ ✅ 旧版analyze-move阻塞
- [x] ~~旧版分析工具删除~~ ✅ 前端+后端已清理
- [ ] 验证走棋后深度分析无延迟

### 中优先级
- [ ] 阶段检测优化（考虑过河判断）
- [ ] 中局思维链框架
- [ ] Neo4j数据完善
- [ ] 三档讲解模式（初学者/进阶/教练）

---

## 最近更新

### 2026-03-31 🔧 右侧栏 WebGL 液态玻璃：材质统一 + ResizeObserver 同步

**目标**：右侧栏去掉 CSS backdrop-filter，改为 WebGL 渲染，与左侧栏材质完全一致。

**改动**：
- `index.css`：`.lg-sidebar-right` 去掉 `backdrop-filter` 和 `background`，WebGL 透出
- `App.tsx`：右侧栏加 `ref` + `ResizeObserver` + `useLayoutEffect`，实时同步 `getBoundingClientRect` 给 WebGL
- `LiquidGlassApp.tsx`：新增 `rightSidebarRect` prop + `rightSidebarRectRef`，RAF 中设置 shape3 uniform
- `fragment-main.glsl`：新增 shape3 SDF（圆角矩形）+ 7个 uniform，`mainSDF` 扩展支持三形状混合
- `fragment-bg.glsl`：同步 shape3 阴影计算

**WebGL shape 架构**：
- shape1：装饰圆点（`u_showShape1` 控制，默认关闭）
- shape2：左侧栏（`u_mouseSpring` 固定位置，220px）
- shape3：右侧栏（`u_shape3Pos/Width/Height` 实时同步 DOM rect，坐标用 `rectCenterX * dpr`）

**材质完全共享**：shape2 和 shape3 共用同一套折射/菲涅尔/glare 逻辑。

**待调**：shape3 坐标定位（分析模式下形状位置微调中）

### 2026-03-31 🔧 前端清理：删除左侧栏冗余 DOM

**问题**：左侧栏 `<aside>` 完全冗余 — Grid 列宽硬编码，不依赖 DOM；棋盘/引擎图动画使用独立 ref，与 aside 无关。

**改动**：
- 删除 `App.tsx` 中的 `<aside className="lg-sidebar lg-sidebar-webgl">` 及 `S.leftSidebar` 样式
- 删除 `index.css` 中 `.lg-sidebar-webgl` / `.lg-sidebar-left` 死代码

**效果**：WebGL canvas 全屏穿透，左侧 220px 区域交给 WebGL 渲染，为未来 WebGL 按钮铺路。

### 2026-03-31 💾 液态玻璃参数持久化：启动读JSON + 一键保存

#### 核心改动

调参 → 保存 → 下次刷新生效，完整闭环：

**后端**（`api/main.py`）：
- `POST /api/glass-preset/save` — 接收前端参数，写入 `frontend/public/presets/default.json`
- `GET /api/glass-preset/load` — 读取当前预设（验证用）

**前端**（`LiquidGlassApp.tsx`）：
- 启动时 `fetch('/presets/default.json')` 读取 JSON
- 用 `levaStore.setValueAtPath('液态玻璃参数.key', value)` 批量注入 Leva 面板初始值
  - 注意：Leva 内部用 `.` 分隔符（不是 `/`）
- 右上角新增 **💾 保存为默认** 按钮
- 点击后用 `levaStore.getData()` 获取所有当前值，POST 到后端

**默认配置**：`frontend/public/presets/default.json`

**工作流程**：
```
Leva 调参 → 点"保存为默认" → POST /api/glass-preset/save
                                      ↓
                            后端写入 default.json
                                      ↓
                          刷新页面 → fetch 读取新参数
                                      ↓
                          levaStore.setValueAtPath 注入面板
```

**文件变更**：
- `api/main.py` — 新增 glass-preset 端点
- `frontend/src/components/LiquidGlassApp.tsx` — 读取/保存逻辑
- `frontend/public/presets/default.json` — 默认配置文件

### 2026-03-29 🔧 前端分析入口重构：深度分析改为全局功能

#### 核心改动

将"深度分析"从游戏模式中分离，改为独立的全局功能入口：

**修改前**：
- `GameMode` 包含 `'analysis'`，与 PVP/PVE/Replay 并列
- 左侧栏：[分析] [人机] [双人] 混在一起

**修改后**：
- `GameMode` 移除 `'analysis'`
- 新增独立的"深度分析"区域，金色按钮，任何模式下都可用

**文件变更**：
- `frontend/src/App.tsx` — 移除 'analysis' 类型，重组左侧栏布局

### 2026-03-24 🧠 Prompt深度优化：增加"对手处境分析"思维层

#### 问题诊断

当前所有专家的System Prompt都在"汇报发现"：
1. 我看到了什么（描述事实）
2. 这意味着什么（解读标签）
3. 结束

特级大师的思维流程是：
1. 这里最紧张的是什么
2. **如果我是对手，我现在最怕什么**
3. **如果我走X，对手能怎么应？每条应着会通向什么结果？**
4. 所以这步棋的价值是锁死了对手的选项

**差距**：没有要求LLM问自己"对手现在有几条路，每条路结果如何"

#### 解决方案

在所有专家的System Prompt中增加**强制思维步骤**——对手处境分析：

**修改文件**：
1. `xiangqi_coach.py` - 主System Prompt：新增"对手处境（必须分析）"节
2. `tactics_expert.py` - 战术专家：新增"对手视角三问"（必须调用工具验证）
3. `strategy_expert.py` - 战略专家：新增"双方计划分析"（优势方/劣势方）
4. `engine_expert.py` - 引擎专家：新增"候选落差分析"（第一/第二候选对比）
5. `multi_agent_orchestrator.py` - 合成器：新增"综合对手处境"任务

**输出格式新增**：
- 【对手处境】对手选项分析（必须填写）
- 【候选分析】第一/第二候选对比 + 分数落差解读
- 【双方计划】优势方计划 + 劣势方挣扎 + 关键转折点

**关键约束**：不是让LLM瞎猜变化，是让它**必须调用工具**（`engine_alternatives`、`analyze_move`、`get_forcing_sequence`）把"对手视角"变成可验证的事实。

---

### 2026-03-23 🎴 分析面板：重写 AgentCardFlip 动画 + 左右分栏思维流

#### 核心改动

重写深度分析面板的动画序列，达到 Apple/WWDC 风格：

**动画序列**：
```
T=0ms      翻面完成，叠卡整齐显露彩虹背面
T=600ms    翻面完成 → morphing 开始
T=800ms    收缩变形完成 → orbMoving 开始（球曲线滑动 + 逐张发牌）
T=1100ms   三张依次弹出（macOS 最小化拉伸效果）
T=1400ms   三张落地左侧，整体垂直居中
T=1500ms   协调者思维流开始输出
```

**Phase 改造**（`useAgentStore.ts`）：
- 新增 `cardsLanded` / `streaming` phase
- 动画序列更流畅，无硬串停顿

**左右分栏布局**（`AgentThinkingPanel.tsx`）：
- `cardsLanded`/`streaming` 阶段：左侧三专家扑克牌 + 右侧协调者思维流
- 紫色渐变分隔线
- 协调者球 + 金色连接线 + 思维流内容

**新建文件**：
| 文件 | 说明 |
|------|------|
| `ThinkingStream.tsx` | 协调者思维流组件，打字机效果 + 金色子弹点 |
| `SplitLandedCards`（内联） | 落地后的三专家扑克牌（边缘彩虹流光） |

**动画细节**：
- 球呼吸：`orb-breathe` + `orb-body-rotate` 持续循环
- 边缘流光：`card-edge-glow` CSS keyframe（conic-gradient + hue-rotate）
- 发牌拉伸：`scaleX/scaleY` 差异化，stagger 150ms

**Bug 修复**：
- API 端口 `8003 → 8002`
- `ToolCall` 类型添加 `id` 字段
- SSE 事件类型添加 `expert` 字段

**死代码清理**：删除 8 个文件

**文件变更**：
- `AgentCardFlip.tsx` — 重写动画逻辑
- `AgentThinkingPanel.tsx` — 左右分栏布局
- `ThinkingStream.tsx` — 新建
- `index.css` — 新增 `card-edge-glow` keyframe
- `useAgentStore.ts` — phase 类型更新
- `ExpertCard.tsx` — ToolCall 类型更新

### 2026-03-23 🔧 Liquid Glass 按钮效果修复

**v2 问题**：尝试用 SVG `feDisplacementMap` 位移滤镜替代假白点，但：
- `filter` 属性导致 `backdrop-filter` 失效，按钮完全不可见
- `rgba(255,255,255,0.10)` 背景太透明，几乎融入暖米色背景
- 白字在暖米色背景上对比极差

**v3 正确实现**：
- 去掉 SVG 滤镜（与 `backdrop-filter` 不兼容）
- `rgba(255,255,255,0.40)` 背景 — 与 `.glass-panel` 一致的可见度
- `rgba(80,60,40,0.90)` 深色文字 — 在暖米色背景上清晰可见
- `border-top-color` 加亮 — 模拟玻璃顶部高光边
- 径向渐变 `::before` — 左上角柔和光晕，悬停时显现
- 金色变体：深色文字 `rgba(140,100,20,0.95)` + 金色边框 + 顶部高光

**涉及组件**：App.tsx 侧边栏全部按钮 + 分析面板组件

#### Apple iOS 26 水滴边缘反光效果

所有按钮统一升级为 Apple Liquid Glass 悬停光效：

**核心 CSS 类** `.liquid-glass-btn`：
- `backdrop-filter: blur(12px) saturate(160%)` — 玻璃模糊质感
- 多层 `inset box-shadow` — 模拟水滴四边镜面高光（上/下/左/右各有不同强度的白色边缘）
- `::before` / `::after` 伪元素 — 左上角微小白点光斑，悬停时出现（模拟水滴表面反光）
- 悬停时 `scale(1.03)` + 背景变亮 + 四边高光加强
- 按下时 `scale(0.97)` 反馈

**变体**：
- `.sm` — 小尺寸（padding: 4px 10px, border-radius: 8px）
- `.primary` — 金色主题（背景 `rgba(212,175,55,...)`，四边金色高光）
- `:disabled` — 禁用状态保持原样式但禁用交互

**涉及组件**：
- `App.tsx` — 左侧侧边栏全部按钮（☀️主题/在线对局/拍照识别/分析/人机/双人/打棋谱/翻转棋盘/显示提示/重新开始）
- `DeepAnalysisPanel.tsx` — 收起/快速/深度/分析主按钮
- `ReplayNavigator.tsx` — 导航圆按钮（⏮◀▶⏭）/自动讲解开关
- `PositionAnalysisPanel.tsx` — 摘要/棋子/标签标签按钮
- `PGNPanel.tsx` — 加载棋谱按钮
- `ReplayPanel.tsx` — 数据库/PGN标签/搜索/加载/退出按钮
- `ChessBoard.tsx` — 错误关闭按钮
- `ExpertCard.tsx` — 展开/收起按钮
- `BottomTerminalPanel.tsx` — 最小化/关闭按钮
- `AgentDebutPanel.tsx` — 关闭按钮

### 2026-03-22 🎴 分析面板：扑克牌收叠翻面动画 + 全部原有功能恢复

#### 动画序列（Apple 风格）

点击"开始深度分析"后，扑克牌全程连续动画，不消失：

```
T=0ms     面板扩张，卡片随布局自然位移（不中断）
T=100ms   三卡开始收叠（spring stiffness:320, damping:26）
T=600ms   收叠完成，三卡完美重叠
T=700ms   整体 3D 翻面（rotateY spring stiffness:260, damping:28）
T=1100ms  翻面完成，Agent 流光液态玻璃背面展示
```

#### 架构改动

**一套卡片全程渲染**：
- `AgentThinkingPanel` 始终渲染 `AgentCardFlip`，不切换组件
- `AgentCardFlip` 内部通过 `phase` 状态驱动动画
- 无 `AnimatePresence` 组件切换，无卡片消失

**牌的正面**：`CollapsedCardsView` 原有的 Liquid Glass 卡片（含全部交互）：
- Apple 风格 `borderRadius: 16` + `overflow: hidden`
- 鼠标悬停 `onMouseEnter/onMouseLeave`（phase===idle 时启用）
- `hovered` 状态 → `glowColor` box-shadow 光晕增强
- `isSqueezed` 邻居卡让位动画（左右各偏移16px）
- `isHovered ? 1.18 : 1` 悬浮放大
- `ExpertGlassPanel` Portal 弹出详情（abilities 列表）

**牌的背面**：Apple 彩色流光液态玻璃：
- `conic-gradient`（蓝→紫→粉→金→蓝）+ `liquid-shimmer` hue-rotate 动画（3秒无限循环）
- `mixBlendMode: overlay` 叠加质感
- `backdrop-filter: blur(20px) saturate(180%)`
- 多层 inset box-shadow 模拟玻璃厚度
- 皇冠 ♕ + 闪电 ⚡ + 装饰线 + Agent 金色文字

#### CSS 新增

- `@keyframes liquid-shimmer`：hue-rotate + brightness 脉冲流光

**文件变更**：
- `frontend/src/components/AgentCardFlip.tsx` — 新建，核心动画组件
- `frontend/src/components/AgentThinkingPanel.tsx` — 简化为单组件渲染
- `frontend/src/index.css` — 新增 `liquid-shimmer` 动画

### 2026-03-22 🎨 前端视觉增强：侧边栏 Liquid Glass 强化 + 亮暗双模式

#### 侧边栏 Liquid Glass 增强

左右侧边栏从弱玻璃效果升级为 Apple iOS 26 Liquid Glass 风格：

**核心改动**：
- `backdrop-filter: blur(12px)` → `blur(40px)`，玻璃模糊感大幅增强
- 背景透明度提升：`rgba(255,255,255,0.15)` → `rgba(255,255,255,0.18)`
- 边框加粗：`rgba(180,160,140,0.15)` → `rgba(255,255,255,0.28)`
- 多层 box-shadow：外阴影 + inset 高光（模拟玻璃厚度）
- 顶部白边高光：内 inset 反射感

**CSS 新增**：
- `.lg-sidebar` — 完整 Liquid Glass 样式
- `.lg-sidebar-left` / `.lg-sidebar-right` — 左右专属白边
- CSS 变量支持亮暗双模式

**文件变更**：
- `frontend/src/index.css` — 新增 CSS 变量 + `.lg-sidebar` 完整样式
- `frontend/src/App.tsx` — 侧边栏改用 `className="lg-sidebar"`，移除内联弱玻璃样式

#### CollapsedCardsView 扑克牌 Liquid Glass 化

收起状态的三张专家扑克牌（K/J/Q）升级为 Apple Liquid Glass 风格：

- 尺寸 `110×150` → `130×175`
- `backdrop-filter: blur(12px) saturate(150%)`
- 内高光 + 内暗边（inset box-shadow 玻璃厚度感）
- 每张牌专属渗色光晕（K红/J银/Q蓝）
- KJQ 字母 `44px` → `54px`，悬浮时加文字光晕
- 标题字号 `11px → 14px`，金色 `#D4AF37` + 光晕
- 底部文字透明度 `0.5 → 0.75`

**文件变更**：
- `frontend/src/components/CollapsedCardsView.tsx` — 完整重构卡片样式

#### 亮暗双模式切换

- 新增 `data-theme="dark"` 属性切换
- ☀️/🌙 切换按钮放置于左侧 Logo 区域
- 暗色模式：暖色暗底 `rgba(20,15,10,0.32)`，适配暖黄木纹背景
- 亮色模式：微透明白底 `rgba(255,255,255,0.18)`，Apple 原生风格

### 2026-03-22 🎨 前端视觉打磨：高级通透背景 + 分析面板扩张

#### 背景设计重构

将前端背景从"Apple Liquid Glass增强版"升级为"现代中式编辑风 + Apple高级质感"混合方案：

**核心元素**：
- **强颗粒噪点层**：SVG `feTurbulence` 生成电影级颗粒感（`baseFrequency=0.80, numOctaves=4, opacity=0.10`），作为背景材质感核心
- **顶部深墨晕染**：`linear-gradient` 从顶部压下来（`0.28` 起始渐隐），模拟水墨书卷气
- **左上自然光晕**：`radial-gradient` 左上角提亮，模拟自然光感
- **清晰棋盘格**：`0.18` 透明度，清晰可见但不抢眼
- **宣纸拉丝纹**：新增垂直纸纹层，模拟宣纸纤维质感
- **暖灰宣纸底**：`#E0DBD1`，和白色毛玻璃形成良好对比

**技术实现**：
- 颗粒噪点使用 SVG Data URI 背景图片，浏览器原生支持，稳定可靠
- 8层背景叠加（颗粒 + 墨染 + 光晕 + 反光 + 棋盘格 + 纸纹 + 版式线 + 底色）
- 移除之前失败的 `filter: url(#grain-filter)` 伪元素方案

**文件变更**：
- `frontend/index.html` — 添加 SVG Grain 噪点滤镜定义（后移除，改用 Data URI）
- `frontend/src/index.css` — 完整重构 body 背景层，新增8层渐变 + grain 背景
- CSS变量：`--apple-bg` 更新为 `#E0DBD1`
- 顶部注释更新为"Modern Chinese Editorial Style"

#### 分析面板宽度优化

- 分析模式下右侧面板：`380px → 620px`，扩大近一倍
- 正常模式保持 `260px`
- 使用 CSS Grid `gridTemplateColumns` 动态切换

**文件变更**：
- `frontend/src/App.tsx` — `gridTemplateColumns` 分析模式从 `380px` → `620px`

### 2026-03-22 🎨 前端布局重构：命令式 → 声明式（响应式Grid）

#### 核心改动

将前端的坐标计算从命令式（Imperative）重构为声明式（Declarative）响应式布局，彻底解决棋盘缩放时的坐标偏差和动画抖动问题。

**变更内容**：
- 外层容器：`display: flex` → `display: grid`，动态控制第三列宽度 `20vw ↔ 35vw`
- 棋盘动画：移除硬编码 `x: -350`, `y: -80`，仅保留 `scale: 0.75` + `transformOrigin: '0 0'`
- 引擎窗口：移除 `position: absolute` + 手动坐标计算，改为 `flex: 1` 流体填充
- 右侧栏：移除 `position: fixed`，参与 Grid 布局
- 清理：`boardRef`、`ResizeObserver`、`boardCenter`、`engineWidth` 等全部删除
- 动画参数：三组不同参数 → 统一 `stiffness: 260, damping: 26`

**文件变更**：
- `frontend/src/App.tsx` — 重构布局逻辑，清理 ~100行代码
- `frontend/src/components/ChessBoard.tsx` — 移除 `onWidthChange` prop 和 `measureRef`
- `docs/frontend/ENGINE_CHART_DEBUG.md` — 更新文档，记录重构结果
- `docs/frontend/FRONTEND_COMPLETE.md` — 更新 4.5 节说明

### 2026-03-21 🎨 前端整合：替换为新版UI (frontend_new)

#### 核心改动

将 `docs/communication/frontend_new/` 的前端代码整合到 `frontend/` 目录：

**新前端特点**：
- 明亮温暖米色主题（浅色水墨风格）
- 简洁flex布局（三列：左240px | 中auto | 右380px）
- 时间轴式深度分析面板（DeepAnalysisPanel）
- 完整棋子/局面/战术标签/棋谱/PGN组件

**保留的高级功能**（来自旧版frontend）：
- `ExpertCard.tsx` — 三专家卡片组件（战术/战略/引擎）
- `SynthesisPanel.tsx` — 合成器输出面板
- `AgentDebutPanel.tsx` — 专家登场动画
- `EngineChart.tsx` — 引擎评分折线图
- Store 中的 `evalHistory`、`EvalPoint` 类型

**集成要点**：
- 全部新组件替换：`App.tsx`, `main.tsx`, `index.css`, `App.css`, `ChessBoard.tsx`, `DeepAnalysisPanel.tsx`, `PositionAnalysisPanel.tsx`, `TacticalTagsPanel.tsx`, `ReplayPanel.tsx`, `ReplayNavigator.tsx`, `StatCard.tsx`, `PGNPanel.tsx`
- Store/API服务使用新版（简化版）
- 高级组件（ExpertCard等）从旧版保留，未被新App.tsx引用但可复用

**编译状态**：`npm run build` 全绿 ✅

### 2026-03-21 🎯 布局重设计 v2：棋盘左上 + 侧边栏全右 + 苹果登场 (Plan: optimized-jingling-duckling v2)

#### 布局
- 棋盘：居中 → 左上角 smooth slide（spring stiffness:180, damping:22，scale:0.75）
- 侧边栏：380px → 62% 视口宽度，spring 扩张动画
- 中央区域宽高协同动画，无瞬移

#### 登场动画（苹果轮廓 + Claude 呼吸融合）
1. T=0: 三个呼吸光球脉冲聚集（Claude眨眼风格）
2. T=300: 光球→虚线轮廓浮现
3. T=600: 身份揭示 — 图标旋转出现 + 名称打字机效果
4. T=900: 填充着色 + 边框solid化
5. T=1200: 卡片内容 stagger 渐次展开

#### 技术要点
- `motion.div` 作为中央区域容器，`animate={{ width }}` 协同棋盘和侧边栏
- Board: `spring stiffness:180, damping:22` + `scale: 0.75` + margin 动画
- 登场: 纯 CSS `scale/opacity` 循环 + 打字机 effect hook
- 引擎图: 保留在棋盘下方（棋盘左侧+下方空间内）

#### 新增文件
| 文件 | 说明 |
|------|------|
| `frontend/src/components/EngineChart.tsx` | 纯SVG引擎评分折线图（无依赖） |
| `frontend/src/components/AgentDebutPanel.tsx` | 融合登场动画主组件 |
| `frontend/src/components/BottomTerminalPanel.tsx` | 已废弃（可删除） |

### 2026-03-21 🎯 布局重设计：棋盘滑动 + 专家登场动画 (Plan: optimized-jingling-duckling)

#### 核心改动

从"底部终端面板"改为"棋盘滑动 + 扩张侧边栏 + 专家登场动画"：

```
正常状态：
[左侧240px] | [居中棋盘] | [右侧380px]

分析模式：
[左侧240px] | [左上滑动棋盘 scale(0.82)] | [右侧560px - 专家登场动画]
            | [下方：引擎折线图 + 走法记录]
```

#### 动画序列
```
T=0ms     棋盘向左上滑动 (spring)
T=100ms     侧边栏从380px扩张到560px
T=200ms     底部区域出现
T=300ms     三个光球脉冲聚集
T=600ms     光球爆发 + 虚线轮廓浮现
T=900ms     身份揭示 + 专家名打字机
T=1200ms    填充着色 + 卡片展开
T=1500ms    卡片内容 stagger 出现
```

#### 技术实现

- ✅ **BottomTerminalPanel.tsx** — 底部弹出主组件（Framer Motion）
  - 毛玻璃：`backdrop-filter: blur(24px) saturate(180%)`
  - Spring 动画：`stiffness: 400, damping: 28, mass: 0.8`
  - 高度拖拽调整（mousedown/mousemove/mouseup）
  - ESC / 点击背景关闭
  - 高度持久化到 localStorage

- ✅ **Framer Motion 动画编排**
  - 面板：y: 100% → 0 spring 滑入
  - 卡片：staggerChildren 0.12s 依次出现
  - 合成器：delayChildren 0.51s 后淡入

- ✅ **棋盘联动缩放** (Zustand store)
  - 面板打开：`terminalPanelScale = 0.92`
  - 面板关闭：`terminalPanelScale = 1.0`
  - 缓动：`cubic-bezier(0.34, 1.56, 0.64, 1)` — 苹果风格弹性

#### 新增文件
| 文件 | 说明 |
|------|------|
| `frontend/src/components/BottomTerminalPanel.tsx` | 底部弹出终端主组件 |

#### 修改文件
- `frontend/src/store/useGameStore.ts` — 新增 `terminalPanelScale` 状态
- `frontend/src/components/DeepAnalysisPanel.tsx` — 状态管理中枢，渲染 BottomTerminalPanel
- `frontend/src/App.tsx` — 棋盘区域缩放 transform
- `frontend/src/index.css` — 毛玻璃 + 标题栏 + 拖拽条 + 动画

### 2026-03-21 🎨 前端重设计：三列专家卡片布局

#### 核心改动（Plan: delegated-zooming-alpaca）

将深度分析面板从"时间轴"改为"三列专家卡片 + 合成器"布局：

- ✅ **ExpertCard.tsx** — 单专家卡片组件
  - 专家头像/图标 + 名称 + 状态标签
  - 流式思考区域（打字机效果）
  - 工具调用气泡可视化
  - 核心发现区
  - 三种配色：战术(红)、战略(黄)、引擎(蓝)

- ✅ **SynthesisPanel.tsx** — 合成器输出面板
  - 共识/分歧分区展示
  - 流式最终讲解输出
  - 状态指示器

- ✅ **DeepAnalysisPanel.tsx** 重构
  - 从 `AnalysisTimeline` 时间轴改为三列 `ExpertCard` 网格
  - SSE 事件路由到对应专家卡片
  - 集成 `SynthesisPanel` 替代 `resultSection`

- ✅ **index.css** — 新增专家卡片样式、动画

#### 修改文件
- `frontend/src/components/ExpertCard.tsx` — 新建
- `frontend/src/components/SynthesisPanel.tsx` — 新建
- `frontend/src/components/DeepAnalysisPanel.tsx` — 重构
- `frontend/src/index.css` — 新增样式
- `frontend/src/App.tsx` — 修复 pre-existing bug（`'analysis'` → `'deep'`）

### 2026-03-21 🚀 多Agent并行架构 (Plan #002)

#### 核心改动

从单一Agent升级为三专家并行架构：

```
                    ┌─────────────────────────┐
                    │     Orchestrator        │
                    │  自适应决策（简单/复杂） │
                    └────────────┬────────────┘
                                 │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
  │  战术专家    │      │  战略专家    │      │  引擎专家    │
  │(TacticsAgent)│      │(StrategyAgent│      │(EngineAgent)│
  │工具:棋子攻防 │      │工具:局面战略 │      │工具:深度分析 │
  │      +走法  │      │      +走法对比│      │      +候选走法│
  └─────────────┘      └─────────────┘      └─────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │      Synthesizer        │
                    │  综合三方结论 → 统一讲解 │
                    └─────────────────────────┘
```

#### 自适应决策策略

| 条件 | 执行 |
|------|------|
| 张力数量==0 且 开局 | 单Agent快速分析 |
| 张力<=2 | 单Agent+扩展轮次 |
| 张力>=3 或 CRITICAL 或用户要求深度 | 多Agent并行 |
| 用户明确要求深度分析 | 多Agent并行 |

#### 新增文件

| 文件 | 说明 |
|------|------|
| `core/llm/experts/__init__.py` | 专家模块入口 |
| `core/llm/experts/base_expert.py` | 专家基类（共享LLM调用、棋盘生成、工具执行） |
| `core/llm/experts/tactics_expert.py` | 战术专家（6个工具） |
| `core/llm/experts/strategy_expert.py` | 战略专家（4个工具） |
| `core/llm/experts/engine_expert.py` | 引擎专家（4个工具） |
| `core/llm/multi_agent_orchestrator.py` | 协调器 + 合成器 |

#### SSE新事件类型

| 事件类型 | 说明 |
|----------|------|
| `expert_start` | 专家开始分析 |
| `expert_result` | 专家完成（含核心发现） |
| `expert_{name}_thinking` | 专家思考过程 |
| `expert_{name}_tool` | 专家工具调用 |
| `expert_{name}_tool_result` | 专家工具结果 |
| `synthesis_chunk` | 合成器流式输出 |

#### 降级策略

多Agent专家超时（>2分钟）→ 自动降级为单Agent + 扩展轮次（max_rounds=5）

#### 修改文件

- `api/main.py` — 集成Orchestrator，适配新SSE事件类型
- `frontend/src/components/DeepAnalysisPanel.tsx` — 支持多专家时间轴展示
- `frontend/src/index.css` — 新增专家节点样式

### 2026-03-21 🔧 布局动画修复：棋盘真正左上平移 + 侧边栏扩张

#### 核心问题
- 棋盘只有缩小，没有平移（只有 `scale`，没有 `x/y` 位移）
- 侧边栏宽度固定 380px，无扩张动画

#### 修复内容
- `mainArea` 改为 `motion.div` + `layout`，`justifyContent`/`alignItems` 从 `center` → `flex-start`
- `boardContainer` + `boardWrapper` 加 `layout` + `scale` 动画，Framer Motion 自动计算空间位移
- `rightSidebar` 从 `<aside>` 改为 `<motion.aside>`，`width` 380 → 420 弹簧动画
- 统一使用 Apple 风格弹簧参数：`stiffness: 180, damping: 22`
- `overflow: hidden` 已从 `mainArea` 移除，确保缩放棋盘不被裁剪

#### 修改文件
- `frontend/src/App.tsx` — 布局动画修复

### 2026-03-21 🔧 布局动画 v3：去掉scale，丝滑平移填满空间（Apple spring参数）

#### 核心问题（v2）
- v2只有scale缩放，无真正位移
- 布局切换不够丝滑

#### 修复内容（v3）
**去掉所有 `scale`，纯空间位移 + Apple spring参数**

| 动画 | 参数 | 来源 |
|------|------|------|
| 布局/位移主弹簧 | `stiffness: 308, damping: 23` | Apple snappy (duration≈0.4s, bounce=0) |
| 引擎窗口展开 | `stiffness: 395, damping: 28` | Apple interactive (duration≈0.35s) |
| 侧边栏宽度 | 380 → 420px，`layout` 自动过渡 | 填满空隙 |

**Apple物理参数换算**（WWDC23）：
```
stiffness = (2π / duration)²
damping = 1 - 4π × bounce / duration
```
- snappy: duration=0.4s, bounce=0 → stiffness≈308, damping≈23
- interactive: duration=0.35s, bounce=0 → stiffness≈395, damping≈28

### 2026-03-21 🔧 布局动画 v3→v4：CSS Grid三列布局，侧边栏真正抵住棋盘

#### 核心问题（v3）
- 侧边栏扩张后仍然不抵棋盘右侧
- 引擎窗口尺寸不对，不填满棋盘下方
- 根本原因：`flex: 1` 让 mainArea 吃掉所有剩余空间，棋盘永远在巨大空白中被居中

#### 修复内容（v4）

**从 flex 改为 CSS Grid 三列布局**：
```
正常模式：         分析模式：
[左240][中auto][右380]  →  [左240][中auto][右540]
                                    ↗ 侧边栏弹簧扩张
                                    ↗ 棋盘左上贴边
                                    ↗ 引擎窗口展开
```

| 改动 | 说明 |
|------|------|
| `container` | `display: flex` → `display: grid`，`gridTemplateColumns` 随 `isAnalysisMode` 动画 |
| `mainArea` | `flex: 1` 移除，只占内容所需空间（棋盘+引擎的自然尺寸） |
| `gridTemplateColumns` | `240px auto 380px` ↔ `240px auto 540px`，Apple spring `308/23` |
| `EngineChart` compact width | 280px → 480px（匹配棋盘宽度） |
| 引擎窗口 | `marginTop: 0→8` + `height: auto`，`spring 395/28` |

### 2026-03-21 🔧 布局动画 v4→v5：引擎跨列贴合四边，侧边栏弹簧抵棋盘

#### 核心问题（v4）
- 引擎窗口在 mainArea 里，宽度受 Grid 中间列限制，无法跨列贴合
- 侧边栏与棋盘不对齐

#### 修复内容（v5）

**Grid 3列×2行动画布局**：
```
正常模式：                  分析模式：
[左240][ 棋盘 ] [右380]    [左240][ 棋盘 ] [右540]
          [ 引擎 ]                   [ 引擎 ]
          (隐藏)                    (弹簧展开120px)
```
- 左栏：`gridColumn: 1, gridRow: 1/3`
- 棋盘：`gridColumn: 2, gridRow: 1`；分析模式靠左上
- 引擎：`gridColumn: 2, gridRow: 2`，`width: 100%` = 棋盘宽度
- 右侧栏：`gridColumn: 3, gridRow: 1/3`，弹簧扩张 380→540px

**引擎窗口四边贴合**：
- 左/右：column 2 宽度 = 棋盘宽度，天然对齐
- 上：紧贴棋盘（同一列）
- 下：`height: 0 → 120px`，`spring 395/28`
- `gridTemplateRows: 'auto 0px' → 'auto 120px'`，Grid 行高同步动画

---

## 服务状态

| 服务 | 端口 | 状态 |
|------|------|------|
| Neo4j | 7687 | ⚪ 待启动 |
| 后端API | 8002 | 🟢 运行中 |
| 前端 | 3001 | 🟢 运行中 |

---

## 快速启动

```bash
# 后端
python -m uvicorn api.main:app --host 0.0.0.0 --port 8002

# 前端
cd frontend && npm run dev
# 访问 http://127.0.0.1:3001（端口可能被占用，自动顺延）
```

---

## 前端开发状态

### 模块进度

| 模块 | 进度 | 状态 | 说明 |
|------|------|------|------|
| 棋盘组件 | 100% | ✅ 完成 | ChessBoard.tsx |
| 引擎评分图 | 100% | ✅ 完成 | EngineChart.tsx |
| 深度分析面板 | 100% | ✅ 完成 | DeepAnalysisPanel.tsx |
| 局面分析面板 | 100% | ✅ 完成 | PositionAnalysisPanel.tsx |
| 复盘功能 | 100% | ✅ 完成 | ReplayPanel.tsx |
| 状态管理 | 100% | ✅ 完成 | useGameStore.ts, useAgentStore.ts |
| WebGL Liquid Glass | 100% | ✅ 完成 | LiquidGlassApp.tsx, 四步渲染管线 |
| 专家扑克牌动画 | 100% | ✅ 完成 | AgentCardFlip.tsx |
| Liquid Glass参数持久化 | 100% | ✅ 完成 | Leva + localStorage + JSON |

### 前端布局架构

```
初始状态：                                    分析模式：
┌─────────┬──────────────────┬────────┐  ┌─────────┬──────────────────┬──────────┐
│ 左侧栏   │      棋盘居中      │ 右侧栏  │  │ 左侧栏   │ 棋盘←──────────   │ 右侧栏    │
│ 220px   │                  │ 380px  │  │         │  ↑缩小靠左上      │ 扩张到    │
│         │                  │        │  │         │ 引擎窗口填满剩余空间 │ 620px   │
└─────────┴──────────────────┴────────┘  └─────────┴──────────────────┴──────────┘
```

- Grid 第1列：左侧栏固定 220px（WebGL渲染）
- Grid 第2列：中央区域（棋盘 + 引擎图）
- Grid 第3列：右侧栏 `380px → 620px`

### 前端技术栈

| 类别 | 技术 |
|------|------|
| 框架 | React 18 + TypeScript |
| 构建 | Vite |
| 动画 | Framer Motion |
| 状态管理 | Zustand |
| 参数面板 | Leva |
| 3D渲染 | WebGL（原生，无框架） |

### Liquid Glass WebGL渲染管线

```
bgPass → vBlurPass → hBlurPass → mainPass → 屏幕
```

核心着色器：`frontend/src/shaders/liquidglass/fragment-main.glsl`（617行）

### 前端交接记录

#### 2026-03-30 - WebGL液态玻璃UI层立项

**核心决策**：
- 推翻之前"重写渲染器"路线，改为**直接复制粘贴参考项目** `App.tsx` + `GLUtils.ts`
- 架构确认为：全 WebGL UI层（除棋盘和扑克牌外），DOM只保留ChessBoard + PokerCard
- 详细方案见 `docs/plans/frontend/002-liquid-glass.md`

#### 2026-03-19 - 前端文档体系建立

- 建立前端宪法 `docs/guides/frontend.md`
- 建立接口契约 `docs/reference/api_contract.md`
- 建立组件规范 `docs/guides/component.md`
- 建立状态管理规范 `docs/guides/state_management.md`

### 前端技术文档

| 文档 | 位置 | 说明 |
|------|------|------|
| 前端指南 | `docs/guides/frontend.md` | 完整技术文档 |
| Liquid Glass方案 | `docs/plans/frontend/002-liquid-glass.md` | WebGL渲染详细方案 |
| API契约 | `docs/reference/api_contract.md` | 前后端接口 |
| 组件规范 | `docs/guides/component.md` | 组件开发规范 |
| 状态管理 | `docs/guides/state_management.md` | Zustand规范 |

---

## 快速链接

- [项目DNA](DNA.md) - 架构全貌（必读）
- [标签参考](reference/tag_reference.md) - 38个标签详细定义
- [Agent工具规范](reference/agent_tools_spec.md) - 10个工具接口
- [前端指南](guides/frontend.md) - 前端开发完整文档
- [Liquid Glass方案](plans/frontend/002-liquid-glass.md) - WebGL渲染方案
