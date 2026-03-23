import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ExpertCard, ExpertType, ExpertStatus, ToolCall } from './ExpertCard';
import { SynthesisPanel, ConsensusItem, DivergenceItem } from './SynthesisPanel';

// ============================================
// Types
// ============================================

export type AgentPhase = 0 | 1 | 2 | 3 | 4;

export interface ExpertState {
  status: ExpertStatus;
  thinkingContent: string;
  toolCalls: ToolCall[];
  finding: string;
  phase: AgentPhase;
}

export interface SynthesisState {
  isActive: boolean;
  content: string;
  consensusItems: ConsensusItem[];
  divergenceItems: DivergenceItem[];
}

export interface AgentDebutPanelProps {
  isActive: boolean;
  experts: Record<ExpertType, ExpertState>;
  synthesis: SynthesisState;
  onClose: () => void;
}

// ============================================
// Expert Config
// ============================================

const EXPERT_CONFIG: Record<ExpertType, {
  name: string;
  icon: string;
  color: string;
  description: string;
}> = {
  tactics: {
    name: '战术专家',
    icon: '⚔️',
    color: '#ef4444',
    description: '棋子攻防·战术组合',
  },
  strategy: {
    name: '战略专家',
    icon: '🎯',
    color: '#f59e0b',
    description: '全局态势·战略布局',
  },
  engine: {
    name: '引擎专家',
    icon: '📊',
    color: '#3b82f6',
    description: '深度分析·候选走法',
  },
};

// ============================================
// Typing Effect Hook
// ============================================

const useTypingEffect = (text: string, delay = 0) => {
  const [displayed, setDisplayed] = useState('');
  const [started, setStarted] = useState(false);

  useEffect(() => {
    setDisplayed('');
    setStarted(false);
    const startTimer = setTimeout(() => setStarted(true), delay);
    return () => clearTimeout(startTimer);
  }, [text, delay]);

  useEffect(() => {
    if (!started) return;
    if (displayed.length >= text.length) return;
    const timer = setTimeout(() => {
      setDisplayed(text.slice(0, displayed.length + 1));
    }, 35);
    return () => clearTimeout(timer);
  }, [displayed, text, started]);

  return displayed;
};

// ============================================
// Phase 1: Breathing Indicator (Claude-style)
// ============================================

const BreathingDot: React.FC<{ color: string; delay?: number }> = ({ color, delay = 0 }) => (
  <motion.div
    initial={{ opacity: 0, scale: 0 }}
    animate={{ opacity: 1, scale: 1 }}
    transition={{ delay, duration: 0.4, ease: [0.32, 0.72, 0, 1] }}
    style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px 0' }}
  >
    <motion.div
      animate={{
        scale: [1, 1.08, 1],
        opacity: [0.7, 1, 0.7],
      }}
      transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
      style={{
        width: 12,
        height: 12,
        borderRadius: '50%',
        background: color,
        boxShadow: `0 0 12px ${color}80, 0 0 24px ${color}40`,
      }}
    />
  </motion.div>
);

// ============================================
// Phase 2: Apple Outline Trace
// ============================================

const OutlineCard: React.FC<{
  type: ExpertType;
  phase: number;
  index: number;
}> = ({ type, phase, index }) => {
  const config = EXPERT_CONFIG[type];
  const show = phase >= 2;

  const typedName = useTypingEffect(config.name, show ? 0.2 + index * 0.15 : 999);
  const typedDesc = useTypingEffect(config.description, show ? 0.5 + index * 0.15 : 999);

  if (!show) return null;

  const isIdentity = phase >= 3;
  const isFilled = phase >= 4;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      style={{
        borderRadius: 12,
        padding: 16,
        background: isFilled
          ? `linear-gradient(135deg, ${config.color}08, transparent)`
          : 'transparent',
        border: `1.5px ${isFilled ? 'solid' : 'dashed'} ${config.color}50`,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 8,
        minHeight: 180,
        transition: 'all 0.4s cubic-bezier(0.32, 0.72, 0, 1)',
      }}
    >
      {/* Icon */}
      <motion.div
        initial={{ scale: 0, rotate: -30 }}
        animate={{ scale: isIdentity ? 1 : 0, rotate: isIdentity ? 0 : -30 }}
        transition={{ type: 'spring', stiffness: 300, damping: 20, delay: index * 0.1 }}
        style={{
          width: 48,
          height: 48,
          borderRadius: '50%',
          background: `${config.color}20`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 24,
          border: `1px solid ${config.color}40`,
        }}
      >
        {config.icon}
      </motion.div>

      {/* Name */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: isIdentity ? 1 : 0 }}
        style={{
          fontSize: 13,
          fontWeight: 700,
          color: config.color,
          fontFamily: '"Noto Serif SC", serif',
          minHeight: 20,
        }}
      >
        {typedName}
        {!isIdentity && <motion.span animate={{ opacity: [0, 1, 0] }} transition={{ duration: 0.8, repeat: Infinity }}>|</motion.span>}
      </motion.div>

      {/* Description */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: isIdentity ? 0.6 : 0 }}
        style={{ fontSize: 10, color: '#888', textAlign: 'center' }}
      >
        {typedDesc}
      </motion.div>

      {/* Status */}
      {isIdentity && (
        <motion.div
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 + index * 0.1 }}
          style={{
            marginTop: 4,
            padding: '3px 10px',
            borderRadius: 10,
            fontSize: 10,
            fontWeight: 600,
            background: `${config.color}15`,
            color: config.color,
            border: `1px solid ${config.color}30`,
          }}
        >
          准备中...
        </motion.div>
      )}
    </motion.div>
  );
};

// ============================================
// Phase 3-4: Full Expert Card
// ============================================

const FullExpertCard: React.FC<{
  type: ExpertType;
  state: ExpertState;
  index: number;
  phase: number;
}> = ({ type, state, index, phase }) => {
  if (phase < 4) return null;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{
        type: 'spring',
        stiffness: 260,
        damping: 22,
        delay: index * 0.12,
      }}
    >
      <ExpertCard
        type={type}
        status={state.status}
        thinkingContent={state.thinkingContent}
        toolCalls={state.toolCalls}
        finding={state.finding}
      />
    </motion.div>
  );
};

// ============================================
// Main Expert Debut Grid
// ============================================

const ExpertDebutGrid: React.FC<{
  experts: Record<ExpertType, ExpertState>;
  phase: number;
}> = ({ experts, phase }) => {
  const expertsOrder: ExpertType[] = ['tactics', 'strategy', 'engine'];

  return (
    <motion.div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: 10,
      }}
    >
      {expertsOrder.map((type, i) => (
        <div key={type}>
          {/* Outline (shown until phase 4) */}
          {phase < 4 && (
            <OutlineCard type={type} phase={phase} index={i} />
          )}
          {/* Full card (shown from phase 4) */}
          <AnimatePresence>
            {phase >= 4 && (
              <FullExpertCard
                type={type}
                state={experts[type]}
                index={i}
                phase={phase}
              />
            )}
          </AnimatePresence>
        </div>
      ))}
    </motion.div>
  );
};

// ============================================
// Debut Sequence Orchestrator
// ============================================

const DebutSequence: React.FC<{
  onPhaseChange: (phase: number) => void;
}> = ({ onPhaseChange }) => {
  const phaseTimings = [300, 600, 900, 1200]; // phase 1-4 delays

  useEffect(() => {
    const timers = phaseTimings.map((delay, i) =>
      setTimeout(() => onPhaseChange(i + 1), delay)
    );
    return () => timers.forEach(clearTimeout);
  }, []);

  return null;
};

// ============================================
// Main Panel
// ============================================

export const AgentDebutPanel: React.FC<AgentDebutPanelProps> = ({
  isActive,
  experts,
  synthesis,
  onClose,
}) => {
  const [phase, setPhase] = useState(0);

  // Reset phase when panel opens/closes
  useEffect(() => {
    if (isActive) {
      setPhase(0);
    }
  }, [isActive]);

  const handlePhaseChange = (p: number) => setPhase(p);

  // Keyboard: Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isActive) onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isActive, onClose]);

  const isAnalyzing = Object.values(experts).some(e => e.status === 'thinking');
  const expertsOrder: ExpertType[] = ['tactics', 'strategy', 'engine'];

  return (
    <div style={styles.container}>
      {/* Header */}
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
        <button className="liquid-glass-btn sm" onClick={onClose}>×</button>
      </div>

      {/* Content */}
      <div style={styles.content}>
        {/* Debut sequence orchestrator */}
        {isActive && phase === 0 && (
          <DebutSequence onPhaseChange={handlePhaseChange} />
        )}

        {/* Breathing dots */}
        {phase >= 1 && phase < 4 && (
          <motion.div
            style={styles.breathingArea}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <div style={styles.breathingRow}>
              {expertsOrder.map((type, i) => (
                <BreathingDot
                  key={type}
                  color={EXPERT_CONFIG[type].color}
                  delay={i * 0.08}
                />
              ))}
            </div>
            <motion.div
              animate={{ opacity: [0.3, 0.7, 0.3] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              style={styles.breathingLabel}
            >
              正在召集专家...
            </motion.div>
          </motion.div>
        )}

        {/* Expert cards / outlines */}
        {phase >= 2 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
          >
            <ExpertDebutGrid experts={experts} phase={phase} />
          </motion.div>
        )}
      </div>

      {/* Synthesis Panel */}
      <AnimatePresence>
        {phase >= 4 && synthesis.content && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, type: 'spring', stiffness: 260, damping: 22 }}
          >
            <SynthesisPanel
              isActive={synthesis.isActive}
              synthesisContent={synthesis.content}
              consensusItems={synthesis.consensusItems}
              divergenceItems={synthesis.divergenceItems}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

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
  content: {
    flex: 1,
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  breathingArea: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 8,
    padding: '16px 0',
  },
  breathingRow: {
    display: 'flex',
    gap: 24,
    alignItems: 'center',
  },
  breathingLabel: {
    fontSize: 11,
    color: '#666',
    fontFamily: '"Noto Serif SC", serif',
  },
};

export default AgentDebutPanel;
