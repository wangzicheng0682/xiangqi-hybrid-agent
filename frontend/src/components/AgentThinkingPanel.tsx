import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { useAgentStore } from '../store/useAgentStore';
import { AgentCardFlip } from './AgentCardFlip';

/**
 * AgentThinkingPanel — 专家扑克牌展示面板
 *
 * 收起状态（260px）：三张 K/J/Q 扑克牌散开显示
 * 扩张状态（620px）：扑克牌收叠翻面
 *
 * 卡片始终渲染，只改变 phase 状态驱动动画
 */
export const AgentThinkingPanel: React.FC = () => {
  const { phase, isPanelActive, resetAll } = useAgentStore();

  // 当面板激活时，触发 AgentCardFlip 内部动画
  useEffect(() => {
    if (!isPanelActive) {
      resetAll();
      return;
    }
    // 不在这里设置 phase，由 AgentCardFlip 自己监听 isPanelActive
  }, [isPanelActive]);

  const isExpanded = phase !== 'collapsed' && phase !== 'idle';

  return (
    <div
      style={{
        height: '100%',
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* ── 面板主体 — 始终渲染 AgentCardFlip，动画在组件内部驱动 ── */}
      <motion.div
        key="panel"
        animate={{ opacity: isExpanded ? 1 : 1 }}
        transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
        style={{ flex: 1, overflow: 'hidden' }}
      >
        <AgentCardFlip />
      </motion.div>
    </div>
  );
};

export default AgentThinkingPanel;
