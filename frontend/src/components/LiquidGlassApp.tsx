/**
 * LiquidGlassApp — 复制自 liquid-glass-studio/src/App.tsx
 *
 * 变更：
 * - 背景默认使用 /bg.jpg（u_bgType = 11）
 * - 删除 ResizableWindow，canvas 全屏
 * - 保留 Leva 参数调控面板
 *
 * Shader 逻辑、渲染管线、uniform 名字：零改动
 */

import { useEffect, useLayoutEffect, useRef, useState, useCallback } from 'react';
import { useControls, levaStore } from 'leva';
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
// Controls — 从 Leva 迁移为硬编码默认值
// 后续由 props 传入
// ============================================
interface Controls {
  bgType: number;            // 默认 11 = 自定义图片
  shapeWidth: number;
  shapeHeight: number;
  shapeRadius: number;        // 百分比，相对于 shapeWidth/Height
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
  refFresnelHardness: number;     // 0-100，shader 中 /100
  refFresnelFactor: number;       // 0-100，shader 中 /100
  glareRange: number;
  glareFactor: number;             // 0-100，shader 中 /100
  glareAngle: number;
  glareHardness: number;          // 0-100，shader 中 /100
  glareConvergence: number;        // 0-100，shader 中 /100
  glareOppositeFactor: number;     // 0-100，shader 中 /100
  blurEdge: boolean;
  step: number;
  springSizeFactor: number;
  shapePosX: number;  // 玻璃区域固定位置 X（像素）
  shapePosY: number;  // 玻璃区域固定位置 Y（像素）
}

// 参考项目 liquid-glass-studio 的原始默认值（fallback）
const DEFAULT_CONTROLS: Controls = {
  bgType: 11,              // 自定义图片
  shapeWidth: 220,         // 左侧栏宽度
  shapeHeight: 800,
  shapeRadius: 40,
  shapeRoundness: 2.0,
  mergeRate: 0.05,
  showShape1: false,
  blurRadius: 1,
  shadowExpand: 25,
  shadowFactor: 15,        // shader 中 /100
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
};
export interface LiquidGlassAppProps {
  bgImage?: string;
}

// ============================================
// Component
// ============================================
const LiquidGlassApp: React.FC<LiquidGlassAppProps> = ({
  bgImage = '/bg.jpg',
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<MultiPassRenderer | null>(null);
  const rafRef = useRef<number>(0);
  const [presetLoading, setPresetLoading] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
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
  });

  // Leva 实时参数调控 — useControls 返回稳定引用，直接在 RAF 中使用
  const levaControls = useControls('液态玻璃参数', {
    shapeWidth: { value: DEFAULT_CONTROLS.shapeWidth, min: 20, max: 800, step: 1 },
    shapeHeight: { value: DEFAULT_CONTROLS.shapeHeight, min: 20, max: 1600, step: 1 },
    shapeRadius: { value: DEFAULT_CONTROLS.shapeRadius, min: 1, max: 100, step: 0.1 },
    shapeRoundness: { value: DEFAULT_CONTROLS.shapeRoundness, min: 2, max: 7, step: 0.01 },
    mergeRate: { value: DEFAULT_CONTROLS.mergeRate, min: 0, max: 0.3, step: 0.01 },
    showShape1: DEFAULT_CONTROLS.showShape1,
    blurRadius: { value: DEFAULT_CONTROLS.blurRadius, min: 1, max: 200, step: 1 },
    refThickness: { value: DEFAULT_CONTROLS.refThickness, min: 1, max: 80, step: 0.01 },
    refFactor: { value: DEFAULT_CONTROLS.refFactor, min: 1, max: 4, step: 0.01 },
    refDispersion: { value: DEFAULT_CONTROLS.refDispersion, min: 0, max: 50, step: 0.01 },
    refFresnelRange: { value: DEFAULT_CONTROLS.refFresnelRange, min: 0, max: 100, step: 0.01 },
    refFresnelHardness: { value: DEFAULT_CONTROLS.refFresnelHardness, min: 0, max: 100, step: 0.01 },
    refFresnelFactor: { value: DEFAULT_CONTROLS.refFresnelFactor, min: 0, max: 100, step: 0.01 },
    glareRange: { value: DEFAULT_CONTROLS.glareRange, min: 0, max: 100, step: 0.01 },
    glareFactor: { value: DEFAULT_CONTROLS.glareFactor, min: 0, max: 120, step: 0.01 },
    glareAngle: { value: DEFAULT_CONTROLS.glareAngle, min: -180, max: 180, step: 0.01 },
    glareHardness: { value: DEFAULT_CONTROLS.glareHardness, min: 0, max: 100, step: 0.01 },
    glareConvergence: { value: DEFAULT_CONTROLS.glareConvergence, min: 0, max: 100, step: 0.01 },
    glareOppositeFactor: { value: DEFAULT_CONTROLS.glareOppositeFactor, min: 0, max: 100, step: 0.01 },
    shadowExpand: { value: DEFAULT_CONTROLS.shadowExpand, min: 2, max: 100, step: 0.01 },
    shadowFactor: { value: DEFAULT_CONTROLS.shadowFactor, min: 0, max: 100, step: 0.01 },
    blurEdge: DEFAULT_CONTROLS.blurEdge,
    step: { value: DEFAULT_CONTROLS.step, min: 0, max: 9, step: 1 },
    springSizeFactor: { value: DEFAULT_CONTROLS.springSizeFactor, min: 0, max: 50, step: 0.01 },
    shapePosX: { value: DEFAULT_CONTROLS.shapePosX, min: 0, max: 800, step: 1 },
    shapePosY: { value: DEFAULT_CONTROLS.shapePosY, min: 0, max: 1200, step: 1 },
  });

  // 启动时从 /presets/default.json 读取默认参数
  useEffect(() => {
    setPresetLoading(true);
    fetch('/presets/default.json')
      .then(r => r.json())
      .then(preset => {
        const p = preset.params;
        // Leva 内部用 '.' 做路径分隔符，如 '液态玻璃参数.shapeWidth'
        const prefix = '液态玻璃参数';
        const overrides: [string, unknown][] = [
          [`${prefix}.shapeWidth`, p.shapeWidth],
          [`${prefix}.shapeHeight`, p.shapeHeight ?? 800],
          [`${prefix}.shapeRadius`, p.shapeRadius],
          [`${prefix}.shapeRoundness`, p.shapeRoundness],
          [`${prefix}.mergeRate`, p.mergeRate],
          [`${prefix}.blurRadius`, p.blurRadius],
          [`${prefix}.refThickness`, p.refThickness],
          [`${prefix}.refFactor`, p.refFactor],
          [`${prefix}.refDispersion`, p.refDispersion],
          [`${prefix}.refFresnelRange`, p.refFresnelRange],
          [`${prefix}.refFresnelHardness`, p.refFresnelHardness],
          [`${prefix}.refFresnelFactor`, p.refFresnelFactor],
          [`${prefix}.glareRange`, p.glareRange],
          [`${prefix}.glareFactor`, p.glareFactor],
          [`${prefix}.glareAngle`, p.glareAngle],
          [`${prefix}.glareHardness`, p.glareHardness],
          [`${prefix}.glareConvergence`, p.glareConvergence],
          [`${prefix}.glareOppositeFactor`, p.glareOppositeFactor],
          [`${prefix}.shadowExpand`, p.shadowExpand],
          [`${prefix}.shadowFactor`, p.shadowFactor],
          [`${prefix}.blurEdge`, !!p.blurEdge],
          [`${prefix}.step`, 9],
          [`${prefix}.springSizeFactor`, 0],
          [`${prefix}.shapePosX`, p.shapePosX ?? 110],
          [`${prefix}.shapePosY`, p.shapePosY ?? 450],
        ];
        overrides.forEach(([k, v]) => {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          try { (levaStore as any).setValueAtPath(k, v, 0); } catch (e) { console.warn('setValueAtPath failed:', k, e); }
        });
      })
      .catch(() => { /* 用 DEFAULT_CONTROLS */ })
      .finally(() => setPresetLoading(false));
  }, []);

  // 保存当前参数到 default.json
  const handleSavePreset = useCallback(async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const allData = (levaStore as any).getData() as Record<string, { value: unknown }>;
    if (!allData) { setSaveMsg('❌ 读取失败'); setTimeout(() => setSaveMsg(null), 3000); return; }
    // 提取所有 '液态玻璃参数.' 开头的路径值
    const values: Record<string, unknown> = {};
    const prefix = '液态玻璃参数.';
    Object.entries(allData).forEach(([k, v]) => {
      if (k.startsWith(prefix)) values[k.slice(prefix.length)] = v.value;
    });
    const preset = {
      name: 'default',
      component: 'liquid-glass',
      params: {
        shapeWidth: values.shapeWidth,
        shapeHeight: values.shapeHeight,
        shapeRadius: values.shapeRadius,
        shapeRoundness: values.shapeRoundness,
        mergeRate: values.mergeRate,
        blurRadius: values.blurRadius,
        refThickness: values.refThickness,
        refFactor: values.refFactor,
        refDispersion: values.refDispersion,
        refFresnelRange: values.refFresnelRange,
        refFresnelHardness: values.refFresnelHardness,
        refFresnelFactor: values.refFresnelFactor,
        glareRange: values.glareRange,
        glareFactor: values.glareFactor,
        glareAngle: values.glareAngle,
        glareHardness: values.glareHardness,
        glareConvergence: values.glareConvergence,
        glareOppositeFactor: values.glareOppositeFactor,
        shadowExpand: values.shadowExpand,
        shadowFactor: values.shadowFactor,
        blurEdge: values.blurEdge,
        shapePosX: values.shapePosX,
        shapePosY: values.shapePosY,
      },
    };
    try {
      const res = await fetch('http://localhost:8002/api/glass-preset/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preset),
      });
      const result = await res.json();
      setSaveMsg(result.success ? '✅ 已保存' : '❌ 保存失败');
    } catch {
      setSaveMsg('❌ 保存失败');
    }
    setTimeout(() => setSaveMsg(null), 3000);
  }, []);

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

    // Start loading
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

      // Spring update
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

      // Lerp mouseSpringPos toward canvasPointerPos
      stateRef.current.mouseSpringPos = { x: pos.x, y: pos.y };
    };

    canvas.addEventListener('pointermove', onPointerMove);
    return () => canvas.removeEventListener('pointermove', onPointerMove);
  }, []);

  // Compute blur weights (reactive to levaControls)
  useEffect(() => {
    stateRef.current.blurWeights = computeGaussianKernelByRadius(levaControls.blurRadius);
  }, [levaControls.blurRadius]);

  // Animation loop
  useEffect(() => {
    const render = () => {
      rafRef.current = requestAnimationFrame(render);

      const renderer = rendererRef.current;
      if (!renderer) return;

      const canvas = canvasRef.current;
      if (!canvas) return;

      const ci = stateRef.current.canvasInfo;
      const ctrls = levaControls;

      // Resize if needed
      if (canvas.width !== ci.width * ci.dpr || canvas.height !== ci.height * ci.dpr) {
        canvas.width = ci.width * ci.dpr;
        canvas.height = ci.height * ci.dpr;
        renderer.resize(canvas.width, canvas.height);
        renderer.setUniform('u_resolution', [canvas.width, canvas.height]);
      }

      // Clear
      const gl = renderer.getGL();
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

      // Shape size with spring speed (kept from reference, not used in fixed mode)
      const shapeSizeSpring = {
        x: ctrls.shapeWidth + Math.abs(stateRef.current.mouseSpringSpeed.x) * ctrls.shapeWidth * ctrls.springSizeFactor / 100,
        y: ctrls.shapeHeight + Math.abs(stateRef.current.mouseSpringSpeed.y) * ctrls.shapeHeight * ctrls.springSizeFactor / 100,
      };

      renderer.setUniforms({
        u_resolution: [canvas.width, canvas.height],
        u_dpr: ci.dpr,
        u_blurWeights: stateRef.current.blurWeights,
        u_blurRadius: ctrls.blurRadius,
        u_mouse: [stateRef.current.canvasPointerPos.x, stateRef.current.canvasPointerPos.y],
        // 固定位置：左侧栏中心（需要乘以 dpr，shader 会转换坐标系）
        u_mouseSpring: [ctrls.shapePosX * ci.dpr, (ci.height - ctrls.shapePosY) * ci.dpr],
        u_shapeWidth: shapeSizeSpring.x,
        u_shapeHeight: shapeSizeSpring.y,
        u_shapeRadius: (Math.min(shapeSizeSpring.x, shapeSizeSpring.y) / 2 * ctrls.shapeRadius) / 100,
        u_shapeRoundness: ctrls.shapeRoundness,
        u_mergeRate: ctrls.mergeRate,
        u_glareAngle: (ctrls.glareAngle * Math.PI) / 180,
        u_showShape1: ctrls.showShape1 ? 1 : 0,
      });

      renderer.render({
        bgPass: {
          u_bgType: 11,  // 自定义图片
          u_bgTexture: stateRef.current.bgTexture ?? undefined,
          u_bgTextureRatio: stateRef.current.bgTextureRatio,
          u_bgTextureReady: stateRef.current.bgTextureReady ? 1 : 0,
          u_shadowExpand: ctrls.shadowExpand,
          u_shadowFactor: ctrls.shadowFactor / 100,
          u_shadowPosition: [DEFAULT_CONTROLS.shadowPosition.x, DEFAULT_CONTROLS.shadowPosition.y],
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
  }, [levaControls]);

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
        }}
      />
      {/* 保存按钮 */}
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
          onClick={handleSavePreset}
          disabled={presetLoading}
          style={{
            padding: '8px 16px',
            background: '#1a1a2e',
            color: '#fff',
            border: '1px solid #4a4a6a',
            borderRadius: 6,
            cursor: 'pointer',
            fontSize: 13,
            opacity: presetLoading ? 0.5 : 1,
          }}
        >
          {presetLoading ? '加载中…' : '💾 保存为默认'}
        </button>
        {saveMsg && (
          <span style={{
            color: saveMsg.includes('✅') ? '#4ade80' : '#f87171',
            fontSize: 12,
            background: 'rgba(0,0,0,0.7)',
            padding: '4px 10px',
            borderRadius: 4,
          }}>
            {saveMsg}
          </span>
        )}
      </div>
    </>
  );
};

export default LiquidGlassApp;
