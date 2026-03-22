import { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { motion } from 'framer-motion';
import { useAgentStore } from '../store/useAgentStore';

/** 和 CollapsedCardsView 完全一致的数据 */
const EXPERT_DETAILS = {
  tactics: {
    rank: 'K', suit: '♥', color: '#dc2626',
    glowColor: 'rgba(220,38,38,0.35)',
    gradientFrom: 'rgba(255,180,180,0.18)', gradientTo: 'rgba(220,38,38,0.08)',
    badge: '⚔️', name: '战术专家', tagline: '棋子攻防 · 战术组合',
    rotation: -5,
    abilities: ['分析棋子间的攻防关系', '识别将军与抽将威胁', '计算吃子方案与兑子策略', '寻找组合拳与精妙妙手'],
  },
  strategy: {
    rank: 'J', suit: '♠', color: '#1a1a1a',
    glowColor: 'rgba(200,200,200,0.3)',
    gradientFrom: 'rgba(220,220,220,0.15)', gradientTo: 'rgba(150,150,150,0.06)',
    badge: '🎯', name: '战略专家', tagline: '全局态势 · 战略布局',
    rotation: 0,
    abilities: ['评估全局子力平衡', '把控局面节奏与方向', '分析战略目标与计划', '权衡得失与长期优势'],
  },
  engine: {
    rank: 'Q', suit: '♦', color: '#2563eb',
    glowColor: 'rgba(37,99,235,0.35)',
    gradientFrom: 'rgba(180,210,255,0.18)', gradientTo: 'rgba(37,99,235,0.08)',
    badge: '📊', name: '引擎专家', tagline: '深度分析 · 候选走法',
    rotation: 5,
    abilities: ['搜索最佳候选走法', '计算精确局面评估分', '提供多步深度分析', '量化优劣与胜率预估'],
  },
} as const;

type ExpertType = keyof typeof EXPERT_DETAILS;
const EXPERT_TYPES: ExpertType[] = ['tactics', 'strategy', 'engine'];

const CARD_W = 130;
const CARD_H = 175;
const CARD_GAP = 12;
const TOTAL_SPREAD = CARD_H * 3 + CARD_GAP * 2; // 537
const STACK_TOP = (TOTAL_SPREAD - CARD_H) / 2; // 181

type FlipPhase = 'idle' | 'stacking' | 'flipping' | 'flipped';

/** ExpertGlassPanel — 和 CollapsedCardsView 一模一样，弹出详情 */
const ExpertGlassPanel: React.FC<{ expert: ExpertType; cardRect: DOMRect }> = ({ expert, cardRect }) => {
  const d = EXPERT_DETAILS[expert];
  const content = (
    <motion.div
      initial={{ opacity: 0, x: -16, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: -16, scale: 0.95 }}
      transition={{ type: 'spring', stiffness: 300, damping: 26, mass: 0.85 }}
      className={`liquid-glass-popup ${expert}`}
      style={{
        position: 'fixed',
        left: cardRect.left - 296,
        top: cardRect.top,
        width: 280,
        padding: '16px 18px',
        zIndex: 99999,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
        <div style={{
          width: 40, height: 56, borderRadius: 10,
          background: `linear-gradient(145deg, ${d.gradientFrom}, ${d.gradientTo})`,
          border: `1px solid ${d.color}30`,
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 2,
          boxShadow: `0 4px 14px rgba(0,0,0,0.2), 0 0 12px ${d.glowColor}`, flexShrink: 0,
          backdropFilter: 'blur(8px)',
        }}>
          <div style={{ fontSize: 18, fontWeight: 900, color: d.color, lineHeight: 1 }}>{d.rank}</div>
          <div style={{ fontSize: 13, color: d.color, lineHeight: 1 }}>{d.suit}</div>
        </div>
        <div>
          <div style={{ fontSize: 16, fontWeight: 800, color: 'rgba(255,255,255,0.95)', fontFamily: '"Noto Serif SC", serif', letterSpacing: '0.02em' }}>{d.name}</div>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.50)', marginTop: 4 }}>{d.tagline}</div>
        </div>
      </div>
      <div style={{ height: 1, background: `linear-gradient(90deg, transparent, ${d.color}35, transparent)`, marginBottom: 10 }} />
      {d.abilities.map((ability) => (
        <div key={ability} style={{ display: 'flex', alignItems: 'flex-start', gap: 6, fontSize: 12, color: 'rgba(255,255,255,0.85)', fontFamily: '"Noto Serif SC", serif', lineHeight: 1.6, marginBottom: 5 }}>
          <span style={{ color: d.color, fontWeight: 700, flexShrink: 0, marginTop: 2 }}>▸</span>
          <span>{ability}</span>
        </div>
      ))}
    </motion.div>
  );
  return createPortal(content, document.body);
};

/** 牌的正面 — 和 CollapsedCardsView 一模一样，含 hover 光晕 */
const CardFront: React.FC<{ type: ExpertType; isFlipped: boolean; isHovered: boolean }> = ({ type, isFlipped, isHovered }) => {
  const d = EXPERT_DETAILS[type];
  return (
    <motion.div
      animate={{ rotateY: isFlipped ? -180 : 0, opacity: isFlipped ? 0 : 1 }}
      transition={{ type: 'spring', stiffness: 280, damping: 30 }}
      style={{
        position: 'absolute', inset: 0, borderRadius: 16,
        overflow: 'hidden' as const,
        backfaceVisibility: 'hidden' as const,
        WebkitBackfaceVisibility: 'hidden' as const,
      }}
    >
      <div
        className="lg-card"
        data-expert={type}
        style={{
          width: CARD_W, height: CARD_H,
          background: `linear-gradient(145deg, ${d.gradientFrom}, ${d.gradientTo})`,
          outline: '1px solid rgba(255,255,255,0.15)',
          outlineOffset: -1,
          boxShadow: isHovered
            ? `0 16px 40px rgba(0,0,0,0.3), 0 6px 16px rgba(0,0,0,0.15), 0 0 32px ${d.glowColor}, inset 0 1px 0 rgba(255,255,255,0.25), inset 0 -1px 0 rgba(0,0,0,0.1)`
            : `0 8px 24px rgba(0,0,0,0.22), 0 3px 8px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.2), inset 0 -1px 0 rgba(0,0,0,0.08)`,
          backdropFilter: 'blur(12px) saturate(150%)',
          WebkitBackdropFilter: 'blur(12px) saturate(150%)',
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
        }}
      >
        {/* 顶层高光 */}
        <div style={{ position: 'absolute', inset: 0, borderRadius: 16, background: 'radial-gradient(ellipse at 30% 20%, rgba(255,255,255,0.22) 0%, transparent 60%)', pointerEvents: 'none', zIndex: 1 }} />
        {/* 底层暗角 */}
        <div style={{ position: 'absolute', inset: 0, borderRadius: 16, background: 'radial-gradient(ellipse at 70% 80%, rgba(0,0,0,0.12) 0%, transparent 50%)', pointerEvents: 'none', zIndex: 1 }} />

        <div style={{ position: 'absolute', top: 8, right: 10, fontSize: 14, zIndex: 2 }}>{d.badge}</div>
        <div style={{ position: 'absolute', top: 8, left: 10, fontSize: 16, color: d.color, opacity: 0.8, lineHeight: 1, zIndex: 2 }}>{d.suit}</div>
        <div style={{
          fontSize: 54, fontWeight: 900, lineHeight: 1, color: d.color,
          fontFamily: '"SF Pro Display", serif', marginTop: 4,
          textShadow: isHovered ? `0 0 20px ${d.glowColor}, 0 2px 4px rgba(0,0,0,0.2)` : `0 2px 4px rgba(0,0,0,0.15)`,
          zIndex: 2, position: 'relative',
        }}>{d.rank}</div>
        <div style={{ fontSize: 36, color: d.color, lineHeight: 1, opacity: 0.7, zIndex: 2, position: 'relative' }}>{d.suit}</div>
        <div style={{ position: 'absolute', bottom: 28, right: 10, fontSize: 16, color: d.color, opacity: 0.8, lineHeight: 1, transform: 'rotate(180deg)', zIndex: 2 }}>{d.suit}</div>
        <div style={{ position: 'absolute', bottom: 6, left: 0, right: 0, textAlign: 'center', fontSize: 11, fontWeight: 700, color: d.color, opacity: 0.9, fontFamily: '"Noto Serif SC", serif', letterSpacing: '0.02em', zIndex: 2 }}>{d.name}</div>
      </div>
    </motion.div>
  );
};

/** 牌的背面：Apple 彩色流光液态玻璃 */
const CardBack: React.FC<{ isFlipped: boolean }> = ({ isFlipped }) => (
  <motion.div
    animate={{ rotateY: isFlipped ? 0 : 180, opacity: 1 }}
    transition={{ type: 'spring', stiffness: 280, damping: 30 }}
    style={{
      position: 'absolute', inset: 0, borderRadius: 16,
      backfaceVisibility: 'hidden' as const,
      WebkitBackfaceVisibility: 'hidden' as const,
      overflow: 'hidden' as const,
      background: 'linear-gradient(135deg, rgba(96,165,250,0.25) 0%, rgba(167,139,250,0.2) 25%, rgba(244,114,182,0.18) 50%, rgba(251,191,36,0.15) 75%, rgba(96,165,250,0.25) 100%)',
      backdropFilter: 'blur(20px) saturate(180%)',
      WebkitBackdropFilter: 'blur(20px) saturate(180%)',
      boxShadow: `inset 0 1px 0 rgba(255,255,255,0.4), inset 0 -1px 0 rgba(0,0,0,0.1), inset 1px 0 0 rgba(255,255,255,0.2), inset -1px 0 0 rgba(255,255,255,0.15), 0 8px 32px rgba(0,0,0,0.25), 0 0 40px rgba(167,139,250,0.15), 0 0 80px rgba(96,165,250,0.1)`,
    }}
  >
    <div style={{ position: 'absolute', inset: 0, borderRadius: 16, background: 'conic-gradient(from 0deg at 50% 50%, #60a5fa, #a78bfa, #f472b6, #fbbf24, #60a5fa)', opacity: 0.35, animation: 'liquid-shimmer 3s linear infinite', mixBlendMode: 'overlay' }} />
    <div style={{ position: 'absolute', top: 0, left: '10%', right: '10%', height: 1, background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.5), transparent)', zIndex: 2 }} />
    <div style={{ position: 'absolute', top: '30%', left: '50%', transform: 'translate(-50%, -50%)', fontSize: 32, filter: 'drop-shadow(0 0 10px rgba(212,175,55,0.8)) drop-shadow(0 0 24px rgba(167,139,250,0.5))', animation: 'pulse 2.5s ease-in-out infinite', zIndex: 2 }}>♕</div>
    <div style={{ position: 'absolute', top: '55%', left: '50%', transform: 'translate(-50%, -50%)', fontSize: 16, color: '#fbbf24', textShadow: '0 0 12px rgba(251,191,36,0.9)', fontWeight: 700, zIndex: 2 }}>⚡</div>
    <div style={{ position: 'absolute', top: '66%', left: '15%', right: '15%', height: 1, background: 'linear-gradient(90deg, transparent, rgba(212,175,55,0.5), transparent)', zIndex: 2 }} />
    <div style={{ position: 'absolute', bottom: 10, left: 0, right: 0, textAlign: 'center', fontSize: 12, fontWeight: 700, color: '#D4AF37', fontFamily: '"Noto Serif SC", serif', letterSpacing: '0.12em', textShadow: '0 0 14px rgba(212,175,55,0.7), 0 0 28px rgba(251,191,36,0.3)', zIndex: 2 }}>Agent</div>
  </motion.div>
);

export const AgentCardFlip: React.FC = () => {
  const { isPanelActive } = useAgentStore();
  const [phase, setPhase] = useState<FlipPhase>('idle');
  const [hovered, setHovered] = useState<ExpertType | null>(null);
  const [cardRect, setCardRect] = useState<DOMRect | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearTimers = () => {
    timerRef.current.forEach(clearTimeout);
    timerRef.current = [];
  };

  useEffect(() => {
    if (!isPanelActive) {
      clearTimers();
      setPhase('idle');
      setHovered(null);
      setCardRect(null);
      return;
    }
    clearTimers();
    const timers: ReturnType<typeof setTimeout>[] = [];
    timers.push(setTimeout(() => setPhase('stacking'), 100));
    timers.push(setTimeout(() => setPhase('flipping'), 700));
    timers.push(setTimeout(() => setPhase('flipped'), 1100));
    timerRef.current = timers;
    return () => clearTimers();
  }, [isPanelActive]);

  const handleHoverStart = (type: ExpertType) => {
    if (phase === 'idle') {
      setHovered(type);
      const el = document.querySelector(`[data-card="${type}"]`);
      if (el) setCardRect(el.getBoundingClientRect());
    }
  };

  const handleHoverEnd = () => {
    setHovered(null);
    setCardRect(null);
  };

  const isFlipped = phase === 'flipping' || phase === 'flipped';
  // idle 阶段：可用 hover；其余阶段禁用
  const hoverDisabled = phase !== 'idle';

  return (
    <>
      <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', perspective: 600 }}>
        {/* 整体翻转容器 */}
        <motion.div
          animate={{ rotateY: isFlipped ? -180 : 0 }}
          transition={{ type: 'spring', stiffness: 260, damping: 28 }}
          style={{ transformStyle: 'preserve-3d' }}
        >
          {/* 三张卡叠在一起 */}
          <div style={{ position: 'relative', width: CARD_W, height: TOTAL_SPREAD }}>
            {EXPERT_TYPES.map((type, i) => {
              const d = EXPERT_DETAILS[type];
              const isHovered = hovered === type;
              const leftNeighbor = i > 0 ? EXPERT_TYPES[i - 1] : null;
              const rightNeighbor = i < EXPERT_TYPES.length - 1 ? EXPERT_TYPES[i + 1] : null;
              const isLeftNeighbor = !isHovered && hovered === leftNeighbor;
              const isRightNeighbor = !isHovered && hovered === rightNeighbor;
              const isSqueezed = isLeftNeighbor || isRightNeighbor;

              // idle：散开 + hover；其余：叠合
              const idleSpreadTop = i === 0 ? 0 : i * (CARD_H + CARD_GAP);
              const stackTop = STACK_TOP;

              return (
                <motion.div
                  key={type}
                  data-card={type}
                  onMouseEnter={() => !hoverDisabled && handleHoverStart(type)}
                  onMouseLeave={handleHoverEnd}
                  animate={{
                    y: phase === 'idle' ? idleSpreadTop : stackTop,
                    rotateZ: phase === 'idle' ? (isSqueezed ? (isLeftNeighbor ? 16 : -16) : d.rotation) : 0,
                    scale: phase === 'idle'
                      ? (isSqueezed ? 0.85 : isHovered ? 1.18 : 1)
                      : 0.88,
                    opacity: phase === 'idle' ? (isSqueezed ? 0.45 : isHovered ? 1 : 0.9) : 1,
                    zIndex: isHovered ? 10 : 1,
                  }}
                  transition={{
                    type: 'spring',
                    stiffness: isHovered ? 340 : 320,
                    damping: isHovered ? 20 : 26,
                    mass: 0.75,
                  }}
                  style={{
                    position: 'absolute', top: 0, left: 0,
                    width: CARD_W, height: CARD_H,
                    transformStyle: 'preserve-3d',
                  }}
                >
                  <CardFront type={type} isFlipped={isFlipped} isHovered={isHovered} />
                  <CardBack isFlipped={isFlipped} />
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      </div>

      {/* ExpertGlassPanel — 和 CollapsedCardsView 完全一致 */}
      {hovered && cardRect && phase === 'idle' && (
        <ExpertGlassPanel expert={hovered} cardRect={cardRect} />
      )}
    </>
  );
};

export default AgentCardFlip;
