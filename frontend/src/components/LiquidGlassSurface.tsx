/**
 * LiquidGlassSurface Component
 *
 * Universal WebGL2-powered liquid glass surface.
 * Uses multi-pass rendering for authentic glass effect.
 * Can wrap any children content.
 */

import { useRef, useEffect, useCallback, useState } from 'react';
import {
  MultiPassRenderer,
  PassConfig,
  computeGaussianKernelByRadius,
} from '../utils/LiquidGlassGLUtils';
import { getRegionConfig, GlassRegion } from '../utils/LiquidGlassConfig';

// Import shaders as raw strings
import VertexShader from '../shaders/liquidglass/vertex.glsl?raw';
import FragmentBgShader from '../shaders/liquidglass/fragment-bg.glsl?raw';
import FragmentBgVblurShader from '../shaders/liquidglass/fragment-bg-vblur.glsl?raw';
import FragmentBgHblurShader from '../shaders/liquidglass/fragment-bg-hblur.glsl?raw';
import FragmentMainShader from '../shaders/liquidglass/fragment-main.glsl?raw';

// ========================================
// Types
// ========================================

export interface LiquidGlassSurfaceProps {
  region: GlassRegion;
  children?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  /** Override default intensity (0-1) */
  intensity?: number;
  /** External background texture (for shared background) */
  bgTexture?: WebGLTexture | null;
  /** Whether external background texture is ready */
  bgTextureReady?: boolean;
  /** External background texture ratio (width/height) */
  bgTextureRatio?: number;
}

// ========================================
// Component
// ========================================

export const LiquidGlassSurface: React.FC<LiquidGlassSurfaceProps> = ({
  region,
  children,
  className = '',
  style,
  intensity = 0.6,
  bgTexture: externalBgTexture,
  bgTextureReady: externalBgTextureReady = false,
  bgTextureRatio: externalBgTextureRatio = 1,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<MultiPassRenderer | null>(null);
  const frameRef = useRef<number>(0);
  const startTimeRef = useRef<number>(performance.now());

  // 分离目标位置(鼠标)和弹簧状态
  const targetRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const springRef = useRef<{ x: number; y: number; vx: number; vy: number }>({
    x: 0,
    y: 0,
    vx: 0,
    vy: 0,
  });

  // Background texture
  const bgTextureRef = useRef<WebGLTexture | null>(null);
  const bgTextureReadyRef = useRef(false);
  const bgTextureRatioRef = useRef(1);

  // Size state (measured from container)
  const [size, setSize] = useState({ width: 200, height: 200 });

  // Get region config
  const config = getRegionConfig(region);

  // Sync refs to avoid stale closure in animation loop
  const sizeRef = useRef(size);
  const configRef = useRef(config);
  const intensityRef = useRef(intensity);

  useEffect(() => { sizeRef.current = size; }, [size]);
  useEffect(() => { configRef.current = config; }, [config]);
  useEffect(() => { intensityRef.current = intensity; }, [intensity]);

  // Measure container size
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (width > 0 && height > 0) {
          setSize({ width: Math.round(width), height: Math.round(height) });
        }
      }
    });

    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  // Initialize WebGL2 renderer
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Create render passes configuration
    const passConfigs: PassConfig[] = [
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
      startTimeRef.current = performance.now();
    } catch (error) {
      console.error('Failed to create LiquidGlassSurface renderer:', error);
      return;
    }

    return () => {
      if (rendererRef.current) {
        rendererRef.current.dispose();
        rendererRef.current = null;
      }
    };
  }, []);

  // Load background texture or use external
  useEffect(() => {
    // If external texture is provided and ready, use it
    if (externalBgTexture && externalBgTextureReady) {
      bgTextureRef.current = externalBgTexture;
      bgTextureReadyRef.current = true;
      bgTextureRatioRef.current = externalBgTextureRatio;
      return;
    }

    // Otherwise load from /bg.jpg
    const renderer = rendererRef.current;
    if (!renderer) return;
    const gl = renderer.getGL();

    const texture = gl.createTexture();
    if (!texture) return;

    const image = new Image();
    image.onload = () => {
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

      bgTextureRef.current = texture;
      bgTextureReadyRef.current = true;
      bgTextureRatioRef.current = image.naturalWidth / image.naturalHeight;
    };
    image.src = '/O.webp';

    return () => {
      if (bgTextureRef.current && !externalBgTexture) {
        gl.deleteTexture(bgTextureRef.current);
        bgTextureRef.current = null;
        bgTextureReadyRef.current = false;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [externalBgTexture, externalBgTextureReady, externalBgTextureRatio]);

  // Resize canvas when size changes
  useEffect(() => {
    const renderer = rendererRef.current;
    const canvas = canvasRef.current;
    if (!renderer || !canvas) return;

    const dpr = window.devicePixelRatio || 1;
    const w = Math.round(size.width * dpr);
    const h = Math.round(size.height * dpr);

    canvas.width = w;
    canvas.height = h;
    canvas.style.width = `${size.width}px`;
    canvas.style.height = `${size.height}px`;

    renderer.resize(w, h);
  }, [size.width, size.height]);

  // Handle pointer move
  const handlePointerMove = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const currentSize = sizeRef.current;
    targetRef.current = {
      x: (e.clientX - rect.left) * dpr,
      y: (currentSize.height * dpr) - (e.clientY - rect.top) * dpr,
    };
  }, []);

  // Animation loop - runs once, uses refs for all dynamic values
  useEffect(() => {
    const renderer = rendererRef.current;
    if (!renderer) return;

    const dpr = window.devicePixelRatio || 1;
    const stiffness = 0.12;
    const damping = 0.8;

    // Pre-compute blur weights (depends on initial config.blurRadius)
    const currentConfig = configRef.current;
    const blurWeights = computeGaussianKernelByRadius(currentConfig.blurRadius);

    const render = () => {
      const elapsed = (performance.now() - startTimeRef.current) / 1000;
      const gl = renderer.getGL();

      // Read latest values from refs to avoid stale closure
      const { width, height } = sizeRef.current;
      const cfg = configRef.current;
      const itn = intensityRef.current;
      const target = targetRef.current;
      const spring = springRef.current;

      // Clear
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

      // Mouse spring physics - 分离目标位置和弹簧状态
      const dx = target.x - spring.x;
      const dy = target.y - spring.y;
      spring.vx += dx * stiffness;
      spring.vy += dy * stiffness;
      spring.vx *= damping;
      spring.vy *= damping;
      spring.x += spring.vx;
      spring.y += spring.vy;

      // Global uniforms
      // 注意：u_mouseSpring 用于控制形状位置，对于静态组件应该固定在中心
      // 参考项目用这个做交互效果，但侧栏不需要形状跟随鼠标
      const centerX = width * dpr / 2;
      const centerY = height * dpr / 2;
      renderer.setUniforms({
        u_resolution: [width * dpr, height * dpr],
        u_dpr: dpr,
        u_time: elapsed,
        u_mouse: [spring.x, spring.y],
        u_mouseSpring: [centerX, centerY],  // 固定在中心，不让形状跟随鼠标
        u_shapeWidth: width,
        u_shapeHeight: height,
        u_shapeRadius: cfg.shapeRadius,
        u_shapeRoundness: cfg.shapeRoundness,
        u_mergeRate: cfg.mergeRate,
        u_shadowExpand: cfg.shadowExpand,
        u_shadowFactor: cfg.shadowFactor,
        u_shadowPosition: [cfg.shadowPositionX, cfg.shadowPositionY],
        u_showShape1: 0,
        u_blurRadius: cfg.blurRadius,
        u_blur_weights: blurWeights,
      });

      // Render passes with specific uniforms
      renderer.render({
        bgPass: {
          u_bgType: bgTextureReadyRef.current ? 3 : 2, // 3=图片背景, 2=半色背景
          u_bgTexture: bgTextureRef.current,
          u_bgTextureRatio: bgTextureRatioRef.current,
          u_bgTextureReady: bgTextureReadyRef.current ? 1 : 0,
          u_shadowExpand: cfg.shadowExpand,
          u_shadowFactor: cfg.shadowFactor,
          u_shadowPosition: [cfg.shadowPositionX, cfg.shadowPositionY],
          u_showShape1: 0,
        },
        mainPass: {
          u_tint: [cfg.tintR, cfg.tintG, cfg.tintB, cfg.tintAlpha * itn],
          u_refThickness: cfg.refThickness,
          u_refFactor: cfg.refFactor,
          u_refDispersion: cfg.refDispersion,
          u_refFresnelRange: cfg.fresnelRange,
          u_refFresnelFactor: cfg.fresnelFactor,
          u_refFresnelHardness: cfg.fresnelHardness,
          u_glareRange: cfg.glareRange,
          u_glareFactor: cfg.glareFactor * itn,
          u_glareAngle: (cfg.glareAngle * Math.PI) / 180,
          u_glareHardness: cfg.glareHardness,
          u_glareConvergence: cfg.glareConvergence,
          u_glareOppositeFactor: cfg.glareOppositeFactor,
          u_blurEdge: cfg.blurEdge ? 1 : 0,
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
  }, []); // 空依赖 - 动画循环一旦创建就不再改变

  return (
    <div
      ref={containerRef}
      className={`liquid-glass-surface ${className}`}
      style={{
        position: 'relative',
        overflow: 'hidden',
        borderRadius: 'var(--radius-lg, 20px)',
        ...style,
      }}
      onPointerMove={handlePointerMove}
    >
      {/* WebGL Canvas Layer */}
      <canvas
        ref={canvasRef}
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none',
        }}
      />
      {/* Content Layer */}
      <div
        className="liquid-glass-content"
        style={{
          position: 'relative',
          zIndex: 1,
          width: '100%',
          height: '100%',
        }}
      >
        {children}
      </div>
    </div>
  );
};

export default LiquidGlassSurface;
