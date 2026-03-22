import React, { useState } from 'react';
import { useGameStore } from '../store/useGameStore';

type TabType = 'database' | 'pgn';

export default function ReplayPanel() {
  const [tab, setTab] = useState<TabType>('database');
  const [searchText, setSearchText] = useState('');
  const [pgnText, setPgnText] = useState('');

  const {
    replayState,
    searchGames,
    loadGameFromNeo4j,
    loadGameFromPGN,
    setGameMode
  } = useGameStore();

  const { games, isLoadingGames, selectedGame } = replayState;

  const handleSearch = () => {
    if (searchText.trim()) {
      searchGames(searchText.trim());
    }
  };

  const handleSelectGame = (gameId: number) => {
    loadGameFromNeo4j(gameId);
  };

  const handleLoadPGN = () => {
    if (pgnText.trim()) {
      loadGameFromPGN(pgnText.trim());
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        const content = event.target?.result as string;
        setPgnText(content);
      };
      reader.readAsText(file);
    }
  };

  return (
    <div style={styles.container}>
      {/* 标签切换 */}
      <div style={styles.tabBar}>
        <button
          onClick={() => setTab('database')}
          style={{ ...styles.tab, ...(tab === 'database' ? styles.tabActive : {}) }}
        >
          📚 数据库
        </button>
        <button
          onClick={() => setTab('pgn')}
          style={{ ...styles.tab, ...(tab === 'pgn' ? styles.tabActive : {}) }}
        >
          📄 导入PGN
        </button>
      </div>

      {/* 数据库搜索 */}
      {tab === 'database' && (
        <div style={styles.section}>
          <div style={styles.searchRow}>
            <input
              type="text"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="搜索棋手名或赛事..."
              style={styles.searchInput}
            />
            <button
              onClick={handleSearch}
              disabled={isLoadingGames}
              style={styles.searchButton}
            >
              {isLoadingGames ? '...' : '搜索'}
            </button>
          </div>

          <div style={styles.gamesList}>
            {games.length > 0 ? (
              games.map((game) => (
                <div
                  key={game.game_id}
                  onClick={() => handleSelectGame(game.game_id)}
                  style={{
                    ...styles.gameItem,
                    ...(selectedGame?.game_id === game.game_id ? styles.gameItemActive : {})
                  }}
                >
                  <div style={styles.gameTitle}>
                    🔴 {game.red} <span style={styles.vs}>vs</span> ⚫ {game.black}
                  </div>
                  <div style={styles.gameMeta}>
                    <span>{game.event || '未知赛事'}</span>
                    <span>{game.date || ''}</span>
                  </div>
                  <div style={{
                    ...styles.gameResult,
                    color: game.result === '1-0' ? '#22C55E' : game.result === '0-1' ? '#EF4444' : '#888'
                  }}>
                    {game.result === '1-0' ? '红胜' : game.result === '0-1' ? '黑胜' : game.result === '1/2-1/2' ? '和棋' : game.result}
                  </div>
                </div>
              ))
            ) : (
              <div style={styles.emptyState}>
                <div style={styles.emptyIcon}>🔍</div>
                <div>搜索棋手或赛事</div>
                <div style={styles.emptyHint}>如: 许银川、吕钦、碧桂园杯</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* PGN导入 */}
      {tab === 'pgn' && (
        <div style={styles.section}>
          <label style={styles.fileUpload}>
            <input
              type="file"
              accept=".pgn,.pgns,.txt"
              onChange={handleFileUpload}
              style={{ display: 'none' }}
            />
            📁 点击选择PGN文件
          </label>

          <textarea
            value={pgnText}
            onChange={(e) => setPgnText(e.target.value)}
            placeholder="或粘贴PGN内容..."
            style={styles.pgnTextarea}
          />

          <button
            onClick={handleLoadPGN}
            disabled={!pgnText.trim()}
            style={{
              ...styles.loadButton,
              ...(pgnText.trim() ? {} : styles.loadButtonDisabled)
            }}
          >
            加载棋谱
          </button>
        </div>
      )}

      {/* 当前对局信息 */}
      {selectedGame && (
        <div style={styles.currentGame}>
          <h4 style={styles.currentGameTitle}>📋 当前对局</h4>
          <div style={styles.gameInfo}>
            <div style={styles.gameInfoRow}>
              <span style={styles.gameInfoLabel}>红方</span>
              <span style={styles.gameInfoValue}>{selectedGame.red}</span>
            </div>
            <div style={styles.gameInfoRow}>
              <span style={styles.gameInfoLabel}>黑方</span>
              <span style={styles.gameInfoValue}>{selectedGame.black}</span>
            </div>
            <div style={styles.gameInfoRow}>
              <span style={styles.gameInfoLabel}>赛事</span>
              <span style={styles.gameInfoValue}>{selectedGame.event || '未知'}</span>
            </div>
            <div style={styles.gameInfoRow}>
              <span style={styles.gameInfoLabel}>日期</span>
              <span style={styles.gameInfoValue}>{selectedGame.date || '未知'}</span>
            </div>
            <div style={styles.gameInfoRow}>
              <span style={styles.gameInfoLabel}>结果</span>
              <span style={{
                ...styles.gameInfoValue,
                color: selectedGame.result === '1-0' ? '#22C55E' : selectedGame.result === '0-1' ? '#EF4444' : '#888'
              }}>
                {selectedGame.result === '1-0' ? '红胜' : selectedGame.result === '0-1' ? '黑胜' : selectedGame.result === '1/2-1/2' ? '和棋' : selectedGame.result}
              </span>
            </div>
            <div style={styles.gameInfoRow}>
              <span style={styles.gameInfoLabel}>步数</span>
              <span style={styles.gameInfoValue}>{replayState.totalMoves} 步</span>
            </div>
          </div>
          <button
            onClick={() => {
              useGameStore.getState().exitReplay();
              setGameMode('analysis');
            }}
            style={styles.exitButton}
          >
            退出棋谱模式
          </button>
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },

  // 标签栏
  tabBar: {
    display: 'flex',
    gap: 4,
    background: 'rgba(0,0,0,0.2)',
    borderRadius: 6,
    padding: 3,
  },
  tab: {
    flex: 1,
    padding: '10px 12px',
    background: 'transparent',
    border: 'none',
    borderRadius: 4,
    color: '#666',
    fontSize: 12,
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  tabActive: {
    background: 'rgba(196,30,58,0.3)',
    color: '#C41E3A',
  },

  // 区块
  section: {
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
  },

  // 搜索行
  searchRow: {
    display: 'flex',
    gap: 8,
  },
  searchInput: {
    flex: 1,
    padding: '10px 12px',
    borderRadius: 6,
    border: '1px solid rgba(255,255,255,0.1)',
    background: 'rgba(255,255,255,0.05)',
    color: '#fff',
    fontSize: 13,
    outline: 'none',
  },
  searchButton: {
    padding: '10px 16px',
    borderRadius: 6,
    border: 'none',
    background: '#D4AF37',
    color: '#1a1a2e',
    fontWeight: 'bold',
    cursor: 'pointer',
    fontSize: 13,
  },

  // 游戏列表
  gamesList: {
    maxHeight: 280,
    overflowY: 'auto',
    borderRadius: 6,
    border: '1px solid rgba(255,255,255,0.08)',
    background: 'rgba(0,0,0,0.2)',
  },
  gameItem: {
    padding: '12px 14px',
    borderBottom: '1px solid rgba(255,255,255,0.05)',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  gameItemActive: {
    background: 'rgba(196,30,58,0.2)',
    borderLeft: '3px solid #C41E3A',
  },
  gameTitle: {
    fontWeight: 'bold',
    fontSize: 13,
    marginBottom: 6,
    color: '#fff',
  },
  vs: {
    color: '#666',
    fontWeight: 'normal',
    margin: '0 4px',
  },
  gameMeta: {
    fontSize: 11,
    color: '#666',
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  gameResult: {
    fontSize: 11,
    fontWeight: 'bold',
  },

  // 空状态
  emptyState: {
    padding: 40,
    textAlign: 'center',
    color: '#555',
  },
  emptyIcon: {
    fontSize: 36,
    marginBottom: 12,
    opacity: 0.5,
  },
  emptyHint: {
    fontSize: 11,
    marginTop: 6,
    color: '#444',
  },

  // 文件上传
  fileUpload: {
    display: 'block',
    padding: '14px',
    border: '2px dashed rgba(255,255,255,0.15)',
    borderRadius: 6,
    textAlign: 'center',
    cursor: 'pointer',
    fontSize: 12,
    color: '#888',
    transition: 'all 0.2s',
  },

  // PGN文本框
  pgnTextarea: {
    width: '100%',
    height: 140,
    padding: 10,
    borderRadius: 6,
    border: '1px solid rgba(255,255,255,0.1)',
    background: 'rgba(0,0,0,0.2)',
    color: '#ccc',
    fontSize: 11,
    fontFamily: 'monospace',
    resize: 'vertical',
    outline: 'none',
  },

  // 加载按钮
  loadButton: {
    width: '100%',
    padding: '12px',
    borderRadius: 6,
    border: 'none',
    background: '#D4AF37',
    color: '#1a1a2e',
    fontWeight: 'bold',
    cursor: 'pointer',
    fontSize: 13,
  },
  loadButtonDisabled: {
    background: '#444',
    color: '#666',
    cursor: 'not-allowed',
  },

  // 当前对局
  currentGame: {
    padding: 14,
    background: 'rgba(255,255,255,0.03)',
    borderRadius: 8,
    border: '1px solid rgba(255,255,255,0.08)',
  },
  currentGameTitle: {
    color: '#D4AF37',
    fontSize: 13,
    margin: '0 0 12px 0',
    paddingBottom: 8,
    borderBottom: '1px solid rgba(212,175,55,0.3)',
  },
  gameInfo: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
  },
  gameInfoRow: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: 12,
  },
  gameInfoLabel: {
    color: '#666',
  },
  gameInfoValue: {
    color: '#ccc',
  },
  exitButton: {
    width: '100%',
    marginTop: 14,
    padding: '10px',
    borderRadius: 6,
    border: '1px solid #C41E3A',
    background: 'transparent',
    color: '#C41E3A',
    cursor: 'pointer',
    fontSize: 12,
    transition: 'all 0.2s',
  },
};
