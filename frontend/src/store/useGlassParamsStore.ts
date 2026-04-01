/**
 * useGlassParamsStore — 液态玻璃参数持久化存储
 *
 * 使用 Zustand + persist 中间件，数据保存在 localStorage
 * 键名: 'glass-params'
 *
 * 架构：
 *   Leva GUI (useControls)
 *     ↕ 双向同步
 *   useGlassParamsStore (Zustand + localStorage)
 *     ↓ RAF 读取
 *   LiquidGlassApp → shader uniforms
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// ============================================
// Shape1（左侧栏）参数
// ============================================
interface Shape1Params {
  shapeWidth: number;
  shapeHeight: number;
  shapeRadius: number;
  shapeRoundness: number;
  mergeRate: number;
  blurRadius: number;
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
  shadowExpand: number;
  shadowFactor: number;
  blurEdge: boolean;
  springSizeFactor: number;
  shapePosX: number;
  shapePosY: number;
}

// ============================================
// Shape3（右侧栏）参数
// ============================================
interface Shape3Params {
  shape3Radius: number;
  shape3Roundness: number;
  shape3BlurRadius: number;
  shape3RefThickness: number;
  shape3RefFactor: number;
  shape3RefDispersion: number;
  shape3RefFresnelRange: number;
  shape3RefFresnelHardness: number;
  shape3RefFresnelFactor: number;
  shape3GlareRange: number;
  shape3GlareFactor: number;
  shape3GlareAngle: number;
  shape3GlareHardness: number;
  shape3GlareConvergence: number;
  shape3GlareOppositeFactor: number;
  shape3ShadowExpand: number;
  shape3ShadowFactor: number;
  shape3ShadowPosX: number;
  shape3ShadowPosY: number;
}

// ============================================
// Store 类型
// ============================================
type GlassParamsStore = Shape1Params & Shape3Params & {
  setParam: <K extends keyof GlassParamsStore>(key: K, value: GlassParamsStore[K]) => void;
  resetToDefaults: () => void;
};

// ============================================
// 默认值（Shape1 — 来自原 LiquidGlassApp.tsx DEFAULT_CONTROLS）
// ============================================
type GlassParamsData = Omit<GlassParamsStore, 'setParam' | 'resetToDefaults'>;
const DEFAULTS: GlassParamsData = {
  // Shape1
  shapeWidth: 220,
  shapeHeight: 800,
  shapeRadius: 40,
  shapeRoundness: 2.0,
  mergeRate: 0.05,
  blurRadius: 1,
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
  shadowExpand: 25,
  shadowFactor: 15,
  blurEdge: true,
  springSizeFactor: 0,
  shapePosX: 110,
  shapePosY: 450,
  // Shape3
  shape3Radius: 28,
  shape3Roundness: 2.0,
  shape3BlurRadius: 1,
  shape3RefThickness: 20,
  shape3RefFactor: 1.4,
  shape3RefDispersion: 0.6,
  shape3GlareConvergence: 60,
  shape3GlareOppositeFactor: 90,
  shape3RefFresnelRange: 30,
  shape3RefFresnelHardness: 12,
  shape3RefFresnelFactor: 60,
  shape3GlareRange: 250,
  shape3GlareFactor: 90,
  shape3GlareAngle: -45,
  shape3GlareHardness: 8,
  shape3ShadowExpand: 25,
  shape3ShadowFactor: 15,
  shape3ShadowPosX: 0,
  shape3ShadowPosY: -10,
};

// ============================================
// Store 实现
// ============================================
export const useGlassParamsStore = create<GlassParamsStore>()(
  persist(
    (set) => ({
      ...DEFAULTS,

      setParam: (key, value) => set({ [key]: value }),

      resetToDefaults: () => set({ ...DEFAULTS }),
    }),
    {
      name: 'glass-params',
    }
  )
);

export type { GlassParamsStore };
