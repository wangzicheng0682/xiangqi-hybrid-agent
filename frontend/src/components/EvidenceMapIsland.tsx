import { motion, AnimatePresence } from 'framer-motion';
import { useMemo } from 'react';
import { useAgentStore } from '../store/useAgentStore';

const EXPERT_META = {
  tactics: { label: '战术', color: '#ff7b72' },
  strategy: { label: '战略', color: '#fbbf24' },
  engine: { label: '引擎', color: '#7cc4ff' },
} as const;

const TOOL_LABELS: Record<string, string> = {
  engine_deep_analysis: '深度算路',
  engine_alternatives: '候选着法',
  analyze_move: '走法分析',
  compare_moves: '走法对比',
  simulate_move: '局面推演',
  query_chess_principles: '棋理原则',
  search_chess_knowledge: '知识检索',
  get_forcing_sequence: '强制序列',
  get_candidate_moves: '候选列表',
};

function toToolLabel(raw: string) {
  if (!raw) return '工具调用';

  for (const [key, value] of Object.entries(TOOL_LABELS)) {
    if (raw.includes(key)) {
      return value;
    }
  }

  if (raw.includes('engine')) return '引擎计算';
  if (raw.includes('search')) return '知识检索';
  if (raw.includes('simulate')) return '局面推演';
  if (raw.includes('principle')) return '棋理原则';
  if (raw.includes('compare')) return '走法对比';

  return raw.length > 14 ? `${raw.slice(0, 14)}…` : raw;
}

function parseTime(id: string) {
  const first = Number((id || '').split('-')[0]);
  return Number.isFinite(first) ? first : 0;
}

export default function EvidenceMapIsland() {
  const experts = useAgentStore((state) => state.experts);
  const orchestrator = useAgentStore((state) => state.orchestrator);
  const isAnalyzing = useAgentStore((state) => state.isAnalyzing);

  const toolFeed = useMemo(() => {
    return (Object.entries(experts) as Array<[keyof typeof experts, (typeof experts)[keyof typeof experts]]>)
      .flatMap(([expert, state]) =>
        state.toolCalls.map((toolCall) => ({
          id: toolCall.id,
          expert,
          label: toToolLabel(toolCall.toolName),
          raw: toolCall.toolName,
          result: toolCall.result,
          ts: parseTime(toolCall.id),
        }))
      )
      .sort((a, b) => b.ts - a.ts)
      .slice(0, 6);
  }, [experts]);

  const liveFeed = useMemo(() => {
    return (Object.entries(experts) as Array<[keyof typeof experts, (typeof experts)[keyof typeof experts]]>)
      .map(([expert, state]) => {
        const latestStep = state.steps[state.steps.length - 1];
        const latestText = latestStep?.content || state.subtitle || state.thinkingContent || '';
        return {
          expert,
          label: EXPERT_META[expert].label,
          status: state.status,
          text: latestText.trim(),
        };
      })
      .filter((item) => item.status === 'thinking' && item.text)
      .slice(0, 3);
  }, [experts]);

  const dispatchLabel = useMemo(() => {
    if (!orchestrator.subtitles.length) {
      return isAnalyzing ? '调度建立中' : 'Evidence Map 待命';
    }
    return orchestrator.subtitles[orchestrator.subtitles.length - 1];
  }, [isAnalyzing, orchestrator.subtitles]);

  const stagePulse = useMemo(() => {
    const hasStrategySignal = toolFeed.some((item) => item.expert === 'strategy') || dispatchLabel.includes('开局') || dispatchLabel.includes('调度');
    const hasEngineSignal = toolFeed.some((item) => item.expert === 'engine') || dispatchLabel.includes('评估');
    const hasSynthesisSignal = Boolean(orchestrator.steps.length || orchestrator.content.trim());

    return [
      { label: '识别', active: isAnalyzing },
      { label: '棋理', active: hasStrategySignal },
      { label: '评估', active: hasEngineSignal },
      { label: '综合', active: hasSynthesisSignal },
    ];
  }, [dispatchLabel, isAnalyzing, orchestrator.content, orchestrator.steps.length, toolFeed]);

  return (
    <div
      style={{
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        pointerEvents: 'none',
      }}
    >
      <motion.section
        initial={false}
        animate={{
          opacity: isAnalyzing ? 1 : 0.72,
          scale: isAnalyzing ? 1 : 0.96,
          y: isAnalyzing ? 0 : 8,
        }}
        transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
        style={{
          width: 142,
          minHeight: 318,
          maxHeight: '76vh',
          borderRadius: 26,
          padding: '14px 11px',
          display: 'flex',
          flexDirection: 'column',
          gap: 11,
          pointerEvents: 'auto',
          background: 'linear-gradient(180deg, rgba(246,250,255,0.24) 0%, rgba(202,230,255,0.16) 22%, rgba(110,176,255,0.12) 100%)',
          border: '1px solid rgba(255,255,255,0.18)',
          boxShadow: '0 16px 42px rgba(15, 38, 70, 0.20), inset 0 1px 0 rgba(255,255,255,0.24)',
          backdropFilter: 'blur(16px) saturate(150%)',
          WebkitBackdropFilter: 'blur(16px) saturate(150%)',
          contain: 'layout paint style',
          transform: 'translateZ(0)',
          willChange: 'transform, opacity',
        }}
      >
        <div>
          <div style={{ fontSize: 8, color: 'rgba(255,255,255,0.62)', letterSpacing: '0.16em', marginBottom: 5 }}>
            EVIDENCE MAP
          </div>
          <div style={{ fontSize: 15, color: '#ffffff', fontWeight: 700, lineHeight: 1.25 }}>
            实时证据岛
          </div>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
            gap: 6,
          }}
        >
          {stagePulse.map((item) => (
            <div
              key={item.label}
              style={{
                borderRadius: 999,
                padding: '6px 0',
                textAlign: 'center',
                fontSize: 10,
                color: item.active ? '#f8fdff' : 'rgba(255,255,255,0.46)',
                background: item.active ? 'linear-gradient(180deg, rgba(255,255,255,0.20), rgba(255,255,255,0.08))' : 'rgba(255,255,255,0.05)',
                border: `1px solid ${item.active ? 'rgba(255,255,255,0.16)' : 'rgba(255,255,255,0.06)'}`,
                boxShadow: item.active ? 'inset 0 1px 0 rgba(255,255,255,0.12)' : 'none',
              }}
            >
              {item.label}
            </div>
          ))}
        </div>

        <div
          style={{
            borderRadius: 17,
            padding: '9px 10px',
            background: 'linear-gradient(180deg, rgba(255,255,255,0.16), rgba(255,255,255,0.07))',
            border: '1px solid rgba(255,255,255,0.14)',
          }}
        >
          <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.58)', marginBottom: 4 }}>当前调度</div>
          <div style={{ fontSize: 11, color: '#f7fbff', lineHeight: 1.5 }}>
            {dispatchLabel}
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minHeight: 0, flex: 1 }}>
          <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.58)', letterSpacing: '0.12em' }}>
            实时动向
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
            {liveFeed.length > 0 ? liveFeed.map((item) => {
              const meta = EXPERT_META[item.expert];
              return (
                <div
                  key={`live-${item.expert}`}
                  style={{
                    borderRadius: 15,
                    padding: '8px 9px',
                    background: 'linear-gradient(180deg, rgba(255,255,255,0.10), rgba(255,255,255,0.04))',
                    border: '1px solid rgba(255,255,255,0.08)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                    <span style={{ fontSize: 9, color: meta.color }}>{item.label}</span>
                    <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.48)' }}>进行中</span>
                  </div>
                  <div style={{ marginTop: 5, fontSize: 10, color: 'rgba(255,255,255,0.72)', lineHeight: 1.5 }}>
                    {item.text.length > 44 ? `${item.text.slice(0, 44)}…` : item.text}
                  </div>
                </div>
              );
            }) : (
              <div
                style={{
                  borderRadius: 15,
                  padding: '10px 10px',
                  background: 'linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03))',
                  border: '1px solid rgba(255,255,255,0.08)',
                  fontSize: 10,
                  color: 'rgba(255,255,255,0.56)',
                  lineHeight: 1.55,
                }}
              >
                {isAnalyzing ? '协调者正在分发任务，专家的实时步骤会先在这里冒出来。' : '等待分析开始后，这里会先出现专家的实时步骤，再接工具轨迹。'}
              </div>
            )}
          </div>

          <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.58)', letterSpacing: '0.12em' }}>
            工具活动
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, overflowY: 'auto', paddingRight: 2 }}>
            <AnimatePresence initial={false}>
              {toolFeed.length > 0 ? (
                toolFeed.map((item) => {
                  const meta = EXPERT_META[item.expert];
                  return (
                    <motion.div
                      key={item.id}
                      initial={{ opacity: 0, y: 12, scale: 0.94 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: -8, scale: 0.96 }}
                      transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
                      style={{
                        borderRadius: 17,
                        padding: '9px 10px',
                        background: 'linear-gradient(180deg, rgba(255,255,255,0.12), rgba(255,255,255,0.05))',
                        border: '1px solid rgba(255,255,255,0.10)',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginBottom: 6 }}>
                        <span
                          style={{
                            fontSize: 9,
                            color: meta.color,
                            padding: '2px 6px',
                            borderRadius: 999,
                            background: 'rgba(255,255,255,0.08)',
                            border: '1px solid rgba(255,255,255,0.08)',
                          }}
                        >
                          {meta.label}
                        </span>
                        <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.54)' }}>
                          {item.result ? '已返回' : '调用中'}
                        </span>
                      </div>
                      <div style={{ fontSize: 11, color: '#ffffff', fontWeight: 600, lineHeight: 1.32 }}>
                        {item.label}
                      </div>
                      <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.54)', marginTop: 4, lineHeight: 1.4 }}>
                        {item.result
                          ? (item.result.length > 30 ? `${item.result.slice(0, 30)}…` : item.result)
                          : '等待工具结果'}
                      </div>
                    </motion.div>
                  );
                })
              ) : (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  style={{
                    borderRadius: 17,
                    padding: '13px 11px',
                    background: 'linear-gradient(180deg, rgba(255,255,255,0.10), rgba(255,255,255,0.03))',
                    border: '1px solid rgba(255,255,255,0.10)',
                    fontSize: 10,
                    color: 'rgba(255,255,255,0.58)',
                    lineHeight: 1.6,
                  }}
                >
                  {isAnalyzing ? '当前先展示调度脉冲，工具与证据会沿着这里连续浮现。' : '点击深度分析后，这里会先亮起调度脉冲，再接入实时工具轨迹。'}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </motion.section>
    </div>
  );
}