import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ExpertCard, ExpertType, ExpertStatus, ToolCall } from './ExpertCard';
import { SynthesisPanel, ConsensusItem, DivergenceItem } from './SynthesisPanel';

// ============================================
// Types
// ============================================

export interface ExpertState {
  status: ExpertStatus;
  thinkingContent: string;
  toolCalls: ToolCall[];
  finding: string;
}

export interface SynthesisState {
  isActive: boolean;
  content: string;
  consensusItems: ConsensusItem[];
  divergenceItems: DivergenceItem[];
}

export interface BottomTerminalPanelProps {
  isOpen: boolean;
  onClose: () => void;
  experts: Record<ExpertType, ExpertState>;
  synthesis: SynthesisState;
  mode: 'quick' | 'deep';
}

// ============================================
// Constants
// ============================================

const MIN_HEIGHT = 300;
const MAX_RATIO = 0.75;

// ============================================
// Framer Motion Variants
// ============================================

const panelVariants = {
  hidden: {
    y: '100%',
    opacity: 0,
  },
  visible: {
    y: 0,
    opacity: 1,
    transition: {
      type: 'spring',
      stiffness: 400,
      damping: 28,
      mass: 0.8,
    },
  },
  exiting: {
    y: '100%',
    opacity: 0,
    transition: {
      type: 'spring',
      stiffness: 400,
      damping: 30,
    },
  },
};

const backdropVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.2 } },
  exiting: { opacity: 0, transition: { duration: 0.15 } },
};

const cardVariants = {
  hidden: { opacity: 0, y: 20, scale: 0.95 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      type: 'spring',
      stiffness: 400,
      damping: 28,
      delay: i * 0.12 + 0.15,
    },
  }),
};

const synthesisVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      type: 'spring',
      stiffness: 400,
      damping: 28,
      delay: 0.15 + 0.12 * 3,
    },
  },
};

// ============================================
// ResizeHandle
// ============================================

interface ResizeHandleProps {
  isDragging: boolean;
  onMouseDown: (e: React.MouseEvent) => void;
}

const ResizeHandle: React.FC<ResizeHandleProps> = ({ isDragging, onMouseDown }) => (
  <motion.div
    className="terminal-resize-handle"
    onMouseDown={onMouseDown}
    style={{
      cursor: isDragging ? 'ns-resize' : 'ns-resize',
      background: isDragging
        ? 'rgba(212,175,55,0.15)'
        : 'linear-gradient(180deg, rgba(255,255,255,0.06), transparent)',
    }}
    whileHover={{ background: 'rgba(212,175,55,0.1)' }}
    transition={{ type: 'spring', stiffness: 500 }}
  >
    <motion.div
      className="terminal-resize-grip"
      animate={{ width: isDragging ? 64 : 48, opacity: isDragging ? 1 : 0.5 }}
      transition={{ type: 'spring', stiffness: 500, damping: 30 }}
    />
  </motion.div>
);

// ============================================
// TitleBar
// ============================================

interface TitleBarProps {
  onClose: () => void;
  isAnalyzing: boolean;
}

const TitleBar: React.FC<TitleBarProps> = ({ onClose, isAnalyzing }) => (
  <div className="terminal-titlebar">
    <div className="terminal-titlebar-left">
      <span className="terminal-titlebar-icon">🎯</span>
      <span className="terminal-titlebar-title">三专家协作分析</span>
      {isAnalyzing && (
        <span className="terminal-titlebar-status">
          <span className="terminal-status-dot" />
          分析中
        </span>
      )}
    </div>
    <div className="terminal-titlebar-actions">
      <button className="liquid-glass-btn sm" onClick={onClose}>
        −
      </button>
      <button className="liquid-glass-btn sm" onClick={onClose}>
        ×
      </button>
    </div>
  </div>
);

// ============================================
// Main Component
// ============================================

export const BottomTerminalPanel: React.FC<BottomTerminalPanelProps> = ({
  isOpen,
  onClose,
  experts,
  synthesis,
}) => {
  const [height, setHeight] = useState(() => {
    const saved = localStorage.getItem('terminalPanelHeight');
    return saved ? parseInt(saved) : Math.min(500, window.innerHeight * 0.45);
  });
  const [isDragging, setIsDragging] = useState(false);
  const dragStartMouseY = useRef(0);
  const dragStartHeightRef = useRef(0);

  const maxHeight = Math.min(window.innerHeight * MAX_RATIO, 800);

  // Keyboard shortcut: Escape to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Prevent scroll on body when open
  useEffect(() => {
    if (isOpen) {
      document.body.classList.add('terminal-panel-open');
    } else {
      document.body.classList.remove('terminal-panel-open');
    }
    return () => document.body.classList.remove('terminal-panel-open');
  }, [isOpen]);

  // Mouse events for resize
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    dragStartMouseY.current = e.clientY;
    dragStartHeightRef.current = height;
  }, [height]);

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      const delta = dragStartMouseY.current - e.clientY;
      const newHeight = Math.max(
        MIN_HEIGHT,
        Math.min(maxHeight, dragStartHeightRef.current + delta)
      );
      setHeight(newHeight);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      localStorage.setItem('terminalPanelHeight', String(height));
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, height, maxHeight]);

  // Window resize handler
  useEffect(() => {
    const handleResize = () => {
      setHeight(prev => Math.min(prev, window.innerHeight * MAX_RATIO));
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const isAnalyzing = Object.values(experts).some(e => e.status === 'thinking');
  const expertsOrder: ExpertType[] = ['tactics', 'strategy', 'engine'];

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="terminal-backdrop"
            variants={backdropVariants}
            initial="hidden"
            animate="visible"
            exit="exiting"
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            className="terminal-panel"
            variants={panelVariants}
            initial="hidden"
            animate="visible"
            exit="exiting"
            style={{ height }}
          >
            {/* Resize Handle */}
            <ResizeHandle isDragging={isDragging} onMouseDown={handleMouseDown} />

            {/* Title Bar */}
            <TitleBar onClose={onClose} isAnalyzing={isAnalyzing} />

            {/* Content */}
            <div className="terminal-content">
              {/* Experts Grid */}
              <motion.div
                className="terminal-experts-grid"
                variants={{
                  visible: { transition: { staggerChildren: 0.12, delayChildren: 0.15 } },
                }}
                initial="hidden"
                animate="visible"
              >
                {expertsOrder.map((type, i) => (
                  <motion.div key={type} custom={i} variants={cardVariants}>
                    <ExpertCard
                      type={type}
                      status={experts[type].status}
                      thinkingContent={experts[type].thinkingContent}
                      toolCalls={experts[type].toolCalls}
                      finding={experts[type].finding}
                    />
                  </motion.div>
                ))}
              </motion.div>

              {/* Synthesis Panel */}
              <motion.div
                variants={synthesisVariants}
                initial="hidden"
                animate="visible"
              >
                <SynthesisPanel
                  isActive={synthesis.isActive}
                  synthesisContent={synthesis.content}
                  consensusItems={synthesis.consensusItems}
                  divergenceItems={synthesis.divergenceItems}
                />
              </motion.div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default BottomTerminalPanel;
