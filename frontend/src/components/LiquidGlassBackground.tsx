/**
 * LiquidGlassBackground - 全屏 WebGL 液态玻璃背景
 *
 * 参考 liquid-glass-studio 的架构，但支持多个形状
 */

import { useRef, useEffect, useState } from 'react';
import {
  MultiPassRenderer,
  PassConfig,
  computeGaussianKernelByRadius,
} from '../utils/LiquidGlassGLUtils';

// Import shaders
import VertexShader from '../shaders/liquidglass/vertex.glsl?raw';
import FragmentBgShader from '../shaders/liquidglass/fragment-bg.glsl?raw';
import FragmentBgVblurShader from '../shaders/liquidglass/fragment-bg-vblur.glsl?raw';
import FragmentBgHblurShader from '../shaders/liquidglass/fragment-bg-hblur.glsl?raw';
import FragmentMainShader from '../shaders/liquidglass/fragment-main.glsl?raw';

// ============================================
// Types
// ============================================

export interface GlassShape {
  id: string;
  x: number;      // 中心 x (像素)
  y: number;      // 中心 y (像素)
  width: number;
  height: number;
  radius: number;
  roundness: number;
  tint: [number, number, number, number];
  refThickness: number;
  refFactor: number;
  fresnelFactor: number;
  glareFactor: number;
}

export interface LiquidGlassBackgroundProps {
  shapes: GlassShape[];
  bgType?: number;  // 0=棋盘格, 2=半色, 3=图片
  bgImage?: string;
  children?: React.ReactNode;
}

// ============================================
// Component
// ============================================

export const LiquidGlassBackground: React.FC<LiquidGlassBackgroundProps> = ({
  shapes,
  bgType = 2,
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
      console.error('Failed to create renderer:', error);
      return;
    }

    return () => {
      if (rendererRef.current) {
        rendererRef.current.dispose();
        rendererRef.current = null;
      }
    };
  }, []);

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
    const blurWeights = computeGaussianKernelByRadius(40);

    const render = () => {
      const elapsed = (performance.now() - startTimeRef.current) / 1000;
      const gl = renderer.getGL();

      // Clear
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

      // Global uniforms - 使用第一个形状的参数
      // TODO: 支持多个形状需要修改 shader
      const firstShape = shapes[0];
      const shapeW = firstShape?.width || width;
      const shapeH = firstShape?.height || height;
      const shapeX = firstShape?.x || width / 2;
      const shapeY = firstShape?.y || height / 2;

      // shader 中 p2 = (vec2(0,0) - u_mouseSpring) / u_resolution.y
      // u_mouseSpring 是形状在 canvas 坐标系中的中心位置（像素）
      // gl_FragCoord 原点在左下角，Y 轴向上
      // shapes 中的 x, y 是屏幕坐标（Y 轴向下），需要翻转
      const mouseSpringX = shapeX * dpr;
      const mouseSpringY = (height - shapeY) * dpr;  // 翻转 Y：屏幕坐标 -> canvas 坐标

      renderer.setUniforms({
        u_resolution: [width * dpr, height * dpr],
        u_dpr: dpr,
        u_time: elapsed,
        u_mouse: [mouseSpringX, mouseSpringY],
        u_mouseSpring: [mouseSpringX, mouseSpringY],
        u_shapeWidth: shapeW,
        u_shapeHeight: shapeH,
        u_shapeRadius: firstShape?.radius || 20,
        u_shapeRoundness: firstShape?.roundness || 2,
        u_mergeRate: 0.1,
        u_shadowExpand: 40,
        u_shadowFactor: 0.5,
        u_shadowPosition: [0, 20],
        u_showShape1: 0,
        u_blurRadius: 40,
        u_blur_weights: blurWeights,
      });

      // Render passes
      renderer.render({
        bgPass: {
          u_bgType: bgTextureReadyRef.current ? 3 : bgType,
          u_bgTexture: bgTextureRef.current,
          u_bgTextureRatio: bgTextureRatioRef.current,
          u_bgTextureReady: bgTextureReadyRef.current ? 1 : 0,
        },
        mainPass: {
          u_tint: firstShape?.tint || [1, 1, 1, 0.1],
          u_refThickness: firstShape?.refThickness || 40,
          u_refFactor: firstShape?.refFactor || 1.5,
          u_refDispersion: 0.5,
          u_refFresnelRange: 500,
          u_refFresnelFactor: firstShape?.fresnelFactor || 70,
          u_refFresnelHardness: 0.1,
          u_glareRange: 400,
          u_glareFactor: firstShape?.glareFactor || 60,
          u_glareAngle: 45 * Math.PI / 180,
          u_glareHardness: 10,
          u_glareConvergence: 50,
          u_glareOppositeFactor: 80,
          u_blurEdge: 0,
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
  }, [windowSize, shapes, bgType]);

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

export default LiquidGlassBackground;
