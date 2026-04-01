/**
 * LiquidCardSurface Component
 *
 * WebGL2-powered true liquid glass card surface.
 * Uses multi-pass rendering for authentic glass effect.
 */

import { useRef, useEffect, useCallback, useMemo } from 'react';
import { CardPhase, ExpertType, EXPERT_ACCENT_COLORS } from '../hooks/useLiquidCardUniforms';
import {
  MultiPassRenderer,
  RenderPassConfig,
  computeGaussianKernelByRadius,
} from '../utils/LiquidGlassGLUtils';
import { getRegionConfig } from '../utils/LiquidGlassConfig';

// Import shaders as raw strings
import VertexShader from '../shaders/liquidglass/vertex.glsl?raw';
import FragmentBgShader from '../shaders/liquidglass/fragment-bg.glsl?raw';
import FragmentBgVblurShader from '../shaders/liquidglass/fragment-bg-vblur.glsl?raw';
import FragmentBgHblurShader from '../shaders/liquidglass/fragment-bg-hblur.glsl?raw';
import FragmentMainShader from '../shaders/liquidglass/fragment-main.glsl?raw';

// ========================================
// Types
// ========================================

export interface LiquidCardSurfaceProps {
  width: number;
  height: number;
  expertType: ExpertType;
  hover?: number;      // 0-1
  flip?: number;       // 0-1
  morph?: number;      // 0-1
  glow?: number;       // 0-1
  phase?: CardPhase;
  className?: string;
  style?: React.CSSProperties;
}

// ========================================
// Phase intensity mapping
// ========================================

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

// ========================================
// Component
// ========================================

export const LiquidCardSurface: React.FC<LiquidCardSurfaceProps> = ({
  width,
  height,
  expertType,
  hover = 0,
  flip: _flip = 0,
  morph: _morph = 0,
  glow: _glow = 0,
  phase = CardPhase.Idle,
  className,
  style,
}) => {
  // Reserved for future animation phases
  void _flip;
  void _morph;
  void _glow;
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<MultiPassRenderer | null>(null);
  const frameRef = useRef<number>(0);
  const startTimeRef = useRef<number>(performance.now());
  const pointerRef = useRef<{ x: number; y: number; vx: number; vy: number }>({
    x: width / 2,
    y: height / 2,
    vx: 0,
    vy: 0
  });

  // Get expert accent color
  const accent = EXPERT_ACCENT_COLORS[expertType] || [1, 1, 1];

  // Expert type config
  const expertConfig = useMemo(() => {
    const baseConfig = getRegionConfig('card-hero');
    return {
      ...baseConfig,
      tintR: accent[0],
      tintG: accent[1],
      tintB: accent[2],
      tintAlpha: 0.12,
    };
  }, [accent]);

  // Initialize WebGL2 renderer
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const gl = canvas.getContext('webgl2', {
      alpha: true,
      premultipliedAlpha: false,
      antialias: true,
    });

    if (!gl) {
      console.error('WebGL2 not supported');
      return;
    }

    // Check for float texture extension
    const ext = gl.getExtension('EXT_color_buffer_float');
    if (!ext) {
      console.warn('EXT_color_buffer_float not supported');
    }

    // Create render passes configuration
    const passConfigs: RenderPassConfig[] = [
      { name: 'bgPass', shader: { vertex: VertexShader, fragment: FragmentBgShader } },
      {
        name: 'vBlurPass',
        shader: { vertex: VertexShader, fragment: FragmentBgVblurShader },
        inputs: { u_prevPassTexture: 'bgPass' }
      },
      {
        name: 'hBlurPass',
        shader: { vertex: VertexShader, fragment: FragmentBgHblurShader },
        inputs: { u_prevPassTexture: 'vBlurPass' }
      },
      {
        name: 'mainPass',
        shader: { vertex: VertexShader, fragment: FragmentMainShader },
        inputs: { u_blurredBg: 'hBlurPass', u_bg: 'bgPass' },
        outputToScreen: true
      },
    ];

    try {
      const renderer = new MultiPassRenderer(canvas, passConfigs);
      rendererRef.current = renderer;

      // Set initial uniforms
      const dpr = window.devicePixelRatio || 1;
      renderer.setUniform('u_resolution', [width * dpr, height * dpr]);
      renderer.setUniform('u_dpr', dpr);
    } catch (error) {
      console.error('Failed to create LiquidGlass renderer:', error);
      return;
    }

    return () => {
      if (rendererRef.current) {
        rendererRef.current.dispose();
        rendererRef.current = null;
      }
    };
  }, []);

  // Resize canvas
  useEffect(() => {
    const renderer = rendererRef.current;
    if (!renderer) return;

    const dpr = window.devicePixelRatio || 1;
    const w = Math.round(width * dpr);
    const h = Math.round(height * dpr);

    const canvas = canvasRef.current;
    if (canvas) {
      canvas.width = w;
      canvas.height = h;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
    }

    renderer.resize(w, h);
    renderer.setUniform('u_resolution', [w, h]);
    renderer.setUniform('u_dpr', dpr);
  }, [width, height]);

  // Handle mouse move
  const handlePointerMove = useCallback((e: React.PointerEvent<HTMLCanvasElement>) => {
    if (!canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    pointerRef.current = {
      ...pointerRef.current,
      x: (e.clientX - rect.left) * dpr,
      y: (height * dpr) - (e.clientY - rect.top) * dpr, // Flip Y
    };
  }, [height]);

  // Animation loop
  useEffect(() => {
    const renderer = rendererRef.current;
    if (!renderer) return;

    const config = expertConfig;
    const dpr = window.devicePixelRatio || 1;
    const blurWeights = computeGaussianKernelByRadius(config.blurRadius);
    const intensity = getPhaseIntensity(phase);

    const render = () => {
      const elapsed = (performance.now() - startTimeRef.current) / 1000;
      const gl = renderer.getGL();

      // Clear
      gl.clearColor(0, 1, 1, 0);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

      // Mouse spring physics
      const spring = pointerRef.current;
      const stiffness = 0.15;
      const damping = 0.75;

      spring.vx += (spring.x - spring.x) * stiffness;
      spring.vy += (spring.y - spring.y) * stiffness
      spring.vx *= damping;
      spring.vy *= damping
      spring.x += spring.vx;
      spring.y += spring.vy

      // Global uniforms
      renderer.setUniforms({
        u_resolution: [width * dpr, height * dpr],
        u_dpr: dpr,
        u_time: elapsed,
        u_mouse: [pointerRef.current.x, pointerRef.current.y],
        u_mouseSpring: [spring.x, spring.y],
        u_shapeWidth: width,
        u_shapeHeight: height,
        u_shapeRadius: config.shapeRadius,
        u_shapeRoundness: config.shapeRoundness,
        u_mergeRate: config.mergeRate,
        u_shadowExpand: config.shadowExpand,
        u_shadowFactor: config.shadowFactor,
        u_shadowPosition: [config.shadowPositionX, config.shadowPositionY],
        u_showShape1: 0,
        u_blurRadius: config.blurRadius,
        u_blur_weights: blurWeights,
      });

      // Render passes with specific uniforms
      renderer.render({
        bgPass: {
          u_bgType: 0, // Use half-color background
          u_bgTexture: null,
          u_bgTextureRatio: 1,
          u_bgTextureReady: 0,
        },
        mainPass: {
          u_tint: [config.tintR, config.tintG, config.tintB, config.tintAlpha * intensity],
          u_refThickness: config.refThickness,
          u_refFactor: config.refFactor,
          u_refDispersion: config.refDispersion,
          u_refFresnelRange: config.fresnelRange,
          u_refFresnelFactor: config.fresnelFactor * 100,
          u_refFresnelHardness: config.fresnelHardness,
          u_glareRange: config.glareRange,
          u_glareFactor: config.glareFactor * 100 * intensity,
          u_glareAngle: (config.glareAngle * Math.PI) / 180,
          u_glareHardness: config.glareHardness * 100,
          u_glareConvergence: config.glareConvergence * 100,
          u_glareOppositeFactor: config.glareOppositeFactor * 100,
          u_blurEdge: config.blurEdge ? 1 : 0,
          STEP: 10,
        },
      });

      frameRef.current = requestAnimationFrame(render);
    };

    frameRef.current = requestAnimationFrame(render);

    return () => {
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
      }
    };
  }, [width, height, expertConfig, phase]);

  return (
    <canvas
      ref={canvasRef}
      className={className}
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        pointerEvents: hover > 0 ? 'auto' : 'none',
        ...style,
      }}
      onPointerMove={handlePointerMove}
    />
  );
};

export default LiquidCardSurface;
