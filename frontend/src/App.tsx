import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useGameStore } from './store/useGameStore';
import { useAgentStore } from './store/useAgentStore';
import ChessBoard from './components/ChessBoard';
import AgentThinkingPanel from './components/AgentThinkingPanel';
import EvidenceMapIsland from './components/EvidenceMapIsland';
import EngineChart from './components/EngineChart';
import LiquidGlassApp from './components/LiquidGlassApp';
import LeftSidebar from './components/LeftSidebar';
import { api } from './services/api';
import type { ExpertType } from './components/CardContent';
import type { ExpertStatus } from './components/ExpertCard';

interface GlassRect {
  x: number;
  y: number;
  width: number;
  height: number;
  radius: number;
}

const TOOL_NAME_MAP: Record<string, string> = {
  engine_deep_analysis: '深度算路',
  engine_alternatives: '候选着法',
  analyze_move: '走法分析',
  compare_moves: '走法对比',
  simulate_move: '局面推演',
  query_chess_principles: '棋理原则',
  search_chess_knowledge: '知识检索',
  get_forcing_sequence: '强制序列',
  get_candidate_moves: '候选列表',
};

const EXPERT_NAME_MAP: Record<ExpertType, string> = {
  tactics: '战术专家',
  strategy: '战略专家',
  engine: '引擎专家',
};

const EXPERT_STEP_OFFSET: Record<ExpertType, number> = {
  tactics: 1000,
  strategy: 2000,
  engine: 3000,
};

/** 专家思考阶段标题 — chunk流入时自动轮换 */
const EXPERT_THINKING_PHASES: Record<ExpertType, string[]> = {
  tactics: [
    '扫描战术威胁',
    '检测强制序列',
    '分析子力交换',
    '评估战术组合',
    '验证战术结论',
    '深入分析变化',
  ],
  strategy: [
    '评估局面形势',
    '分析阵型结构',
    '检测位置弱点',
    '审视子力协调',
    '整理战略建议',
    '综合评判局面',
  ],
  engine: [
    '启动深度算路',
    '计算候选变化',
    '评估最佳着法',
    '验证引擎判断',
  ],
};

/** chunk驱动步骤生成间隔(ms) */
const STEP_INTERVAL_MS = 4000;

function getExpertStepId(expert: ExpertType, stepIndex: number) {
  return EXPERT_STEP_OFFSET[expert] + stepIndex;
}

/**
 * 前端兜底净化：移除后端可能遗漏的内部标记
 */
const _RE_CLAIM = /\[(?:CLAIM|EVIDENCE|CONFIDENCE)\]\s*/g;
const _RE_MD_HEADING = /^##\s*\d+\s+.*$/gm;
const _RE_STEP_INLINE = /\[STEP:[^\]]*\]/g;
const _RE_ISOLATED_HASH = /^##\s*[;；]?\s*$/gm;

function sanitizeDisplayText(text: string): string {
  return text
    .replace(_RE_CLAIM, '')
    .replace(_RE_MD_HEADING, '')
    .replace(_RE_STEP_INLINE, '')
    .replace(_RE_ISOLATED_HASH, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function toDispatchSubtitle(msg: AnalysisStreamMessage) {
  if (msg.mode === 'opening_fast_path') {
    return msg.opening_name
      ? `协调者识别为开局阶段，直接调用开局知识：${msg.opening_name}`
      : '协调者识别为开局阶段，直接走快速讲解';
  }

  const experts = (msg.selected_experts || [])
    .map((expert) => EXPERT_NAME_MAP[expert as ExpertType] || expert)
    .filter(Boolean);

  if (experts.length > 0) {
    return `协调者已分派 ${experts.join('、')} 协同分析`;
  }

  if (msg.reason) {
    return `协调者正在规划分析路径：${msg.reason}`;
  }

  return '协调者正在组织多专家分析';
}

function toChineseToolLabel(raw: string) {
  if (!raw) return '工具调用';

  for (const [key, label] of Object.entries(TOOL_NAME_MAP)) {
    if (raw.includes(key)) {
      return label;
    }
  }

  if (raw.includes('engine')) return '引擎计算';
  if (raw.includes('search')) return '知识检索';
  if (raw.includes('simulate')) return '局面推演';
  if (raw.includes('compare')) return '走法对比';

  return raw.length > 16 ? `${raw.slice(0, 16)}…` : raw;
}

interface AnalysisStreamMessage {
  type: string;
  stage?: number;
  message?: string;
  tool?: string;
  finding?: string;
  summary?: string;
  expert?: string;
  title?: string;
  content?: string;
  step_index?: number;
  duration_ms?: number;
  explanation?: string;
  confidence?: string;
  success?: boolean;
  reason?: string;
  mode?: string;
  phase?: string;
  move_count?: number;
  parallelism?: number;
  opening_name?: string;
  selected_experts?: string[];
}

export default function App() {
  const {
    fen,
    previousFen,
    history,
    lastMove,
    gameMode,
    isBoardCollapsed,
    setBoardCollapsed,
    refreshEngineEvaluation,
  } = useGameStore();

  const { setPanelActive, setAnalyzing, isAnalyzing, isPanelActive, resetAll } = useAgentStore();

  const boardRef = useRef<HTMLDivElement>(null);
  const boardAreaRef = useRef<HTMLDivElement>(null);
  const [boardLeft, setBoardLeft] = useState(0);
  const [boardWidth, setBoardWidth] = useState(0);
  const [engineFrame, setEngineFrame] = useState({ top: 0, left: 0, width: 0 });
  const [leftGlassRect, setLeftGlassRect] = useState<GlassRect>({ x: 14, y: 14, width: 220, height: window.innerHeight - 28, radius: 34 });

  const showEngineDock = gameMode !== 'replay';

  useEffect(() => {
    const updateTop = () => {
      if (!boardRef.current || !boardAreaRef.current) return;
      const boardRect = boardRef.current.getBoundingClientRect();
      const areaRect = boardAreaRef.current.getBoundingClientRect();
      setBoardLeft(boardRect.left);
      setBoardWidth(boardRect.width);
      setEngineFrame({
        top: Math.round(boardRect.bottom - areaRect.top + 14),
        left: Math.round(boardRect.left - areaRect.left),
        width: Math.round(boardRect.width),
      });
    };

    updateTop();
    const ro = new ResizeObserver(updateTop);
    if (boardAreaRef.current) ro.observe(boardAreaRef.current);
    if (boardRef.current) ro.observe(boardRef.current);
    return () => ro.disconnect();
  }, [isBoardCollapsed]);

  useEffect(() => {
    if (gameMode === 'replay') return;
    void refreshEngineEvaluation(fen);
  }, [fen, gameMode, refreshEngineEvaluation]);

  // 右侧栏 ref + 尺寸监听（WebGL shape3 同步）
  const rightSidebarRef = useRef<HTMLElement>(null);
  const islandRef = useRef<HTMLElement>(null);
  const [rightSidebarRect, setRightSidebarRect] = useState({ x: 0, y: 0, width: 0, height: 0 });

  useLayoutEffect(() => {
    const el = rightSidebarRef.current;
    if (el) setRightSidebarRect(el.getBoundingClientRect());
  }, []);

  useEffect(() => {
    const el = rightSidebarRef.current;
    if (!el) return;
    const update = () => setRightSidebarRect(el.getBoundingClientRect());
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // 深度分析触发
  // 追踪每个专家当前在协调者时间线里的"实时步骤 id"
  const expertLiveStepRef = useRef<Record<ExpertType, number | null>>({
    tactics: null,
    strategy: null,
    engine: null,
  });
  // 追踪每个专家的轮次（用于生成唯一 step id）
  const expertRoundRef = useRef<Record<ExpertType, number>>({
    tactics: 0,
    strategy: 0,
    engine: 0,
  });
  // 追踪每个专家上次创建步骤的时间 (ms)
  const expertLastStepTimeRef = useRef<Record<ExpertType, number>>({
    tactics: 0,
    strategy: 0,
    engine: 0,
  });
  // 追踪每个专家当前思考阶段索引
  const expertPhaseIndexRef = useRef<Record<ExpertType, number>>({
    tactics: 0,
    strategy: 0,
    engine: 0,
  });
  // 综合阶段过渡步骤时间跟踪
  const synthesisStepTimeRef = useRef<number>(0);
  const synthesisPhaseRef = useRef<number>(0);

  const applyStreamMessage = useCallback((msg: AnalysisStreamMessage) => {
    const store = useAgentStore.getState();
    // 从 msg.expert 取专家类型；如果缺失，从 msg.type 中提取 (expert_tactics_chunk → tactics)
    let expertType = msg.expert as ExpertType | undefined;
    if (!expertType && msg.type) {
      const m = msg.type.match(/^expert_(tactics|strategy|engine)_/);
      if (m) expertType = m[1] as ExpertType;
    }

    const validExpert = expertType && ['tactics', 'strategy', 'engine'].includes(expertType);

    if (validExpert && expertType) {
      if (msg.type === 'expert_start') {
        store.updateExpert(expertType, {
          status: 'thinking' as ExpertStatus,
          subtitle: `${EXPERT_NAME_MAP[expertType]}已接手`,
        });
        // 创建初始标题步骤，并启动chunk驱动计时
        const phases = EXPERT_THINKING_PHASES[expertType];
        expertPhaseIndexRef.current[expertType] = 0;
        const round = expertRoundRef.current[expertType];
        const stepId = getExpertStepId(expertType, round);
        expertLiveStepRef.current[expertType] = stepId;
        store.addOrchestratorStep(`${EXPERT_NAME_MAP[expertType]} · ${phases[0]}`, stepId);
        expertLastStepTimeRef.current[expertType] = Date.now();
      } else if (msg.type === 'expert_result') {
        // 关闭当前活跃步骤
        const liveStep = expertLiveStepRef.current[expertType];
        if (liveStep !== null) {
          store.finalizeOrchestratorStep(liveStep);
          expertLiveStepRef.current[expertType] = null;
        }
        store.updateExpert(expertType, {
          status: 'completed' as ExpertStatus,
          finding: sanitizeDisplayText(msg.finding || msg.summary || msg.message || ''),
          subtitle: msg.summary || msg.title || '',
        });
        // 检查是否所有启动过的专家都已完成 → 创建综合过渡步骤
        const allStarted = Object.values(expertLastStepTimeRef.current).some((t) => t > 0);
        const allDone = allStarted && (['tactics', 'strategy', 'engine'] as ExpertType[]).every(
          (e) => expertLastStepTimeRef.current[e] === 0 || expertLiveStepRef.current[e] === null
        );
        if (allDone) {
          store.addOrchestratorStep('协调者正在综合各路见解', 8000);
          synthesisStepTimeRef.current = Date.now();
        }
      } else if (msg.type === 'expert_step_start' || msg.type === 'expert_step_content' || msg.type === 'expert_step_end') {
        // 后处理步骤事件 → 用标题更新副标题
        if (msg.type === 'expert_step_start' && msg.title) {
          store.updateExpert(expertType, { subtitle: msg.title });
          // expert_step_start 也驱动时间步骤（弥补chunk停止后的空白期）
          const now = Date.now();
          const lastStepTime = expertLastStepTimeRef.current[expertType];
          if (lastStepTime > 0 && (now - lastStepTime) >= STEP_INTERVAL_MS) {
            const liveStep = expertLiveStepRef.current[expertType];
            if (liveStep !== null) {
              store.finalizeOrchestratorStep(liveStep);
            }
            expertRoundRef.current[expertType] += 1;
            const nextStepId = getExpertStepId(expertType, expertRoundRef.current[expertType]);
            expertLiveStepRef.current[expertType] = nextStepId;
            store.addOrchestratorStep(
              `${EXPERT_NAME_MAP[expertType]} · ${msg.title}`,
              nextStepId,
            );
            expertLastStepTimeRef.current[expertType] = now;
          }
        }
      } else if (msg.type === `expert_${expertType}_thinking` || msg.type === `expert_${expertType}_chunk` || msg.type === `expert_${expertType}_reasoning`) {
        // 实时 chunk → 更新专家 thinkingContent（悬浮卡片）
        store.updateExpert(expertType, { status: 'thinking' as ExpertStatus });
        const chunk = msg.message || '';
        store.appendExpertThinking(expertType, chunk);

        // === chunk驱动步骤生成器 ===
        // 每隔 STEP_INTERVAL_MS 自动 finalize 当前步骤并创建下一个思考阶段步骤
        const now = Date.now();
        const lastStepTime = expertLastStepTimeRef.current[expertType];
        if (lastStepTime > 0 && (now - lastStepTime) >= STEP_INTERVAL_MS) {
          // finalize 当前活跃步骤
          const liveStep = expertLiveStepRef.current[expertType];
          if (liveStep !== null) {
            store.finalizeOrchestratorStep(liveStep);
          }
          // 推进到下一个思考阶段
          const phases = EXPERT_THINKING_PHASES[expertType];
          const phaseIdx = expertPhaseIndexRef.current[expertType];
          const nextPhaseIdx = (phaseIdx + 1) % phases.length;
          expertPhaseIndexRef.current[expertType] = nextPhaseIdx;
          // 创建新步骤
          expertRoundRef.current[expertType] += 1;
          const nextStepId = getExpertStepId(expertType, expertRoundRef.current[expertType]);
          expertLiveStepRef.current[expertType] = nextStepId;
          store.addOrchestratorStep(
            `${EXPERT_NAME_MAP[expertType]} · ${phases[nextPhaseIdx]}`,
            nextStepId,
          );
          expertLastStepTimeRef.current[expertType] = now;
        }
      } else if (msg.type === `expert_${expertType}_tool`) {
        store.addExpertToolCall(expertType, {
          id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
          toolName: toChineseToolLabel(msg.message || 'tool'),
          params: '',
          result: '',
        });
        // 关闭旧步骤，新建工具标题步骤
        const liveStep = expertLiveStepRef.current[expertType];
        if (liveStep !== null) {
          store.finalizeOrchestratorStep(liveStep);
        }
        expertRoundRef.current[expertType] += 1;
        const toolStepId = getExpertStepId(expertType, expertRoundRef.current[expertType]);
        expertLiveStepRef.current[expertType] = toolStepId;
        store.addOrchestratorStep(
          `${EXPERT_NAME_MAP[expertType]} · ${toChineseToolLabel(msg.message || 'tool')}`,
          toolStepId
        );
      } else if (msg.type === `expert_${expertType}_tool_result`) {
        store.updateExpertToolResult(expertType, msg.message || '工具已返回');
        // 关闭工具步骤，新建下一轮分析步骤
        const liveStep = expertLiveStepRef.current[expertType];
        if (liveStep !== null) {
          store.finalizeOrchestratorStep(liveStep);
          expertRoundRef.current[expertType] += 1;
          const nextStepId = getExpertStepId(expertType, expertRoundRef.current[expertType]);
          expertLiveStepRef.current[expertType] = nextStepId;
          store.addOrchestratorStep(`${EXPERT_NAME_MAP[expertType]} · 分析中`, nextStepId);
        }
      }
    }

    if (msg.type === 'synthesis_step_start') {
      // 关闭综合等待过渡步骤（可能是 8000, 8001, 8002...）
      if (synthesisStepTimeRef.current > 0) {
        const phase = synthesisPhaseRef.current;
        store.finalizeOrchestratorStep(8000 + phase);
        for (let i = 0; i <= phase; i++) {
          store.finalizeOrchestratorStep(8000 + i);
        }
        synthesisStepTimeRef.current = 0;
      }
      store.updateOrchestratorSubtitle(msg.title || '协调者正在综合各路观点');
      store.addOrchestratorStep(msg.title || '综合分析', 9000 + (msg.step_index ?? 0));
    } else if (msg.type === 'synthesis_step_content') {
      // 综合步骤也只保留标题，不追加内容
    } else if (msg.type === 'synthesis_step_end') {
      store.finalizeOrchestratorStep(9000 + (msg.step_index ?? 0), msg.duration_ms);
    } else if (msg.type === 'orchestrator_subtitle') {
      store.updateOrchestratorSubtitle(msg.message || '');
    } else if (msg.type === 'dispatch_info') {
      store.updateOrchestratorSubtitle(toDispatchSubtitle(msg));
      // 调度信息也作为一个步骤出现
      store.addOrchestratorStep(toDispatchSubtitle(msg), 100);
      store.finalizeOrchestratorStep(100);
    } else if (msg.type === 'synthesis_chunk') {
      if (msg.message) {
        if (!store.orchestrator.subtitle) {
          store.updateOrchestratorSubtitle('综合讲解生成中');
        }
        store.appendOrchestratorContent(sanitizeDisplayText(msg.message));
        // synthesis_chunk 驱动过渡步骤: 在synthesis_step_start之前为空白期填充步骤
        const SYNTHESIS_TRANSITIONS = ['整合专家观点', '梳理分析要点', '生成教学讲解'];
        const now = Date.now();
        const lastT = synthesisStepTimeRef.current;
        if (lastT > 0 && (now - lastT) >= STEP_INTERVAL_MS) {
          const phase = synthesisPhaseRef.current;
          const nextPhase = (phase + 1) % SYNTHESIS_TRANSITIONS.length;
          synthesisPhaseRef.current = nextPhase;
          store.finalizeOrchestratorStep(8000 + phase);
          store.addOrchestratorStep(SYNTHESIS_TRANSITIONS[nextPhase], 8000 + nextPhase + 1);
          synthesisStepTimeRef.current = now;
        }
      }
    } else if (msg.type === 'thinking' || msg.type === 'thinking_chunk') {
      if (msg.message) {
        const progressMessage = msg.message.trim();
        const progressHints = ['启动分析', '检测局面', '引擎评估', 'AI分析中', '分析进行中', '专家分析中'];
        if (progressHints.some((hint) => progressMessage.includes(hint))) {
          store.updateOrchestratorSubtitle(progressMessage);
        }
        // 综合等待期: 通过 thinking 心跳驱动过渡步骤
        const WAITING_PHASES = ['汇总证据链', '比对专家分歧', '构建讲解框架', '准备综合分析'];
        const now = Date.now();
        const lastT = synthesisStepTimeRef.current;
        if (lastT > 0 && (now - lastT) >= STEP_INTERVAL_MS) {
          const phase = synthesisPhaseRef.current;
          const nextPhase = (phase + 1) % WAITING_PHASES.length;
          synthesisPhaseRef.current = nextPhase;
          store.finalizeOrchestratorStep(8000 + phase);
          store.addOrchestratorStep(WAITING_PHASES[nextPhase], 8000 + nextPhase + 1);
          synthesisStepTimeRef.current = now;
        }
      }
    }
  }, []);

  const triggerDeepAnalysis = useCallback(async () => {
    if (!fen || isAnalyzing) {
      return;
    }

    const lastMoveUci = lastMove
      ? `${String.fromCharCode(97 + lastMove.from.col)}${9 - lastMove.from.row}${String.fromCharCode(97 + lastMove.to.col)}${9 - lastMove.to.row}`
      : undefined;

    const hasMoveContext = Boolean(lastMoveUci && history.length > 0);
    const analysisFen = hasMoveContext ? (previousFen || fen) : fen;
    const question = hasMoveContext
      ? `分析刚才走的棋 ${lastMoveUci}，这步棋走得怎么样？`
      : '请严格基于当前棋盘局面进行分析，不要假设刚刚已经走过某一步。';

    resetAll();
    // 重置专家轮次跟踪
    expertLiveStepRef.current = { tactics: null, strategy: null, engine: null };
    expertRoundRef.current = { tactics: 0, strategy: 0, engine: 0 };
    expertLastStepTimeRef.current = { tactics: 0, strategy: 0, engine: 0 };
    expertPhaseIndexRef.current = { tactics: 0, strategy: 0, engine: 0 };
    synthesisStepTimeRef.current = 0;
    synthesisPhaseRef.current = 0;
    setPanelActive(true);
    setAnalyzing(true);
    setBoardCollapsed(true);

    try {
      await api.analyzeDeep(
        {
          fen: analysisFen,
          move: hasMoveContext ? lastMoveUci : undefined,
          history,
          question,
          show_thinking: true,
        },
        (msg) => {
          applyStreamMessage(msg);
        },
        (result) => {
          const store = useAgentStore.getState();
          if (!store.orchestrator.subtitle) {
            store.updateOrchestratorSubtitle('分析完成');
          }
          if (result.explanation && !store.orchestrator.content.trim()) {
            const cleaned = sanitizeDisplayText(result.explanation);
            store.appendOrchestratorContent(store.orchestrator.content ? `\n\n${cleaned}` : cleaned);
          }
          setAnalyzing(false);
        },
        (error) => {
          const store = useAgentStore.getState();
          store.updateOrchestratorSubtitle('分析失败');
          store.appendOrchestratorContent(`分析请求失败：${error}`);
          setAnalyzing(false);
        }
      );
    } catch (error) {
      const store = useAgentStore.getState();
      store.updateOrchestratorSubtitle('分析失败');
      store.appendOrchestratorContent(`分析请求失败：${error instanceof Error ? error.message : '未知错误'}`);
      setAnalyzing(false);
    }
  }, [applyStreamMessage, fen, history.length, isAnalyzing, lastMove, previousFen, resetAll, setAnalyzing, setBoardCollapsed, setPanelActive]);

  useEffect(() => {
    if (isPanelActive) {
      return;
    }

    if (api._activeEventSource) {
      api._activeEventSource.close();
      api._activeEventSource = null;
    }
  }, [isPanelActive]);

  return (
    <>
      {/* z=0: WebGL 背景层 */}
      <LiquidGlassApp
        bgImage="/O.webp"
        leftGlassRect={leftGlassRect}
        rightSidebarRect={rightSidebarRect}
        onDeepAnalysis={triggerDeepAnalysis}
      />

      <LeftSidebar boardLeft={boardLeft} onGlassRectChange={setLeftGlassRect} onDeepAnalysis={triggerDeepAnalysis} />

      {/* z=1: DOM 层 — 棋盘和右侧栏 */}
      <div
        style={{
          position: 'fixed',
          inset: 0,
          display: 'grid',
          gridTemplateColumns: `220px minmax(0, 1fr) ${isBoardCollapsed ? '156px' : '18px'} ${isBoardCollapsed ? '632px' : '260px'}`,
          height: '100vh',
          color: 'var(--apple-text)',
          overflow: 'hidden',
          transition: 'grid-template-columns 0.34s cubic-bezier(0.16, 1, 0.3, 1)',
          zIndex: 1,
        }}
      >
        {/* 左侧栏占位（宽度保持；内容在 z=3 固定定位层） */}
        <aside style={{ gridColumn: 1, pointerEvents: 'none' }} />

        {/* ── 中央棋盘区域 ── */}
        <main ref={boardAreaRef} style={{ ...S.boardArea, gridColumn: 2 }}>
          <motion.div
            ref={boardRef}
            animate={{
              scale: isBoardCollapsed ? 0.79 : showEngineDock ? 0.92 : 1,
              x: isBoardCollapsed ? -26 : 0,
              y: isBoardCollapsed ? -60 : showEngineDock ? -34 : 0,
            }}
            transition={{ type: 'spring', stiffness: 320, damping: 28, mass: 0.85 }}
            style={{ transformOrigin: 'center center', width: 'fit-content', zIndex: 10, willChange: 'transform', transform: 'translateZ(0)' }}
          >
            <ChessBoard />
          </motion.div>

          <AnimatePresence>
            {showEngineDock && (
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 10 }}
                transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
                style={{
                  ...S.engineDock,
                  top: engineFrame.top,
                  left: engineFrame.left,
                  width: engineFrame.width > 0 ? engineFrame.width : boardWidth || 680,
                }}
              >
                <EngineChart fluid={true} />
              </motion.div>
            )}
          </AnimatePresence>
        </main>

        <motion.aside
          ref={islandRef}
          initial={false}
          animate={{ opacity: isBoardCollapsed ? 0.94 : 0.16, x: isBoardCollapsed ? 0 : 10 }}
          transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
          style={{
            gridColumn: 3,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: isBoardCollapsed ? '18px 8px 18px 0' : '18px 0',
            overflow: 'visible',
            pointerEvents: 'auto',
          }}
        >
          <EvidenceMapIsland />
        </motion.aside>

        {/* ── 右侧透明占位（供 WebGL shape3 定位）── */}
        <motion.aside
          ref={rightSidebarRef}
          style={{ ...S.rightSidebar, gridColumn: 4, background: 'transparent', boxShadow: 'none', borderRadius: 28 }}
        >
          <div style={{ height: '100%', overflow: 'visible' }}>
            <AgentThinkingPanel />
          </div>
        </motion.aside>
      </div>
    </>
  );
}

const S: Record<string, React.CSSProperties> = {
  boardArea: {
    position: 'relative' as const,
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    padding: '16px 32px 24px',
    overflow: 'visible',
    height: '100%',
  },
  engineDock: {
    position: 'absolute' as const,
    height: 224,
    maxWidth: '100%',
    zIndex: 5,
  },
  rightSidebar: {
    display: 'flex',
    flexDirection: 'column' as const,
    overflow: 'visible',
  },
};
