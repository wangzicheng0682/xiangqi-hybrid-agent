import { useState, useEffect } from 'react';
import { flushSync } from 'react-dom';
import { useGameStore } from '../store/useGameStore';
import { api } from '../services/api';

interface ThinkingMessage {
  type: string;
  stage?: number;
  message?: string;
  tool?: string;
  finding?: string;
}

// ============================================
// 时间轴子组件
// ============================================

interface TimelineNodeProps {
  icon: string;
  title: string;
  content?: string;
  dotClass: string;
  children?: React.ReactNode;
  showLine?: boolean;
}

const TimelineNode: React.FC<TimelineNodeProps> = ({
  icon, title, content, dotClass, children, showLine = true
}) => (
  <div className="timeline-node">
    {showLine && <div className="timeline-line" />}
    <div className={`timeline-dot ${dotClass}`} />
    <div className="timeline-content">
      <div className="timeline-title">{icon} {title}</div>
      {content && <div className="timeline-text">{content}</div>}
      {children}
    </div>
  </div>
);

// 主要矛盾金色卡片
const PrimaryContradictionCard: React.FC<{ message: string }> = ({ message }) => {
  const lines = message.split('\n');
  return (
    <div className="primary-contradiction-card">
      {lines.map((line, i) => (
        <div key={i} className={i === 0 ? 'contradiction-first-line' : 'contradiction-line'}>
          {line}
        </div>
      ))}
    </div>
  );
};

// 工具结果（可展开）
const ToolResultContent: React.FC<{ message: string }> = ({ message }) => {
  const [expanded, setExpanded] = useState(false);
  // 提取摘要（第一行或前50字符）
  const summary = message.split('\n')[0]?.slice(0, 50) || message.slice(0, 50);
  const hasMore = message.length > 50 || message.includes('\n');

  return (
    <div className="tool-result-content">
      <div className="result-summary">
        {expanded ? message : summary + (hasMore ? '...' : '')}
      </div>
      {hasMore && (
        <button className="expand-btn" onClick={() => setExpanded(!expanded)}>
          {expanded ? '收起' : '展开详情'}
        </button>
      )}
    </div>
  );
};

// ============================================
// 时间轴组件
// ============================================

interface AnalysisTimelineProps {
  thinkingLog: ThinkingMessage[];
  isAnalyzing: boolean;
}

const AnalysisTimeline: React.FC<AnalysisTimelineProps> = ({ thinkingLog, isAnalyzing }) => {
  const [displayedCount, setDisplayedCount] = useState(0);

  // 流式动画：节点依次出现
  useEffect(() => {
    if (thinkingLog.length > displayedCount) {
      const timer = setTimeout(() => {
        setDisplayedCount(prev => prev + 1);
      }, 120); // 120ms 延迟
      return () => clearTimeout(timer);
    }
  }, [thinkingLog.length, displayedCount]);

  const visibleNodes = thinkingLog.slice(0, displayedCount);

  const renderNode = (msg: ThinkingMessage, index: number) => {
    const isFirst = index === 0;

    switch (msg.type) {
      case 'thinking':
        // LLM真实思考内容，直接显示
        return (
          <TimelineNode
            key={index}
            icon="💭"
            title={msg.message || '思考中...'}
            dotClass="dot-thinking"
            showLine={!isFirst}
          />
        );

      case 'tool_call':
        // 工具调用，简化显示
        return (
          <TimelineNode
            key={index}
            icon="🔧"
            title={msg.message || '调用工具'}
            dotClass="dot-tool_call"
            showLine={!isFirst}
          />
        );

      case 'tool_result':
        return (
          <TimelineNode
            key={index}
            icon="📊"
            title="工具结果"
            dotClass="dot-tool_result"
            showLine={!isFirst}
          >
            <ToolResultContent message={msg.message || ''} />
          </TimelineNode>
        );

      case 'result':
        return (
          <TimelineNode
            key={index}
            icon="✅"
            title={msg.message || '分析完成'}
            dotClass="dot-result"
            showLine={!isFirst}
          />
        );

      default:
        return (
          <TimelineNode
            key={index}
            icon="📝"
            title={msg.message || ''}
            dotClass="dot-thinking"
            showLine={!isFirst}
          />
        );
    }
  };

  return (
    <div className="analysis-timeline">
      {visibleNodes.map(renderNode)}
      {isAnalyzing && displayedCount >= thinkingLog.length && (
        <div className="typing-indicator">
          <span className="typing-dots">生成讲解中...</span>
        </div>
      )}
    </div>
  );
};

// ============================================
// 主组件
// ============================================

export default function DeepAnalysisPanel() {
  const { fen, previousFen, lastMove } = useGameStore();
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [thinkingLog, setThinkingLog] = useState<ThinkingMessage[]>([]);
  const [result, setResult] = useState<{ explanation: string; confidence: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<'quick' | 'deep'>('deep');

  const lastMoveUci = lastMove
    ? `${String.fromCharCode(97 + lastMove.from.col)}${9 - lastMove.from.row}${String.fromCharCode(97 + lastMove.to.col)}${9 - lastMove.to.row}`
    : undefined;

  const handleDeepAnalysis = async () => {
    if (!fen) return;

    console.log('[DEBUG] 点击按钮，开始分析', performance.now());
    setIsAnalyzing(true);
    setThinkingLog([]);
    setResult(null);
    setError(null);

    const question = lastMoveUci
      ? `分析刚才走的棋 ${lastMoveUci}，这步棋走得怎么样？`
      : '请分析当前局面';

    console.log('[DEBUG] 准备发送请求', performance.now());
    await api.analyzeDeep(
      {
        fen: previousFen || fen,
        move: lastMoveUci,
        question,
        show_thinking: true
      },
      (msg) => {
        console.log('[DEBUG] 收到消息', performance.now(), msg.type, msg.message?.slice(0, 20));
        flushSync(() => {
          setThinkingLog(prev => {
            // 流式内容片段：累积到最后一个thinking节点
            if (msg.type === 'thinking_chunk') {
              if (prev.length > 0 && prev[prev.length - 1].type === 'thinking') {
                // 追加到最后一个thinking节点
                const updated = [...prev];
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  message: (updated[updated.length - 1].message || '') + (msg.message || '')
                };
                return updated;
              } else {
                // 没有现有的thinking节点，创建一个新的
                return [...prev, { type: 'thinking', message: msg.message || '' }];
              }
            }
            // 其他类型：新增节点
            return [...prev, msg];
          });
        });
      },
      (res) => {
        setResult(res);
        setIsAnalyzing(false);
      },
      (err) => {
        setError(err);
        setIsAnalyzing(false);
      }
    );
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>🔍 深度分析</h3>
        <div style={styles.modeToggle}>
          <button
            style={{ ...styles.modeBtn, ...(mode === 'quick' ? styles.modeBtnActive : {}) }}
            onClick={() => setMode('quick')}
          >
            快速
          </button>
          <button
            style={{ ...styles.modeBtn, ...(mode === 'deep' ? styles.modeBtnActive : {}) }}
            onClick={() => setMode('deep')}
          >
            深度
          </button>
        </div>
      </div>

      <button
        style={{
          ...styles.analyzeBtn,
          ...(isAnalyzing ? styles.analyzeBtnDisabled : {})
        }}
        onClick={handleDeepAnalysis}
        disabled={isAnalyzing || !fen}
      >
        {isAnalyzing ? '🔄 分析中...' : '🧠 开始深度分析'}
      </button>

      {thinkingLog.length > 0 && (
        <AnalysisTimeline thinkingLog={thinkingLog} isAnalyzing={isAnalyzing} />
      )}

      {error && (
        <div style={styles.errorBox}>
          ❌ {error}
        </div>
      )}

      {result && (
        <div style={styles.resultSection}>
          <div style={styles.resultHeader}>
            <span style={styles.resultTitle}>📋 分析结果</span>
            <span style={{
              ...styles.confidenceBadge,
              ...(result.confidence === 'high' ? styles.confidenceHigh : styles.confidenceMedium)
            }}>
              {result.confidence === 'high' ? '高置信度' : '中等置信度'}
            </span>
          </div>
          <div style={styles.resultContent}>
            {result.explanation.split('\n').map((line, i) => (
              <p key={i} style={styles.resultLine}>{line}</p>
            ))}
          </div>
        </div>
      )}

      {!isAnalyzing && !result && thinkingLog.length === 0 && (
        <div style={styles.emptyState}>
          <div style={styles.emptyIcon}>🧠</div>
          <div style={styles.emptyText}>
            {mode === 'quick' ? '快速模式：直接基于标签分析' : '深度模式：Agent调用工具深入分析'}
          </div>
          <div style={styles.emptyHint}>点击上方按钮开始分析当前局面</div>
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
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  title: {
    fontSize: 14,
    color: '#D4AF37',
    margin: 0,
  },
  modeToggle: {
    display: 'flex',
    gap: 4,
    background: 'rgba(255,255,255,0.05)',
    borderRadius: 6,
    padding: 2,
  },
  modeBtn: {
    padding: '4px 12px',
    fontSize: 11,
    border: 'none',
    background: 'transparent',
    color: '#4a5568',
    cursor: 'pointer',
    borderRadius: 4,
    transition: 'all 0.2s',
  },
  modeBtnActive: {
    background: 'rgba(212,175,55,0.2)',
    color: '#D4AF37',
    fontWeight: 'bold',
  },
  analyzeBtn: {
    width: '100%',
    padding: '12px 16px',
    fontSize: 14,
    fontWeight: 'bold',
    border: 'none',
    borderRadius: 8,
    background: 'linear-gradient(135deg, #C41E3A, #8B0000)',
    color: '#fff',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  analyzeBtnDisabled: {
    opacity: 0.6,
    cursor: 'not-allowed',
  },
  errorBox: {
    padding: 12,
    background: 'rgba(239,68,68,0.15)',
    borderRadius: 8,
    border: '1px solid rgba(239,68,68,0.3)',
    color: '#f87171',
    fontSize: 12,
  },
  resultSection: {
    padding: 14,
    background: 'linear-gradient(135deg, rgba(34,197,94,0.1), rgba(16,185,129,0.1))',
    borderRadius: 8,
    border: '1px solid rgba(34,197,94,0.2)',
  },
  resultHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  resultTitle: {
    fontSize: 13,
    color: '#22c55e',
    fontWeight: 'bold',
  },
  confidenceBadge: {
    padding: '3px 8px',
    fontSize: 10,
    borderRadius: 4,
  },
  confidenceHigh: {
    background: 'rgba(34,197,94,0.2)',
    color: '#22c55e',
  },
  confidenceMedium: {
    background: 'rgba(234,179,8,0.2)',
    color: '#eab308',
  },
  resultContent: {
    fontSize: 13,
    lineHeight: 1.8,
    color: '#2d3748',
  },
  resultLine: {
    margin: '4px 0',
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 30,
    textAlign: 'center',
    gap: 8,
  },
  emptyIcon: {
    fontSize: 40,
    marginBottom: 8,
    opacity: 0.5,
  },
  emptyText: {
    color: '#4a5568',
    fontSize: 12,
  },
  emptyHint: {
    color: '#718096',
    fontSize: 11,
  },
};
