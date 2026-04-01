/**
 * CardVisualShader Component
 *
 * Four-layer card structure:
 * 1. card-shadow-layer - CSS shadow
 * 2. card-shader-layer - LiquidCardSurface (WebGL)
 * 3. card-glass-overlay - CSS light overlay
 * 4. card-content-layer - DOM text layer
 */

import React from 'react';
import LiquidCardSurface, { LiquidCardSurfaceProps } from './LiquidCardSurface';
import { CardPhase, ExpertType } from '../hooks/useLiquidCardUniforms';

// ========================================
// Types
// ========================================

export interface CardVisualShaderProps extends Omit<LiquidCardSurfaceProps, 'expertType'> {
  type: ExpertType;
  isHovered?: boolean;
}

// ========================================
// Expert styling config
// ========================================

const EXPERT_STYLES = {
  tactics: {
    auraAnim: 'card-aura-tactics',
    energy: { a: '#ff4060', b: '#ff9020', c: '#ffdd00', rgb: '255,64,96' },
    badge: '⚔️',
    name: '战术专家',
  },
  strategy: {
    auraAnim: 'card-aura-strategy',
    energy: { a: '#c8d8ff', b: '#a090ff', c: '#e8c8ff', rgb: '160,144,255' },
    badge: '🎯',
    name: '战略专家',
  },
  engine: {
    auraAnim: 'card-aura-engine',
    energy: { a: '#40b0ff', b: '#5060ff', c: '#40e0c0', rgb: '64,160,255' },
    badge: '📊',
    name: '引擎专家',
  },
} as const;

// ========================================
// Emboss shadow generator
// ========================================

function emboss(colorRgb: string): string {
  return `
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
}

// ========================================
// Component
// ========================================

export const CardVisualShader: React.FC<CardVisualShaderProps> = ({
  type,
  isHovered = false,
  width = 130,
  height = 175,
  hover = 0,
  flip = 0,
  morph = 0,
  glow = 0,
  phase = CardPhase.Idle,
  className,
  style,
}) => {
  const config = EXPERT_STYLES[type];
  const { energy, auraAnim, badge, name } = config;
  const d = { rank: type === 'tactics' ? 'K' : type === 'strategy' ? 'J' : 'Q', suit: type === 'tactics' ? '♥' : type === 'strategy' ? '♠' : '♦', color: energy.a };

  // Derived hover value
  const hoverValue = isHovered ? 1 : hover;

  return (
    <div
      className={className}
      style={{
        width: '100%',
        height: '100%',
        borderRadius: 16,
        position: 'relative',
        animation: `${auraAnim} 2.4s ease-in-out infinite`,
        transition: 'filter 0.3s ease',
        filter: isHovered ? 'brightness(1.15)' : 'brightness(1)',
        ...style,
      }}
    >
      {/* Layer 1: Shadow (CSS) */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: 16,
          boxShadow: `
            0 4px 16px rgba(0,0,0,0.15),
            0 8px 32px rgba(0,0,0,0.1)
          `,
          pointerEvents: 'none',
          zIndex: 0,
        }}
      />

      {/* Layer 2: Shader (WebGL) */}
      <LiquidCardSurface
        width={width}
        height={height}
        expertType={type}
        hover={hoverValue}
        flip={flip}
        morph={morph}
        glow={glow}
        phase={phase}
        style={{ zIndex: 1 }}
      />

      {/* Layer 3: Glass overlay (CSS) */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: 16,
          background: `linear-gradient(180deg,
            rgba(255,255,255,0.12) 0%,
            rgba(255,255,255,0.04) 40%,
            transparent 100%
          )`,
          pointerEvents: 'none',
          zIndex: 2,
        }}
      />

      {/* Layer 4: Content (DOM) */}
      <div
        style={{
          position: 'absolute',
          inset: 2,
          borderRadius: 14,
          zIndex: 5,
          overflow: 'hidden',
          pointerEvents: 'none',
        }}
      >
        {/* Left-top corner */}
        <div style={{ position: 'absolute', top: 7, left: 8, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
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

        {/* Right-top badge */}
        <div style={{
          position: 'absolute', top: 6, right: 7, fontSize: 14,
          filter: `drop-shadow(0 2px 3px rgba(0,0,0,0.55)) drop-shadow(0 0 7px rgba(${energy.rgb},0.8))`,
        }}>{badge}</div>

        {/* Center suit */}
        <div style={{
          position: 'absolute', top: '50%', left: '50%',
          transform: 'translate(-50%, -52%)',
          fontSize: 56, lineHeight: 1, userSelect: 'none',
          color: energy.a,
          textShadow: emboss(energy.rgb),
        }}>{d.suit}</div>

        {/* Bottom name */}
        <div style={{
          position: 'absolute', bottom: 6, left: 0, right: 0,
          textAlign: 'center', fontSize: 10, fontWeight: 700,
          color: 'rgba(255,255,255,0.75)',
          fontFamily: '"Noto Serif SC", serif', letterSpacing: '0.06em',
          textShadow: `0 1px 0 rgba(0,0,0,0.5), 0 0 8px rgba(${energy.rgb},0.7)`,
        }}>{name}</div>

        {/* Right-bottom corner (inverted) */}
        <div style={{
          position: 'absolute', bottom: 7, right: 8,
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          transform: 'rotate(180deg)',
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

export default CardVisualShader;
