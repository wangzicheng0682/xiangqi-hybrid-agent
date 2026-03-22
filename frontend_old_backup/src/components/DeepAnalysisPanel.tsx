import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useGameStore, ExpertType, AgentPhase } from '../store/useGameStore';
import { api } from '../services/api';
import { ExpertCard } from './ExpertCard';
import { SynthesisPanel } from './SynthesisPanel';
import { AgentDebutPanel } from './AgentDebutPanel';

// ============================================
// Types
// ============================================

interface ToolCall {
  toolName: string;
  params: string;
  result: string;
}

interface ExpertState {
  status: 'idle' | 'thinking' | 'completed' | 'failed';
  thinkingContent: string;
  toolCalls: ToolCall[];
  finding: string;
  phase: AgentPhase;
}

interface SynthesisState {
  isActive: boolean;
  content: string;
  consensusItems: { expert: string; point: string }[];
  divergenceItems: { expert1: string; expert2: string; point: string }[];
}

// ============================================
// Main Component
// ============================================

export default function DeepAnalysisPanel() {
  const { fen, previousFen, lastMove, setAnalysisMode } = useGameStore();

  const [isPanelActive, setIsPanelActive] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 专家状态
  const [experts, setExperts] = useState<Record<ExpertType, ExpertState>>({
    tactics: { status: 'idle', thinkingContent: '', toolCalls: [], finding: '', phase: 0 },
    strategy: { status: 'idle', thinkingContent: '', toolCalls: [], finding: '', phase: 0 },
    engine: { status: 'idle', thinkingContent: '', toolCalls: [], finding: '', phase: 0 },
  });

  // 合成器状态
  const [synthesis, setSynthesis] = useState<SynthesisState>({
    isActive: false,
    content: '',
    consensusItems: [],
    divergenceItems: [],
  });

  // 面板激活时显示登场动画
  const [showDebut, setShowDebut] = useState(false);

  const lastMoveUci = lastMove
    ? `${String.fromCharCode(97 + lastMove.from.col)}${9 - lastMove.from.row}${String.fromCharCode(97 + lastMove.to.col)}${9 - lastMove.to.row}`
    : undefined;

  const handleStartAnalysis = useCallback(() => {
    if (!fen) return;

    // 进入分析模式
    setAnalysisMode(true);
    setIsPanelActive(true);
    setShowDebut(true);
    setIsAnalyzing(true);
    setError(null);

    // 重置专家状态
    setExperts({
      tactics: { status: 'idle', thinkingContent: '', toolCalls: [], finding: '', phase: 0 },
      strategy: { status: 'idle', thinkingContent: '', toolCalls: [], finding: '', phase: 0 },
      engine: { status: 'idle', thinkingContent: '', toolCalls: [], finding: '', phase: 0 },
    });
    setSynthesis({
      isActive: false,
      content: '',
      consensusItems: [],
      divergenceItems: [],
    });

    const question = lastMoveUci
      ? `分析刚才走的棋 ${lastMoveUci}，这步棋走得怎么样？`
      : '请分析当前局面';

    api.analyzeDeep(
      {
        fen: previousFen || fen,
        move: lastMoveUci,
        question,
        show_thinking: true,
      },
      (msg) => {
        // 路由SSE事件到对应专家
        const type = msg.type || '';

        if (type === 'expert_start') {
          const expert = (msg as any).expert as ExpertType;
          if (expert && ['tactics', 'strategy', 'engine'].includes(expert)) {
            setExperts(prev => ({
              ...prev,
              [expert]: { ...prev[expert], status: 'thinking', phase: 4 as AgentPhase },
            }));
          }
        } else if (type === 'expert_result') {
          const data = msg as any;
          const expert = data.expert as ExpertType;
          if (expert && ['tactics', 'strategy', 'engine'].includes(expert)) {
            setExperts(prev => ({
              ...prev,
              [expert]: {
                ...prev[expert],
                status: data.success ? 'completed' : 'failed',
                finding: data.finding || '',
                phase: 4 as AgentPhase,
              },
            }));
          }
        } else if (type.startsWith('expert_tactics_')) {
          const subtype = type.replace('expert_tactics_', '');
          handleExpertEvent('tactics', subtype, msg.message || '');
        } else if (type.startsWith('expert_strategy_')) {
          const subtype = type.replace('expert_strategy_', '');
          handleExpertEvent('strategy', subtype, msg.message || '');
        } else if (type.startsWith('expert_engine_')) {
          const subtype = type.replace('expert_engine_', '');
          handleExpertEvent('engine', subtype, msg.message || '');
        } else if (type === 'synthesis_chunk') {
          setSynthesis(prev => ({
            ...prev,
            isActive: true,
            content: prev.content + (msg.message || ''),
          }));
        } else if (type === 'thinking' || type === 'thinking_chunk') {
          // 通用思考消息，分配给当前正在思考的专家
          const activeExpert = findActiveExpert();
          if (activeExpert) {
            handleExpertEvent(activeExpert, 'chunk', msg.message || '');
          }
        }
      },
      (_result) => {
        setIsAnalyzing(false);
        setShowDebut(false);
        setSynthesis(prev => ({
          ...prev,
          isActive: false,
        }));
      },
      (err) => {
        setError(err);
        setIsAnalyzing(false);
        setShowDebut(false);
        setExperts(prev => ({
          tactics: { ...prev.tactics, status: 'failed' },
          strategy: { ...prev.strategy, status: 'failed' },
          engine: { ...prev.engine, status: 'failed' },
        }));
      }
    );
  }, [fen, previousFen, lastMoveUci, setAnalysisMode]);

  // 处理专家事件
  const handleExpertEvent = (expert: ExpertType, subtype: string, message: string) => {
    setExperts(prev => {
      const current = prev[expert];

      if (subtype === 'thinking') {
        return { ...prev, [expert]: { ...current, thinkingContent: message } };
      } else if (subtype === 'chunk') {
        return { ...prev, [expert]: { ...current, thinkingContent: current.thinkingContent + message } };
      } else if (subtype === 'tool') {
        // 工具调用开始 - 追加工具记录
        return { ...prev, [expert]: { ...current, toolCalls: [...current.toolCalls, { toolName: message.replace('调用工具: ', ''), params: '', result: '' }] } };
      } else if (subtype === 'tool_result') {
        // 工具结果返回 - 更新最后一个工具记录
        const toolCalls = [...current.toolCalls];
        if (toolCalls.length > 0) {
          const last = toolCalls[toolCalls.length - 1];
          const resultPart = message.split(': ').slice(1).join(': ');
          toolCalls[toolCalls.length - 1] = { ...last, result: resultPart || message };
        }
        return { ...prev, [expert]: { ...current, toolCalls } };
      }

      return prev;
    });
  };

  // 找到当前正在思考的专家
  const findActiveExpert = (): ExpertType | null => {
    if (experts.tactics.status === 'thinking') return 'tactics';
    if (experts.strategy.status === 'thinking') return 'strategy';
    if (experts.engine.status === 'thinking') return 'engine';
    return null;
  };

  const handleClose = () => {
    setIsPanelActive(false);
    setShowDebut(false);
    setAnalysisMode(false);
    setIsAnalyzing(false);
  };

  const isAnyExpertActive = Object.values(experts).some(e => e.status === 'thinking' || e.status === 'completed');
  const hasResult = synthesis.content.length > 0 || isAnyExpertActive;

  return (
    <div style={styles.container}>
      {/* 标题栏 */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <span style={styles.headerIcon}>⚡</span>
          <span style={styles.headerTitle}>深度分析</span>
          {isAnalyzing && (
            <motion.div
              animate={{ opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              style={styles.analyzingBadge}
            >
              <motion.span
                animate={{ scale: [1, 1.15, 1] }}
                transition={{ duration: 1, repeat: Infinity }}
                style={{ ...styles.dot, background: '#f59e0b' }}
              />
              <span style={{ fontSize: 10, color: '#f59e0b' }}>分析中</span>
            </motion.div>
          )}
        </div>
        {isPanelActive && (
          <button style={styles.closeBtn} onClick={handleClose}>×</button>
        )}
      </div>

      {/* 还未开始分析 - 显示开始按钮 */}
      {!isPanelActive && (
        <div style={styles.startSection}>
          <button
            style={{
              ...styles.startBtn,
              ...(isAnalyzing ? styles.startBtnDisabled : {}),
            }}
            onClick={handleStartAnalysis}
            disabled={isAnalyzing || !fen}
          >
            {isAnalyzing ? '分析中...' : '开始深度分析'}
          </button>
          <div style={styles.startHint}>
            多专家并行分析，深度讲解
          </div>
        </div>
      )}

      {/* 分析中/已结束 - 显示专家登场 + 卡片 */}
      <AnimatePresence>
        {isPanelActive && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={styles.content}
          >
            {/* 登场动画 */}
            <AgentDebutPanel
              isActive={showDebut}
              experts={experts}
              synthesis={synthesis}
              onClose={handleClose}
            />

            {/* 专家卡片区域 - 登场动画结束后显示 */}
            {hasResult && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.5, type: 'spring', stiffness: 260, damping: 22 }}
                style={styles.expertsGrid}
              >
                <ExpertCard
                  type="tactics"
                  status={experts.tactics.status}
                  thinkingContent={experts.tactics.thinkingContent}
                  toolCalls={experts.tactics.toolCalls}
                  finding={experts.tactics.finding}
                />
                <ExpertCard
                  type="strategy"
                  status={experts.strategy.status}
                  thinkingContent={experts.strategy.thinkingContent}
                  toolCalls={experts.strategy.toolCalls}
                  finding={experts.strategy.finding}
                />
                <ExpertCard
                  type="engine"
                  status={experts.engine.status}
                  thinkingContent={experts.engine.thinkingContent}
                  toolCalls={experts.engine.toolCalls}
                  finding={experts.engine.finding}
                />
              </motion.div>
            )}

            {/* 合成器面板 */}
            {synthesis.content.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2, type: 'spring', stiffness: 260, damping: 22 }}
              >
                <SynthesisPanel
                  isActive={synthesis.isActive}
                  synthesisContent={synthesis.content}
                  consensusItems={synthesis.consensusItems}
                  divergenceItems={synthesis.divergenceItems}
                />
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* 错误提示 */}
      {error && (
        <div style={styles.errorBox}>
          {error}
        </div>
      )}
    </div>
  );
}

// ============================================
// Styles
// ============================================

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
    height: '100%',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '4px 0',
    borderBottom: '1px solid rgba(212,175,55,0.12)',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  headerIcon: {
    fontSize: 14,
  },
  headerTitle: {
    fontSize: 13,
    fontWeight: 600,
    color: '#D4AF37',
    fontFamily: '"Noto Serif SC", serif',
  },
  analyzingBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: 5,
    padding: '2px 8px',
    background: 'rgba(245,158,11,0.1)',
    borderRadius: 10,
    border: '1px solid rgba(245,158,11,0.2)',
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: '50%',
    display: 'inline-block',
  },
  closeBtn: {
    width: 22,
    height: 22,
    borderRadius: '50%',
    border: '1px solid rgba(255,255,255,0.1)',
    background: 'rgba(255,255,255,0.04)',
    color: '#666',
    fontSize: 14,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 0,
    lineHeight: 1,
  },
  startSection: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 8,
    padding: '20px 0',
  },
  startBtn: {
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
  startBtnDisabled: {
    opacity: 0.6,
    cursor: 'not-allowed',
  },
  startHint: {
    fontSize: 11,
    color: '#666',
  },
  content: {
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
    overflowY: 'auto',
    maxHeight: 'calc(100vh - 200px)',
  },
  expertsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: 10,
  },
  errorBox: {
    padding: 12,
    background: 'rgba(239,68,68,0.15)',
    borderRadius: 8,
    border: '1px solid rgba(239,68,68,0.3)',
    color: '#f87171',
    fontSize: 12,
  },
};
