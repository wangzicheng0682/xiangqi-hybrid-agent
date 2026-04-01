/**
 * useLiquidCardUniforms Hook
 *
 * Maps React state to shader uniforms for the liquid card effect.
 * Handles animation frame timing and phase intensity mapping.
 */

import { useRef, useEffect, useCallback } from 'react';
import type { WebGLContext } from './useWebGL';

// Phase enum matching shader
export enum CardPhase {
  Idle = 0,
  Stacking = 1,
  Flipped = 2,
  Morphing = 3,
  OrbMoving = 4,
  CardsLanding = 5,
  CardsLanded = 6,
  Streaming = 7,
}

// Expert type with accent colors
export type ExpertType = 'tactics' | 'strategy' | 'engine';

// Expert accent colors (RGB normalized 0-1)
export const EXPERT_ACCENT_COLORS: Record<ExpertType, [number, number, number]> = {
  tactics: [0.95, 0.25, 0.35],    // Warm red
  strategy: [0.65, 0.65, 0.70],   // Cool gray
  engine: [0.25, 0.45, 0.95],     // Cold blue
};

export interface LiquidCardUniforms {
  // Animation state
  hover: number;      // 0-1 hover intensity
  flip: number;       // 0-1 flip progress
  morph: number;      // 0-1 morph intensity
  glow: number;       // 0-1 global glow
  phase: CardPhase;   // Current phase

  // Expert configuration
  expertType: ExpertType;

  // Interaction
  pointerX: number;   // 0-1 normalized
  pointerY: number;   // 0-1 normalized
}

interface UseLiquidCardUniformsOptions {
  ctx: WebGLContext | null;
  uniforms: LiquidCardUniforms;
}

/**
 * Phase intensity mapping (matches shader)
 */
function getPhaseIntensity(phase: CardPhase): number {
  switch (phase) {
    case CardPhase.Idle: return 0.20;
    case CardPhase.Stacking: return 0.35;
    case CardPhase.Flipped: return 0.75;
    case CardPhase.Morphing: return 0.85;
    case CardPhase.OrbMoving: return 1.00;
    case CardPhase.CardsLanding: return 0.60;
    case CardPhase.CardsLanded: return 0.35;
    case CardPhase.Streaming: return 0.15;
    default: return 0.20;
  }
}

/**
 * Hook that updates shader uniforms based on React state
 */
export function useLiquidCardUniforms(options: UseLiquidCardUniformsOptions) {
  const { ctx, uniforms } = options;
  const frameRef = useRef<number>(0);
  const startTimeRef = useRef<number>(performance.now());

  // Update uniforms on WebGL context
  const updateUniforms = useCallback(() => {
    if (!ctx) return;

    const elapsed = (performance.now() - startTimeRef.current) / 1000;
    const accent = EXPERT_ACCENT_COLORS[uniforms.expertType];
    const intensity = getPhaseIntensity(uniforms.phase);

    // Set all uniforms
    ctx.setUniform('uResolution', [1.0, 1.0]);  // Updated on resize
    ctx.setUniform('uTime', elapsed);
    ctx.setUniform('uHover', uniforms.hover);
    ctx.setUniform('uFlip', uniforms.flip);
    ctx.setUniform('uMorph', uniforms.morph);
    ctx.setUniform('uGlow', uniforms.glow);
    ctx.setUniform('uIntensity', intensity);
    ctx.setUniform('uAccent', accent);
    ctx.setUniform('uPointer', [uniforms.pointerX, uniforms.pointerY]);
  }, [ctx, uniforms]);

  // Animation loop
  useEffect(() => {
    if (!ctx) return;

    const animate = () => {
      updateUniforms();
      ctx.render();
      frameRef.current = requestAnimationFrame(animate);
    };

    frameRef.current = requestAnimationFrame(animate);

    return () => {
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
      }
    };
  }, [ctx, updateUniforms]);

  // Manual render (for when uniforms change outside animation loop)
  const render = useCallback(() => {
    if (!ctx) return;
    updateUniforms();
    ctx.render();
  }, [ctx, updateUniforms]);

  return { render };
}

export default useLiquidCardUniforms;
