import { useState, useEffect } from 'react';
import { flushSync } from 'react-dom';
import { useGameStore } from '../store/useGameStore';
import { useAgentStore } from '../store/useAgentStore';
import { api } from '../services/api';
import { AgentThinkingPanel } from './AgentThinkingPanel';
import type { ExpertType } from './CardContent';
import type { ExpertStatus } from './ExpertCard';

interface ThinkingMessage {
  type: string;
  stage?: number;
  message?: string;
  tool?: string;
  finding?: string;
  expert?: string; // 'tactics' | 'strategy' | 'engine'
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
  const { fen, previousFen, lastMove, setBoardCollapsed } = useGameStore();
  const { isPanelActive, setPanelActive, setAnalyzing, resetAll } = useAgentStore();
  const [isAnalyzingLocal, setIsAnalyzingLocal] = useState(false);
  const [thinkingLog, setThinkingLog] = useState<ThinkingMessage[]>([]);
  const [result, setResult] = useState<{ explanation: string; confidence: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<'quick' | 'deep'>('deep');

  // 当收起状态时，显示新面板
  const showPokerPanel = isPanelActive;

  const lastMoveUci = lastMove
    ? `${String.fromCharCode(97 + lastMove.from.col)}${9 - lastMove.from.row}${String.fromCharCode(97 + lastMove.to.col)}${9 - lastMove.to.row}`
    : undefined;

  const handleDeepAnalysis = async () => {
    if (!fen) return;

    console.log('[DEBUG] 点击按钮，开始分析', performance.now());
    setBoardCollapsed(true); // 触发动画

    // 触发 AgentThinkingPanel 动画序列
    setPanelActive(true);
    setAnalyzing(true);
    setIsAnalyzingLocal(true);
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

        // ── 同步更新 useAgentStore（驱动扑克牌动画 + 思维流）─────────────────
        const store = useAgentStore.getState();
        const expertType = msg.expert as ExpertType | undefined;

        // 专家归属事件 → 更新对应专家状态
        if (expertType && ['tactics', 'strategy', 'engine'].includes(expertType)) {
          if (msg.type === 'expert_start') {
            store.updateExpert(expertType, { status: 'thinking' as ExpertStatus });
          } else if (msg.type === 'expert_result') {
            try {
              const data = typeof msg.message === 'string' ? JSON.parse(msg.message) : msg.message;
              store.updateExpert(expertType, {
                status: 'done' as any,
                finding: data.finding || '',
              });
            } catch {
              store.updateExpert(expertType, { status: 'completed' as any });
            }
          } else if (msg.type === `expert_${expertType}_thinking`) {
            // 专家思考内容（流式）
            store.appendExpertThinking(expertType, msg.message || '');
          } else if (msg.type === `expert_${expertType}_chunk`) {
            // 专家 chunk → 追加到 thinking
            store.appendExpertThinking(expertType, msg.message || '');
          } else if (msg.type === `expert_${expertType}_tool`) {
            // 工具调用（显示工具名即可）
            store.addExpertToolCall(expertType, {
              id: Date.now().toString(),
              toolName: msg.message || 'tool',
              params: '',
              result: '',
            });
          }
        }

        // 协调者小标题事件（目前后端用 synthesis_chunk 代替）
        if (msg.type === 'orchestrator_subtitle' || msg.type === 'synthesis_chunk') {
          store.appendOrchestratorContent(msg.message || '');
        }

        // ── 原有 thinkingLog 更新逻辑 ──────────────────────────────────────
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
            return [...prev, { ...msg, expert: msg.expert }];
          });
        });
      },
      (res) => {
        setResult(res);
        setIsAnalyzingLocal(false);
        setAnalyzing(false);
      },
      (err) => {
        setError(err);
        setIsAnalyzingLocal(false);
        setAnalyzing(false);
      }
    );
  };

  // 当分析激活时，显示新的扑克牌面板
  if (showPokerPanel) {
    return (
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* 关闭按钮 */}
        <div style={{
          display: 'flex',
          justifyContent: 'flex-end',
          padding: '4px 0 8px',
          borderBottom: '1px solid rgba(212,175,55,0.12)',
          marginBottom: 8,
        }}>
          <button
            className="liquid-glass-btn sm"
            onClick={() => {
              setPanelActive(false);
              setAnalyzing(false);
              resetAll();
              setBoardCollapsed(false);
            }}
          >
            收起
          </button>
        </div>
        {/* 新面板 */}
        <AgentThinkingPanel />
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>🔍 深度分析</h3>
        <div style={styles.modeToggle}>
          <button
            className={`liquid-glass-btn sm${mode === 'quick' ? ' primary' : ''}`}
            style={mode === 'quick' ? {} : {}}
            onClick={() => setMode('quick')}
          >
            快速
          </button>
          <button
            className={`liquid-glass-btn sm${mode === 'deep' ? ' primary' : ''}`}
            style={mode === 'deep' ? {} : {}}
            onClick={() => setMode('deep')}
          >
            深度
          </button>
        </div>
      </div>

      <button
        className="liquid-glass-btn primary"
        style={{ width: '100%' }}
        onClick={handleDeepAnalysis}
        disabled={isAnalyzingLocal || !fen}
      >
        {isAnalyzingLocal ? '🔄 分析中...' : '🧠 开始深度分析'}
      </button>

      {thinkingLog.length > 0 && (
        <AnalysisTimeline thinkingLog={thinkingLog} isAnalyzing={isAnalyzingLocal} />
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

      {!isAnalyzingLocal && !result && thinkingLog.length === 0 && (
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
    color: 'rgba(212,175,55,0.85)',
    margin: 0,
    fontWeight: '600',
  },
  modeToggle: {
    display: 'flex',
    gap: 4,
    background: 'rgba(0,0,0,0.04)',
    borderRadius: 'var(--radius-md)',
    padding: 2,
  },
  modeBtn: {
    padding: '5px 12px',
    fontSize: 11,
    border: 'none',
    background: 'transparent',
    color: 'var(--apple-text-secondary)',
    cursor: 'pointer',
    borderRadius: 'var(--radius-sm)',
    transition: 'all 0.18s cubic-bezier(0.16, 1, 0.3, 1)',
  },
  modeBtnActive: {
    background: 'rgba(212,175,55,0.15)',
    color: 'rgba(212,175,55,0.9)',
    fontWeight: '600',
  },
  analyzeBtn: {
    width: '100%',
    padding: '12px 16px',
    fontSize: 13,
    fontWeight: '600',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    background: 'linear-gradient(135deg, rgba(196,30,58,0.85), rgba(139,0,0,0.85))',
    color: '#fff',
    cursor: 'pointer',
    transition: 'all 0.18s cubic-bezier(0.16, 1, 0.3, 1)',
  },
  analyzeBtnDisabled: {
    opacity: 0.55,
    cursor: 'not-allowed',
  },
  errorBox: {
    padding: 12,
    background: 'rgba(239,68,68,0.1)',
    borderRadius: 'var(--radius-md)',
    border: '1px solid rgba(239,68,68,0.2)',
    color: 'rgba(239,68,68,0.85)',
    fontSize: 12,
  },
  resultSection: {
    padding: 14,
    background: 'rgba(34,197,94,0.06)',
    borderRadius: 'var(--radius-md)',
    border: '1px solid rgba(34,197,94,0.18)',
  },
  resultHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  resultTitle: {
    fontSize: 13,
    color: 'rgba(22,101,52,0.85)',
    fontWeight: '600',
  },
  confidenceBadge: {
    padding: '3px 8px',
    fontSize: 10,
    borderRadius: 'var(--radius-full)',
  },
  confidenceHigh: {
    background: 'rgba(34,197,94,0.15)',
    color: 'rgba(22,101,52,0.85)',
  },
  confidenceMedium: {
    background: 'rgba(234,179,8,0.15)',
    color: 'rgba(180,130,20,0.85)',
  },
  resultContent: {
    fontSize: 13,
    lineHeight: 1.8,
    color: 'var(--apple-text)',
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
    fontSize: 36,
    marginBottom: 8,
    opacity: 0.35,
  },
  emptyText: {
    color: 'var(--apple-text-secondary)',
    fontSize: 12,
  },
  emptyHint: {
    color: 'var(--apple-text-tertiary)',
    fontSize: 11,
  },
};
