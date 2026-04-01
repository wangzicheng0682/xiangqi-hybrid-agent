/**
 * LiquidGlassRendererMini - 最小化 WebGL 液态玻璃渲染器
 *
 * Phase 1: 单区域玻璃效果（左侧栏）
 *
 * 核心特性：
 * - 全屏 WebGL canvas
 * - 4 pass 渲染管线（复用现有 shader）
 * - 支持一个固定的矩形区域
 */

import { useRef, useEffect, useState } from 'react';
import {
  MultiPassRenderer,
  PassConfig,
  computeGaussianKernelByRadius,
} from '../utils/LiquidGlassGLUtils';
import { type LiquidGlassConfig } from '../utils/LiquidGlassConfig';

// Import shaders
import VertexShader from '../shaders/liquidglass/vertex.glsl?raw';
import FragmentBgShader from '../shaders/liquidglass/fragment-bg.glsl?raw';
import FragmentBgVblurShader from '../shaders/liquidglass/fragment-bg-vblur.glsl?raw';
import FragmentBgHblurShader from '../shaders/liquidglass/fragment-bg-hblur.glsl?raw';
import FragmentMainShader from '../shaders/liquidglass/fragment-main.glsl?raw';

// ============================================
// Types
// ============================================

export interface GlassRegionConfig {
  x: number;      // 中心 x (屏幕坐标，像素)
  y: number;      // 中心 y (屏幕坐标，像素)
  width: number;
  height: number;
  config: LiquidGlassConfig;
}

export interface LiquidGlassRendererMiniProps {
  region: GlassRegionConfig;
  bgImage?: string;
  children?: React.ReactNode;
}

// ============================================
// Component
// ============================================

export const LiquidGlassRendererMini: React.FC<LiquidGlassRendererMiniProps> = ({
  region,
  bgImage,
  children,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<MultiPassRenderer | null>(null);
  const frameRef = useRef<number>(0);
  const startTimeRef = useRef<number>(performance.now());

  // Background texture
  const bgTextureRef = useRef<WebGLTexture | null>(null);
  const bgTextureReadyRef = useRef(false);
  const bgTextureRatioRef = useRef(1);

  // Window size
  const [windowSize, setWindowSize] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
    dpr: window.devicePixelRatio || 1,
  });

  // Update window size
  useEffect(() => {
    const handleResize = () => {
      setWindowSize({
        width: window.innerWidth,
        height: window.innerHeight,
        dpr: window.devicePixelRatio || 1,
      });
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Initialize renderer
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const { width, height, dpr } = windowSize;
    canvas.width = width * dpr;
    canvas.height = height * dpr;

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
      console.error('Failed to create LiquidGlassRendererMini:', error);
      return;
    }

    return () => {
      if (rendererRef.current) {
        rendererRef.current.dispose();
        rendererRef.current = null;
      }
    };
  }, [windowSize]);

  // Load background image
  useEffect(() => {
    if (!bgImage) {
      bgTextureReadyRef.current = false;
      return;
    }

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
    image.src = bgImage;

    return () => {
      if (bgTextureRef.current) {
        gl.deleteTexture(bgTextureRef.current);
        bgTextureRef.current = null;
        bgTextureReadyRef.current = false;
      }
    };
  }, [bgImage]);

  // Resize canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    const renderer = rendererRef.current;
    if (!canvas || !renderer) return;

    const { width, height, dpr } = windowSize;
    const w = Math.round(width * dpr);
    const h = Math.round(height * dpr);

    canvas.width = w;
    canvas.height = h;
    renderer.resize(w, h);
  }, [windowSize]);

  // Animation loop
  useEffect(() => {
    const renderer = rendererRef.current;
    if (!renderer) return;

    const { width, height, dpr } = windowSize;
    const cfg = region.config;
    const blurWeights = computeGaussianKernelByRadius(cfg.blurRadius);

    const render = () => {
      const elapsed = (performance.now() - startTimeRef.current) / 1000;
      const gl = renderer.getGL();

      // Clear
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

      // 原版坐标：x=110(中心), y=height/2(垂直居中)
      const mouseSpringX = region.x * dpr;
      const mouseSpringY = (height - region.y) * dpr;

      renderer.setUniforms({
        u_resolution: [width * dpr, height * dpr],
        u_dpr: dpr,
        u_time: elapsed,
        u_mouse: [mouseSpringX, mouseSpringY],
        u_mouseSpring: [mouseSpringX, mouseSpringY],
        u_shapeWidth: region.width,
        u_shapeHeight: region.height,
        u_shapeRadius: cfg.shapeRadius,
        u_shapeRoundness: cfg.shapeRoundness,
        u_mergeRate: cfg.mergeRate,
        u_shadowExpand: cfg.shadowExpand,
        u_shadowFactor: cfg.shadowFactor,
        u_shadowPosition: [cfg.shadowPositionX, cfg.shadowPositionY],
        u_showShape1: 0,
        u_blurRadius: cfg.blurRadius,
        u_blurWeights: blurWeights,
      });

      // Render passes
      renderer.render({
        bgPass: {
          u_bgType: bgTextureReadyRef.current ? 3 : 2, // 3=图片背景, 2=半色背景
          u_bgTexture: bgTextureRef.current,
          u_bgTextureRatio: bgTextureRatioRef.current,
          u_bgTextureReady: bgTextureReadyRef.current ? 1 : 0,
        },
        mainPass: {
          u_tint: [cfg.tintR, cfg.tintG, cfg.tintB, cfg.tintAlpha],
          u_refThickness: cfg.refThickness,
          u_refFactor: cfg.refFactor,
          u_refDispersion: cfg.refDispersion,
          u_refFresnelRange: cfg.fresnelRange,
          u_refFresnelFactor: cfg.fresnelFactor,
          u_refFresnelHardness: cfg.fresnelHardness,
          u_glareRange: cfg.glareRange,
          u_glareFactor: cfg.glareFactor,
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
  }, [windowSize, region, bgImage]);

  return (
    <div style={{ position: 'fixed', inset: 0, overflow: 'hidden' }}>
      {/* WebGL Canvas Layer */}
      <canvas
        ref={canvasRef}
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
        }}
      />
      {/* HTML Content Layer */}
      <div style={{ position: 'relative', width: '100%', height: '100%', zIndex: 1 }}>
        {children}
      </div>
    </div>
  );
};

export default LiquidGlassRendererMini;
