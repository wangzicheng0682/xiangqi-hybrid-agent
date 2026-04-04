import { useState, useEffect, useRef } from 'react';

// ============================================
// Types
// ============================================

export type ExpertType = 'tactics' | 'strategy' | 'engine';

export type ExpertStatus = 'idle' | 'thinking' | 'completed' | 'failed';

export interface ToolCall {
  id: string;
  toolName: string;
  params: string;
  result: string;
}

export interface ExpertStep {
  index: number;
  title: string;
  content: string;
  status: 'thinking' | 'completed';
  durationMs?: number;
}

export interface ExpertCardProps {
  type: ExpertType;
  status: ExpertStatus;
  thinkingContent: string;
  toolCalls: ToolCall[];
  finding: string;
  steps?: ExpertStep[];
}

// ============================================
// Expert Config
// ============================================

const EXPERT_CONFIG: Record<ExpertType, {
  name: string;
  icon: string;
  color: string;
  borderColor: string;
  bgColor: string;
  accentColor: string;
  description: string;
}> = {
  tactics: {
    name: '战术专家',
    icon: '⚔️',
    color: '#ef4444',
    borderColor: 'rgba(239, 68, 68, 0.4)',
    bgColor: 'rgba(239, 68, 68, 0.06)',
    accentColor: '#ef4444',
    description: '棋子攻防·战术组合',
  },
  strategy: {
    name: '战略专家',
    icon: '🎯',
    color: '#f59e0b',
    borderColor: 'rgba(245, 158, 11, 0.4)',
    bgColor: 'rgba(245, 158, 11, 0.06)',
    accentColor: '#f59e0b',
    description: '全局态势·战略布局',
  },
  engine: {
    name: '引擎专家',
    icon: '📊',
    color: '#3b82f6',
    borderColor: 'rgba(59, 130, 246, 0.4)',
    bgColor: 'rgba(59, 130, 246, 0.06)',
    accentColor: '#3b82f6',
    description: '深度分析·候选走法',
  },
};

// ============================================
// 流式文字组件
// ============================================

const StreamText: React.FC<{ text: string; speed?: number }> = ({ text, speed = 30 }) => {
  const cursorRef = useRef(0);
  const [displayed, setDisplayed] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  // text 被截短（如 reset）时回退游标
  useEffect(() => {
    if (text.length < cursorRef.current) {
      cursorRef.current = 0;
      setDisplayed('');
    }
  }, [text]);

  useEffect(() => {
    if (!text || cursorRef.current >= text.length) return;

    const tick = () => {
      cursorRef.current = Math.min(text.length, cursorRef.current + 1);
      setDisplayed(text.slice(0, cursorRef.current));
      if (containerRef.current) {
        containerRef.current.scrollTop = containerRef.current.scrollHeight;
      }
      if (cursorRef.current < text.length) {
        timerRef.current = setTimeout(tick, speed);
      }
    };

    timerRef.current = setTimeout(tick, speed);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [text, speed]);

  // 高亮格式：**[粗体]**、[工具名]、(坐标)
  const highlightText = (t: string) => {
    // 简单替换
    let result = t
      .replace(/\*\*([^*]+)\*\*/g, '§BOLD§$1§/BOLD§')
      .replace(/\[([^\]]+)\]/g, '§TOOL§[$1]§/TOOL§')
      .replace(/\(([^)]+)\)/g, '§COORD§($1)§/COORD§');

    const segments = result.split('§');
    return segments.map((seg, i) => {
      if (seg === 'BOLD') return null;
      if (seg === '/BOLD') return null;
      if (seg === 'TOOL') return null;
      if (seg === '/TOOL') return null;
      if (seg === 'COORD') return null;
      if (seg === '/COORD') return null;
      if (seg.startsWith('BOLD§')) {
        const inner = seg.replace('BOLD§', '');
        return <strong key={i} style={{ color: '#f5f5f5' }}>{inner}</strong>;
      }
      if (seg.startsWith('TOOL§[')) {
        return <span key={i} style={{ color: '#60a5fa', fontFamily: 'monospace', fontSize: '0.9em' }}>[{seg.replace('TOOL§[', '')}]</span>;
      }
      if (seg.startsWith('COORD§(')) {
        return <span key={i} style={{ color: '#a78bfa' }}>{seg.replace('COORD§', '')}</span>;
      }
      return <span key={i}>{seg}</span>;
    });
  };

  return (
    <div ref={containerRef} style={streamTextStyles.container}>
      <span style={streamTextStyles.cursor}>|</span>
      {highlightText(displayed)}
    </div>
  );
};

// ============================================
// 工具调用气泡
// ============================================

const ToolCallBubble: React.FC<{ toolCall: ToolCall; accentColor: string }> = ({ toolCall, accentColor }) => {
  const [expanded, setExpanded] = useState(false);
  const resultPreview = toolCall.result.slice(0, 40) + (toolCall.result.length > 40 ? '...' : '');

  return (
    <div style={toolBubbleStyles.wrapper}>
      <div style={toolBubbleStyles.header}>
        <span style={{ ...toolBubbleStyles.toolIcon, color: accentColor }}>🔧</span>
        <span style={toolBubbleStyles.toolName}>{toolCall.toolName}</span>
        <span style={toolBubbleStyles.arrow}>→</span>
        <span style={toolBubbleStyles.resultPreview}>{resultPreview}</span>
      </div>
      {expanded && (
        <div style={toolBubbleStyles.expandedResult}>
          {toolCall.result}
        </div>
      )}
      {toolCall.result.length > 40 && (
        <button
          className="liquid-glass-btn sm"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? '收起' : '展开详情'}
        </button>
      )}
    </div>
  );
};

// ============================================
// 状态标签
// ============================================

const StatusBadge: React.FC<{ status: ExpertStatus }> = ({ status }) => {
  const statusConfig: Record<ExpertStatus, { label: string; bgColor: string; textColor: string; dotColor: string }> = {
    idle: { label: '待命', bgColor: 'rgba(255,255,255,0.05)', textColor: '#888', dotColor: '#888' },
    thinking: { label: '思考中', bgColor: 'rgba(245,158,11,0.15)', textColor: '#f59e0b', dotColor: '#f59e0b' },
    completed: { label: '已完成', bgColor: 'rgba(34,197,94,0.15)', textColor: '#22c55e', dotColor: '#22c55e' },
    failed: { label: '失败', bgColor: 'rgba(239,68,68,0.15)', textColor: '#ef4444', dotColor: '#ef4444' },
  };

  const config = statusConfig[status];

  return (
    <span style={{
      ...statusBadgeStyles.base,
      background: config.bgColor,
      color: config.textColor,
    }}>
      <span style={{
        ...statusBadgeStyles.dot,
        background: config.dotColor,
        ...(status === 'thinking' ? { animation: 'pulse 1.5s infinite' } : {}),
      }} />
      {config.label}
    </span>
  );
};

// ============================================
// 主组件：ExpertCard
// ============================================

export const ExpertCard: React.FC<ExpertCardProps> = ({
  type,
  status,
  thinkingContent,
  toolCalls,
  finding,
}) => {
  const config = EXPERT_CONFIG[type];
  const isActive = status === 'thinking';
  const isCompleted = status === 'completed';

  return (
    <div
      style={{
        ...cardStyles.container,
        borderColor: isActive ? config.color : config.borderColor,
        background: isActive
          ? `linear-gradient(135deg, ${config.bgColor}, rgba(0,0,0,0.2))`
          : config.bgColor,
        boxShadow: isActive
          ? `0 0 20px ${config.color}33, 0 4px 12px rgba(0,0,0,0.3)`
          : '0 4px 12px rgba(0,0,0,0.3)',
        ...(isActive ? { animation: 'glow 2s ease-in-out infinite' } : {}),
      }}
    >
      {/* 卡片头部 */}
      <div style={cardStyles.header}>
        <div style={cardStyles.headerLeft}>
          <span style={cardStyles.icon}>{config.icon}</span>
          <div>
            <div style={cardStyles.expertName}>{config.name}</div>
            <div style={cardStyles.expertDesc}>{config.description}</div>
          </div>
        </div>
        <StatusBadge status={status} />
      </div>

      {/* 思考区域 */}
      <div
        style={{
          ...cardStyles.thinkingArea,
          ...(isCompleted ? { maxHeight: 80 } : {}),
        }}
      >
        {thinkingContent ? (
          <StreamText text={thinkingContent} speed={isActive ? 25 : 0} />
        ) : (
          <div style={cardStyles.placeholder}>
            {status === 'idle' ? '等待分析...' : '准备中...'}
          </div>
        )}
      </div>

      {/* 工具调用区 */}
      {toolCalls.length > 0 && (
        <div style={cardStyles.toolSection}>
          <div style={cardStyles.toolSectionTitle}>
            <span>🔧</span> 工具调用
          </div>
          <div style={cardStyles.toolList}>
            {toolCalls.map((tc, i) => (
              <ToolCallBubble key={i} toolCall={tc} accentColor={config.accentColor} />
            ))}
          </div>
        </div>
      )}

      {/* 核心发现 */}
      {isCompleted && finding && (
        <div style={{
          ...cardStyles.findingSection,
          borderColor: `${config.color}40`,
          background: `${config.bgColor}`,
        }}>
          <div style={cardStyles.findingLabel}>
            <span>💡</span> 核心发现
          </div>
          <div style={cardStyles.findingText}>{finding}</div>
        </div>
      )}
    </div>
  );
};

// ============================================
// Styles
// ============================================

const streamTextStyles: Record<string, React.CSSProperties> = {
  container: {
    fontSize: 11,
    lineHeight: 1.6,
    color: '#ccc',
    minHeight: 20,
    fontFamily: '"Noto Serif SC", serif',
    position: 'relative',
    paddingRight: 8,
    wordBreak: 'break-word',
  },
  cursor: {
    color: '#D4AF37',
    fontWeight: 'bold',
    marginRight: 1,
    animation: 'blink 1s step-end infinite',
  },
};

const toolBubbleStyles: Record<string, React.CSSProperties> = {
  wrapper: {
    marginBottom: 6,
    padding: '6px 8px',
    background: 'rgba(0,0,0,0.2)',
    borderRadius: 6,
    border: '1px solid rgba(255,255,255,0.06)',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    flexWrap: 'wrap',
  },
  toolIcon: {
    fontSize: 10,
  },
  toolName: {
    fontSize: 10,
    fontFamily: 'monospace',
    color: '#60a5fa',
    fontWeight: 600,
  },
  arrow: {
    color: '#555',
    fontSize: 10,
  },
  resultPreview: {
    fontSize: 10,
    color: '#4ade80',
    flex: 1,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  expandedResult: {
    marginTop: 6,
    fontSize: 10,
    color: '#aaa',
    fontFamily: 'monospace',
    background: 'rgba(0,0,0,0.3)',
    padding: 6,
    borderRadius: 4,
    whiteSpace: 'pre-wrap',
    maxHeight: 100,
    overflow: 'auto',
  },
  expandBtn: {
    fontSize: 9,
    color: '#60a5fa',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    padding: '2px 0',
    marginTop: 2,
  },
};

const statusBadgeStyles: Record<string, React.CSSProperties> = {
  base: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 4,
    padding: '3px 8px',
    borderRadius: 10,
    fontSize: 10,
    fontWeight: 600,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: '50%',
    flexShrink: 0,
  },
};

const cardStyles: Record<string, React.CSSProperties> = {
  container: {
    borderRadius: 12,
    border: '1px solid',
    padding: 14,
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
    transition: 'all 0.3s ease',
    height: '100%',
    minHeight: 200,
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
    fontSize: 24,
  },
  expertName: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#f5f5f5',
    fontFamily: '"Noto Serif SC", serif',
  },
  expertDesc: {
    fontSize: 10,
    color: '#888',
  },
  thinkingArea: {
    flex: 1,
    overflow: 'auto',
    maxHeight: 160,
    transition: 'max-height 0.3s ease',
  },
  placeholder: {
    color: '#555',
    fontSize: 11,
    fontStyle: 'italic',
    padding: '4px 0',
  },
  toolSection: {
    borderTop: '1px solid rgba(255,255,255,0.06)',
    paddingTop: 8,
  },
  toolSectionTitle: {
    fontSize: 10,
    color: '#888',
    marginBottom: 6,
    display: 'flex',
    alignItems: 'center',
    gap: 4,
  },
  toolList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  findingSection: {
    borderRadius: 8,
    border: '1px solid',
    padding: '8px 10px',
  },
  findingLabel: {
    fontSize: 10,
    color: '#888',
    marginBottom: 4,
    display: 'flex',
    alignItems: 'center',
    gap: 4,
  },
  findingText: {
    fontSize: 12,
    color: '#e8e8e8',
    lineHeight: 1.5,
  },
};

export default ExpertCard;
