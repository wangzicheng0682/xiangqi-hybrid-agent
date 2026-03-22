import { useState, useEffect } from 'react';
import { useGameStore } from './store/useGameStore';
import ChessBoard from './components/ChessBoard';
import DeepAnalysisPanel from './components/DeepAnalysisPanel';
import PositionAnalysisPanel from './components/PositionAnalysisPanel';
import TacticalTagsPanel from './components/TacticalTagsPanel';
import ReplayPanel from './components/ReplayPanel';
import ReplayNavigator from './components/ReplayNavigator';

type GameMode = 'analysis' | 'pvp' | 'pve_red' | 'pve_black' | 'replay';
type RightTab = 'deep' | 'position' | 'tags' | 'moves';
type InputMode = 'online' | 'camera';

export default function App() {
  const {
    gameMode, setGameMode, resetGame, redToMove,
    flipped, toggleFlip, showArrows, toggleShowArrows,
    history, replayState
  } = useGameStore();

  const [rightTab, setRightTab] = useState<RightTab>('deep');
  const [inputMode, setInputMode] = useState<InputMode>('online');

  useEffect(() => {
    if (gameMode === 'replay') {
      setRightTab('moves');
    }
  }, [gameMode]);

  const tabLabels: Record<RightTab, { label: string; icon: string }> = {
    'deep': { label: '深度分析', icon: '🧠' },
    'position': { label: '局面解析', icon: '🏰' },
    'tags': { label: '战术标签', icon: '🏷️' },
    'moves': { label: '走法记录', icon: '📜' },
  };

  const handleModeChange = (mode: GameMode) => {
    if (mode === 'replay') {
      setGameMode(mode);
    } else {
      if (gameMode === 'replay') {
        useGameStore.getState().exitReplay();
      }
      setGameMode(mode);
    }
  };

  const handleInputModeChange = (mode: InputMode) => {
    setInputMode(mode);
    if (mode === 'camera') {
      alert('拍照识别功能开发中，敬请期待！');
    }
  };

  return (
    <div style={styles.container}>
      {/* 左侧边栏 */}
      <aside style={styles.leftSidebar}>
        {/* Logo区域 */}
        <div style={styles.logoSection}>
          <div style={styles.logo}>🏯</div>
          <div style={styles.logoText}>
            <div style={styles.logoTitle}>象棋AI教练</div>
            <div style={styles.logoSubtitle}>混合代理系统</div>
          </div>
        </div>

        {/* 输入局面 */}
        <div style={styles.section}>
          <div style={styles.sectionTitle}>输入局面</div>
          <div style={styles.inputModeGrid}>
            <button
              onClick={() => handleInputModeChange('online')}
              style={{
                ...styles.inputModeBtn,
                ...(inputMode === 'online' ? styles.inputModeBtnActive : {})
              }}
            >
              <span style={styles.inputModeIcon}>🖥️</span>
              <span style={styles.inputModeLabel}>在线对局</span>
              <span style={styles.inputModeHint}>网页棋盘上走棋</span>
            </button>
            <button
              onClick={() => handleInputModeChange('camera')}
              style={{
                ...styles.inputModeBtn,
                ...(inputMode === 'camera' ? styles.inputModeBtnActive : {})
              }}
            >
              <span style={styles.inputModeIcon}>📷</span>
              <span style={styles.inputModeLabel}>拍照识别</span>
              <span style={styles.inputModeHint}>拍现实棋盘进入</span>
            </button>
          </div>
        </div>

        {/* 对局模式 */}
        <div style={styles.section}>
          <div style={styles.sectionTitle}>对局模式</div>
          <div style={styles.modeGrid}>
            <button
              onClick={() => handleModeChange('analysis')}
              style={{
                ...styles.modeButton,
                ...(gameMode === 'analysis' ? styles.modeButtonActive : {})
              }}
            >
              <span style={styles.modeIcon}>📊</span>
              <span>分析</span>
            </button>
            <button
              onClick={() => handleModeChange('pve_red')}
              style={{
                ...styles.modeButton,
                ...(gameMode === 'pve_red' ? styles.modeButtonActive : {})
              }}
            >
              <span style={styles.modeIcon}>🤖</span>
              <span>人机</span>
            </button>
            <button
              onClick={() => handleModeChange('pvp')}
              style={{
                ...styles.modeButton,
                ...(gameMode === 'pvp' ? styles.modeButtonActive : {})
              }}
            >
              <span style={styles.modeIcon}>👥</span>
              <span>双人</span>
            </button>
          </div>
        </div>

        {/* 学习模式 */}
        <div style={styles.section}>
          <div style={styles.sectionTitle}>学习模式</div>
          <button
            onClick={() => handleModeChange('replay')}
            style={{
              ...styles.modeButton,
              width: '100%',
              ...(gameMode === 'replay' ? styles.modeButtonActive : {})
            }}
          >
            <span style={styles.modeIcon}>📚</span>
            <span>打棋谱</span>
          </button>
        </div>

        {/* 设置选项 */}
        {gameMode !== 'replay' && (
          <div style={styles.section}>
            <div style={styles.sectionTitle}>显示设置</div>
            <div style={styles.settingList}>
              <button
                onClick={toggleFlip}
                style={{
                  ...styles.settingButton,
                  ...(flipped ? styles.settingButtonActive : {})
                }}
              >
                <span>🔄</span>
                <span>翻转棋盘</span>
                <span style={styles.toggleIndicator}>{flipped ? '✓' : ''}</span>
              </button>
              <button
                onClick={toggleShowArrows}
                style={{
                  ...styles.settingButton,
                  ...(showArrows ? styles.settingButtonActive : {})
                }}
              >
                <span>🎯</span>
                <span>显示提示</span>
                <span style={styles.toggleIndicator}>{showArrows ? '✓' : ''}</span>
              </button>
            </div>
          </div>
        )}

        {/* 当前状态 */}
        <div style={styles.section}>
          <div style={styles.sectionTitle}>当前状态</div>
          <div style={styles.statusCard}>
            <div style={styles.statusRow}>
              <span style={styles.statusLabel}>回合</span>
              <span style={{
                ...styles.statusValue,
                background: redToMove ? '#C41E3A' : '#2C3E50',
              }}>
                {redToMove ? '红方' : '黑方'}
              </span>
            </div>
            <div style={styles.statusRow}>
              <span style={styles.statusLabel}>步数</span>
              <span style={styles.statusValuePlain}>{history.length} 步</span>
            </div>
            {gameMode === 'replay' && replayState.selectedGame && (
              <>
                <div style={styles.divider} />
                <div style={styles.replayInfo}>
                  <div style={styles.replayTitle}>
                    {replayState.selectedGame.red} vs {replayState.selectedGame.black}
                  </div>
                  <div style={styles.replayMeta}>
                    {replayState.currentIndex} / {replayState.totalMoves}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>

        {/* 走法记录（简化版） */}
        {history.length > 0 && gameMode !== 'replay' && (
          <div style={styles.section}>
            <div style={styles.sectionTitle}>走法记录</div>
            <div style={styles.moveList}>
              {history.map((move, i) => (
                <span
                  key={i}
                  style={{
                    ...styles.moveItem,
                    background: i % 2 === 0 ? 'rgba(196,30,58,0.15)' : 'rgba(44,62,80,0.1)',
                    color: i % 2 === 0 ? '#C41E3A' : '#2C3E50',
                  }}
                >
                  {Math.floor(i/2) + 1}{i % 2 === 0 ? '.' : '...'} {move}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* 重置按钮 */}
        {gameMode !== 'replay' && (
          <button style={styles.resetButton} onClick={resetGame}>
            🔄 重新开始
          </button>
        )}
      </aside>

      {/* 中央棋盘区域 */}
      <main style={styles.mainContent}>
        <div style={styles.boardWrapper}>
          <ChessBoard />
        </div>
        {gameMode === 'replay' && replayState.selectedGame && (
          <div style={styles.replayNavigator}>
            <ReplayNavigator />
          </div>
        )}
      </main>

      {/* 右侧分析面板 */}
      <aside style={styles.rightSidebar}>
        {/* 标签页头部 */}
        <div style={styles.tabHeader}>
          {(Object.keys(tabLabels) as RightTab[]).map(tab => (
            <button
              key={tab}
              onClick={() => setRightTab(tab)}
              style={{
                ...styles.tabButton,
                ...(rightTab === tab ? styles.tabButtonActive : {})
              }}
              title={tabLabels[tab].label}
            >
              <span style={styles.tabIcon}>{tabLabels[tab].icon}</span>
            </button>
          ))}
        </div>

        {/* 标签页内容 */}
        <div style={styles.tabContent}>
          {rightTab === 'deep' && <DeepAnalysisPanel />}
          {rightTab === 'position' && <PositionAnalysisPanel />}
          {rightTab === 'tags' && <TacticalTagsPanel />}
          {rightTab === 'moves' && gameMode === 'replay' && <ReplayPanel />}
          {rightTab === 'moves' && gameMode !== 'replay' && (
            <div style={styles.emptyState}>
              <div style={styles.emptyIcon}>📜</div>
              <div>走法记录显示在左侧边栏</div>
              <div style={styles.emptyHint}>打棋谱模式下可在此查看棋谱</div>
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}

// 样式定义
const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    minHeight: '100vh',
    background: 'linear-gradient(180deg, #FFF8F0 0%, #F5EDE4 50%, #EDE4D8 100%)',
    color: '#4A4A4A',
    position: 'relative',
    overflow: 'hidden',
  },

  // 左侧边栏 - 浅米色 + 水墨晕染
  leftSidebar: {
    width: 240,
    background: 'linear-gradient(180deg, #FAF6F1 0%, #F5EDE4 100%)',
    borderRight: '1px solid rgba(212,175,55,0.3)',
    padding: 16,
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
    overflowY: 'auto',
  },

  // Logo区域
  logoSection: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '12px 0',
    borderBottom: '1px solid rgba(212,175,55,0.3)',
    marginBottom: 8,
  },
  logo: {
    fontSize: 32,
    filter: 'drop-shadow(0 0 8px rgba(212,175,55,0.6))',
  },
  logoText: {
    display: 'flex',
    flexDirection: 'column',
  },
  logoTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#C9934A',
  },
  logoSubtitle: {
    fontSize: 11,
    color: '#8B7355',
  },

  // 通用section
  section: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  sectionTitle: {
    fontSize: 11,
    color: '#8B7355',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 4,
  },

  // 模式选择
  modeGrid: {
    display: 'flex',
    gap: 4,
  },
  modeButton: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 4,
    padding: '10px 8px',
    background: 'rgba(255,255,255,0.5)',
    border: '1px solid rgba(212,175,55,0.2)',
    borderRadius: 8,
    color: '#6B5344',
    cursor: 'pointer',
    fontSize: 12,
    transition: 'all 0.2s',
  },
  modeButtonActive: {
    background: 'linear-gradient(135deg, rgba(212,175,55,0.3), rgba(201,147,74,0.2))',
    border: '1px solid rgba(201,147,74,0.5)',
    color: '#8B4513',
  },
  modeIcon: {
    fontSize: 18,
  },

  // 输入模式
  inputModeGrid: {
    display: 'flex',
    gap: 8,
  },
  inputModeBtn: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 4,
    padding: '12px 8px',
    background: 'rgba(255,255,255,0.6)',
    border: '1px solid rgba(212,175,55,0.2)',
    borderRadius: 10,
    color: '#8B7355',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  inputModeBtnActive: {
    background: 'linear-gradient(135deg, rgba(212,175,55,0.25), rgba(201,147,74,0.15))',
    border: '1px solid rgba(201,147,74,0.5)',
    color: '#8B4513',
  },
  inputModeIcon: {
    fontSize: 24,
  },
  inputModeLabel: {
    fontSize: 12,
    fontWeight: 'bold',
  },
  inputModeHint: {
    fontSize: 10,
    opacity: 0.7,
  },

  // 设置按钮
  settingList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  settingButton: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '8px 12px',
    background: 'rgba(255,255,255,0.5)',
    border: '1px solid rgba(212,175,55,0.2)',
    borderRadius: 6,
    color: '#6B5344',
    cursor: 'pointer',
    fontSize: 12,
    transition: 'all 0.2s',
  },
  settingButtonActive: {
    background: 'rgba(212,175,55,0.2)',
    border: '1px solid rgba(201,147,74,0.4)',
    color: '#8B4513',
  },
  toggleIndicator: {
    marginLeft: 'auto',
    fontWeight: 'bold',
  },

  // 状态卡片
  statusCard: {
    background: 'rgba(255,255,255,0.6)',
    borderRadius: 8,
    padding: 12,
    border: '1px solid rgba(212,175,55,0.15)',
  },
  statusRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  statusLabel: {
    fontSize: 12,
    color: '#8B7355',
  },
  statusValue: {
    padding: '2px 10px',
    borderRadius: 4,
    fontSize: 12,
    fontWeight: 'bold',
    color: '#fff',
  },
  statusValuePlain: {
    fontSize: 12,
    color: '#6B5344',
  },
  divider: {
    height: 1,
    background: 'rgba(212,175,55,0.2)',
    margin: '8px 0',
  },
  replayInfo: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  replayTitle: {
    fontSize: 11,
    color: '#2d3748',
  },
  replayMeta: {
    fontSize: 10,
    color: '#4a5568',
  },

  // 走法记录
  moveList: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 4,
    maxHeight: 200,
    overflowY: 'auto',
    padding: 4,
    background: 'rgba(212,175,55,0.08)',
    borderRadius: 6,
    border: '1px solid rgba(212,175,55,0.15)',
  },
  moveItem: {
    padding: '3px 6px',
    borderRadius: 3,
    fontSize: 11,
    fontFamily: 'monospace',
  },

  // 重置按钮 - 暖橙色
  resetButton: {
    marginTop: 'auto',
    padding: '12px 16px',
    background: 'linear-gradient(135deg, #E8944A, #C9753A)',
    border: 'none',
    borderRadius: 8,
    color: '#fff',
    fontSize: 13,
    fontWeight: 'bold',
    cursor: 'pointer',
    transition: 'all 0.2s',
    boxShadow: '0 4px 12px rgba(201,117,58,0.3)',
  },

  // 中央内容区
  mainContent: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    gap: 16,
  },
  boardWrapper: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  replayNavigator: {
    width: '100%',
    maxWidth: 800,
  },

  // 右侧边栏 - 浅米色 + 水墨晕染
  rightSidebar: {
    width: 380,
    background: 'linear-gradient(180deg, #FAF6F1 0%, #F5EDE4 100%)',
    borderLeft: '1px solid rgba(212,175,55,0.3)',
    display: 'flex',
    flexDirection: 'column',
    position: 'relative',
    boxShadow: 'inset 20px 0 40px -20px rgba(139,105,20,0.08), -4px 0 20px rgba(0,0,0,0.05)',
  },

  // 标签页
  tabHeader: {
    display: 'flex',
    background: 'rgba(212,175,55,0.08)',
    borderBottom: '1px solid rgba(212,175,55,0.2)',
  },
  tabButton: {
    flex: 1,
    padding: '14px 8px',
    background: 'transparent',
    border: 'none',
    borderRight: '1px solid rgba(212,175,55,0.1)',
    color: '#8B7355',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  tabButtonActive: {
    background: 'rgba(212,175,55,0.15)',
    color: '#C9934A',
    borderBottom: '2px solid #C9934A',
  },
  tabIcon: {
    fontSize: 18,
  },
  tabContent: {
    flex: 1,
    overflow: 'auto',
    padding: 16,
  },

  // 空状态
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 40,
    color: '#8B7355',
    textAlign: 'center',
    gap: 8,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 8,
    opacity: 0.5,
  },
  emptyHint: {
    fontSize: 11,
    color: '#A89080',
    marginTop: 4,
  },
};
