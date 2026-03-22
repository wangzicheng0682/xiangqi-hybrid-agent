import { useState, useEffect, useRef } from 'react';

export interface ConsensusItem {
  expert: string;
  point: string;
}

export interface DivergenceItem {
  expert1: string;
  expert2: string;
  point: string;
}

export interface SynthesisPanelProps {
  isActive: boolean;
  synthesisContent: string;
  consensusItems: ConsensusItem[];
  divergenceItems: DivergenceItem[];
  onComplete?: () => void;
}

// ============================================
// 流式文字（带打字机效果）
// ============================================

const StreamText: React.FC<{ text: string; speed?: number; onComplete?: () => void }> = ({
  text,
  speed = 20,
  onComplete,
}) => {
  const [displayed, setDisplayed] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setDisplayed('');
    setCurrentIndex(0);
  }, [text]);

  useEffect(() => {
    if (currentIndex >= text.length) {
      onComplete?.();
      return;
    }

    const timer = setTimeout(() => {
      setDisplayed(text.slice(0, currentIndex + 1));
      setCurrentIndex(prev => prev + 1);

      if (containerRef.current) {
        containerRef.current.scrollTop = containerRef.current.scrollHeight;
      }
    }, speed);

    return () => clearTimeout(timer);
  }, [text, currentIndex, speed, onComplete]);

  // 智能高亮
  const highlightText = (t: string) => {
    const result = t
      .replace(/\*\*([^*]+)\*\*/g, '§BOLD§$1§/BOLD§')
      .replace(/\[([^\]]+)\]/g, '§TOOL§[$1]§/TOOL§')
      .replace(/\(([^)]+)\)/g, '§COORD§($1)§/COORD§');

    const segments = result.split('§');
    return segments.map((seg, i) => {
      if (seg === 'BOLD' || seg === '/BOLD') return null;
      if (seg === 'TOOL' || seg === '/TOOL') return null;
      if (seg === 'COORD' || seg === '/COORD') return null;
      if (seg.startsWith('BOLD§')) {
        return <strong key={i} style={{ color: '#f5f5f5', fontWeight: 700 }}>{seg.replace('BOLD§', '')}</strong>;
      }
      if (seg.startsWith('TOOL§[')) {
        return <span key={i} style={{ color: '#60a5fa', fontFamily: 'monospace', fontSize: '0.9em', background: 'rgba(96,165,250,0.1)', padding: '0 3px', borderRadius: 3 }}>[{seg.replace('TOOL§[', '')}]</span>;
      }
      if (seg.startsWith('COORD§(')) {
        return <span key={i} style={{ color: '#a78bfa', fontFamily: 'monospace' }}>{seg.replace('COORD§', '')}</span>;
      }
      return <span key={i}>{seg}</span>;
    });
  };

  return (
    <div ref={containerRef} style={styles.streamContainer}>
      <span style={styles.cursor}>|</span>
      {highlightText(displayed)}
    </div>
  );
};

// ============================================
// 主组件：SynthesisPanel
// ============================================

export const SynthesisPanel: React.FC<SynthesisPanelProps> = ({
  isActive,
  synthesisContent,
  consensusItems,
  divergenceItems,
}) => {
  const isStreaming = isActive && synthesisContent.length > 0;
  const hasContent = synthesisContent.length > 0;

  return (
    <div
      style={{
        ...styles.container,
        ...(isActive
          ? {
              borderColor: 'rgba(244, 114, 182, 0.5)',
              background: 'linear-gradient(135deg, rgba(244, 114, 182, 0.08), rgba(168, 85, 247, 0.06))',
              boxShadow: '0 0 24px rgba(244, 114, 182, 0.2), 0 4px 12px rgba(0,0,0,0.3)',
            }
          : {}),
      }}
    >
      {/* 头部 */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <span style={styles.icon}>🎯</span>
          <div>
            <div style={styles.title}>综合裁判</div>
            <div style={styles.subtitle}>整合三位专家观点 · 生成最终讲解</div>
          </div>
        </div>
        <span style={{
          ...styles.statusTag,
          background: isStreaming
            ? 'rgba(244, 114, 182, 0.2)'
            : hasContent
            ? 'rgba(34, 197, 94, 0.2)'
            : 'rgba(255,255,255,0.05)',
          color: isStreaming
            ? '#f472b6'
            : hasContent
            ? '#22c55e'
            : '#888',
        }}>
          {isStreaming ? '⚡ 综合中...' : hasContent ? '✅ 完成' : '待命'}
        </span>
      </div>

      {/* 共识区 */}
      {consensusItems.length > 0 && (
        <div style={styles.section}>
          <div style={styles.sectionLabel}>
            <span>✅</span> 共识
          </div>
          <div style={styles.consensusList}>
            {consensusItems.map((item, i) => (
              <div key={i} style={styles.consensusItem}>
                <span style={styles.consensusExpert}>{item.expert}</span>
                <span style={styles.consensusText}>{item.point}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 分歧区 */}
      {divergenceItems.length > 0 && (
        <div style={styles.section}>
          <div style={styles.sectionLabel}>
            <span>🤔</span> 分歧
          </div>
          <div style={styles.divergenceList}>
            {divergenceItems.map((item, i) => (
              <div key={i} style={styles.divergenceItem}>
                <span style={styles.divergenceLabel}>
                  {item.expert1} ↔ {item.expert2}
                </span>
                <span style={styles.divergenceText}>{item.point}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 流式输出区 */}
      <div style={styles.outputSection}>
        <div style={styles.outputLabel}>
          <span>📖</span> 最终讲解
        </div>
        <div style={styles.outputBox}>
          {synthesisContent ? (
            <StreamText
              text={synthesisContent}
              speed={isStreaming ? 18 : 0}
            />
          ) : (
            <div style={styles.outputPlaceholder}>
              {isActive ? '正在整合专家观点...' : '三位专家分析完成后，将在此生成综合讲解'}
            </div>
          )}
        </div>
      </div>

      {/* 底部装饰 */}
      {isStreaming && (
        <div style={styles.bottomIndicator}>
          <span style={styles.indicatorDot} />
          综合裁判正在整合三位专家的分析结论
        </div>
      )}
    </div>
  );
};

// ============================================
// Styles
// ============================================

const styles: Record<string, React.CSSProperties> = {
  container: {
    borderRadius: 12,
    border: '1px solid rgba(244, 114, 182, 0.3)',
    padding: 14,
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
    transition: 'all 0.4s ease',
    background: 'rgba(244, 114, 182, 0.04)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  icon: {
    fontSize: 22,
  },
  title: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#f5f5f5',
    fontFamily: '"Noto Serif SC", serif',
  },
  subtitle: {
    fontSize: 10,
    color: '#888',
  },
  statusTag: {
    padding: '3px 10px',
    borderRadius: 10,
    fontSize: 10,
    fontWeight: 600,
  },
  section: {
    borderTop: '1px solid rgba(255,255,255,0.06)',
    paddingTop: 8,
  },
  sectionLabel: {
    fontSize: 10,
    color: '#888',
    marginBottom: 6,
    display: 'flex',
    alignItems: 'center',
    gap: 4,
  },
  consensusList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  consensusItem: {
    display: 'flex',
    gap: 6,
    fontSize: 11,
    padding: '4px 8px',
    background: 'rgba(34, 197, 94, 0.08)',
    borderRadius: 4,
    border: '1px solid rgba(34, 197, 94, 0.15)',
  },
  consensusExpert: {
    color: '#22c55e',
    fontWeight: 600,
    flexShrink: 0,
  },
  consensusText: {
    color: '#ccc',
  },
  divergenceList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  divergenceItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
    fontSize: 11,
    padding: '4px 8px',
    background: 'rgba(245, 158, 11, 0.08)',
    borderRadius: 4,
    border: '1px solid rgba(245, 158, 11, 0.15)',
  },
  divergenceLabel: {
    color: '#f59e0b',
    fontWeight: 600,
    fontSize: 10,
  },
  divergenceText: {
    color: '#ccc',
  },
  outputSection: {
    borderTop: '1px solid rgba(255,255,255,0.06)',
    paddingTop: 8,
  },
  outputLabel: {
    fontSize: 10,
    color: '#888',
    marginBottom: 6,
    display: 'flex',
    alignItems: 'center',
    gap: 4,
  },
  outputBox: {
    background: 'rgba(0,0,0,0.2)',
    borderRadius: 8,
    padding: '10px 12px',
    minHeight: 60,
    maxHeight: 200,
    overflow: 'auto',
    border: '1px solid rgba(255,255,255,0.04)',
  },
  outputPlaceholder: {
    color: '#555',
    fontSize: 11,
    fontStyle: 'italic',
    textAlign: 'center',
    padding: '10px 0',
  },
  streamContainer: {
    fontSize: 12,
    lineHeight: 1.8,
    color: '#e8e8e8',
    fontFamily: '"Noto Serif SC", serif',
    position: 'relative',
    wordBreak: 'break-word',
  },
  cursor: {
    color: '#f472b6',
    fontWeight: 'bold',
    marginRight: 1,
    animation: 'blink 1s step-end infinite',
  },
  bottomIndicator: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    fontSize: 10,
    color: '#888',
    paddingTop: 4,
  },
  indicatorDot: {
    width: 6,
    height: 6,
    borderRadius: '50%',
    background: '#f472b6',
    animation: 'pulse 1.5s infinite',
    flexShrink: 0,
  },
};

export default SynthesisPanel;
