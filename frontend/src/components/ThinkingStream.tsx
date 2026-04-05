import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAgentStore } from '../store/useAgentStore';

// ============================================================
// 思考计时器 Hook
// ============================================================

function useThinkingTimer(isActive: boolean) {
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef<number | null>(null);

  useEffect(() => {
    if (isActive) {
      if (!startRef.current) startRef.current = Date.now();
      const id = setInterval(() => {
        setElapsed(Math.floor((Date.now() - startRef.current!) / 1000));
      }, 1000);
      return () => clearInterval(id);
    }
  }, [isActive]);

  const reset = () => {
    startRef.current = null;
    setElapsed(0);
  };

  return { elapsed, reset };
}

// ============================================================
// 单条思考步骤 — 只有标题，无内容体
// ============================================================

const ThinkingStepItem: React.FC<{
  title: string;
  icon: string;
  status: 'thinking' | 'completed';
  isLast: boolean;
}> = ({ title, icon, status, isLast }) => {
  const isActive = status === 'thinking' && isLast;

  return (
    <motion.div
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '7px 0',
      }}
    >
      {/* 图标 */}
      <span style={{ fontSize: 14, flexShrink: 0, width: 20, textAlign: 'center' }}>
        {status === 'completed' ? (
          <span style={{ color: '#86efac', fontSize: 13 }}>✓</span>
        ) : isActive ? (
          <motion.span
            animate={{ rotate: 360 }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
            style={{ display: 'inline-block', fontSize: 13 }}
          >
            {icon}
          </motion.span>
        ) : (
          <span style={{ fontSize: 13 }}>{icon}</span>
        )}
      </span>

      {/* 标题 */}
      <span
        style={{
          fontSize: 13,
          color: isActive ? 'rgba(255,255,255,0.95)' : status === 'completed' ? 'rgba(255,255,255,0.6)' : 'rgba(255,255,255,0.8)',
          fontWeight: isActive ? 600 : 400,
          lineHeight: 1.4,
        }}
      >
        {title}
      </span>

      {/* 活跃指示器 */}
      {isActive && (
        <motion.span
          animate={{ opacity: [1, 0.3] }}
          transition={{ duration: 1, repeat: Infinity, ease: 'easeInOut' }}
          style={{
            display: 'inline-block',
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: '#fbbf24',
            marginLeft: 2,
            flexShrink: 0,
          }}
        />
      )}
    </motion.div>
  );
};

// ============================================================
// 思考流容器 — 仿顶尖大模型 thinking 面板
// ============================================================

export const ThinkingStream: React.FC = () => {
  const { orchestrator, isAnalyzing } = useAgentStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  const steps = orchestrator.steps;
  const hasSteps = steps.length > 0;
  const allCompleted = hasSteps && steps.every((s) => s.status === 'completed');
  const { elapsed } = useThinkingTimer(isAnalyzing);

  // 自动滚动到底部
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [steps.length]);

  // 没有步骤时不渲染
  if (!hasSteps && !isAnalyzing) return null;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        width: '100%',
        height: '100%',
        minHeight: 0,
      }}
    >
      {/* 顶栏：思考 + 计时器 */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 2px 10px',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          marginBottom: 6,
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 13, fontWeight: 700, color: 'rgba(255,255,255,0.85)' }}>
            思考
          </span>
          {!allCompleted && isAnalyzing && (
            <motion.span
              animate={{ opacity: [1, 0.4] }}
              transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: '#fbbf24',
                display: 'inline-block',
              }}
            />
          )}
        </div>
        {elapsed > 0 && (
          <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)' }}>
            {elapsed}s
          </span>
        )}
      </div>

      {/* 步骤列表 */}
      <div
        ref={scrollRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          minHeight: 0,
          padding: '2px 0',
        }}
      >
        <AnimatePresence>
          {steps.map((step, i) => (
            <ThinkingStepItem
              key={step.index}
              title={step.title}
              icon={getStepIcon(step.title)}
              status={step.status}
              isLast={i === steps.length - 1}
            />
          ))}
        </AnimatePresence>

        {/* 等待首个步骤时的占位 */}
        {!hasSteps && isAnalyzing && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 0',
              color: 'rgba(255,255,255,0.35)',
              fontSize: 13,
            }}
          >
            <motion.span
              animate={{ rotate: 360 }}
              transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
              style={{ display: 'inline-block' }}
            >
              ◎
            </motion.span>
            正在启动分析...
          </motion.div>
        )}
      </div>

      {/* 底栏：完成状态 */}
      {allCompleted && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '10px 0 0',
            borderTop: '1px solid rgba(255,255,255,0.06)',
            marginTop: 6,
            flexShrink: 0,
          }}
        >
          <span style={{ color: '#86efac', fontSize: 13 }}>✓</span>
          <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)' }}>
            已思考 {elapsed}s · 完成
          </span>
        </motion.div>
      )}
    </div>
  );
};

/** 根据步骤标题推断图标 */
function getStepIcon(title: string): string {
  if (title.includes('战术')) return '⚔️';
  if (title.includes('战略')) return '🎯';
  if (title.includes('引擎')) return '📊';
  if (title.includes('综合') || title.includes('协调')) return '🔄';
  if (title.includes('算路') || title.includes('推演') || title.includes('序列')) return '🔧';
  if (title.includes('检索') || title.includes('知识') || title.includes('棋理')) return '📚';
  if (title.includes('候选') || title.includes('对比')) return '📋';
  if (title.includes('检测') || title.includes('局面')) return '🔍';
  if (title.includes('调度') || title.includes('分配')) return '📡';
  return '◎';
}

export default ThinkingStream;
