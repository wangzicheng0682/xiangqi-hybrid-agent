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

/** 单张扑克牌正面内容 — iOS 26 液态玻璃风格 */
export const CardContent: React.FC<{ type: ExpertType; isHovered: boolean; enable3D?: boolean }> = ({ type, isHovered, enable3D }) => {
  const d = EXPERT_DETAILS[type];

  // iOS 26 彩虹光晕颜色
  const rainbowGlow = {
    tactics:  { inner: 'rgba(255,100,120,0.45)', mid: 'rgba(255,140,80,0.30)', outer: 'rgba(255,180,180,0.18)' },
    strategy: { inner: 'rgba(180,160,255,0.45)', mid: 'rgba(200,180,255,0.30)', outer: 'rgba(220,200,255,0.18)' },
    engine:   { inner: 'rgba(80,160,255,0.45)', mid: 'rgba(64,200,192,0.30)', outer: 'rgba(100,180,255,0.18)' },
  }[type];

  return (
    <div
      className="lg-card"
      data-expert={type}
      style={{
        width: 130, height: 175,
        borderRadius: 16,
        position: 'relative',
        overflow: 'hidden',
        background: `linear-gradient(180deg,
          rgba(255,255,255,0.16) 0%,
          ${d.gradientFrom} 30%,
          ${d.gradientTo} 70%,
          rgba(0,0,0,0.08) 100%
        )`,
        border: 'none',
        boxShadow: isHovered
          ? /* 悬停时：4层彩虹光晕 */
            `0 0 0 1.5px rgba(255,255,255,0.50),
             0 0 10px 2px ${rainbowGlow.inner},
             0 0 22px 5px ${rainbowGlow.mid},
             0 0 38px 10px ${rainbowGlow.outer},
             0 0 60px 18px rgba(200,200,255,0.10),
             0 16px 40px rgba(0,0,0,0.32),
             /* 内层湿润高光 */
             inset 0  2px 0 rgba(255,255,255,0.70),
             inset 0  5px 10px rgba(255,255,255,0.15),
             inset 0 -1.5px 0 rgba(0,0,0,0.18)`
          : /* 普通：3层彩虹光晕 */
            `0 0 0 1px rgba(255,255,255,0.35),
             0 0 6px 1px ${rainbowGlow.inner},
             0 0 14px 3px ${rainbowGlow.mid},
             0 0 28px 7px ${rainbowGlow.outer},
             0 8px 24px rgba(0,0,0,0.25),
             /* 内层湿润高光 */
             inset 0  1.5px 0 rgba(255,255,255,0.55),
             inset 0  3px 6px rgba(255,255,255,0.10),
             inset 0 -1px 0 rgba(0,0,0,0.15)`,
        backdropFilter: 'blur(20px) saturate(200%)',
        WebkitBackdropFilter: 'blur(20px) saturate(200%)',
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        padding: 0, gap: 0,
      }}
    >
      {/* iOS 26 彩虹渐变边框 */}
      <div style={{
        position: 'absolute', inset: 0, borderRadius: 16,
        padding: '1.5px',
        background: `linear-gradient(135deg,
          rgba(255,255,255,0.75) 0%,
          rgba(200,220,255,0.55) 20%,
          rgba(220,200,255,0.45) 40%,
          rgba(255,200,220,0.40) 60%,
          rgba(200,255,240,0.45) 80%,
          rgba(255,255,255,0.65) 100%
        )`,
        WebkitMask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
        mask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
        WebkitMaskComposite: 'xor',
        maskComposite: 'exclude',
        pointerEvents: 'none', zIndex: 1,
      }} />

      {/* 左上角光源光斑 */}
      <div style={{
        position: 'absolute', top: 0, left: 0, width: '65%', height: '50%',
        background: `radial-gradient(ellipse 80% 100% at 15% 0%,
          rgba(255,255,255,0.38) 0%,
          rgba(200,220,255,0.18) 40%,
          transparent 70%
        )`,
        pointerEvents: 'none', zIndex: 1,
      }} />

      {/* 顶部折射高光 */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: '55%',
        background: `linear-gradient(180deg,
          rgba(255,255,255,0.28) 0%,
          rgba(200,220,255,0.12) 40%,
          transparent 100%
        )`,
        borderRadius: '15px 15px 60% 60% / 15px 15px 30% 30%',
        pointerEvents: 'none', zIndex: 1,
      }} />

      {/* 底层暗角 */}
      <div style={{
        position: 'absolute', inset: 0, borderRadius: 16,
        background: `radial-gradient(ellipse at 70% 85%, rgba(0,0,0,0.18) 0%, transparent 50%)`,
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
