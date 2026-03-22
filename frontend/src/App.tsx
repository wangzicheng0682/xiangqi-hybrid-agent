import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useGameStore } from './store/useGameStore';
import { useAgentStore } from './store/useAgentStore';
import ChessBoard from './components/ChessBoard';
import AgentThinkingPanel from './components/AgentThinkingPanel';
import ReplayNavigator from './components/ReplayNavigator';
import EngineChart from './components/EngineChart';

type GameMode = 'analysis' | 'pvp' | 'pve_red' | 'pve_black' | 'replay';
type InputMode = 'online' | 'camera';

export default function App() {
  const {
    gameMode, setGameMode, resetGame, redToMove,
    flipped, toggleFlip, showArrows, toggleShowArrows,
    history, replayState,
    isBoardCollapsed, setBoardCollapsed, toggleBoardCollapsed,
  } = useGameStore();

  const { setPanelActive, setAnalyzing } = useAgentStore();

  const [inputMode, setInputMode] = useState<InputMode>('online');
  const [isDark, setIsDark] = useState(() =>
    document.documentElement.getAttribute('data-theme') === 'dark'
  );

  const toggleTheme = () => {
    const next = !isDark;
    setIsDark(next);
    document.documentElement.setAttribute('data-theme', next ? 'dark' : '');
  };

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

  const handleModeChange = (mode: GameMode) => {
    if (mode === 'replay') {
      setGameMode(mode);
    } else {
      if (gameMode === 'replay') {
        useGameStore.getState().exitReplay();
      }
      setGameMode(mode);
    }
    if (mode === 'analysis') {
      // 触发分析模式：启动扑克牌动画（棋盘收缩由 handleToggleBoard 处理）
      setPanelActive(true);
      setAnalyzing(true);
    } else {
      setBoardCollapsed(false);
    }
  };

  const handleToggleBoard = () => {
    toggleBoardCollapsed();
  };

  const handleInputModeChange = (mode: InputMode) => {
    setInputMode(mode);
    if (mode === 'camera') {
      alert('拍照识别功能开发中，敬请期待！');
    }
  };

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: `220px 1fr ${isBoardCollapsed ? '620px' : '260px'}`,
        height: '100vh',
        color: 'var(--apple-text)',
        overflow: 'hidden',
        transition: 'grid-template-columns 0.45s cubic-bezier(0.16, 1, 0.3, 1)',
      }}
    >
      {/* ── 左侧边栏 ── */}
      <aside className="lg-sidebar lg-sidebar-left" style={S.leftSidebar}>
        {/* Logo区域 */}
        <div style={S.logoSection}>
          <div style={S.logoIcon}>♕</div>
          <div>
            <div style={S.logoTitle}>象棋AI教练</div>
            <div style={S.logoSubtitle}>混合代理系统</div>
          </div>
          <button
            onClick={toggleTheme}
            title={isDark ? '浅色模式' : '深色模式'}
            style={{
              marginLeft: 'auto',
              background: 'rgba(255,255,255,0.15)',
              border: '1px solid rgba(255,255,255,0.2)',
              borderRadius: 8,
              width: 32,
              height: 32,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              fontSize: 16,
              color: 'rgba(255,255,255,0.7)',
              flexShrink: 0,
              transition: 'background 0.2s',
            }}
          >
            {isDark ? '☀️' : '🌙'}
          </button>
        </div>

        {/* 输入局面 */}
        <div style={S.section}>
          <div style={S.sectionLabel}>输入局面</div>
          <div style={S.inputModeGrid}>
            <button
              onClick={() => handleInputModeChange('online')}
              className="glass-panel"
              style={{
                ...S.inputModeBtn,
                ...(inputMode === 'online' ? S.inputModeBtnActive : {}),
              }}
            >
              <div style={S.inputModeIcon}>◻</div>
              <div style={S.inputModeLabel}>在线对局</div>
              <div style={S.inputModeHint}>网页棋盘走棋</div>
            </button>
            <button
              onClick={() => handleInputModeChange('camera')}
              className="glass-panel"
              style={{
                ...S.inputModeBtn,
                ...(inputMode === 'camera' ? S.inputModeBtnActive : {}),
              }}
            >
              <div style={S.inputModeIcon}>◎</div>
              <div style={S.inputModeLabel}>拍照识别</div>
              <div style={S.inputModeHint}>拍现实棋盘识别</div>
            </button>
          </div>
        </div>

        {/* 对局模式 */}
        <div style={S.section}>
          <div style={S.sectionLabel}>对局模式</div>
          <div style={S.modeGrid}>
            {(['analysis', 'pve_red', 'pvp'] as GameMode[]).map(mode => (
              <button
                key={mode}
                onClick={() => { handleModeChange(mode); if (mode === 'analysis') handleToggleBoard(); }}
                className="glass-panel"
                style={{
                  ...S.modeButton,
                  ...(gameMode === mode ? S.modeButtonActive : {}),
                }}
              >
                <div style={S.modeIcon}>{mode === 'analysis' ? '◈' : mode === 'pve_red' ? '◉' : '◎'}</div>
                <div>{mode === 'analysis' ? '分析' : mode === 'pve_red' ? '人机' : '双人'}</div>
              </button>
            ))}
          </div>
        </div>

        {/* 学习模式 */}
        <div style={S.section}>
          <div style={S.sectionLabel}>学习模式</div>
          <button
            onClick={() => handleModeChange('replay')}
            className={`glass-panel ${gameMode === 'replay' ? '' : ''}`}
            style={{
              ...S.modeButton,
              width: '100%',
              ...(gameMode === 'replay' ? S.modeButtonActive : {}),
            }}
          >
            <div style={S.modeIcon}>▣</div>
            <div>打棋谱</div>
          </button>
        </div>

        {/* 显示设置 */}
        {gameMode !== 'replay' && (
          <div style={S.section}>
            <div style={S.sectionLabel}>显示设置</div>
            <div style={S.settingList}>
              <button
                onClick={toggleFlip}
                className="glass-panel glass-panel-hover"
                style={{
                  ...S.settingButton,
                  ...(flipped ? S.settingButtonActive : {}),
                }}
              >
                <span>↺</span>
                <span>翻转棋盘</span>
                <span style={S.toggleIndicator}>{flipped ? '✓' : ''}</span>
              </button>
              <button
                onClick={toggleShowArrows}
                className="glass-panel glass-panel-hover"
                style={{
                  ...S.settingButton,
                  ...(showArrows ? S.settingButtonActive : {}),
                }}
              >
                <span>→</span>
                <span>显示提示</span>
                <span style={S.toggleIndicator}>{showArrows ? '✓' : ''}</span>
              </button>
            </div>
          </div>
        )}

        {/* 当前状态 */}
        <div style={S.section}>
          <div style={S.sectionLabel}>当前状态</div>
          <div className="glass-panel-sm" style={S.statusCard}>
            <div style={S.statusRow}>
              <span style={S.statusLabel}>回合</span>
              <span style={{
                ...S.statusBadge,
                background: redToMove ? 'rgba(196,30,58,0.75)' : 'rgba(44,62,80,0.75)',
              }}>
                {redToMove ? '红方' : '黑方'}
              </span>
            </div>
            <div style={S.statusRow}>
              <span style={S.statusLabel}>步数</span>
              <span style={S.statusValue}>{history.length} 步</span>
            </div>
            {gameMode === 'replay' && replayState.selectedGame && (
              <>
                <div style={S.divider} />
                <div style={S.replayInfo}>
                  <div style={S.replayTitle}>{replayState.selectedGame.red} vs {replayState.selectedGame.black}</div>
                  <div style={S.replayMeta}>{replayState.currentIndex} / {replayState.totalMoves}</div>
                </div>
              </>
            )}
          </div>
        </div>

        {/* 走法记录 */}
        {history.length > 0 && gameMode !== 'replay' && (
          <div style={S.section}>
            <div style={S.sectionLabel}>走法记录</div>
            <div className="glass-panel-sm" style={S.moveList}>
              {history.map((move, i) => (
                <span
                  key={i}
                  style={{
                    ...S.moveItem,
                    background: i % 2 === 0 ? 'rgba(196,30,58,0.12)' : 'rgba(44,62,80,0.1)',
                    color: i % 2 === 0 ? 'rgba(196,30,58,0.9)' : 'rgba(44,62,80,0.9)',
                  }}
                >
                  {Math.floor(i/2) + 1}{i % 2 === 0 ? '.' : '..'} {move}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* 重置按钮 */}
        {gameMode !== 'replay' && (
          <button className="apple-btn-gold" style={S.resetButton} onClick={resetGame}>
            ↺ 重新开始
          </button>
        )}
      </aside>

      {/* ── 中央棋盘区域 ── */}
      <main ref={boardAreaRef} style={S.boardArea}>
        {/* 棋盘 */}
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

        {/* 引擎图 */}
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
        className="lg-sidebar lg-sidebar-right"
        style={S.rightSidebar}
        layout
        transition={{ type: 'spring', stiffness: 280, damping: 24 }}
      >
        {/* 分析栏内部：直接渲染 AgentThinkingPanel */}
        <div style={{ height: '100%', overflow: 'visible' }}>
          <AgentThinkingPanel />
        </div>
      </motion.aside>
    </div>
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
