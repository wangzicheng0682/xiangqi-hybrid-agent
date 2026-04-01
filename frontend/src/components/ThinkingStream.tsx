import { useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
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

function useNaturalTypewriter(text: string, enabled: boolean, startDelay: number = 0, baseSpeed: number = 20) {
  const [displayed, setDisplayed] = useState('');

  useEffect(() => {
    if (!text) {
      setDisplayed('');
      return;
    }
    if (!enabled) {
      setDisplayed(text);
      return;
    }

    let cancelled = false;
    let timeoutId: number | undefined;
    let index = 0;

    const step = () => {
      if (cancelled) return;
      index += 1;
      setDisplayed(text.slice(0, index));
      if (index >= text.length) return;

      const current = text[index - 1];
      let delay = baseSpeed + Math.random() * 18;
      if ('，,；;：:'.includes(current)) delay += 70;
      if ('。！？!?\n'.includes(current)) delay += 180;
      timeoutId = window.setTimeout(step, delay);
    };

    timeoutId = window.setTimeout(step, startDelay);
    return () => {
      cancelled = true;
      if (timeoutId) window.clearTimeout(timeoutId);
    };
  }, [text, enabled, startDelay, baseSpeed]);

  return displayed;
}

// ============================================================
// 思维流单项
// ============================================================

const StepItem: React.FC<{
  title: string;
  content: string;
  status: 'thinking' | 'completed';
  durationMs?: number;
  delay: number;
}> = ({ title, content, status, durationMs, delay }) => {
  const displayed = useTypewriter(content, 18, delay);
  const isActive = status === 'thinking';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
      style={{
        border: `1px solid ${isActive ? 'rgba(251,191,36,0.28)' : 'rgba(255,255,255,0.08)'}`,
        borderRadius: 12,
        background: isActive ? 'rgba(251,191,36,0.06)' : 'rgba(255,255,255,0.03)',
        padding: '10px 12px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: displayed ? 6 : 0 }}>
        <span style={{ color: isActive ? '#fbbf24' : '#86efac', fontWeight: 700, fontSize: 12 }}>
          {isActive ? '⟳' : '✓'}
        </span>
        <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.9)', fontWeight: 600 }}>
          {title}
        </span>
        {durationMs ? (
          <span style={{ marginLeft: 'auto', fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>
            {(durationMs / 1000).toFixed(1)}s
          </span>
        ) : null}
      </div>
      {displayed ? (
        <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.78)', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
          {displayed}
        </div>
      ) : null}
    </motion.div>
  );
};

// ============================================================
// 思维流容器
// ============================================================

export const ThinkingStream: React.FC = () => {
  const { orchestrator } = useAgentStore();
  const contentRef = useRef<HTMLDivElement>(null);
  const visibleSteps = orchestrator.steps;
  // content 直接渲染，不再作为 items 累加（避免流式 chunk 导致重复）
  const streamingContent = orchestrator.content;
  const typedStreamingContent = useNaturalTypewriter(streamingContent, visibleSteps.length === 0, 0, 16);
  const currentSubtitle = useMemo(
    () => orchestrator.subtitle || orchestrator.subtitles[orchestrator.subtitles.length - 1] || '',
    [orchestrator.subtitle, orchestrator.subtitles]
  );

  useEffect(() => {
    if (contentRef.current) {
      contentRef.current.scrollTo({ top: contentRef.current.scrollHeight, behavior: 'smooth' });
    }
  }, [typedStreamingContent, visibleSteps.length]);

  if (visibleSteps.length > 0) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, width: '100%' }}>
        {visibleSteps.map((step, index) => (
          <StepItem
            key={step.index}
            title={step.title}
            content={step.content}
            status={step.status}
            durationMs={step.durationMs}
            delay={index * 80}
          />
        ))}
      </div>
    );
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: 12,
      width: '100%',
      minHeight: 0,
    }}>
      <div style={{
        borderRadius: 14,
        border: '1px solid rgba(255,255,255,0.08)',
        background: 'linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03))',
        boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.10)',
        padding: '12px 14px',
      }}>
        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 6, letterSpacing: '0.08em' }}>
          当前阶段
        </div>
        {currentSubtitle ? (
          <motion.div
            key={currentSubtitle}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            style={{ fontSize: 18, color: '#fbbf24', fontWeight: 700, lineHeight: 1.35, fontFamily: '"Noto Serif SC", serif' }}
          >
            {currentSubtitle}
          </motion.div>
        ) : (
          <div style={{ fontSize: 14, color: 'rgba(255,255,255,0.38)' }}>等待阶段标题...</div>
        )}
        {orchestrator.subtitles.length > 1 ? (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 10 }}>
            {orchestrator.subtitles.slice(-4).map((subtitle) => (
              <span key={subtitle} style={{ fontSize: 11, padding: '4px 8px', borderRadius: 999, background: 'rgba(255,255,255,0.05)', color: subtitle === currentSubtitle ? '#fbbf24' : 'rgba(255,255,255,0.48)' }}>
                {subtitle}
              </span>
            ))}
          </div>
        ) : null}
      </div>

      <div style={{ position: 'relative', minHeight: 180, flex: 1, borderRadius: 18, border: '1px solid rgba(255,255,255,0.05)', background: 'linear-gradient(180deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.015) 100%)', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', top: 14, bottom: 18, left: 14, width: 1, background: 'linear-gradient(180deg, rgba(251,191,36,0.42) 0%, rgba(154,223,255,0.20) 100%)', pointerEvents: 'none' }} />
        <div
          ref={contentRef}
          style={{
            maxHeight: 300,
            overflowY: 'auto',
            padding: '14px 14px 22px 24px',
            maskImage: 'linear-gradient(to bottom, transparent 0, black 18px, black calc(100% - 32px), transparent 100%)',
            WebkitMaskImage: 'linear-gradient(to bottom, transparent 0, black 18px, black calc(100% - 32px), transparent 100%)',
          }}
        >
          {typedStreamingContent && typedStreamingContent.trim() ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              style={{
                fontSize: 13,
                color: 'rgba(255,255,255,0.84)',
                fontFamily: '"Noto Serif SC", "SF Pro Display", serif',
                lineHeight: 1.85,
                letterSpacing: '0.01em',
                whiteSpace: 'pre-wrap',
              }}
            >
              {typedStreamingContent}
              <motion.span
                animate={{ opacity: [1, 0] }}
                transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
                style={{
                  display: 'inline-block',
                  width: 1.5,
                  height: 13,
                  background: 'rgba(251,191,36,0.8)',
                  marginLeft: 1,
                  verticalAlign: 'middle',
                }}
              />
            </motion.div>
          ) : null}
        </div>
        <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: 56, pointerEvents: 'none', background: 'linear-gradient(180deg, rgba(255,255,255,0) 0%, rgba(19,26,37,0.18) 72%, rgba(19,26,37,0.34) 100%)' }} />
      </div>

      {/* 当没有任何内容时显示占位提示 */}
      {!currentSubtitle && (!typedStreamingContent || !typedStreamingContent.trim()) && (
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
