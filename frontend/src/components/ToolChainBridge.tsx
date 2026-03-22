import { motion, AnimatePresence } from 'framer-motion';
import { useState, useEffect } from 'react';

export type ToolStatus = 'idle' | 'calling' | 'success' | 'error';

export interface ToolCall {
  id: string;
  name: string;
  status: ToolStatus;
  startTime: number;
}

interface ToolChainBridgeProps {
  tools: ToolCall[];
}

// 呼吸状态灯
function StatusDot({ status }: { status: ToolStatus }) {
  const base = 'w-2 h-2 rounded-full flex-shrink-0';
  if (status === 'idle') return <div className={`${base} bg-gray-300`} />;
  if (status === 'calling') return (
    <div className={`${base} bg-blue-400 animate-pulse`}
      style={{ boxShadow: '0 0 6px rgba(96,165,250,0.6)' }} />
  );
  if (status === 'success') return (
    <motion.div
      className={`${base} bg-green-400`}
      initial={{ scale: 1, opacity: 1 }}
      animate={{ scale: [1, 1.5, 1], opacity: [1, 0.6, 1] }}
      transition={{ duration: 0.4 }}
    />
  );
  return (
    <div className={`${base} bg-red-400`}
      style={{ boxShadow: '0 0 6px rgba(248,113,113,0.6)' }} />
  );
}

// 单个胶囊
function ToolCapsule({ tool }: { tool: ToolCall }) {
  const [visible, setVisible] = useState(true);

  // success 状态后 2.5s 自动消失
  useEffect(() => {
    if (tool.status === 'success') {
      const timer = setTimeout(() => setVisible(false), 2500);
      return () => clearTimeout(timer);
    }
  }, [tool.status]);

  if (!visible) return null;

  const label = tool.name.length > 28 ? tool.name.slice(0, 28) + '…' : tool.name;

  return (
    <motion.div
      layout
      initial={{ width: 40, opacity: 0, scale: 0.9 }}
      animate={{ width: 'auto', opacity: 1, scale: 1 }}
      exit={{ width: 40, opacity: 0, scale: 0.9, x: 40 }}
      transition={{ type: 'spring', stiffness: 280, damping: 24 }}
      className="glass-panel px-4 py-2 flex items-center gap-3"
      style={{ height: 36, whiteSpace: 'nowrap', flexShrink: 0 }}
    >
      <StatusDot status={tool.status} />
      <AnimatePresence mode="wait">
        {tool.status !== 'success' ? (
          <motion.span
            key="label"
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ duration: 0.15 }}
            className="text-xs font-medium tracking-tight"
            style={{ color: 'var(--apple-text)', fontFamily: 'SF Mono, JetBrains Mono, Consolas, monospace' }}
          >
            {label}
          </motion.span>
        ) : (
          <motion.span
            key="done"
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 0.6, x: 0 }}
            className="text-xs"
            style={{ color: 'var(--apple-text-secondary)', fontFamily: 'SF Mono, JetBrains Mono, Consolas, monospace' }}
          >
            ✓ {label}
          </motion.span>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export default function ToolChainBridge({ tools }: ToolChainBridgeProps) {
  const activeTools = tools.filter(t => t.status !== 'idle');

  if (activeTools.length === 0) return null;

  return (
    <div className="flex items-center gap-3 px-4">
      <AnimatePresence>
        {activeTools.map(tool => (
          <ToolCapsule
            key={tool.id}
            tool={tool}
            />
        ))}
      </AnimatePresence>
    </div>
  );
}
