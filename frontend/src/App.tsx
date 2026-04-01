import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useGameStore } from './store/useGameStore';
import { useAgentStore } from './store/useAgentStore';
import ChessBoard from './components/ChessBoard';
import AgentThinkingPanel from './components/AgentThinkingPanel';
import EngineChart from './components/EngineChart';
import LiquidGlassApp from './components/LiquidGlassApp';
import LeftSidebar from './components/LeftSidebar';

interface GlassRect {
  x: number;
  y: number;
  width: number;
  height: number;
  radius: number;
}

export default function App() {
  const {
    fen,
    gameMode,
    isBoardCollapsed,
    toggleBoardCollapsed,
    refreshEngineEvaluation,
  } = useGameStore();

  const { setPanelActive, setAnalyzing } = useAgentStore();

  const boardRef = useRef<HTMLDivElement>(null);
  const boardAreaRef = useRef<HTMLDivElement>(null);
  const [boardLeft, setBoardLeft] = useState(0);
  const [boardWidth, setBoardWidth] = useState(0);
  const [engineFrame, setEngineFrame] = useState({ top: 0, left: 0, width: 0 });
  const [leftGlassRect, setLeftGlassRect] = useState<GlassRect>({ x: 14, y: 14, width: 220, height: window.innerHeight - 28, radius: 34 });

  const showEngineDock = gameMode === 'analysis';

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
    if (gameMode !== 'analysis') {
      return;
    }
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
  const triggerDeepAnalysis = () => {
    setPanelActive(true);
    setAnalyzing(true);
    toggleBoardCollapsed();
  };

  return (
    <>
      {/* z=0: WebGL 背景层 */}
      <LiquidGlassApp
        bgImage="/bg.jpg"
        leftGlassRect={leftGlassRect}
        rightSidebarRect={rightSidebarRect}
        onDeepAnalysis={triggerDeepAnalysis}
      />

      <LeftSidebar boardLeft={boardLeft} onGlassRectChange={setLeftGlassRect} />

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
