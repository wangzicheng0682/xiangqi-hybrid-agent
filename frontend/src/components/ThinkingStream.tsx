import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAgentStore } from '../store/useAgentStore';

// ============================================================
// 打字机 Hook
// ============================================================

function useTypewriter(text: string, speed: number = 30, startDelay: number = 0) {
  const [displayed, setDisplayed] = useState('');

  useEffect(() => {
    if (!text) {
      setDisplayed('');
      return;
    }
    setDisplayed('');
    const timer = setTimeout(() => {
      let i = 0;
      const interval = setInterval(() => {
        i++;
        setDisplayed(text.slice(0, i));
        if (i >= text.length) clearInterval(interval);
      }, speed);
      return () => clearInterval(interval);
    }, startDelay);
    return () => clearTimeout(timer);
  }, [text, speed, startDelay]);

  return displayed;
}

// ============================================================
// 思维流单项
// ============================================================

const StreamItem: React.FC<{ text: string; delay: number }> = ({ text, delay }) => {
  const displayed = useTypewriter(text, 25, delay);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1], delay: delay * 0.5 }}
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 8,
        padding: '6px 0',
      }}
    >
      {/* 金色子弹点 */}
      <div style={{
        width: 4,
        height: 4,
        borderRadius: '50%',
        background: 'linear-gradient(135deg, #fbbf24, #f59e0b)',
        boxShadow: '0 0 6px rgba(251,191,36,0.6)',
        marginTop: 8,
        flexShrink: 0,
      }} />
      <span style={{
        fontSize: 12,
        color: 'rgba(255,255,255,0.88)',
        fontFamily: '"Noto Serif SC", "SF Pro Display", serif',
        lineHeight: 1.7,
        letterSpacing: '0.01em',
      }}>
        {displayed}
        {/* 光标 */}
        <motion.span
          animate={{ opacity: [1, 0] }}
          transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
          style={{
            display: 'inline-block',
            width: 1.5,
            height: 12,
            background: 'rgba(251,191,36,0.8)',
            marginLeft: 1,
            verticalAlign: 'middle',
          }}
        />
      </span>
    </motion.div>
  );
};

// ============================================================
// 思维流容器
// ============================================================

interface StreamItemData {
  id: number;
  text: string;
}

export const ThinkingStream: React.FC = () => {
  const { orchestrator } = useAgentStore();
  const [items, setItems] = useState<StreamItemData[]>([]);
  const nextIdRef = useRef(0);

  // 监听 orchestrator.subtitle 变化，追加新项
  useEffect(() => {
    const subtitle = orchestrator.subtitle;
    if (subtitle && subtitle.trim()) {
      setItems(prev => {
        const exists = prev.some(item => item.text === subtitle);
        if (!exists) {
          return [...prev, { id: nextIdRef.current++, text: subtitle }];
        }
        return prev;
      });
    }
  }, [orchestrator.subtitle]);

  // 如果有 content（最终讲解），追加为最后一项
  useEffect(() => {
    const content = orchestrator.content;
    if (content && content.trim()) {
      setItems(prev => {
        const exists = prev.some(item => item.text === content);
        if (!exists) {
          return [...prev, { id: nextIdRef.current++, text: content }];
        }
        return prev;
      });
    }
  }, [orchestrator.content]);

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: 0,
      width: '100%',
    }}>
      <AnimatePresence>
        {items.map((item, index) => (
          <StreamItem
            key={item.id}
            text={item.text}
            delay={index * 0.1}
          />
        ))}
      </AnimatePresence>

      {/* 当没有内容时显示占位提示 */}
      {items.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          style={{
            fontSize: 12,
            color: 'rgba(255,255,255,0.3)',
            fontFamily: '"Noto Serif SC", serif',
            textAlign: 'center',
            padding: '20px 0',
          }}
        >
          协调者正在分析...
        </motion.div>
      )}
    </div>
  );
};

export default ThinkingStream;
