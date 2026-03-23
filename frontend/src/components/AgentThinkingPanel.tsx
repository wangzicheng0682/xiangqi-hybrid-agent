import { useEffect } from 'react';
import { useAgentStore } from '../store/useAgentStore';
import { AgentCardFlip } from './AgentCardFlip';

/**
 * AgentThinkingPanel — 专家扑克牌展示面板
 *
 * 现在只是一个简单的容器，所有动画逻辑都在 AgentCardFlip 内部处理。
 * 动画流程：
 * - idle/stacking/flipped/morphing: 叠卡收叠翻面
 * - orbMoving/cardsLanding: 分栏布局展开
 * - cardsLanded/streaming: 最终稳定状态
 */
export const AgentThinkingPanel: React.FC = () => {
  const { isPanelActive, resetAll } = useAgentStore();

  useEffect(() => {
    if (!isPanelActive) {
      resetAll();
    }
  }, [isPanelActive, resetAll]);

  return (
    <div
      style={{
        height: '100%',
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      <AgentCardFlip />
    </div>
  );
};

export default AgentThinkingPanel;
