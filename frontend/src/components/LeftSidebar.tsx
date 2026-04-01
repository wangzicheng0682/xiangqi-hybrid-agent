import { AnimatePresence, motion } from 'framer-motion';
import { CSSProperties, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { useGameStore } from '../store/useGameStore';
import { formatMovePairs } from '../utils/moveNotation';

interface LeftSidebarProps {
  boardLeft: number;
  onGlassRectChange?: (rect: { x: number; y: number; width: number; height: number; radius: number }) => void;
}

const SEGMENT_MODES = ['analysis', 'pve_red', 'pvp'] as const;

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

const resultText = (result: string): string => {
  if (result === '1-0') return '红胜';
  if (result === '0-1') return '黑胜';
  if (result === '1/2-1/2') return '和棋';
  return result || '未知';
};

interface SidebarButtonProps {
  label: string;
  onClick?: () => void;
  disabled?: boolean;
  variant?: 'default' | 'primary' | 'gold';
  style?: CSSProperties;
  buttonRef?: React.RefObject<HTMLButtonElement>;
}

function SidebarButton({
  label,
  onClick,
  disabled = false,
  variant = 'default',
  style,
  buttonRef,
}: SidebarButtonProps) {
  const palette =
    variant === 'primary'
      ? {
          background: 'linear-gradient(180deg, rgba(149, 236, 255, 0.18) 0%, rgba(72, 177, 255, 0.12) 100%)',
          border: 'rgba(209, 248, 255, 0.42)',
          color: 'rgba(240, 251, 255, 0.98)',
          shadow: '0 10px 24px rgba(34, 133, 206, 0.16), inset 0 1px 0 rgba(255,255,255,0.28)',
        }
      : variant === 'gold'
        ? {
            background: 'linear-gradient(180deg, rgba(255, 231, 150, 0.20) 0%, rgba(236, 192, 79, 0.14) 100%)',
            border: 'rgba(255, 228, 155, 0.44)',
            color: 'rgba(58, 37, 7, 0.92)',
            shadow: '0 10px 24px rgba(194, 145, 39, 0.18), inset 0 1px 0 rgba(255,250,220,0.48)',
          }
        : {
            background: 'linear-gradient(180deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.06) 100%)',
            border: 'rgba(255,255,255,0.22)',
            color: 'rgba(244, 241, 222, 0.94)',
            shadow: '0 8px 20px rgba(7, 18, 38, 0.18), inset 0 1px 0 rgba(255,255,255,0.2)',
          };

  return (
    <motion.button
      ref={buttonRef}
      type="button"
      whileHover={disabled ? undefined : { y: -1.5, scale: 1.01 }}
      whileTap={disabled ? undefined : { y: 0, scale: 0.985 }}
      transition={{ type: 'spring', stiffness: 460, damping: 28 }}
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      style={{
        ...styles.controlButton,
        background: palette.background,
        borderColor: palette.border,
        color: palette.color,
        boxShadow: palette.shadow,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.58 : 1,
        ...style,
      }}
    >
      {label}
    </motion.button>
  );
}

const rectFromElement = (element: HTMLElement, radius: number) => {
  const rect = element.getBoundingClientRect();
  return {
    x: rect.left,
    y: rect.top,
    width: rect.width,
    height: rect.height,
    radius,
  };
};

export default function LeftSidebar({ boardLeft, onGlassRectChange }: LeftSidebarProps) {
  const {
    gameMode,
    history,
    replayState,
    showArrows,
    setGameMode,
    exitReplay,
    toggleFlip,
    toggleShowArrows,
    resetGame,
    searchGames,
    loadGameFromNeo4j,
    navigateReplay,
    setBoardCollapsed,
  } = useGameStore();

  const [searchOpen, setSearchOpen] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [isSelectingGame, setIsSelectingGame] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const searchOverlayRef = useRef<HTMLDivElement>(null);
  const searchShellRef = useRef<HTMLDivElement>(null);
  const searchTriggerRef = useRef<HTMLButtonElement>(null);
  const searchTriggerRectRef = useRef<{ x: number; y: number; width: number; height: number; radius: number } | null>(null);

  const activeSegIndex = SEGMENT_MODES.indexOf(gameMode as (typeof SEGMENT_MODES)[number]);
  const inReplay = gameMode === 'replay' && replayState.selectedGame;
  const moves = inReplay ? replayState.moves : history;
  const movePairs = useMemo(() => formatMovePairs(moves), [moves]);
  const activeMoveIndex = inReplay ? replayState.currentIndex - 1 : moves.length - 1;
  const overlayWidth = useMemo(() => {
    const viewportWidth = typeof window === 'undefined' ? 1280 : window.innerWidth;
    const available = (boardLeft || viewportWidth * 0.58) - 264;
    return clamp(available, 360, Math.min(820, viewportWidth - 320));
  }, [boardLeft]);

  useEffect(() => {
    if (!scrollRef.current) return;

    const active = scrollRef.current.querySelector('[data-active="true"]') as HTMLElement | null;
    if (active) {
      active.scrollIntoView({ block: 'nearest' });
      return;
    }

    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [movePairs, activeMoveIndex, inReplay]);

  useEffect(() => {
    if (!searchOpen) return;
    const timer = window.setTimeout(() => searchInputRef.current?.focus(), 88);
    return () => window.clearTimeout(timer);
  }, [searchOpen]);

  useEffect(() => {
    if (!searchTriggerRef.current) return;
    searchTriggerRectRef.current = rectFromElement(searchTriggerRef.current, 24);
  });

  useLayoutEffect(() => {
    const target = searchOpen ? searchOverlayRef.current : wrapperRef.current;
    if (!target || !onGlassRectChange) return;

    const update = () => {
      onGlassRectChange(rectFromElement(target, searchOpen ? 32 : 34));
    };

    const raf = window.requestAnimationFrame(update);
    const resizeObserver = new ResizeObserver(update);
    resizeObserver.observe(target);
    window.addEventListener('resize', update);

    return () => {
      window.cancelAnimationFrame(raf);
      resizeObserver.disconnect();
      window.removeEventListener('resize', update);
    };
  }, [onGlassRectChange, searchOpen]);

  const handleSegmentClick = useCallback((idx: number) => {
    if (idx === activeSegIndex) return;
    if (gameMode === 'replay') exitReplay();
    setSearchOpen(false);
    setGameMode(SEGMENT_MODES[idx]);
  }, [activeSegIndex, exitReplay, gameMode, setGameMode]);

  const handleSearch = useCallback(async () => {
    const value = searchText.trim();
    if (!value) return;
    await searchGames(value);
  }, [searchGames, searchText]);

  const handleOpenSearch = useCallback(() => {
    setBoardCollapsed(false);
    if (searchTriggerRef.current && onGlassRectChange) {
      onGlassRectChange(rectFromElement(searchTriggerRef.current, 24));
    }
    setSearchOpen(true);
  }, [onGlassRectChange, setBoardCollapsed]);

  const handleSelectGame = useCallback(async (gameId: number) => {
    try {
      setIsSelectingGame(true);
      await loadGameFromNeo4j(gameId);
      setGameMode('replay');
      setBoardCollapsed(false);
      setSearchOpen(false);
    } finally {
      setIsSelectingGame(false);
    }
  }, [loadGameFromNeo4j, setBoardCollapsed, setGameMode]);

  const handleExitReplay = useCallback(() => {
    exitReplay();
    setGameMode('analysis');
    setSearchOpen(false);
  }, [exitReplay, setGameMode]);

  const handleCloseSearch = useCallback(() => {
    if (searchTriggerRectRef.current && onGlassRectChange) {
      onGlassRectChange(searchTriggerRectRef.current);
    }
    setSearchOpen(false);
  }, [onGlassRectChange]);

  const handleCameraUpload = useCallback(() => {
    cameraInputRef.current?.click();
  }, []);

  return (
    <div ref={wrapperRef} style={styles.wrapper}>
      <div style={styles.logoRow}>
        <span style={styles.logoMark}>♕</span>
        <div>
          <div style={styles.logoTitle}>象棋AI教练</div>
          <div style={styles.logoSubtitle}>Hybrid Agent System</div>
        </div>
      </div>

      <AnimatePresence mode="wait">
        {!searchOpen && (
          <motion.div
            key="sidebar-main"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6, filter: 'blur(8px)' }}
            transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
            style={styles.mainContent}
          >
            {inReplay ? (
              <>
                <section style={styles.replayInfo}>
                  <div style={styles.sectionHeader}>
                    <span>打棋谱回放</span>
                    <span style={styles.sectionMeta}>{replayState.currentIndex}/{replayState.totalMoves}</span>
                  </div>
                  <div style={styles.metaPair}><span style={styles.metaLabel}>红方</span><span>{replayState.selectedGame?.red || '未知'}</span></div>
                  <div style={styles.metaPair}><span style={styles.metaLabel}>黑方</span><span>{replayState.selectedGame?.black || '未知'}</span></div>
                  <div style={styles.metaPair}><span style={styles.metaLabel}>赛事</span><span>{replayState.selectedGame?.event || '未知赛事'}</span></div>
                </section>

                <div style={styles.buttonColumn}>
                  <div style={styles.buttonRow}>
                    <SidebarButton label="◀ 上一步" onClick={() => navigateReplay('prev')} style={styles.halfButton} />
                    <SidebarButton label="▶ 下一步" onClick={() => navigateReplay('next')} variant="primary" style={styles.halfButton} />
                  </div>
                  <SidebarButton label="退出打棋谱" onClick={handleExitReplay} variant="gold" style={styles.fullButton} />
                </div>
              </>
            ) : (
              <>
                <div
                  className="ios-segmented-control"
                  style={styles.segmentedControl}
                  onClick={(event) => {
                    const rect = event.currentTarget.getBoundingClientRect();
                    const relX = event.clientX - rect.left - 4;
                    const segIndex = Math.floor(relX / 58);
                    if (segIndex >= 0 && segIndex < 3) handleSegmentClick(segIndex);
                  }}
                >
                  <div
                    className="segment-indicator"
                    style={{ transform: `translateX(${Math.max(0, Math.min(activeSegIndex, 2)) * 58}px)` }}
                  />
                  {['分析', '人机', '双人'].map((label, index) => (
                    <span key={label} className={`segment-label ${activeSegIndex === index ? 'active' : ''}`}>
                      {label}
                    </span>
                  ))}
                </div>

                <div style={styles.buttonColumn}>
                  <SidebarButton label="⌕ 打棋谱" onClick={handleOpenSearch} variant="primary" style={styles.heroButton} buttonRef={searchTriggerRef} />

                  <div style={styles.buttonRow}>
                    <SidebarButton label="翻转棋盘" onClick={toggleFlip} style={styles.halfButton} />
                    <SidebarButton label={showArrows ? '关闭提示' : '显示提示'} onClick={toggleShowArrows} variant={showArrows ? 'primary' : 'default'} style={styles.halfButton} />
                  </div>

                  <div style={styles.buttonRow}>
                    <SidebarButton label="重新开始" onClick={resetGame} variant="gold" style={styles.largeButton} />
                    <SidebarButton label="识别" onClick={handleCameraUpload} style={styles.iconButton} />
                  </div>
                </div>
              </>
            )}

            <section style={styles.historyPanel}>
              <div style={styles.sectionHeader}>
                <span>走法记录</span>
                <span style={styles.sectionMeta}>{moves.length} 手</span>
              </div>

              <div ref={scrollRef} style={styles.historyList}>
                {movePairs.length === 0 && (
                  <div style={styles.emptyState}>对局开始后，这里会实时滚动显示完整棋谱。</div>
                )}

                {movePairs.map((pair) => (
                  <div key={pair.round} style={styles.moveRow}>
                    <div style={styles.roundCell}>{pair.round}.</div>
                    <div
                      data-active={pair.red?.index === activeMoveIndex}
                      style={{
                        ...styles.moveCell,
                        ...styles.redMove,
                        ...(pair.red?.index === activeMoveIndex ? styles.activeMove : null),
                      }}
                    >
                      {pair.red?.text || '...'}
                    </div>
                    <div
                      data-active={pair.black?.index === activeMoveIndex}
                      style={{
                        ...styles.moveCell,
                        ...styles.blackMove,
                        ...(pair.black?.index === activeMoveIndex ? styles.activeMove : null),
                      }}
                    >
                      {pair.black?.text || '...'}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {searchOpen && (
          <motion.div
            ref={searchOverlayRef}
            key="search-overlay"
            initial={{ opacity: 0, scale: 0.92, filter: 'blur(8px)' }}
            animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
            exit={{ opacity: 0, scale: 0.94, filter: 'blur(6px)' }}
            transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
            style={{ ...styles.searchOverlay, width: overlayWidth, transformOrigin: '24px 0%' }}
          >
            <motion.div
              ref={searchShellRef}
              initial={{ opacity: 0.58, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0.48, y: 6 }}
              transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
              style={styles.searchShell}
            >
              <div style={styles.searchRail}>
                <button type="button" onClick={handleCloseSearch} style={styles.backButton}>
                  ← 退出
                </button>

                <div style={styles.searchIntro}>
                  <div style={styles.searchKicker}>打棋谱</div>
                  <div style={styles.searchTitle}>从棋手、赛事或关键字进入历史对局</div>
                </div>

                <div style={styles.searchInputWrap}>
                  <span style={styles.searchIcon}>⌕</span>
                  <input
                    ref={searchInputRef}
                    value={searchText}
                    onChange={(event) => setSearchText(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') void handleSearch();
                    }}
                    placeholder="搜索棋手名或赛事"
                    style={styles.searchInput}
                  />
                </div>

                <SidebarButton label={replayState.isLoadingGames ? '搜索中...' : '开始搜索'} onClick={() => void handleSearch()} variant="primary" disabled={replayState.isLoadingGames} style={styles.searchButton} />
              </div>

              <div style={styles.resultPane}>
                <div style={styles.resultHeader}>
                  <span>搜索结果</span>
                  <span style={styles.sectionMeta}>{replayState.games.length} 局</span>
                </div>

                <div style={styles.resultList}>
                  {replayState.games.length === 0 ? (
                    <div style={styles.resultEmpty}>
                      输入棋手或赛事名后开始检索，例如：许银川、吕钦、全国个人赛。
                    </div>
                  ) : (
                    replayState.games.map((game) => (
                      <button
                        key={game.game_id}
                        type="button"
                        onClick={() => void handleSelectGame(game.game_id)}
                        disabled={isSelectingGame}
                        style={styles.resultItem}
                      >
                        <div style={styles.resultPlayers}>
                          <span style={styles.resultRed}>{game.red || '红方未知'}</span>
                          <span style={styles.resultVs}>vs</span>
                          <span style={styles.resultBlack}>{game.black || '黑方未知'}</span>
                        </div>
                        <div style={styles.resultMeta}>{game.event || '未知赛事'} · {game.date || '日期未知'}</div>
                        <div style={styles.resultOutcome}>{resultText(game.result)}</div>
                      </button>
                    ))
                  )}
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        style={{ display: 'none' }}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) {
            console.log('camera upload:', file.name);
          }
          event.target.value = '';
        }}
      />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    position: 'fixed',
    top: 14,
    left: 14,
    zIndex: 3,
    width: 220,
    height: 'calc(100vh - 28px)',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'visible',
    padding: '16px 12px 12px',
  },
  logoRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    paddingBottom: 10,
    borderBottom: '1px solid rgba(255, 255, 255, 0.12)',
    marginBottom: 14,
    flexShrink: 0,
  },
  logoMark: {
    fontSize: 26,
    color: 'rgba(212, 175, 55, 0.92)',
    lineHeight: 1,
  },
  logoTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: 'rgba(244, 241, 222, 0.96)',
    letterSpacing: '-0.01em',
  },
  logoSubtitle: {
    fontSize: 10,
    color: 'rgba(244, 241, 222, 0.52)',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
  },
  mainContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
    flex: 1,
  },
  historyPanel: {
    padding: '12px 12px 10px',
    borderRadius: 22,
    height: 176,
    maxHeight: 176,
    display: 'flex',
    flexDirection: 'column',
    flexShrink: 0,
    marginTop: 'auto',
    background: 'linear-gradient(180deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.025) 100%)',
    border: '1px solid rgba(255,255,255,0.10)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.12)',
  },
  sectionHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    fontSize: 11,
    color: 'rgba(244, 241, 222, 0.78)',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
    marginBottom: 10,
  },
  sectionMeta: {
    color: 'rgba(244, 241, 222, 0.48)',
    fontVariantNumeric: 'tabular-nums',
  },
  historyList: {
    flex: 1,
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
    paddingRight: 2,
  },
  moveRow: {
    display: 'grid',
    gridTemplateColumns: '24px minmax(0, 1fr) minmax(0, 1fr)',
    gap: 6,
    alignItems: 'stretch',
  },
  roundCell: {
    color: 'rgba(244, 241, 222, 0.42)',
    fontSize: 11,
    paddingTop: 7,
    fontVariantNumeric: 'tabular-nums',
  },
  moveCell: {
    minHeight: 28,
    borderRadius: 12,
    padding: '6px 8px',
    fontSize: 12,
    lineHeight: 1.4,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    border: '1px solid rgba(255,255,255,0.06)',
  },
  redMove: {
    color: '#ffb0aa',
    background: 'linear-gradient(180deg, rgba(176,54,48,0.20) 0%, rgba(80,18,24,0.16) 100%)',
  },
  blackMove: {
    color: 'rgba(235, 232, 220, 0.88)',
    background: 'linear-gradient(180deg, rgba(86,104,130,0.18) 0%, rgba(25,38,59,0.14) 100%)',
  },
  activeMove: {
    outline: '1px solid rgba(212, 175, 55, 0.45)',
    boxShadow: '0 0 0 1px rgba(212, 175, 55, 0.18), 0 8px 18px rgba(0, 0, 0, 0.22)',
    transform: 'translateY(-1px)',
  },
  emptyState: {
    minHeight: 86,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    textAlign: 'center',
    padding: '16px 12px',
    color: 'rgba(244, 241, 222, 0.46)',
    fontSize: 12,
    lineHeight: 1.6,
  },
  segmentedControl: {
    width: '100%',
    height: 40,
    padding: 4,
    flexShrink: 0,
  },
  buttonColumn: {
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
    flexShrink: 0,
  },
  buttonRow: {
    display: 'flex',
    gap: 10,
  },
  controlButton: {
    position: 'relative',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 40,
    padding: '0 14px',
    borderRadius: 18,
    borderStyle: 'solid',
    borderWidth: 1,
    fontSize: 12,
    fontWeight: 600,
    letterSpacing: '0.01em',
    outline: 'none',
    userSelect: 'none',
    backdropFilter: 'blur(10px) saturate(135%)',
    WebkitBackdropFilter: 'blur(10px) saturate(135%)',
  },
  heroButton: {
    width: '100%',
    minHeight: 46,
    borderRadius: 20,
    fontSize: 14,
  },
  fullButton: {
    width: '100%',
    minHeight: 42,
    borderRadius: 18,
  },
  halfButton: {
    width: 'calc(50% - 5px)',
    minHeight: 38,
  },
  largeButton: {
    width: 'calc(100% - 62px)',
    minHeight: 40,
  },
  iconButton: {
    width: 52,
    minHeight: 40,
    padding: 0,
  },
  replayInfo: {
    padding: '12px 12px 10px',
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    borderRadius: 18,
    background: 'linear-gradient(180deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%)',
    border: '1px solid rgba(255,255,255,0.10)',
    flexShrink: 0,
  },
  metaPair: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: 10,
    fontSize: 12,
    color: 'rgba(244, 241, 222, 0.82)',
  },
  metaLabel: {
    color: 'rgba(244, 241, 222, 0.48)',
  },
  searchOverlay: {
    position: 'absolute',
    top: 76,
    left: 18,
    maxWidth: 'calc(100vw - 180px)',
    zIndex: 6,
  },
  searchShell: {
    display: 'grid',
    gridTemplateColumns: '180px minmax(0, 1fr)',
    gap: 14,
    padding: 18,
    borderRadius: 30,
    background: 'transparent',
    border: '1px solid rgba(255,255,255,0.16)',
  },
  searchRail: {
    display: 'flex',
    flexDirection: 'column',
    gap: 14,
    minWidth: 0,
  },
  backButton: {
    height: 38,
    borderRadius: 999,
    border: '1px solid rgba(115,97,59,0.18)',
    background: 'linear-gradient(180deg, rgba(255,255,255,0.18) 0%, rgba(255,255,255,0.08) 100%)',
    color: 'rgba(82, 62, 28, 0.88)',
    cursor: 'pointer',
    fontSize: 12,
    backdropFilter: 'blur(14px)',
  },
  searchIntro: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
  },
  searchKicker: {
    color: 'rgba(171, 126, 32, 0.88)',
    fontSize: 11,
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
  },
  searchTitle: {
    color: 'rgba(84, 64, 28, 0.96)',
    fontSize: 16,
    lineHeight: 1.4,
    textShadow: '0 1px 0 rgba(255,255,255,0.22)',
  },
  searchInputWrap: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    height: 48,
    padding: '0 14px',
    borderRadius: 18,
    border: '1px solid rgba(115,97,59,0.18)',
    background: 'linear-gradient(180deg, rgba(255,255,255,0.18) 0%, rgba(255,255,255,0.08) 100%)',
  },
  searchButton: {
    width: 144,
    minHeight: 42,
  },
  searchIcon: {
    color: 'rgba(177, 136, 48, 0.92)',
    fontSize: 14,
  },
  searchInput: {
    flex: 1,
    background: 'transparent',
    border: 'none',
    outline: 'none',
    color: 'rgba(70, 55, 27, 0.92)',
    fontSize: 14,
  },
  resultPane: {
    minWidth: 0,
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
  },
  resultHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    color: 'rgba(88, 67, 31, 0.82)',
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
  },
  resultList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    maxHeight: 360,
    overflowY: 'auto',
    paddingRight: 4,
  },
  resultEmpty: {
    minHeight: 220,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    textAlign: 'center',
    color: 'rgba(106, 82, 39, 0.72)',
    fontSize: 13,
    lineHeight: 1.7,
    padding: '0 20px',
  },
  resultItem: {
    textAlign: 'left',
    padding: '12px 14px',
    borderRadius: 18,
    border: '1px solid rgba(115,97,59,0.14)',
    background: 'linear-gradient(180deg, rgba(255,255,255,0.16) 0%, rgba(255,255,255,0.07) 100%)',
    color: 'rgba(72, 56, 28, 0.92)',
    cursor: 'pointer',
  },
  resultPlayers: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginBottom: 6,
    fontSize: 14,
  },
  resultRed: {
    color: '#ffaea2',
    fontWeight: 600,
  },
  resultVs: {
    color: 'rgba(92, 76, 48, 0.44)',
    fontSize: 11,
    textTransform: 'uppercase',
  },
  resultBlack: {
    color: 'rgba(57, 48, 31, 0.88)',
    fontWeight: 600,
  },
  resultMeta: {
    color: 'rgba(92, 74, 42, 0.70)',
    fontSize: 12,
  },
  resultOutcome: {
    marginTop: 8,
    color: 'rgba(212, 175, 55, 0.84)',
    fontSize: 11,
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
  },
};
