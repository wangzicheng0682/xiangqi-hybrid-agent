import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useGameStore } from './store/useGameStore';
import { useAgentStore } from './store/useAgentStore';
import ChessBoard from './components/ChessBoard';
import AgentThinkingPanel from './components/AgentThinkingPanel';
import ReplayNavigator from './components/ReplayNavigator';
import EngineChart from './components/EngineChart';
import LiquidGlassApp from './components/LiquidGlassApp';

export default function App() {
  const {
    gameMode,
    replayState,
    isBoardCollapsed,
    toggleBoardCollapsed,
  } = useGameStore();

  const { setPanelActive, setAnalyzing } = useAgentStore();

  // 测量棋盘高度，用于计算引擎图的 top 位置
  const boardRef = useRef<HTMLDivElement>(null);
  const boardAreaRef = useRef<HTMLDivElement>(null);
  const [engineTop, setEngineTop] = useState(0);

  useEffect(() => {
    const updateTop = () => {
      if (!boardRef.current || !boardAreaRef.current) return;
      const boardRect = boardRef.current.getBoundingClientRect();
      const areaRect = boardAreaRef.current.getBoundingClientRect();
      const visualH = boardRect.height;
      const top = (boardRect.top - areaRect.top) + visualH + 8;
      setEngineTop(top);
    };

    updateTop();
    const ro = new ResizeObserver(updateTop);
    if (boardAreaRef.current) ro.observe(boardAreaRef.current);
    return () => ro.disconnect();
  }, [isBoardCollapsed]);

  // 深度分析触发（独立功能，任何模式下都可用）
  const triggerDeepAnalysis = () => {
    setPanelActive(true);
    setAnalyzing(true);
    toggleBoardCollapsed(); // 触发棋盘收缩 + 右侧栏扩张
  };

  return (
    <>
      {/* z=0: WebGL 背景层 */}
      <LiquidGlassApp bgImage="/bg.jpg" />

      {/* z=1: DOM 层 — 棋盘和扑克牌 */}
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
        {/* ── 左侧边栏（空的，WebGL 覆盖，禁用 CSS backdrop-filter） */}
        <aside className="lg-sidebar lg-sidebar-webgl" style={S.leftSidebar} />

        {/* ── 中央棋盘区域 ── */}
        <main ref={boardAreaRef} style={S.boardArea}>
          <motion.div
            ref={boardRef}
            animate={{
              scale: isBoardCollapsed ? 0.75 : 1,
              x: isBoardCollapsed ? -120 : 0,
              y: isBoardCollapsed ? -80 : 0,
            }}
            transition={{ type: 'spring', stiffness: 280, damping: 24 }}
            style={{
              transformOrigin: 'center center',
              width: 'fit-content',
              zIndex: 10,
            }}
          >
            <ChessBoard />
          </motion.div>

          <AnimatePresence>
            {isBoardCollapsed && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ delay: 0.15, duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                style={{ ...S.engineAbs, top: engineTop }}
              >
                <EngineChart fluid={true} />
              </motion.div>
            )}
          </AnimatePresence>

          {gameMode === 'replay' && replayState.selectedGame && (
            <div style={S.replayNavigator}>
              <ReplayNavigator />
            </div>
          )}
        </main>

        {/* ── 右侧分析面板 ── */}
        <motion.aside
          className="lg-sidebar liquid-glass-strong lg-sidebar-right"
          style={S.rightSidebar}
          layout
          transition={{ type: 'spring', stiffness: 280, damping: 24 }}
        >
          {!isBoardCollapsed && (
            <div style={S.analysisTrigger}>
              <button
                className="apple-btn-gold"
                style={S.analysisBtn}
                onClick={triggerDeepAnalysis}
              >
                <span style={S.analysisBtnIcon}>◈</span>
                <span>深度分析</span>
              </button>
            </div>
          )}

          <div style={{ height: '100%', overflow: 'visible' }}>
            <AgentThinkingPanel />
          </div>
        </motion.aside>
      </div>
    </>
  );
}

const S: Record<string, React.CSSProperties> = {
  // ── 左侧边栏 ──────────────────────────
  leftSidebar: {
    padding: '20px 14px',
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
    overflowY: 'auto',
    position: 'relative' as const,
  } as React.CSSProperties,

  logoSection: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    paddingBottom: 16,
    borderBottom: '1px solid rgba(180,160,140,0.15)',
  },
  logoIcon: {
    fontSize: 28,
    color: 'rgba(212,175,55,0.85)',
    lineHeight: 1,
  },
  logoTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: 'var(--apple-text)',
    letterSpacing: '-0.01em',
  },
  logoSubtitle: {
    fontSize: 11,
    color: 'var(--apple-text-secondary)',
    marginTop: 2,
  },

  section: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  sectionLabel: {
    fontSize: 10,
    fontWeight: '600',
    color: 'var(--apple-text-tertiary)',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
  },

  modeGrid: {
    display: 'flex',
    gap: 6,
  },
  modeButton: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    gap: 5,
    padding: '10px 6px',
    cursor: 'pointer',
    fontSize: 12,
    transition: 'all 0.18s cubic-bezier(0.16, 1, 0.3, 1)',
    background: 'transparent',
    border: 'none',
  },
  modeButtonActive: {
    background: 'rgba(212,175,55,0.1)',
    border: '1px solid rgba(212,175,55,0.25)',
    borderTopColor: 'rgba(212,175,55,0.4)',
  },
  modeIcon: {
    fontSize: 16,
    color: 'var(--apple-text-secondary)',
  },

  inputModeGrid: {
    display: 'flex',
    gap: 6,
  },
  inputModeBtn: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    gap: 4,
    padding: '10px 6px',
    cursor: 'pointer',
    fontSize: 11,
    transition: 'all 0.18s cubic-bezier(0.16, 1, 0.3, 1)',
    background: 'transparent',
    border: 'none',
  },
  inputModeBtnActive: {
    background: 'rgba(212,175,55,0.1)',
    border: '1px solid rgba(212,175,55,0.25)',
    borderTopColor: 'rgba(212,175,55,0.4)',
  },
  inputModeIcon: {
    fontSize: 18,
    color: 'var(--apple-text-secondary)',
    lineHeight: 1,
  },
  inputModeLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: 'var(--apple-text)',
  },
  inputModeHint: {
    fontSize: 9,
    color: 'var(--apple-text-tertiary)',
  },

  settingList: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 4,
  },
  settingButton: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '8px 10px',
    cursor: 'pointer',
    fontSize: 12,
    transition: 'all 0.18s cubic-bezier(0.16, 1, 0.3, 1)',
    background: 'transparent',
    border: 'none',
    borderRadius: 'var(--radius-sm)',
  },
  settingButtonActive: {
    background: 'rgba(212,175,55,0.1)',
    border: '1px solid rgba(212,175,55,0.2)',
  },
  toggleIndicator: {
    marginLeft: 'auto',
    fontWeight: '700',
    fontSize: 11,
    color: 'rgba(212,175,55,0.8)',
  },

  statusCard: {
    background: 'rgba(0,0,0,0.02)',
    backdropFilter: 'blur(12px)',
    WebkitBackdropFilter: 'blur(12px)',
    borderRadius: 'var(--radius-md)',
    padding: '10px 12px',
  },
  statusRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  statusLabel: {
    fontSize: 12,
    color: 'var(--apple-text-secondary)',
  },
  statusBadge: {
    padding: '2px 10px',
    borderRadius: 'var(--radius-full)',
    fontSize: 11,
    fontWeight: '600',
    color: '#fff',
  },
  statusValue: {
    fontSize: 12,
    color: 'var(--apple-text)',
    fontWeight: '500',
  },
  divider: {
    height: 1,
    background: 'var(--apple-border)',
    margin: '6px 0',
  },
  replayInfo: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 2,
  },
  replayTitle: {
    fontSize: 11,
    color: 'var(--apple-text)',
  },
  replayMeta: {
    fontSize: 10,
    color: 'var(--apple-text-secondary)',
  },

  moveList: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: 4,
    maxHeight: 160,
    overflowY: 'auto',
    padding: 4,
  },
  moveItem: {
    padding: '3px 6px',
    borderRadius: 'var(--radius-xs)',
    fontSize: 11,
    fontFamily: 'SF Mono, JetBrains Mono, Consolas, monospace',
  },

  resetButton: {
    marginTop: 'auto',
    padding: '10px 16px',
    borderRadius: 'var(--radius-md)',
    fontSize: 13,
    fontWeight: '600',
    cursor: 'pointer',
    width: '100%',
  },

  // ── 棋盘区域 ──────────────────────────
  boardArea: {
    position: 'relative' as const,
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    padding: '16px 32px',
    overflow: 'hidden',
    height: '100%',
  },

  engineAbs: {
    position: 'absolute' as const,
    left: 32,
    right: 32,
    bottom: 16,
    zIndex: 5,
  },

  replayNavigator: {
    width: '100%',
    maxWidth: 500,
    marginTop: 12,
  },

  // ── 右侧边栏 ──────────────────────────
  rightSidebar: {
    display: 'flex',
    flexDirection: 'column' as const,
    overflow: 'visible',
  },

  // 深度分析触发按钮区域
  analysisTrigger: {
    padding: '12px 14px',
    flexShrink: 0,
  },
  analysisBtn: {
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    padding: '10px 16px',
    borderRadius: 'var(--radius-md)',
    fontSize: 13,
    fontWeight: '600',
    cursor: 'pointer',
  },
  analysisBtnIcon: {
    fontSize: 16,
  },

  tabHeader: {
    display: 'flex',
    background: 'rgba(0,0,0,0.02)',
    borderBottom: '1px solid var(--apple-border-subtle)',
    borderRadius: 'var(--radius-lg) var(--radius-lg) 0 0',
    overflow: 'hidden',
    flexShrink: 0,
  },
  tabButton: {
    flex: 1,
    padding: '12px 4px',
    background: 'transparent',
    border: 'none',
    borderRight: '1px solid var(--apple-border-subtle)',
    color: 'var(--apple-text-secondary)',
    cursor: 'pointer',
    transition: 'all 0.18s cubic-bezier(0.16, 1, 0.3, 1)',
    fontSize: 16,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  tabButtonActive: {
    background: 'rgba(0,0,0,0.03)',
    color: 'var(--apple-text)',
    borderBottom: '2px solid rgba(212,175,55,0.6)',
  },
  tabIcon: {
    fontSize: 16,
  },

  tabContent: {
    flex: 1,
    overflow: 'auto',
    padding: '14px 14px',
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    padding: '40px 20px',
    textAlign: 'center' as const,
    gap: 8,
  },
  emptyIcon: {
    fontSize: 36,
    color: 'var(--apple-text-tertiary)',
    marginBottom: 4,
  },
  emptyHint: {
    fontSize: 11,
    color: 'var(--apple-text-tertiary)',
    marginTop: 2,
  },
};
