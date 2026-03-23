import { createPortal } from 'react-dom';
import { motion } from 'framer-motion';

/** 专家详情内容 */
const EXPERT_DETAILS = {
  tactics: {
    rank: 'K', suit: '♥', color: '#dc2626',
    glowColor: 'rgba(220,38,38,0.35)',
    gradientFrom: 'rgba(255,180,180,0.18)', gradientTo: 'rgba(220,38,38,0.08)',
    badge: '⚔️', name: '战术专家', tagline: '棋子攻防 · 战术组合',
    abilities: ['分析棋子间的攻防关系', '识别将军与抽将威胁', '计算吃子方案与兑子策略', '寻找组合拳与精妙妙手'],
  },
  strategy: {
    rank: 'J', suit: '♠', color: '#1a1a1a',
    glowColor: 'rgba(200,200,200,0.3)',
    gradientFrom: 'rgba(220,220,220,0.15)', gradientTo: 'rgba(150,150,150,0.06)',
    badge: '🎯', name: '战略专家', tagline: '全局态势 · 战略布局',
    abilities: ['评估全局子力平衡', '把控局面节奏与方向', '分析战略目标与计划', '权衡得失与长期优势'],
  },
  engine: {
    rank: 'Q', suit: '♦', color: '#2563eb',
    glowColor: 'rgba(37,99,235,0.35)',
    gradientFrom: 'rgba(180,210,255,0.18)', gradientTo: 'rgba(37,99,235,0.08)',
    badge: '📊', name: '引擎专家', tagline: '深度分析 · 候选走法',
    abilities: ['搜索最佳候选走法', '计算精确局面评估分', '提供多步深度分析', '量化优劣与胜率预估'],
  },
};

export type ExpertType = keyof typeof EXPERT_DETAILS;

/** 毛玻璃介绍框（通过 Portal 渲染到 document.body） */
export const ExpertGlassPanel: React.FC<{ expert: ExpertType; cardRect: DOMRect }> = ({ expert, cardRect }) => {
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

/** 单张扑克牌正面内容 — 一字不改，严格复制自 CollapsedCardsView */
export const CardContent: React.FC<{ type: ExpertType; isHovered: boolean; enable3D?: boolean }> = ({ type, isHovered, enable3D }) => {
  const d = EXPERT_DETAILS[type];

  return (
    <div
      className="lg-card"
      data-expert={type}
      style={{
        width: 130, height: 175,
        borderRadius: 16,
        position: 'relative',
        overflow: 'hidden',
        background: `linear-gradient(145deg, ${d.gradientFrom}, ${d.gradientTo})`,
        outline: `1px solid rgba(255,255,255,0.15)`,
        outlineOffset: -1,
        boxShadow: isHovered
          ? `0 16px 40px rgba(0,0,0,0.3), 0 6px 16px rgba(0,0,0,0.15), 0 0 32px ${d.glowColor}, inset 0 1px 0 rgba(255,255,255,0.25), inset 0 -1px 0 rgba(0,0,0,0.1)`
          : `0 8px 24px rgba(0,0,0,0.22), 0 3px 8px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.2), inset 0 -1px 0 rgba(0,0,0,0.08)`,
        backdropFilter: 'blur(12px) saturate(150%)',
        WebkitBackdropFilter: 'blur(12px) saturate(150%)',
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        padding: 0, gap: 0,
      }}
    >
      {/* 顶层高光渐变 */}
      <div style={{
        position: 'absolute', inset: 0, borderRadius: 16,
        background: `radial-gradient(ellipse at 30% 20%, rgba(255,255,255,0.22) 0%, transparent 60%)`,
        pointerEvents: 'none', zIndex: 1,
      }} />
      {/* 底层暗角 */}
      <div style={{
        position: 'absolute', inset: 0, borderRadius: 16,
        background: `radial-gradient(ellipse at 70% 80%, rgba(0,0,0,0.12) 0%, transparent 50%)`,
        pointerEvents: 'none', zIndex: 1,
      }} />

      {/* 右上角徽章 */}
      <div style={{ position: 'absolute', top: 8, right: 10, fontSize: 14, zIndex: 2 }}>{d.badge}</div>
      {/* 左上角花色 */}
      <div style={{ position: 'absolute', top: 8, left: 10, fontSize: 16, color: d.color, opacity: 0.8, lineHeight: 1, zIndex: 2 }}>{d.suit}</div>

      {/* 主字母 K / J / Q — 3D 立体圆润效果 */}
      {enable3D ? (
        <div
          style={{
            fontSize: 54, fontWeight: 900, lineHeight: 1,
            fontFamily: '"SF Pro Display", serif',
            marginTop: 4,
            background: `linear-gradient(180deg, rgba(255,255,255,0.45) 0%, rgba(255,255,255,0.12) 35%, rgba(0,0,0,0.06) 60%, rgba(0,0,0,0.18) 100%)`,
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            color: 'transparent',
            textShadow: `
              2px 2px 0 rgba(0,0,0,0.18),
              1px 1px 0 rgba(0,0,0,0.12),
              0 -1px 0 rgba(255,255,255,0.35),
              0 0 10px rgba(${d.color === '#1a1a1a' ? '100,100,100' : d.color === '#dc2626' ? '220,38,38' : '37,99,235'},0.4)
            `,
            zIndex: 2, position: 'relative',
          }}
        >{d.rank}</div>
      ) : (
        <div style={{
          fontSize: 54, fontWeight: 900, lineHeight: 1,
          color: d.color,
          fontFamily: '"SF Pro Display", serif',
          marginTop: 4,
          textShadow: isHovered
            ? `0 0 20px ${d.glowColor}, 0 2px 4px rgba(0,0,0,0.2)`
            : `0 2px 4px rgba(0,0,0,0.15)`,
          zIndex: 2, position: 'relative',
        }}>{d.rank}</div>
      )}

      {/* 中央大花色 */}
      <div style={{
        fontSize: 36, color: d.color, lineHeight: 1,
        opacity: 0.7,
        zIndex: 2, position: 'relative',
      }}>{d.suit}</div>

      {/* 右下角花色（倒置） */}
      <div style={{ position: 'absolute', bottom: 28, right: 10, fontSize: 16, color: d.color, opacity: 0.8, lineHeight: 1, transform: 'rotate(180deg)', zIndex: 2 }}>{d.suit}</div>

      {/* 底部名字标签 */}
      <div style={{
        position: 'absolute', bottom: 6, left: 0, right: 0, textAlign: 'center',
        fontSize: 11, fontWeight: 700, color: d.color, opacity: 0.9,
        fontFamily: '"Noto Serif SC", serif',
        letterSpacing: '0.02em',
        zIndex: 2,
      }}>{d.name}</div>
    </div>
  );
};

export default CardContent;
