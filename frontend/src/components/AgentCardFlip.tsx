import { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useAgentStore } from '../store/useAgentStore';
import { CardContent, ExpertType } from './CardContent';
import { ThinkingStream } from './ThinkingStream';

// ============================================================
// Types & Constants
// ============================================================

type FlipPhase = 'idle' | 'stacking' | 'flipped' | 'morphing' | 'orbMoving' | 'cardsLanding' | 'cardsLanded' | 'streaming';

interface Offset {
  x: number;
  y: number;
}

interface OrbOffset extends Offset {
  scale: number;
}

const CARD_W = 130;
const CARD_H = 175;
const CARD_GAP = 12;
const TOTAL_SPREAD = CARD_H * 3 + CARD_GAP * 2;
const STACK_TOP = (TOTAL_SPREAD - CARD_H) / 2;
const ORB_SCALE = 0.72;
const ORB_FINAL_SIZE = 46;

const EXPERT_TYPES: ExpertType[] = ['tactics', 'strategy', 'engine'];

const EXPERT_DETAILS = {
  tactics: { rank: 'K', suit: '♥', color: '#dc2626', glowColor: 'rgba(220,38,38,0.35)', gradientFrom: 'rgba(255,180,180,0.18)', gradientTo: 'rgba(220,38,38,0.08)', rotation: -5 },
  strategy: { rank: 'J', suit: '♠', color: '#1a1a1a', glowColor: 'rgba(200,200,200,0.3)', gradientFrom: 'rgba(220,220,220,0.15)', gradientTo: 'rgba(150,150,150,0.06)', rotation: 0 },
  engine: { rank: 'Q', suit: '♦', color: '#2563eb', glowColor: 'rgba(37,99,235,0.35)', gradientFrom: 'rgba(180,210,255,0.18)', gradientTo: 'rgba(37,99,235,0.08)', rotation: 5 },
} as const;

const ANIMATION_STYLES = `
@keyframes liquid-shimmer { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
@keyframes orb-aura-pulse { 0%,100%{opacity:0.5;transform:scale(1)} 50%{opacity:0.9;transform:scale(1.12)} }
@keyframes orb-breathe { 0%,100%{transform:scale(1)} 50%{transform:scale(1.05)} }
@keyframes orb-inner-cw  { from{transform:rotate(0deg)}  to{transform:rotate(360deg)}  }
@keyframes orb-inner-ccw { from{transform:rotate(0deg)}  to{transform:rotate(-360deg)} }

@keyframes border-spin {
  from { transform: translate(-50%,-50%) rotate(0deg);   }
  to   { transform: translate(-50%,-50%) rotate(360deg); }
}

@keyframes stream-caret { 0%, 48% { opacity: 1 } 52%, 100% { opacity: 0 } }
`;

// ============================================================
// 辅助函数
// ============================================================

const getCenter = (el: HTMLElement | null): Offset => {
  if (!el) return { x: 0, y: 0 };
  const rect = el.getBoundingClientRect();
  return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
};

const ExpertHoverStream: React.FC<{ expert: ExpertType; color: string }> = ({ expert, color }) => {
  const expertState = useAgentStore((state) => state.experts[expert]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const isThinking = expertState.status === 'thinking';
  // 直接显示 thinkingContent，不做任何打字机延迟
  const rawText = expertState.thinkingContent || expertState.finding || '';
  const displayText = rawText || (isThinking ? '正在组织分析路径...' : '');

  // 内容更新时自动滚到底部
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [displayText]);

  return (
    <div style={{ position: 'relative', minHeight: 160, borderRadius: 12, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', overflow: 'hidden' }}>
      <div
        ref={scrollRef}
        style={{
          maxHeight: 220,
          overflowY: 'auto',
          padding: '12px 12px 18px',
          fontSize: 12,
          color: 'rgba(255,255,255,0.86)',
          fontFamily: '"Noto Serif SC", serif',
          lineHeight: 1.75,
          whiteSpace: 'pre-wrap',
          maskImage: 'linear-gradient(to bottom, transparent 0, black 16px, black calc(100% - 28px), transparent 100%)',
          WebkitMaskImage: 'linear-gradient(to bottom, transparent 0, black 16px, black calc(100% - 28px), transparent 100%)',
        }}
      >
        {displayText}
        {isThinking && (
          <motion.span
            animate={{ opacity: [1, 0] }}
            transition={{ duration: 0.6, repeat: Infinity, ease: 'linear' }}
            style={{ display: 'inline-block', width: 1.5, height: 12, background: color, marginLeft: 1, verticalAlign: 'middle', animation: 'stream-caret 0.9s step-end infinite' }}
          />
        )}
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: 46, pointerEvents: 'none', background: 'linear-gradient(180deg, rgba(30,25,35,0) 0%, rgba(30,25,35,0.78) 65%, rgba(30,25,35,0.94) 100%)' }} />
    </div>
  );
};

// ============================================================
// ExpertGlassPanel
// ============================================================

export const ExpertGlassPanelFlip: React.FC<{ expert: ExpertType; cardRect: DOMRect }> = ({ expert, cardRect }) => {
  const d = {
    tactics: { rank: 'K', suit: '♥', color: '#dc2626', glowColor: 'rgba(220,38,38,0.35)', gradientFrom: 'rgba(255,180,180,0.18)', gradientTo: 'rgba(220,38,38,0.08)', badge: '⚔️', name: '战术专家', tagline: '棋子攻防 · 战术组合', abilities: ['分析棋子间的攻防关系', '识别将军与抽将威胁', '计算吃子方案与兑子策略', '寻找组合拳与精妙妙手'] },
    strategy: { rank: 'J', suit: '♠', color: '#1a1a1a', glowColor: 'rgba(200,200,200,0.3)', gradientFrom: 'rgba(220,220,220,0.15)', gradientTo: 'rgba(150,150,150,0.06)', badge: '🎯', name: '战略专家', tagline: '全局态势 · 战略布局', abilities: ['评估全局子力平衡', '把控局面节奏与方向', '分析战略目标与计划', '权衡得失与长期优势'] },
    engine: { rank: 'Q', suit: '♦', color: '#2563eb', glowColor: 'rgba(37,99,235,0.35)', gradientFrom: 'rgba(180,210,255,0.18)', gradientTo: 'rgba(37,99,235,0.08)', badge: '📊', name: '引擎专家', tagline: '深度分析 · 候选走法', abilities: ['搜索最佳候选走法', '计算精确局面评估分', '提供多步深度分析', '量化优劣与胜率预估'] },
  } as const;
  const exp = d[expert];
  const expertState = useAgentStore((state) => state.experts[expert]);
  const hasLiveContent = Boolean(expertState.thinkingContent.trim() || expertState.finding.trim());
  const hoverLabel = expertState.status === 'completed'
    ? (hasLiveContent ? '最终结论' : '分析结果')
    : (hasLiveContent ? '实时思考' : '等待输出');
  const statusLabel = expertState.status === 'completed' ? '已收束' : '流式更新';
  const content = (
    <motion.div
      initial={{ opacity: 0, x: -16, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: -16, scale: 0.95 }}
      transition={{ type: 'spring', stiffness: 300, damping: 26, mass: 0.85 }}
      style={{ position: 'fixed', left: cardRect.left - 296, top: cardRect.top, width: 280, padding: '16px 18px', zIndex: 99999, background: 'rgba(30,25,35,0.88)', backdropFilter: 'blur(24px) saturate(180%)', WebkitBackdropFilter: 'blur(24px) saturate(180%)', borderRadius: 16, border: '1px solid rgba(255,255,255,0.12)', boxShadow: '0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1)' }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
        <div style={{ width: 40, height: 56, borderRadius: 10, background: `linear-gradient(145deg, ${exp.gradientFrom}, ${exp.gradientTo})`, border: `1px solid ${exp.color}30`, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 2, boxShadow: `0 4px 14px rgba(0,0,0,0.2), 0 0 12px ${exp.glowColor}`, flexShrink: 0, backdropFilter: 'blur(8px)' }}>
          <div style={{ fontSize: 18, fontWeight: 900, color: exp.color, lineHeight: 1 }}>{exp.rank}</div>
          <div style={{ fontSize: 13, color: exp.color, lineHeight: 1 }}>{exp.suit}</div>
        </div>
        <div>
          <div style={{ fontSize: 16, fontWeight: 800, color: 'rgba(255,255,255,0.95)', fontFamily: '"Noto Serif SC", serif', letterSpacing: '0.02em' }}>{exp.name}</div>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.50)', marginTop: 4 }}>{exp.tagline}</div>
        </div>
      </div>
      <div style={{ height: 1, background: `linear-gradient(90deg, transparent, ${exp.color}35, transparent)`, marginBottom: 10 }} />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.48)', letterSpacing: '0.08em' }}>{hoverLabel}</div>
        <div style={{ fontSize: 11, color: exp.color }}>{statusLabel}</div>
      </div>
      <ExpertHoverStream expert={expert} color={exp.color} />
    </motion.div>
  );
  return createPortal(content, document.body);
};

// ============================================================
// 叠卡翻面
// ============================================================

const StackedCards: React.FC<{
  phase: FlipPhase;
  hovered: ExpertType | null;
  onHoverStart: (type: ExpertType) => void;
  onHoverEnd: () => void;
  containerRef: React.RefObject<HTMLDivElement>;
}> = ({ phase, hovered, onHoverStart, onHoverEnd, containerRef }) => {
  const isFlipped = phase === 'flipped' || phase === 'morphing';
  const isMorphing = phase === 'morphing';
  const show = phase === 'idle' || phase === 'stacking' || phase === 'flipped' || phase === 'morphing';

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          ref={containerRef}
          key="stacked"
          animate={{ rotateY: isFlipped ? -180 : 0 }}
          transition={{ type: 'spring', stiffness: 260, damping: 28 }}
          exit={{ scale: 0.5, opacity: 0, transition: { duration: 0.35, ease: [0.4, 0, 1, 1] } }}
          style={{
            transformStyle: 'preserve-3d',
            position: 'absolute',
            top: '50%',
            left: '50%',
            marginLeft: -CARD_W / 2,
            marginTop: -TOTAL_SPREAD / 2,
            width: CARD_W,
            height: TOTAL_SPREAD,
          }}
        >
          {EXPERT_TYPES.map((type, i) => {
            const d = EXPERT_DETAILS[type];
            const isHov = hovered === type;
            const leftNeighbor = i > 0 ? EXPERT_TYPES[i - 1] : null;
            const rightNeighbor = i < EXPERT_TYPES.length - 1 ? EXPERT_TYPES[i + 1] : null;
            const isLeftNeighbor = !isHov && hovered === leftNeighbor;
            const isRightNeighbor = !isHov && hovered === rightNeighbor;
            const isSqueezed = isLeftNeighbor || isRightNeighbor;

            return (
              <motion.div
                key={type}
                data-card={phase === 'idle' ? type : undefined}
                onMouseEnter={() => onHoverStart(type)}
                onMouseLeave={onHoverEnd}
                animate={{
                  y: phase === 'idle' ? i * (CARD_H + CARD_GAP) : STACK_TOP,
                  rotateZ: phase === 'idle' ? (isSqueezed ? (isLeftNeighbor ? 16 : -16) : d.rotation) : 0,
                  scale: phase === 'idle' ? (isSqueezed ? 0.85 : isHov ? 1.18 : 1) : isMorphing ? ORB_SCALE : 0.88,
                  opacity: phase === 'idle' ? (isSqueezed ? 0.45 : isHov ? 1 : 0.9) : 1,
                  zIndex: isHov ? 10 : 1,
                }}
                transition={{ type: 'spring', stiffness: isHov ? 340 : 320, damping: isHov ? 20 : 26, mass: 0.75 }}
                style={{ position: 'absolute', top: 0, left: 0, width: CARD_W, height: CARD_H, transformStyle: 'preserve-3d' }}
              >
                <motion.div
                  animate={{ rotateY: 0, opacity: isFlipped ? 0 : 1 }}
                  transition={{ type: 'spring', stiffness: 280, damping: 30 }}
                  style={{ position: 'absolute', inset: 0, borderRadius: 16, overflow: 'hidden', zIndex: isFlipped ? 1 : 2 }}
                >
                  <CardContent type={type} isHovered={isHov} />
                </motion.div>
                <motion.div
                  animate={{ rotateY: isFlipped ? 0 : 180, opacity: isFlipped ? 1 : 0 }}
                  transition={{ rotateY: { type: 'spring', stiffness: 280, damping: 30 }, opacity: { duration: 0.3 } }}
                  style={{ position: 'absolute', inset: 0, overflow: 'hidden', zIndex: isFlipped ? 2 : 1 }}
                >
                  <div style={{
                    position: 'absolute', inset: 0,
                    borderRadius: isMorphing ? '50%' : 16,
                    background: 'linear-gradient(135deg, rgba(96,165,250,0.25) 0%, rgba(167,139,250,0.2) 25%, rgba(244,114,182,0.18) 50%, rgba(251,191,36,0.15) 75%, rgba(96,165,250,0.25) 100%)',
                    backdropFilter: 'blur(20px) saturate(180%)', WebkitBackdropFilter: 'blur(20px) saturate(180%)',
                    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.4), inset 0 -1px 0 rgba(0,0,0,0.1), inset 1px 0 0 rgba(255,255,255,0.2), inset -1px 0 0 rgba(255,255,255,0.15), 0 4px 16px rgba(0,0,0,0.2), 0 0 16px rgba(167,139,250,0.12)',
                    transition: 'border-radius 0.5s cubic-bezier(0.34,1.56,0.64,1)',
                  }}>
                    <div style={{
                      position: 'absolute', inset: 0, borderRadius: isMorphing ? '50%' : 16,
                      background: 'conic-gradient(from 0deg at 50% 50%, #60a5fa, #a78bfa, #f472b6, #fbbf24, #60a5fa)',
                      opacity: 0.35, animation: 'liquid-shimmer 3s linear infinite', mixBlendMode: 'overlay',
                      transition: 'border-radius 0.5s cubic-bezier(0.34,1.56,0.64,1)',
                    }} />
                  </div>
                </motion.div>
              </motion.div>
            );
          })}
        </motion.div>
      )}
    </AnimatePresence>
  );
};

// ============================================================
// 扑克牌视觉（呼吸光晕 + 立体浮雕）
// ============================================================

const CardVisual: React.FC<{ type: ExpertType; isHovered?: boolean }> = ({ type, isHovered = false }) => {
  const d = EXPERT_DETAILS[type];
  const badge = type === 'tactics' ? '⚔️' : type === 'strategy' ? '🎯' : '📊';
  const name  = type === 'tactics' ? '战术专家' : type === 'strategy' ? '战略专家' : '引擎专家';

  const energy = {
    tactics:  { a:'#ff4060', b:'#ff9020', c:'#ffdd00', rgb:'255,64,96' },
    strategy: { a:'#c8d8ff', b:'#a090ff', c:'#e8c8ff', rgb:'160,144,255' },
    engine:   { a:'#40b0ff', b:'#5060ff', c:'#40e0c0', rgb:'64,160,255' },
  }[type];

  // 浮雕 textShadow 生成器
  const emboss = (colorRgb: string) => `
    0 -1.5px 0 rgba(255,255,255,0.80),
    0 -0.5px 0 rgba(255,255,255,0.50),
    0  0.5px 0 rgba(0,0,0,0.50),
    0  1.5px 0 rgba(0,0,0,0.40),
    0  2.5px 0 rgba(0,0,0,0.28),
    0  3.5px 0 rgba(0,0,0,0.16),
    0  4.5px 6px rgba(0,0,0,0.22),
    0  0 12px rgba(${colorRgb},0.95),
    0  0 28px rgba(${colorRgb},0.60),
    0  0 48px rgba(${colorRgb},0.30)
  `;

  return (
    // 外壳：负责呼吸光晕（box-shadow 直接作用在这里）
    <div style={{
      width: '100%',
      height: '100%',
      borderRadius: 16,
      position: 'relative',
      transition: 'filter 0.3s ease',
      filter: isHovered ? 'brightness(1.15)' : 'brightness(1)',
      willChange: 'transform, filter',
      transform: 'translateZ(0)',
    }}>

      {/* iOS 26 液态玻璃：彩虹边缘折射光 */}
      <div style={{
        position: 'absolute',
        inset: 0,
        borderRadius: 16,
        padding: '1.5px',
        background: `linear-gradient(135deg,
          rgba(255,255,255,0.70) 0%,
          rgba(200,220,255,0.55) 20%,
          rgba(220,200,255,0.45) 40%,
          rgba(255,200,220,0.40) 60%,
          rgba(200,255,240,0.45) 80%,
          rgba(255,255,255,0.60) 100%
        )`,
        WebkitMask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
        mask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
        WebkitMaskComposite: 'xor',
        maskComposite: 'exclude',
        pointerEvents: 'none',
        zIndex: 1,
      }} />

      {/* 玻璃主体 */}
      <div style={{
        position: 'absolute',
        inset: '2px',
        borderRadius: '14px',
        background: `linear-gradient(180deg,
          rgba(255,255,255,0.18) 0%,
          rgba(255,255,255,0.08) 30%,
          rgba(255,255,255,0.04) 60%,
          rgba(0,0,0,0.06) 100%
        )`,
        backdropFilter: 'blur(24px) saturate(200%)',
        WebkitBackdropFilter: 'blur(24px) saturate(200%)',
        boxShadow: `
          /* 内层湿润高光 - 3层 */
          inset 0  2px 0 rgba(255,255,255,0.65),
          inset 0  4px 8px rgba(200,220,255,0.18),
          inset 0  8px 16px rgba(180,200,255,0.08),
          /* 边缘 */
          inset 0 -1.5px 0 rgba(0,0,0,0.20),
          inset  1px 0 0 rgba(255,255,255,0.20),
          inset -1px 0 0 rgba(0,0,0,0.12)
        `,
        zIndex: 2,
        overflow: 'hidden',
      }}>

        {/* 顶部折射高光 - 更亮更润 */}
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0, height: '55%',
          background: `linear-gradient(180deg,
            rgba(255,255,255,0.32) 0%,
            rgba(200,220,255,0.18) 30%,
            rgba(255,255,255,0.05) 60%,
            transparent 100%
          )`,
          borderRadius: '13px 13px 60% 60% / 13px 13px 30% 30%',
          pointerEvents: 'none',
        }} />

        {/* 左上角光源光斑 */}
        <div style={{
          position: 'absolute', top: 0, left: 0, width: '60%', height: '45%',
          background: `radial-gradient(ellipse 80% 100% at 15% 0%,
            rgba(255,255,255,0.35) 0%,
            rgba(200,220,255,0.15) 40%,
            transparent 70%
          )`,
          pointerEvents: 'none',
        }} />

        {/* 右下暗角 */}
        <div style={{
          position: 'absolute', bottom: 0, right: 0, width: '55%', height: '40%',
          background: `radial-gradient(ellipse at 100% 100%, rgba(0,0,0,0.22) 0%, transparent 70%)`,
          pointerEvents: 'none',
        }} />

        {/* 左上角标 */}
        <div style={{ position: 'absolute', top: 7, left: 8, display: 'flex', flexDirection: 'column', alignItems: 'center', zIndex: 5 }}>
          <div style={{
            fontSize: 16, fontWeight: 900, lineHeight: 1,
            fontFamily: '"Georgia", serif',
            color: energy.a,
            textShadow: emboss(energy.rgb),
          }}>{d.rank}</div>
          <div style={{
            fontSize: 10, lineHeight: 1, marginTop: 2,
            color: energy.a,
            textShadow: `0 1px 2px rgba(0,0,0,0.6), 0 0 8px rgba(${energy.rgb},0.9)`,
          }}>{d.suit}</div>
        </div>

        {/* 右上 badge */}
        <div style={{
          position: 'absolute', top: 6, right: 7, fontSize: 14, zIndex: 5,
          filter: `drop-shadow(0 2px 3px rgba(0,0,0,0.55)) drop-shadow(0 0 7px rgba(${energy.rgb},0.8))`,
        }}>{badge}</div>

        {/* 中央花色大字 */}
        <div style={{
          position: 'absolute', top: '50%', left: '50%',
          transform: 'translate(-50%, -52%)',
          fontSize: 56, lineHeight: 1, userSelect: 'none', zIndex: 5,
          color: energy.a,
          textShadow: emboss(energy.rgb),
        }}>{d.suit}</div>

        {/* 底部名称 */}
        <div style={{
          position: 'absolute', bottom: 6, left: 0, right: 0,
          textAlign: 'center', fontSize: 10, fontWeight: 700,
          color: 'rgba(255,255,255,0.75)',
          fontFamily: '"Noto Serif SC", serif', letterSpacing: '0.06em',
          zIndex: 5,
          textShadow: `0 1px 0 rgba(0,0,0,0.5), 0 0 8px rgba(${energy.rgb},0.7)`,
        }}>{name}</div>

        {/* 右下角标倒置 */}
        <div style={{
          position: 'absolute', bottom: 7, right: 8,
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          transform: 'rotate(180deg)', zIndex: 5,
        }}>
          <div style={{
            fontSize: 16, fontWeight: 900, lineHeight: 1,
            fontFamily: '"Georgia", serif', color: energy.a,
            textShadow: `0 -1px 0 rgba(255,255,255,0.75), 0 1px 0 rgba(0,0,0,0.55), 0 2px 0 rgba(0,0,0,0.38), 0 3px 3px rgba(0,0,0,0.20), 0 0 8px rgba(${energy.rgb},0.9)`,
          }}>{d.rank}</div>
          <div style={{
            fontSize: 10, lineHeight: 1, marginTop: 2, color: energy.a,
            textShadow: `0 1px 2px rgba(0,0,0,0.6), 0 0 6px rgba(${energy.rgb},0.8)`,
          }}>{d.suit}</div>
        </div>

      </div>
    </div>
  );
};

// ============================================================
// 球体视觉
// ============================================================

const OrbVisual: React.FC<{ size: number }> = ({ size }) => {
  const s = size / 46;
  return (
    <div style={{ width: size, height: size, borderRadius: '50%', position: 'relative' }}>
      <div style={{ position: 'absolute', inset: -12 * s, borderRadius: '50%', background: 'radial-gradient(circle, rgba(167,139,250,0.35) 0%, transparent 70%)', filter: `blur(${9 * s}px)`, animation: 'orb-aura-pulse 2.5s ease-in-out infinite', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', inset: 0, borderRadius: '50%', background: 'conic-gradient(from 0deg, #60a5fa, #a78bfa, #f472b6, #fbbf24, #60a5fa)', boxShadow: `inset ${-5 * s}px ${-5 * s}px ${14 * s}px rgba(0,0,0,0.3), inset ${5 * s}px ${5 * s}px ${14 * s}px rgba(255,255,255,0.15)`, filter: `drop-shadow(0 0 ${10 * s}px rgba(167,139,250,0.48)) drop-shadow(0 0 ${18 * s}px rgba(96,165,250,0.26))`, animation: 'orb-breathe 2.5s ease-in-out infinite', pointerEvents: 'none', willChange: 'transform' }} />
      <div style={{ position: 'absolute', inset: 5 * s, borderRadius: '50%', background: 'conic-gradient(from 180deg, transparent 30%, rgba(255,255,255,0.28) 50%, transparent 70%)', animation: 'orb-inner-cw 4s linear infinite', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', inset: 10 * s, borderRadius: '50%', background: 'conic-gradient(from 0deg, transparent 40%, rgba(167,139,250,0.38) 55%, transparent 70%)', animation: 'orb-inner-ccw 6s linear infinite', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', inset: 16 * s, borderRadius: '50%', background: 'radial-gradient(circle at 35% 35%, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0.3) 50%, transparent 70%)', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', inset: 0, borderRadius: '50%', background: 'linear-gradient(135deg, rgba(255,255,255,0.4) 0%, transparent 40%)', pointerEvents: 'none' }} />
    </div>
  );
};

// ============================================================
// 左右分栏布局（使用计算出的偏移量）
// 始终渲染以提供 ref，通过 animate 控制动画
// ============================================================

const SplitLayout: React.FC<{
  phase: FlipPhase;
  hovered: ExpertType | null;
  onHoverStart: (type: ExpertType) => void;
  onHoverEnd: () => void;
  orbInitialOffset: OrbOffset;
  cardsInitialOffset: Offset[];
  orbFinalRef: React.RefObject<HTMLDivElement>;
  cardsFinalRef: React.RefObject<HTMLDivElement>;
  offsetsReady: boolean;
}> = ({ phase, hovered, onHoverStart, onHoverEnd, orbInitialOffset, cardsInitialOffset, orbFinalRef, cardsFinalRef, offsetsReady }) => {
  // 动画阶段：orbMoving 之后才开始动画
  const isActive = phase === 'orbMoving' || phase === 'cardsLanding' || phase === 'cardsLanded' || phase === 'streaming';
  const isSettled = phase === 'cardsLanded' || phase === 'streaming';
  const showThinkingPane = phase === 'cardsLanding' || isSettled;

  // 只有在 isActive 且 offsetsReady 时才动画到终点
  const shouldAnimate = isActive && offsetsReady;

  return (
    <motion.div
      initial={false}
      animate={{ opacity: isActive ? 1 : 0 }}
      transition={{ duration: 0.2 }}
      style={{ position: 'absolute', inset: 0, display: 'flex', gap: 0, pointerEvents: isActive ? 'auto' : 'none', padding: '12px 14px 14px' }}
    >
          {/* 左侧：三专家扑克牌 */}
          <div style={{ width: '40%', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '8px 0 8px 2px' }}>
            <div ref={cardsFinalRef} style={{ display: 'flex', flexDirection: 'column', gap: CARD_GAP, justifyContent: 'center', alignItems: 'center' }}>
              {EXPERT_TYPES.map((type, i) => (
                <div key={type} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  <motion.div
                    data-card={isSettled ? type : undefined}
                    data-final-card={type}
                    onMouseEnter={() => onHoverStart(type)}
                    onMouseLeave={onHoverEnd}
                    initial={false}
                    animate={{
                      x: shouldAnimate ? 0 : (cardsInitialOffset[i]?.x ?? 0),
                      y: shouldAnimate ? 0 : (cardsInitialOffset[i]?.y ?? 0),
                      scale: shouldAnimate ? 1 : 0.88,
                      rotate: shouldAnimate ? 0 : 0,
                      opacity: shouldAnimate ? 1 : 0,
                    }}
                    transition={{
                      duration: 0.65,
                      delay: i * 0.12,
                      ease: [0.16, 1, 0.3, 1],
                    }}
                    whileHover={{ scale: 1.08 }}
                    style={{ width: CARD_W, height: CARD_H, cursor: 'default', position: 'relative' }}
                  >
                    <CardVisual type={type} isHovered={hovered === type} />
                  </motion.div>
                </div>
              ))}
            </div>
          </div>

          {/* 分隔线 */}
          <motion.div
            initial={false}
            animate={{ opacity: shouldAnimate ? 1 : 0, scaleY: shouldAnimate ? 1 : 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            style={{ width: 1, margin: '20px 8px', background: 'linear-gradient(to bottom, transparent, rgba(255,255,255,0.10), transparent)', alignSelf: 'stretch', transformOrigin: 'top' }}
          />

          {/* 右侧：协调者球 + 思维流 */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '12px 12px', overflow: 'hidden', borderRadius: 18, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
              <motion.div
                ref={orbFinalRef}
                initial={false}
                animate={{
                  scale: shouldAnimate ? 1 : orbInitialOffset.scale,
                  x: shouldAnimate ? 0 : orbInitialOffset.x,
                  y: shouldAnimate ? 0 : orbInitialOffset.y,
                }}
                transition={{ duration: 0.75, ease: [0.16, 1, 0.3, 1] }}
              >
                <OrbVisual size={ORB_FINAL_SIZE} />
              </motion.div>
              <div>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'rgba(255,255,255,0.88)', fontFamily: '"Noto Serif SC", serif', letterSpacing: '0.02em' }}>协调者</div>
                <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.36)', fontFamily: '"Noto Serif SC", serif', marginTop: 2 }}>实时综合分析</div>
              </div>
            </div>

            <motion.div
              initial={false}
              animate={{ scaleY: isSettled ? 1 : 0, opacity: isSettled ? 1 : 0 }}
              transition={{ duration: 0.5, delay: 0.15 }}
              style={{ width: 1, height: 12, background: 'linear-gradient(to bottom, rgba(251,191,36,0.4), rgba(251,191,36,0.08))', marginLeft: 23, transformOrigin: 'top' }}
            />

            <motion.div
              initial={false}
              animate={{ opacity: showThinkingPane ? 1 : 0 }}
              transition={{ duration: 0.24 }}
              style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden', paddingLeft: 2, paddingRight: 2, minHeight: 0 }}
            >
                {showThinkingPane && <ThinkingStream />}
            </motion.div>
          </div>
    </motion.div>
  );
};

// ============================================================
// 主组件
// ============================================================

export const AgentCardFlip: React.FC = () => {
  const { isPanelActive } = useAgentStore();
  const [phase, setPhase] = useState<FlipPhase>('idle');
  const [hovered, setHovered] = useState<ExpertType | null>(null);
  const [cardRect, setCardRect] = useState<DOMRect | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  // refs
  const stackedCardsRef = useRef<HTMLDivElement>(null);
  const orbFinalRef = useRef<HTMLDivElement>(null);
  const cardsFinalRef = useRef<HTMLDivElement>(null);
  const animationStartedRef = useRef(false);

  // 计算出的偏移量
  const [orbInitialOffset, setOrbInitialOffset] = useState<OrbOffset>({ x: 0, y: 0, scale: 2.8 });
  const [cardsInitialOffset, setCardsInitialOffset] = useState<Offset[]>([]);
  const [offsetsCalculated, setOffsetsCalculated] = useState(false);

  // 注入样式
  useEffect(() => {
    if (document.getElementById('agent-card-flip-styles')) return;
    const style = document.createElement('style');
    style.id = 'agent-card-flip-styles';
    style.textContent = ANIMATION_STYLES;
    document.head.appendChild(style);
  }, []);

  const clearTimers = useCallback(() => {
    timerRef.current.forEach(clearTimeout);
    timerRef.current = [];
  }, []);

  // 计算偏移量并启动动画
  useEffect(() => {
    if (!isPanelActive) {
      clearTimers();
      animationStartedRef.current = false;
      setPhase('idle');
      setHovered(null);
      setCardRect(null);
      setOffsetsCalculated(false);
      setOrbInitialOffset({ x: 0, y: 0, scale: 2.8 });
      setCardsInitialOffset([]);
      useAgentStore.getState().setPhase('collapsed' as unknown as import('../store/useAgentStore').AgentAnimationPhase);
      return;
    }

    // 已经启动过，不重复执行
    if (animationStartedRef.current) return;
    animationStartedRef.current = true;

    // 等待 DOM 渲染完成后计算偏移
    requestAnimationFrame(() => {
      const stackCenter = getCenter(stackedCardsRef.current);
      const orbCenter = getCenter(orbFinalRef.current);

      // 计算球的偏移
      const orbOffset: OrbOffset = {
        x: stackCenter.x - orbCenter.x,
        y: stackCenter.y - orbCenter.y,
        scale: CARD_H / ORB_FINAL_SIZE, // 叠卡高度 → 球尺寸
      };
      setOrbInitialOffset(orbOffset);

      // 计算每张牌的偏移
      if (cardsFinalRef.current) {
        const cardEls = cardsFinalRef.current.querySelectorAll('[data-final-card]');
        const offsets = Array.from(cardEls).map(el => {
          const cardCenter = getCenter(el as HTMLElement);
          return {
            x: stackCenter.x - cardCenter.x,
            y: stackCenter.y - cardCenter.y,
          };
        });
        setCardsInitialOffset(offsets);
      }

      setOffsetsCalculated(true);

      // 启动 timer 链
      const timers: ReturnType<typeof setTimeout>[] = [];
      timers.push(setTimeout(() => setPhase('stacking'), 60));
      timers.push(setTimeout(() => setPhase('flipped'), 240));
      timers.push(setTimeout(() => setPhase('morphing'), 320));
      timers.push(setTimeout(() => setPhase('orbMoving'), 520));
      timers.push(setTimeout(() => setPhase('cardsLanding'), 720));
      timers.push(setTimeout(() => setPhase('cardsLanded'), 930));
      timers.push(setTimeout(() => setPhase('streaming'), 1080));

      // 同步到 store
      const phases: FlipPhase[] = ['idle', 'stacking', 'flipped', 'morphing', 'orbMoving', 'cardsLanding', 'cardsLanded', 'streaming'];
      [60, 240, 320, 520, 720, 930, 1080].forEach((delay, i) => {
        timers.push(setTimeout(() => {
          useAgentStore.getState().setPhase(phases[i + 1] as unknown as import('../store/useAgentStore').AgentAnimationPhase);
        }, delay));
      });

      timerRef.current = timers;
    });
    // 不返回 cleanup，timer 在 !isPanelActive 分支里手动清除
  }, [isPanelActive]);

  const handleHoverStart = (type: ExpertType) => {
    if (phase === 'idle' || phase === 'cardsLanding' || phase === 'cardsLanded' || phase === 'streaming') {
      setHovered(type);
      const el = document.querySelector(`[data-card="${type}"]`);
      if (el) setCardRect(el.getBoundingClientRect());
    }
  };

  const handleHoverEnd = () => {
    setHovered(null);
    setCardRect(null);
  };

  return (
    <>
      <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', perspective: 600, position: 'relative', padding: 2 }}>
        <StackedCards
          phase={phase}
          hovered={hovered}
          onHoverStart={handleHoverStart}
          onHoverEnd={handleHoverEnd}
          containerRef={stackedCardsRef}
        />

        <SplitLayout
          phase={phase}
          hovered={hovered}
          onHoverStart={handleHoverStart}
          onHoverEnd={handleHoverEnd}
          orbInitialOffset={orbInitialOffset}
          cardsInitialOffset={cardsInitialOffset}
          orbFinalRef={orbFinalRef}
          cardsFinalRef={cardsFinalRef}
          offsetsReady={offsetsCalculated}
        />
      </div>

      {hovered && cardRect && (phase === 'idle' || phase === 'cardsLanding' || phase === 'cardsLanded' || phase === 'streaming') && (
        <ExpertGlassPanelFlip expert={hovered} cardRect={cardRect} />
      )}
    </>
  );
};

export default AgentCardFlip;
