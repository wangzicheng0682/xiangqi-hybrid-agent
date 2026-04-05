/**
 * LiquidGlassApp — WebGL 液态玻璃渲染器（仅渲染背景 + 侧边栏玻璃）
 *
 * 按钮：全部由 App.tsx CSS DOM 实现，不再使用 WebGL 按钮
 */

import { useEffect, useLayoutEffect, useRef } from 'react';
import { useControls } from 'leva';
import { useGlassParamsStore } from '../store/useGlassParamsStore';
import {
  MultiPassRenderer,
  loadTextureFromURL,
  computeGaussianKernelByRadius,
} from '../utils/GLUtils';

// Import shaders — 一比一复制参考项目
import VertexShader from '../shaders/liquidglass/vertex.glsl?raw';
import FragmentBgShader from '../shaders/liquidglass/fragment-bg.glsl?raw';
import FragmentBgVblurShader from '../shaders/liquidglass/fragment-bg-vblur.glsl?raw';
import FragmentBgHblurShader from '../shaders/liquidglass/fragment-bg-hblur.glsl?raw';
import FragmentMainShader from '../shaders/liquidglass/fragment-main.glsl?raw';

// ============================================
// Controls — shape3 参数扩展自 useGlassParamsStore
// ============================================
interface Controls {
  bgType: number;
  shapeWidth: number;
  shapeHeight: number;
  shapeRadius: number;
  shapeRoundness: number;
  mergeRate: number;
  showShape1: boolean;
  blurRadius: number;
  shadowExpand: number;
  shadowFactor: number;
  shadowPosition: { x: number; y: number };
  tint: { r: number; g: number; b: number; a: number };
  refThickness: number;
  refFactor: number;
  refDispersion: number;
  refFresnelRange: number;
  refFresnelHardness: number;
  refFresnelFactor: number;
  glareRange: number;
  glareFactor: number;
  glareAngle: number;
  glareHardness: number;
  glareConvergence: number;
  glareOppositeFactor: number;
  blurEdge: boolean;
  step: number;
  springSizeFactor: number;
  shapePosX: number;
  shapePosY: number;
  // shape3 右侧栏（来自 Zustand store）
  shape3Radius: number;
  shape3Roundness: number;
  shape3RefThickness: number;
  shape3RefFactor: number;
  shape3RefDispersion: number;
  shape3GlareFactor: number;
  shape3GlareAngle: number;
  shape3GlareHardness: number;
  shape3GlareConvergence: number;
  shape3GlareOppositeFactor: number;
  shape3GlareRange: number;
  shape3ShadowExpand: number;
  shape3ShadowFactor: number;
  shape3ShadowPosX: number;
  shape3ShadowPosY: number;
}

// 参考项目默认值 + shape3（取自 useGlassParamsStore DEFAULTS）
const DEFAULT_CONTROLS: Controls = {
  bgType: 11,
  shapeWidth: 220,
  shapeHeight: 800,
  shapeRadius: 40,
  shapeRoundness: 2.0,
  mergeRate: 0.05,
  showShape1: false,
  blurRadius: 1,
  shadowExpand: 25,
  shadowFactor: 15,
  shadowPosition: { x: 0, y: -10 },
  tint: { r: 255, g: 255, b: 255, a: 0 },
  refThickness: 20,
  refFactor: 1.4,
  refDispersion: 0.6,
  refFresnelRange: 30,
  refFresnelHardness: 12,
  refFresnelFactor: 60,
  glareRange: 250,
  glareFactor: 90,
  glareAngle: -45,
  glareHardness: 8,
  glareConvergence: 60,
  glareOppositeFactor: 90,
  blurEdge: true,
  step: 9,
  springSizeFactor: 0,
  shapePosX: 110,
  shapePosY: 450,
  // shape3 — 取自 store defaults
  shape3Radius: 28,
  shape3Roundness: 2.0,
  shape3RefThickness: 20,
  shape3RefFactor: 1.4,
  shape3RefDispersion: 0.6,
  shape3GlareFactor: 90,
  shape3GlareAngle: -45,
  shape3GlareHardness: 8,
  shape3GlareConvergence: 60,
  shape3GlareOppositeFactor: 90,
  shape3GlareRange: 250,
  shape3ShadowExpand: 25,
  shape3ShadowFactor: 15,
  shape3ShadowPosX: 0,
  shape3ShadowPosY: -10,
};

export interface LiquidGlassAppProps {
  bgImage?: string;
  leftGlassRect?: { x: number; y: number; width: number; height: number; radius: number };
  rightSidebarRect?: { x: number; y: number; width: number; height: number };
  onDeepAnalysis?: () => void;
}

const LiquidGlassApp = ({
  bgImage = '/O.webp',
  leftGlassRect,
  rightSidebarRect,
  onDeepAnalysis,
}: LiquidGlassAppProps) => {
  // ── Refs ─────────────────────────────────────────────────────────────────
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<MultiPassRenderer | null>(null);
  const leftGlassRectRef = useRef(leftGlassRect);
  const rightSidebarRectRef = useRef(rightSidebarRect);
  const rafRef = useRef<number>(0);

  const stateRef = useRef<{
    canvasInfo: { width: number; height: number; dpr: number };
    blurWeights: number[];
    canvasPointerPos: { x: number; y: number };
    mouseSpringPos: { x: number; y: number };
    mouseSpringSpeed: { x: number; y: number };
    lastMouseSpringTime: number | null;
    lastMouseSpringValue: { x: number; y: number };
    bgTexture: WebGLTexture | null;
    bgTextureRatio: number;
    bgTextureReady: boolean;
    shape1CenterX: number;
    shape1CenterY: number;
    shape1CenterTargetX: number;
    shape1CenterTargetY: number;
    shape1Width: number;
    shape1WidthTarget: number;
    shape1Height: number;
    shape1HeightTarget: number;
    shape1Radius: number;
    shape1RadiusTarget: number;
    // WebGL 独立控制的 shape3 宽度（动画中）
    shape3Width: number;
    shape3WidthTarget: number;
  }>({
    canvasInfo: { width: window.innerWidth, height: window.innerHeight, dpr: window.devicePixelRatio || 1 },
    blurWeights: [],
    canvasPointerPos: { x: 0, y: 0 },
    mouseSpringPos: { x: 0, y: 0 },
    mouseSpringSpeed: { x: 0, y: 0 },
    lastMouseSpringTime: null,
    lastMouseSpringValue: { x: 0, y: 0 },
    bgTexture: null,
    bgTextureRatio: 1,
    bgTextureReady: false,
    shape1CenterX: 124,
    shape1CenterY: window.innerHeight / 2,
    shape1CenterTargetX: 124,
    shape1CenterTargetY: window.innerHeight / 2,
    shape1Width: 220,
    shape1WidthTarget: 220,
    shape1Height: 800,
    shape1HeightTarget: 800,
    shape1Radius: 40,
    shape1RadiusTarget: 40,
    shape3Width: 260,
    shape3WidthTarget: 260,
  });

  // ── Zustand store + paramsRef ────────────────────────────────────────
  const glassStore = useGlassParamsStore;
  const p = glassStore.getState();
  const paramsRef = useRef({
    shapeWidth: p.shapeWidth, shapeHeight: p.shapeHeight, shapeRadius: p.shapeRadius,
    shapeRoundness: p.shapeRoundness, mergeRate: p.mergeRate, blurRadius: p.blurRadius,
    refThickness: p.refThickness, refFactor: p.refFactor, refDispersion: p.refDispersion,
    refFresnelRange: p.refFresnelRange, refFresnelHardness: p.refFresnelHardness,
    refFresnelFactor: p.refFresnelFactor, glareRange: p.glareRange, glareFactor: p.glareFactor,
    glareAngle: p.glareAngle, glareHardness: p.glareHardness, glareConvergence: p.glareConvergence,
    glareOppositeFactor: p.glareOppositeFactor, shadowExpand: p.shadowExpand,
    shadowFactor: p.shadowFactor, blurEdge: p.blurEdge, showShape1: false, step: 9, springSizeFactor: 0,
    shapePosX: p.shapePosX, shapePosY: p.shapePosY,
    // shape3
    shape3Radius: p.shape3Radius, shape3Roundness: p.shape3Roundness,
    shape3RefThickness: p.shape3RefThickness, shape3RefFactor: p.shape3RefFactor,
    shape3RefDispersion: p.shape3RefDispersion, shape3GlareFactor: p.shape3GlareFactor,
    shape3GlareAngle: p.shape3GlareAngle, shape3GlareHardness: p.shape3GlareHardness,
    shape3GlareConvergence: p.shape3GlareConvergence, shape3GlareOppositeFactor: p.shape3GlareOppositeFactor,
    shape3GlareRange: p.shape3GlareRange, shape3ShadowExpand: p.shape3ShadowExpand,
    shape3ShadowFactor: p.shape3ShadowFactor, shape3ShadowPosX: p.shape3ShadowPosX, shape3ShadowPosY: p.shape3ShadowPosY,
  });
  useEffect(() => {
    return glassStore.subscribe((s) => {
      Object.assign(paramsRef.current, s, { step: 9, springSizeFactor: 0 });
    });
  }, []);

  // ── Leva 控制面板（两文件夹 → Zustand 持久化）─────────────────────────
  useControls('左侧栏', {
    shapeWidth: { value: p.shapeWidth, min: 20, max: 800, step: 1, onChange: (v) => glassStore.getState().setParam('shapeWidth', v) },
    shapeHeight: { value: p.shapeHeight, min: 20, max: 1600, step: 1, onChange: (v) => glassStore.getState().setParam('shapeHeight', v) },
    shapeRadius: { value: p.shapeRadius, min: 1, max: 100, step: 0.1, onChange: (v) => glassStore.getState().setParam('shapeRadius', v) },
    shapeRoundness: { value: p.shapeRoundness, min: 2, max: 7, step: 0.01, onChange: (v) => glassStore.getState().setParam('shapeRoundness', v) },
    mergeRate: { value: p.mergeRate, min: 0, max: 0.3, step: 0.01, onChange: (v) => glassStore.getState().setParam('mergeRate', v) },
    blurRadius: { value: p.blurRadius, min: 1, max: 200, step: 1, onChange: (v) => glassStore.getState().setParam('blurRadius', v) },
    refThickness: { value: p.refThickness, min: 1, max: 80, step: 0.01, onChange: (v) => glassStore.getState().setParam('refThickness', v) },
    refFactor: { value: p.refFactor, min: 1, max: 4, step: 0.01, onChange: (v) => glassStore.getState().setParam('refFactor', v) },
    refDispersion: { value: p.refDispersion, min: 0, max: 50, step: 0.01, onChange: (v) => glassStore.getState().setParam('refDispersion', v) },
    refFresnelRange: { value: p.refFresnelRange, min: 0, max: 100, step: 0.01, onChange: (v) => glassStore.getState().setParam('refFresnelRange', v) },
    refFresnelHardness: { value: p.refFresnelHardness, min: 0, max: 100, step: 0.01, onChange: (v) => glassStore.getState().setParam('refFresnelHardness', v) },
    refFresnelFactor: { value: p.refFresnelFactor, min: 0, max: 100, step: 0.01, onChange: (v) => glassStore.getState().setParam('refFresnelFactor', v) },
    glareRange: { value: p.glareRange, min: 0, max: 100, step: 0.01, onChange: (v) => glassStore.getState().setParam('glareRange', v) },
    glareFactor: { value: p.glareFactor, min: 0, max: 120, step: 0.01, onChange: (v) => glassStore.getState().setParam('glareFactor', v) },
    glareAngle: { value: p.glareAngle, min: -180, max: 180, step: 0.01, onChange: (v) => glassStore.getState().setParam('glareAngle', v) },
    glareHardness: { value: p.glareHardness, min: 0, max: 100, step: 0.01, onChange: (v) => glassStore.getState().setParam('glareHardness', v) },
    glareConvergence: { value: p.glareConvergence, min: 0, max: 100, step: 0.01, onChange: (v) => glassStore.getState().setParam('glareConvergence', v) },
    glareOppositeFactor: { value: p.glareOppositeFactor, min: 0, max: 100, step: 0.01, onChange: (v) => glassStore.getState().setParam('glareOppositeFactor', v) },
    shadowExpand: { value: p.shadowExpand, min: 2, max: 100, step: 0.01, onChange: (v) => glassStore.getState().setParam('shadowExpand', v) },
    shadowFactor: { value: p.shadowFactor, min: 0, max: 100, step: 0.01, onChange: (v) => glassStore.getState().setParam('shadowFactor', v) },
    blurEdge: { value: p.blurEdge, onChange: (v) => glassStore.getState().setParam('blurEdge', v) },
    step: { value: 9, min: 0, max: 9, step: 1 },
    springSizeFactor: { value: 0, min: 0, max: 50, step: 0.01 },
    shapePosX: { value: p.shapePosX, min: 0, max: 800, step: 1, onChange: (v) => glassStore.getState().setParam('shapePosX', v) },
    shapePosY: { value: p.shapePosY, min: 0, max: 1200, step: 1, onChange: (v) => glassStore.getState().setParam('shapePosY', v) },
  });

  useControls('右侧栏', {
    shape3Radius: { value: p.shape3Radius, min: 1, max: 200, step: 1, onChange: (v) => glassStore.getState().setParam('shape3Radius', v) },
    shape3Roundness: { value: p.shape3Roundness, min: 2, max: 7, step: 0.01, onChange: (v) => glassStore.getState().setParam('shape3Roundness', v) },
    shape3RefThickness: { value: p.shape3RefThickness, min: 1, max: 80, step: 0.01, onChange: (v) => glassStore.getState().setParam('shape3RefThickness', v) },
    shape3RefFactor: { value: p.shape3RefFactor, min: 1, max: 4, step: 0.01, onChange: (v) => glassStore.getState().setParam('shape3RefFactor', v) },
    shape3RefDispersion: { value: p.shape3RefDispersion, min: 0, max: 50, step: 0.01, onChange: (v) => glassStore.getState().setParam('shape3RefDispersion', v) },
    shape3GlareFactor: { value: p.shape3GlareFactor, min: 0, max: 120, step: 0.01, onChange: (v) => glassStore.getState().setParam('shape3GlareFactor', v) },
    shape3GlareAngle: { value: p.shape3GlareAngle, min: -180, max: 180, step: 0.01, onChange: (v) => glassStore.getState().setParam('shape3GlareAngle', v) },
    shape3GlareHardness: { value: p.shape3GlareHardness, min: 0, max: 100, step: 0.01, onChange: (v) => glassStore.getState().setParam('shape3GlareHardness', v) },
    shape3GlareConvergence: { value: p.shape3GlareConvergence, min: 0, max: 100, step: 0.01, onChange: (v) => glassStore.getState().setParam('shape3GlareConvergence', v) },
    shape3GlareOppositeFactor: { value: p.shape3GlareOppositeFactor, min: 0, max: 100, step: 0.01, onChange: (v) => glassStore.getState().setParam('shape3GlareOppositeFactor', v) },
    shape3GlareRange: { value: p.shape3GlareRange, min: 0, max: 100, step: 0.01, onChange: (v) => glassStore.getState().setParam('shape3GlareRange', v) },
    shape3ShadowExpand: { value: p.shape3ShadowExpand, min: 2, max: 100, step: 0.01, onChange: (v) => glassStore.getState().setParam('shape3ShadowExpand', v) },
    shape3ShadowFactor: { value: p.shape3ShadowFactor, min: 0, max: 100, step: 0.01, onChange: (v) => glassStore.getState().setParam('shape3ShadowFactor', v) },
  });

  // ── Sync rightSidebarRect prop → ref ─────────────────────────────────
  useEffect(() => {
    leftGlassRectRef.current = leftGlassRect;
    if (leftGlassRect) {
      stateRef.current.shape1CenterTargetX = leftGlassRect.x + leftGlassRect.width / 2;
      stateRef.current.shape1CenterTargetY = window.innerHeight - leftGlassRect.y - leftGlassRect.height / 2;
      stateRef.current.shape1WidthTarget = leftGlassRect.width;
      stateRef.current.shape1HeightTarget = leftGlassRect.height;
      stateRef.current.shape1RadiusTarget = leftGlassRect.radius;
    }
  }, [leftGlassRect]);

  useEffect(() => {
    rightSidebarRectRef.current = rightSidebarRect;
    if (rightSidebarRect) {
      stateRef.current.shape3WidthTarget = rightSidebarRect.width;
    }
  }, [rightSidebarRect]);

  // Init canvas size
  useLayoutEffect(() => {
    const onResize = () => {
      stateRef.current.canvasInfo = {
        width: window.innerWidth,
        height: window.innerHeight,
        dpr: window.devicePixelRatio || 1,
      };
    };
    window.addEventListener('resize', onResize);
    onResize();
    return () => window.removeEventListener('resize', onResize);
  }, []);

  // Init renderer
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ci = stateRef.current.canvasInfo;
    canvas.width = ci.width * ci.dpr;
    canvas.height = ci.height * ci.dpr;

    try {
      const renderer = new MultiPassRenderer(canvas, [
        { name: 'bgPass', shader: { vertex: VertexShader, fragment: FragmentBgShader } },
        { name: 'vBlurPass', shader: { vertex: VertexShader, fragment: FragmentBgVblurShader }, inputs: { u_prevPassTexture: 'bgPass' } },
        { name: 'hBlurPass', shader: { vertex: VertexShader, fragment: FragmentBgHblurShader }, inputs: { u_prevPassTexture: 'vBlurPass' } },
        { name: 'mainPass', shader: { vertex: VertexShader, fragment: FragmentMainShader }, inputs: { u_blurredBg: 'hBlurPass', u_bg: 'bgPass' }, outputToScreen: true },
      ]);
      rendererRef.current = renderer;
    } catch (e) {
      console.error('Failed to create renderer:', e);
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
    const canvas = canvasRef.current;
    const renderer = rendererRef.current;
    if (!canvas || !renderer) return;

    const gl = renderer.getGL();

    stateRef.current.bgTextureReady = false;

    loadTextureFromURL(gl, bgImage).then(({ texture, ratio }) => {
      stateRef.current.bgTexture = texture;
      stateRef.current.bgTextureRatio = ratio;
      stateRef.current.bgTextureReady = true;
    }).catch(err => {
      console.warn('Failed to load background image:', err);
    });

    return () => {
      if (stateRef.current.bgTexture) {
        gl.deleteTexture(stateRef.current.bgTexture);
        stateRef.current.bgTexture = null;
      }
    };
  }, [bgImage]);

  // Mouse tracking
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const onPointerMove = (e: PointerEvent) => {
      const ci = stateRef.current.canvasInfo;
      stateRef.current.canvasPointerPos = {
        x: e.clientX * ci.dpr,
        y: (ci.height - e.clientY) * ci.dpr,
      };

      const pos = stateRef.current.canvasPointerPos;
      const now = Date.now();
      const lastTime = stateRef.current.lastMouseSpringTime;
      if (lastTime !== null) {
        const lastVal = stateRef.current.lastMouseSpringValue;
        const dt = now - lastTime;
        stateRef.current.mouseSpringSpeed = {
          x: (pos.x - lastVal.x) / dt,
          y: (pos.y - lastVal.y) / dt,
        };
      }
      stateRef.current.lastMouseSpringTime = now;
      stateRef.current.lastMouseSpringValue = { x: pos.x, y: pos.y };

      stateRef.current.mouseSpringPos = { x: pos.x, y: pos.y };
    };

    canvas.addEventListener('pointermove', onPointerMove);
    return () => canvas.removeEventListener('pointermove', onPointerMove);
  }, []);

  // Compute blur weights (reactive to store paramsRef)
  useEffect(() => {
    stateRef.current.blurWeights = computeGaussianKernelByRadius(paramsRef.current.blurRadius);
  }, []);

  // Animation loop
  useEffect(() => {
    const render = () => {
      rafRef.current = requestAnimationFrame(render);

      const renderer = rendererRef.current;
      if (!renderer) return;

      const canvas = canvasRef.current;
      if (!canvas) return;

      const ci = stateRef.current.canvasInfo;
      const ctrls = paramsRef.current;

      // Resize if needed
      if (canvas.width !== ci.width * ci.dpr || canvas.height !== ci.height * ci.dpr) {
        canvas.width = ci.width * ci.dpr;
        canvas.height = ci.height * ci.dpr;
        renderer.resize(canvas.width, canvas.height);
        renderer.setUniform('u_resolution', [canvas.width, canvas.height]);
      }

      // Spring 动画：shape1/shape3 向目标几何逼近
      const positionLerp = 0.42;
      const sizeLerp = 0.46;
      const radiusLerp = 0.38;
      const shape1CenterDiffX = stateRef.current.shape1CenterTargetX - stateRef.current.shape1CenterX;
      const shape1CenterDiffY = stateRef.current.shape1CenterTargetY - stateRef.current.shape1CenterY;
      const shape1WidthDiff = stateRef.current.shape1WidthTarget - stateRef.current.shape1Width;
      const shape1HeightDiff = stateRef.current.shape1HeightTarget - stateRef.current.shape1Height;
      const shape1RadiusDiff = stateRef.current.shape1RadiusTarget - stateRef.current.shape1Radius;

      stateRef.current.shape1CenterX += shape1CenterDiffX * positionLerp;
      stateRef.current.shape1CenterY += shape1CenterDiffY * positionLerp;
      stateRef.current.shape1Width += shape1WidthDiff * sizeLerp;
      stateRef.current.shape1Height += shape1HeightDiff * sizeLerp;
      stateRef.current.shape1Radius += shape1RadiusDiff * radiusLerp;

      if (Math.abs(shape1CenterDiffX) < 0.1) stateRef.current.shape1CenterX = stateRef.current.shape1CenterTargetX;
      if (Math.abs(shape1CenterDiffY) < 0.1) stateRef.current.shape1CenterY = stateRef.current.shape1CenterTargetY;
      if (Math.abs(shape1WidthDiff) < 0.1) stateRef.current.shape1Width = stateRef.current.shape1WidthTarget;
      if (Math.abs(shape1HeightDiff) < 0.1) stateRef.current.shape1Height = stateRef.current.shape1HeightTarget;
      if (Math.abs(shape1RadiusDiff) < 0.1) stateRef.current.shape1Radius = stateRef.current.shape1RadiusTarget;

      const wDiff = stateRef.current.shape3WidthTarget - stateRef.current.shape3Width;
      stateRef.current.shape3Width += wDiff * sizeLerp;
      if (Math.abs(wDiff) < 0.1) stateRef.current.shape3Width = stateRef.current.shape3WidthTarget;

      // Clear
      const gl = renderer.getGL();
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

      // Shape size with spring speed
      const shapeSizeSpring = {
        x: stateRef.current.shape1Width + Math.abs(stateRef.current.mouseSpringSpeed.x) * stateRef.current.shape1Width * ctrls.springSizeFactor / 100,
        y: stateRef.current.shape1Height + Math.abs(stateRef.current.mouseSpringSpeed.y) * stateRef.current.shape1Height * ctrls.springSizeFactor / 100,
      };

      renderer.setUniforms({
        u_resolution: [canvas.width, canvas.height],
        u_dpr: ci.dpr,
        u_blurWeights: stateRef.current.blurWeights,
        u_blurRadius: ctrls.blurRadius,
        u_mouse: [stateRef.current.canvasPointerPos.x, stateRef.current.canvasPointerPos.y],
        u_mouseSpring: [stateRef.current.shape1CenterX * ci.dpr, stateRef.current.shape1CenterY * ci.dpr],
        u_shapeWidth: shapeSizeSpring.x,
        u_shapeHeight: shapeSizeSpring.y,
        u_shapeRadius: stateRef.current.shape1Radius,
        u_shapeRoundness: ctrls.shapeRoundness,
        u_mergeRate: ctrls.mergeRate,
        u_glareAngle: (ctrls.glareAngle * Math.PI) / 180,
        u_showShape1: leftGlassRectRef.current && leftGlassRectRef.current.width > 0 ? 1 : 0,
        // shape3 (右侧栏)
        u_shape3PosX: rightSidebarRectRef.current ? (rightSidebarRectRef.current.x + rightSidebarRectRef.current.width / 2) * ci.dpr : 0,
        u_shape3PosY: rightSidebarRectRef.current ? (ci.height - rightSidebarRectRef.current.y - rightSidebarRectRef.current.height / 2) * ci.dpr : 0,
        u_shape3Width: rightSidebarRectRef.current ? rightSidebarRectRef.current.width : 0,
        u_shape3Height: rightSidebarRectRef.current ? rightSidebarRectRef.current.height : 0,
        u_shape3Radius: ctrls.shape3Radius / ci.dpr,
        u_shape3Roundness: ctrls.shapeRoundness,
        u_showShape3: rightSidebarRectRef.current && rightSidebarRectRef.current.width > 0 ? 1 : 0,
      });

      renderer.render({
        bgPass: {
          u_bgType: 11,
          u_bgTexture: stateRef.current.bgTexture ?? undefined,
          u_bgTextureRatio: stateRef.current.bgTextureRatio,
          u_bgTextureReady: stateRef.current.bgTextureReady ? 1 : 0,
          u_shadowExpand: ctrls.shadowExpand,
          u_shadowFactor: ctrls.shadowFactor / 100,
          u_shadowPosition: [DEFAULT_CONTROLS.shadowPosition.x, DEFAULT_CONTROLS.shadowPosition.y],
          u_showShape3: rightSidebarRectRef.current && rightSidebarRectRef.current.width > 0 ? 1 : 0,
          u_shape3PosX: rightSidebarRectRef.current ? (rightSidebarRectRef.current.x + rightSidebarRectRef.current.width / 2) * ci.dpr : 0,
          u_shape3PosY: rightSidebarRectRef.current ? (ci.height - rightSidebarRectRef.current.y - rightSidebarRectRef.current.height / 2) * ci.dpr : 0,
          u_shape3Width: rightSidebarRectRef.current ? rightSidebarRectRef.current.width : 0,
          u_shape3Height: rightSidebarRectRef.current ? rightSidebarRectRef.current.height : 0,
          u_shape3Radius: ctrls.shape3Radius / ci.dpr,
          u_shape3Roundness: ctrls.shapeRoundness,
        },
        mainPass: {
          u_tint: [
            DEFAULT_CONTROLS.tint.r / 255,
            DEFAULT_CONTROLS.tint.g / 255,
            DEFAULT_CONTROLS.tint.b / 255,
            DEFAULT_CONTROLS.tint.a,
          ],
          u_refThickness: ctrls.refThickness,
          u_refFactor: ctrls.refFactor,
          u_refDispersion: ctrls.refDispersion,
          u_refFresnelRange: ctrls.refFresnelRange,
          u_refFresnelHardness: ctrls.refFresnelHardness / 100,
          u_refFresnelFactor: ctrls.refFresnelFactor / 100,
          u_glareRange: ctrls.glareRange,
          u_glareHardness: ctrls.glareHardness / 100,
          u_glareConvergence: ctrls.glareConvergence / 100,
          u_glareOppositeFactor: ctrls.glareOppositeFactor / 100,
          u_glareFactor: ctrls.glareFactor / 100,
          u_blurEdge: ctrls.blurEdge ? 1 : 0,
          STEP: ctrls.step,
        },
      });
    };

    rafRef.current = requestAnimationFrame(render);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  return (
    <>
      <canvas
        ref={canvasRef}
        style={{
          position: 'fixed',
          inset: 0,
          width: '100%',
          height: '100%',
          display: 'block',
          pointerEvents: 'auto',
        }}
      />
      {/* 深度分析按钮 */}
      <div style={{
        position: 'fixed',
        top: 12,
        right: 12,
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-end',
        gap: 8,
      }}>
        <button
          onClick={onDeepAnalysis}
          style={{
            padding: '8px 18px',
            background: 'linear-gradient(180deg, rgba(255,210,120,0.20) 0%, rgba(212,160,48,0.14) 50%, rgba(184,115,51,0.08) 100%)',
            backdropFilter: 'blur(20px) saturate(180%)',
            WebkitBackdropFilter: 'blur(20px) saturate(180%)',
            border: 'none',
            borderRadius: 9999,
            color: '#e8c56a',
            cursor: 'pointer',
            fontSize: 13,
            fontWeight: 600,
            boxShadow: `
              0 0 0 0.8px rgba(255,200,100,0.40),
              0 0 6px 1px rgba(255,180,80,0.35),
              0 0 14px 3px rgba(255,160,60,0.20),
              0 0 24px 5px rgba(255,140,40,0.10),
              0 4px 16px rgba(184,115,51,0.20),
              inset 0 1.5px 0 rgba(255,230,170,0.70),
              inset 0 3px 6px rgba(255,210,140,0.18),
              inset 0 -1px 0 rgba(140,80,30,0.20)
            `,
          }}
        >
          ◈ 深度分析
        </button>
      </div>
    </>
  );
};

export default LiquidGlassApp;
