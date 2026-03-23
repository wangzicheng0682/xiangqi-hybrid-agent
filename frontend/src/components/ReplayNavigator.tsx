import React, { useState, useEffect } from 'react';
import { useGameStore } from '../store/useGameStore';

interface MoveQuality {
  score_change: number;
  quality: 'excellent' | 'good' | 'normal' | 'bad';
}

const getMoveQuality = (scoreChange: number): MoveQuality => {
  if (scoreChange >= 1.5) return { score_change: scoreChange, quality: 'excellent' };
  if (scoreChange >= 0.5) return { score_change: scoreChange, quality: 'good' };
  if (scoreChange >= -0.5) return { score_change: scoreChange, quality: 'normal' };
  return { score_change: scoreChange, quality: 'bad' };
};

const QUALITY_STYLES: Record<string, { icon: string; color: string; label: string }> = {
  excellent: { icon: '↗优', color: '#22C55E', label: '优秀' },
  good: { icon: '→良', color: '#4CAF50', label: '良好' },
  normal: { icon: '→中', color: '#4a5568', label: '一般' },
  bad: { icon: '↘差', color: '#EF4444', label: '失误' },
};

const AUTO_COMMENTARY: Record<string, string> = {
  '炮二平五': '当头炮开局，占据中路，是象棋中最常见的开局方式',
  '马二进三': '跳马护中，同时准备出车，是屏风马的标准应对',
  '车一平二': '出车占位，控制要道，是开局的重要一步',
  '兵七进一': '挺兵活马，为后续进攻做准备',
  '马八进七': '跳正马，增强中路防守',
  '炮八平五': '架中炮，形成双炮联攻',
  '车九平八': '出直车，控制边路',
  '卒7进1': '挺卒制马，是防守反击的常见手段',
};

const DEFAULT_COMMENTARY = '这步棋调整了子力位置，为后续战术做准备';

export default function ReplayNavigator() {
  const { replayState, navigateReplay } = useGameStore();
  const { currentIndex, totalMoves, moves, selectedGame } = replayState;
  const [autoComment, setAutoComment] = useState(true);
  const [currentCommentary, setCurrentCommentary] = useState<string>('');

  if (!selectedGame) return null;

  const currentMove = currentIndex > 0 && currentIndex <= moves.length
    ? moves[currentIndex - 1]
    : null;

  const progress = totalMoves > 0 ? (currentIndex / totalMoves) * 100 : 0;

  useEffect(() => {
    if (autoComment && currentMove) {
      const commentary = AUTO_COMMENTARY[currentMove] || DEFAULT_COMMENTARY;
      setCurrentCommentary(commentary);
    } else {
      setCurrentCommentary('');
    }
  }, [currentIndex, autoComment, currentMove]);

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10);
    navigateReplay('goto', value);
  };

  const getMoveQualityStyle = () => {
    const mockScore = (Math.random() - 0.5) * 3;
    const quality = getMoveQuality(mockScore);
    return QUALITY_STYLES[quality.quality];
  };

  return (
    <div style={styles.container}>
      {/* 导航按钮 */}
      <div style={styles.navButtons}>
        <button
          className="liquid-glass-btn"
          onClick={() => navigateReplay('start')}
          disabled={currentIndex === 0}
          style={{
            width: 38, height: 38,
            borderRadius: '50%',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          ⏮
        </button>
        <button
          className="liquid-glass-btn primary"
          onClick={() => navigateReplay('prev')}
          disabled={currentIndex === 0}
          style={{
            width: 44, height: 44,
            borderRadius: '50%',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          ◀
        </button>
        <button
          className="liquid-glass-btn primary"
          onClick={() => navigateReplay('next')}
          disabled={currentIndex >= totalMoves}
          style={{
            width: 44, height: 44,
            borderRadius: '50%',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          ▶
        </button>
        <button
          className="liquid-glass-btn"
          onClick={() => navigateReplay('end')}
          disabled={currentIndex >= totalMoves}
          style={{
            width: 38, height: 38,
            borderRadius: '50%',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          ⏭
        </button>
      </div>

      {/* 进度条 */}
      <div style={styles.sliderWrapper}>
        <div style={styles.sliderTrack}>
          <div style={{ ...styles.sliderFill, width: `${progress}%` }} />
        </div>
        <input
          type="range"
          min={0}
          max={totalMoves}
          value={currentIndex}
          onChange={handleSliderChange}
          style={styles.slider}
        />
      </div>

      {/* 状态信息 */}
      <div style={styles.statusRow}>
        <span style={styles.stepInfo}>
          第 <strong style={styles.stepCurrent}>{currentIndex}</strong> / {totalMoves} 步
        </span>
        <span style={{
          ...styles.turnBadge,
          background: currentIndex % 2 === 0 ? '#C41E3A' : '#2C3E50',
        }}>
          {currentIndex % 2 === 0 ? '红方' : '黑方'}
        </span>
      </div>

      {/* 当前走法 */}
      {currentMove && (
        <div style={styles.currentMoveCard}>
          <div style={styles.currentMoveLabel}>当前走法</div>
          <div style={styles.currentMoveText}>{currentMove}</div>
          {currentCommentary && (
            <div style={styles.commentaryBox}>
              <span style={styles.commentaryIcon}>💡</span>
              <span style={styles.commentaryText}>{currentCommentary}</span>
            </div>
          )}
        </div>
      )}

      {/* 自动讲解开关 */}
      <div style={styles.autoCommentToggle}>
        <span style={styles.autoCommentLabel}>自动讲解</span>
        <button
          className={`liquid-glass-btn sm${autoComment ? ' primary' : ''}`}
          onClick={() => setAutoComment(!autoComment)}
        >
          {autoComment ? '开 ●' : '关 ○'}
        </button>
      </div>

      {/* 初始状态提示 */}
      {currentIndex === 0 && (
        <div style={styles.initialState}>
          初始局面 - 点击 ▶ 开始浏览
        </div>
      )}

      {/* 走法列表 */}
      <div style={styles.movesList}>
        {moves.map((move, i) => {
          const qualityStyle = getMoveQualityStyle();
          const isActive = i + 1 === currentIndex;
          
          return (
            <span
              key={i}
              onClick={() => navigateReplay('goto', i + 1)}
              style={{
                ...styles.moveTag,
                ...(isActive ? styles.moveTagActive : {}),
                background: isActive
                  ? '#D4AF37'
                  : i % 2 === 0
                    ? 'rgba(196,30,58,0.2)'
                    : 'rgba(44,62,80,0.2)',
                color: isActive
                  ? '#1a1a2e'
                  : i % 2 === 0
                    ? '#C41E3A'
                    : '#888',
              }}
            >
              {Math.floor(i / 2) + 1}{i % 2 === 0 ? '.' : '...'} {move}
              <span style={{
                ...styles.qualityTag,
                color: qualityStyle.color,
              }}>
                {qualityStyle.icon}
              </span>
            </span>
          );
        })}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: 14,
  },

  // 导航按钮
  navButtons: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  navButton: {
    width: 38,
    height: 38,
    borderRadius: '50%',
    border: 'none',
    background: 'rgba(0,0,0,0.06)',
    color: 'var(--apple-text-secondary)',
    cursor: 'pointer',
    fontSize: 14,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.18s cubic-bezier(0.16, 1, 0.3, 1)',
    backdropFilter: 'blur(8px)',
  },
  navButtonMain: {
    width: 44,
    height: 44,
    background: 'rgba(212,175,55,0.75)',
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  navButtonDisabled: {
    opacity: 0.35,
    cursor: 'not-allowed',
  },

  // 滑块
  sliderWrapper: {
    position: 'relative',
    height: 8,
  },
  sliderTrack: {
    position: 'absolute',
    width: '100%',
    height: 4,
    top: '50%',
    transform: 'translateY(-50%)',
    background: 'rgba(0,0,0,0.08)',
    borderRadius: 2,
  },
  sliderFill: {
    height: '100%',
    background: 'rgba(212,175,55,0.75)',
    borderRadius: 2,
    transition: 'width 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
  },
  slider: {
    position: 'absolute',
    width: '100%',
    height: '100%',
    top: 0,
    left: 0,
    opacity: 0,
    cursor: 'pointer',
  },

  // 状态行
  statusRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  stepInfo: {
    fontSize: 12,
    color: 'var(--apple-text-secondary)',
  },
  stepCurrent: {
    color: 'rgba(212,175,55,0.85)',
    fontSize: 16,
    fontWeight: '600',
  },
  turnBadge: {
    padding: '4px 12px',
    borderRadius: 'var(--radius-full)',
    fontSize: 11,
    fontWeight: '600',
    color: '#fff',
  },

  // 当前走法卡片
  currentMoveCard: {
    padding: '12px 16px',
    background: 'rgba(212,175,55,0.08)',
    backdropFilter: 'blur(8px)',
    borderRadius: 'var(--radius-md)',
    border: '1px solid rgba(212,175,55,0.2)',
    borderTopColor: 'rgba(212,175,55,0.35)',
  },
  currentMoveLabel: {
    fontSize: 10,
    color: 'var(--apple-text-tertiary)',
    marginBottom: 6,
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
  },
  currentMoveText: {
    fontSize: 18,
    fontWeight: '600',
    color: 'var(--apple-text)',
    fontFamily: 'SF Mono, JetBrains Mono, Consolas, monospace',
  },

  // 初始状态
  initialState: {
    padding: '12px 16px',
    background: 'rgba(0,0,0,0.03)',
    borderRadius: 'var(--radius-md)',
    textAlign: 'center',
    color: 'var(--apple-text-secondary)',
    fontSize: 12,
  },

  // 走法列表
  movesList: {
    maxHeight: 140,
    overflowY: 'auto',
    padding: 8,
    background: 'rgba(0,0,0,0.03)',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    flexWrap: 'wrap',
    gap: 4,
  },
  moveTag: {
    padding: '4px 8px',
    borderRadius: 'var(--radius-xs)',
    fontSize: 11,
    fontFamily: 'SF Mono, JetBrains Mono, Consolas, monospace',
    cursor: 'pointer',
    transition: 'all 0.15s cubic-bezier(0.16, 1, 0.3, 1)',
    display: 'inline-flex',
    alignItems: 'center',
    gap: 4,
  },
  moveTagActive: {
    fontWeight: '600',
    boxShadow: '0 2px 8px rgba(212,175,55,0.2)',
  },
  qualityTag: {
    fontSize: 9,
    fontWeight: '600',
    marginLeft: 2,
  },

  // 自动讲解
  autoCommentToggle: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '8px 12px',
    background: 'rgba(0,0,0,0.03)',
    borderRadius: 'var(--radius-md)',
  },
  autoCommentLabel: {
    fontSize: 12,
    color: 'var(--apple-text-secondary)',
  },
  toggleBtn: {
    padding: '4px 12px',
    borderRadius: 'var(--radius-sm)',
    border: '1px solid rgba(0,0,0,0.08)',
    background: 'rgba(0,0,0,0.04)',
    color: 'var(--apple-text-secondary)',
    fontSize: 11,
    cursor: 'pointer',
    transition: 'all 0.18s cubic-bezier(0.16, 1, 0.3, 1)',
  },
  toggleBtnActive: {
    background: 'rgba(34,197,94,0.1)',
    borderColor: 'rgba(34,197,94,0.25)',
    color: 'rgba(22,101,52,0.85)',
  },

  // 讲解框
  commentaryBox: {
    marginTop: 10,
    padding: '10px 12px',
    background: 'rgba(0,0,0,0.04)',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    alignItems: 'flex-start',
    gap: 8,
  },
  commentaryIcon: {
    fontSize: 14,
  },
  commentaryText: {
    fontSize: 12,
    lineHeight: 1.6,
    color: 'var(--apple-text)',
    flex: 1,
  },
};
