import { useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { useAgentStore } from '../store/useAgentStore';
import type { ExpertType } from '../components/ExpertCard';

// ============================================================
// 打字机 Hook
// ============================================================

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
}> = ({ title, content, status, durationMs }) => {
  // 内容已由SSE增量推送，无需typewriter（typewriter会在每次chunk到来时重置导致闪烁）
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
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: content ? 6 : 0 }}>
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
      {content ? (
        <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.78)', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
          {content}
          {isActive && (
            <motion.span
              animate={{ opacity: [1, 0] }}
              transition={{ duration: 0.7, repeat: Infinity, ease: 'linear' }}
              style={{ display: 'inline-block', width: 1.5, height: 11, background: 'rgba(251,191,36,0.8)', marginLeft: 1, verticalAlign: 'middle' }}
            />
          )}
        </div>
      ) : null}
    </motion.div>
  );
};

// ============================================================
// 专家进度概览（协调者等待阶段）
// ============================================================

const EXPERT_META: Record<ExpertType, { icon: string; name: string; color: string }> = {
  tactics: { icon: '⚔️', name: '战术专家', color: '#dc2626' },
  strategy: { icon: '🎯', name: '战略专家', color: '#a0a0a0' },
  engine: { icon: '📊', name: '引擎专家', color: '#2563eb' },
};

const ExpertProgressOverview: React.FC = () => {
  const experts = useAgentStore((s) => s.experts);
  const expertTypes: ExpertType[] = ['tactics', 'strategy', 'engine'];
  const completedCount = expertTypes.filter((t) => experts[t].status === 'completed').length;
  const allDone = completedCount === 3;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, width: '100%' }}>
      <div style={{
        borderRadius: 14,
        border: '1px solid rgba(255,255,255,0.08)',
        background: 'linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02))',
        padding: '14px 16px',
      }}>
        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 10, letterSpacing: '0.08em' }}>
          {allDone ? '专家分析完成 · 协调者综合中' : '专家分析进行中'}
        </div>

        {/* 进度条 */}
        <div style={{ height: 3, borderRadius: 2, background: 'rgba(255,255,255,0.06)', marginBottom: 14, overflow: 'hidden' }}>
          <motion.div
            animate={{ width: `${(completedCount / 3) * 100}%` }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            style={{ height: '100%', borderRadius: 2, background: allDone ? '#86efac' : 'linear-gradient(90deg, #fbbf24, #f59e0b)' }}
          />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {expertTypes.map((type) => {
            const meta = EXPERT_META[type];
            const state = experts[type];
            const isCompleted = state.status === 'completed';
            const isThinking = state.status === 'thinking';
            const statusText = isCompleted
              ? '已完成'
              : isThinking
                ? (state.subtitle || '分析中...')
                : '等待中';

            return (
              <motion.div
                key={type}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3 }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '8px 10px',
                  borderRadius: 10,
                  background: isThinking ? 'rgba(251,191,36,0.05)' : 'rgba(255,255,255,0.02)',
                  border: `1px solid ${isThinking ? 'rgba(251,191,36,0.15)' : 'rgba(255,255,255,0.04)'}`,
                }}
              >
                <span style={{ fontSize: 14, flexShrink: 0 }}>{meta.icon}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'rgba(255,255,255,0.85)' }}>
                    {meta.name}
                  </div>
                  <div style={{
                    fontSize: 11,
                    color: isCompleted ? '#86efac' : 'rgba(255,255,255,0.4)',
                    marginTop: 2,
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}>
                    {statusText}
                    {isThinking && (
                      <motion.span
                        animate={{ opacity: [1, 0.3] }}
                        transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
                      >
                        ...
                      </motion.span>
                    )}
                  </div>
                </div>
                <span style={{ fontSize: 11, color: isCompleted ? '#86efac' : 'rgba(255,255,255,0.25)', fontWeight: 700, flexShrink: 0 }}>
                  {isCompleted ? '✓' : isThinking ? '⟳' : '○'}
                </span>
              </motion.div>
            );
          })}
        </div>
      </div>

      {allDone && (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            fontSize: 12,
            color: 'rgba(255,255,255,0.35)',
            textAlign: 'center',
            fontFamily: '"Noto Serif SC", serif',
          }}
        >
          协调者正在综合三位专家结论...
        </motion.div>
      )}
    </div>
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

  // 追踪最后一个step的内容长度，用于自动滚动
  const lastStepContentLen = visibleSteps.length > 0
    ? visibleSteps[visibleSteps.length - 1].content.length
    : 0;

  useEffect(() => {
    if (contentRef.current) {
      contentRef.current.scrollTo({ top: contentRef.current.scrollHeight, behavior: 'smooth' });
    }
  }, [typedStreamingContent, visibleSteps.length, lastStepContentLen]);

  if (visibleSteps.length > 0) {
    return (
      <div ref={contentRef} style={{ display: 'flex', flexDirection: 'column', gap: 10, width: '100%', overflowY: 'auto', minHeight: 0, height: '100%', paddingRight: 2 }}>
        {visibleSteps.map((step) => (
          <StepItem
            key={step.index}
            title={step.title}
            content={step.content}
            status={step.status}
            durationMs={step.durationMs}
            delay={0}
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
            position: 'absolute',
            inset: '0 0 0 0',
            overflowY: 'auto',
            padding: '14px 14px 58px 24px',
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

      {/* 当没有任何协调者内容时，显示专家进度概览 */}
      {!currentSubtitle && (!typedStreamingContent || !typedStreamingContent.trim()) && (
        <ExpertProgressOverview />
      )}
    </div>
  );
};

export default ThinkingStream;
