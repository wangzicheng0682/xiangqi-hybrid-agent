import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useGameStore } from './store/useGameStore';
import { useAgentStore } from './store/useAgentStore';
import ChessBoard from './components/ChessBoard';
import AgentThinkingPanel from './components/AgentThinkingPanel';
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
  const applyStreamMessage = useCallback((msg: AnalysisStreamMessage) => {
    const store = useAgentStore.getState();
    const expertType = msg.expert as ExpertType | undefined;

    const validExpert = expertType && ['tactics', 'strategy', 'engine'].includes(expertType);

    if (validExpert) {
      if (msg.type === 'expert_start') {
        store.updateExpert(expertType, { status: 'thinking' as ExpertStatus });
      } else if (msg.type === 'expert_result') {
        store.updateExpert(expertType, {
          status: 'completed' as ExpertStatus,
          finding: msg.finding || msg.summary || msg.message || '',
          subtitle: msg.summary || msg.title || '',
        });
      } else if (msg.type === 'expert_step_start') {
        store.updateExpert(expertType, {
          status: 'thinking' as ExpertStatus,
          subtitle: msg.title || '',
        });
        store.addExpertStep(expertType, msg.title || '分析步骤', msg.step_index ?? 0);
      } else if (msg.type === 'expert_step_content') {
        store.appendExpertStepContent(expertType, msg.step_index ?? 0, msg.content || msg.message || '');
      } else if (msg.type === 'expert_step_end') {
        store.finalizeExpertStep(expertType, msg.step_index ?? 0, msg.duration_ms);
      } else if (msg.type === `expert_${expertType}_thinking` || msg.type === `expert_${expertType}_chunk`) {
        store.updateExpert(expertType, { status: 'thinking' as ExpertStatus });
        store.appendExpertThinking(expertType, msg.message || '');
      } else if (msg.type === `expert_${expertType}_tool`) {
        store.addExpertToolCall(expertType, {
          id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
          toolName: msg.message || 'tool',
          params: '',
          result: '',
        });
      }
    }

    if (msg.type === 'synthesis_step_start') {
      store.updateOrchestratorSubtitle(msg.title || '综合分析');
      store.addOrchestratorStep(msg.title || '综合分析', msg.step_index ?? 0);
    } else if (msg.type === 'synthesis_step_content') {
      store.appendOrchestratorStepContent(msg.step_index ?? 0, msg.content || msg.message || '');
    } else if (msg.type === 'synthesis_step_end') {
      store.finalizeOrchestratorStep(msg.step_index ?? 0, msg.duration_ms);
    } else if (msg.type === 'orchestrator_subtitle') {
      store.updateOrchestratorSubtitle(msg.message || '');
    } else if (msg.type === 'synthesis_chunk') {
      if (msg.message) {
        if (!store.orchestrator.subtitle) {
          store.updateOrchestratorSubtitle('综合讲解生成中');
        }
        store.appendOrchestratorContent(msg.message);
      }
    } else if (msg.type === 'thinking' || msg.type === 'thinking_chunk') {
      if (msg.message) {
        const progressMessage = msg.message.trim();
        const progressHints = ['启动分析', '检测局面', '引擎评估', 'AI分析中', '分析进行中'];
        if (progressHints.some((hint) => progressMessage.includes(hint))) {
          store.updateOrchestratorSubtitle(progressMessage);
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
    setPanelActive(true);
    setAnalyzing(true);
    setBoardCollapsed(true);

    try {
      await api.analyzeDeep(
        {
          fen: analysisFen,
          move: hasMoveContext ? lastMoveUci : undefined,
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
            store.appendOrchestratorContent(store.orchestrator.content ? `\n\n${result.explanation}` : result.explanation);
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
        bgImage="/bg.jpg"
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
          gridTemplateColumns: `220px 1fr ${isBoardCollapsed ? '620px' : '260px'}`,
          height: '100vh',
          color: 'var(--apple-text)',
          overflow: 'hidden',
          transition: 'grid-template-columns 0.45s cubic-bezier(0.16, 1, 0.3, 1)',
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
              scale: isBoardCollapsed ? 0.75 : showEngineDock ? 0.92 : 1,
              x: isBoardCollapsed ? -120 : 0,
              y: isBoardCollapsed ? -80 : showEngineDock ? -34 : 0,
            }}
            transition={{ type: 'spring', stiffness: 280, damping: 24 }}
            style={{ transformOrigin: 'center center', width: 'fit-content', zIndex: 10 }}
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

        {/* ── 右侧透明占位（供 WebGL shape3 定位）── */}
        <motion.aside
          ref={rightSidebarRef}
          style={{ ...S.rightSidebar, gridColumn: 3, background: 'transparent', boxShadow: 'none', borderRadius: 28 }}
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
