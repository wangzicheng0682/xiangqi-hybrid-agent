---
name: WebGL液态玻璃UI层
type: plan
version: 1.0.0
date: 2026-03-30
owner: AI（自动维护）
changelog:
  - v1.0.0 (2026-03-30): 初始版本
---

# WebGL 液态玻璃 UI 层 — 复制粘贴参考项目

## 背景

将前端左侧栏和右侧栏改造成与 `liquid-glass-studio-main` 一模一样的 WebGL2 液态玻璃效果，UI 层除棋盘和扑克牌外全部 WebGL 化。

**核心原则**：能复制粘贴参考项目的代码，绝不自己写一行。所有 shader 逻辑原样照搬，只改 uniform 参数。

---

## 目标架构

```
z=0: WebGL Canvas (全屏 fixed，覆盖整个 viewport)
│     ├── bg.jpg 背景
│     ├── 左侧栏玻璃（折射 + 菲涅尔 + glare）
│     ├── 左侧栏按钮（SDF + Canvas2D 文字纹理）
│     ├── 右侧栏玻璃（折射 + 菲涅尔 + glare）
│     └── 右侧栏按钮（SDF + Canvas2D 文字纹理）
│
z=1: DOM — ChessBoard + PokerCard (z=10+)
```

- 整个 UI 层（侧边栏、按钮、背景）都是 canvas
- DOM 只承载棋盘和扑克牌
- 参考项目架构完全复用，不重写渲染器

---

## 参考项目文件清单

需要复制的文件（按优先级）：

| 优先级 | 文件 | 说明 |
|--------|------|------|
| P0 | `liquid-glass-studio-main/src/App.tsx` | 完整渲染循环，复制的起点 |
| P0 | `liquid-glass-studio-main/src/utils/GLUtils.ts` | MultiPassRenderer 等工具类 |
| P0 | `liquid-glass-studio-main/src/shaders/*.glsl` | 所有 shader 文件（已复制到 `frontend/src/shaders/liquidglass/`） |
| P1 | `liquid-glass-studio-main/src/utils/presetUtils.ts` | 预设参数工具 |
| P1 | `liquid-glass-studio-main/src/Controls.tsx` | 参数控件（参考控件名称） |
| P2 | `liquid-glass-studio-main/src/components/ResizableWindow/` | 窗口组件（参考 SDF 按钮实现） |

**不复制**：
- `LevaButton/` `LevaContainer/` `LevaImageUpload/` — Leva GUI 控件，不需要
- `PresetControls/` — 预设控件面板，不需要
- `ResizableWindow/` — 独立窗口框架，只参考其 SDF 按钮部分

---

## 实现步骤

### Phase 1：复制 + 最小适配（关键）

**目标**：让参考项目的渲染管线直接跑在象棋项目里，0 改动 shader。

1. 复制 `App.tsx` 到 `frontend/src/components/LiquidGlassApp.tsx`
2. 复制 `utils/GLUtils.ts` 到 `frontend/src/utils/GLUtils.ts`（覆盖已有的 `LiquidGlassGLUtils.ts`）
3. 删除 `LiquidGlassApp.tsx` 中的：
   - Leva GUI 相关 import 和使用
   - PresetControls 组件
   - ResizableWindow 包装（改为直接渲染 canvas）
   - 所有 `controls.*` 的 Leva 控件取值 → 改为硬编码参数
4. 删除 `Controls.tsx` 和所有 Leva 控件引用
5. 把背景图换成 `/bg.jpg`，默认开启图片背景（`u_bgType = 11`）
6. 验证：此时 canvas 应显示 `/bg.jpg` + 一个可拖动的玻璃矩形（来自鼠标位置）

**关键约束**：shader 代码、渲染管线、uniform 名字——**一个字都不改**

### Phase 2：固定玻璃矩形位置（替代鼠标拖动）

**目标**：把玻璃矩形从"鼠标拖动"改为"固定在 sidebar 位置"。

参考项目里 `u_mouseSpring` 是形状中心坐标，来自鼠标事件。改法：
- 删除鼠标监听
- 用固定坐标替代：`u_mouseSpring = [regionCenterX, regionCenterY]`
- 左侧栏 center = `(leftSidebarWidth / 2, canvasHeight / 2)`
- 右侧栏 center = `(canvasWidth - rightSidebarWidth / 2, canvasHeight / 2)`

两个 sidebar 用同一套 shader pass，通过**两组 uniform** 分别控制，或在 shader 中写死两组 SDF 形状。

### Phase 3：双区域渲染

**目标**：同时渲染左右两个 sidebar 玻璃区域。

在 `fragment-main.glsl` 的 `mainSDF` 中：
- 原有一个 circle (shape1) + 一个 roundedRect (shape2)
- 扩展为两个 roundedRect，分别对应左右 sidebar
- 分别传入两组 uniform：`u_shape2Width/Height` 和 `u_mouseSpring2`（右侧）

或者更简单：**两个 render pass**，分别渲染左右侧栏，统一用 `bg.jpg` 做背景。

### Phase 4：WebGL 按钮

**目标**：用 WebGL 渲染侧边栏按钮（文字 + 点击区域）。

参考项目没有独立的按钮实现，需自研：
1. 用 Canvas2D 在离屏 canvas 绘制文字（"人机对弈"、"局势分析"等）
2. 上传为 WebGL 纹理
3. 在 fragment shader 中用 SDF 矩形 + 纹理采样渲染按钮
4. 鼠标点击检测：在 TS 层做 AABB 检测，或在 shader 中用 `discard` 实现点击热区

**简化方案**：先用纯色 SDF 按钮（无文字），文字后续加。

### Phase 5：删除旧组件，清理 CSS

**目标**：移除已有的 LiquidGlass 相关组件和 CSS backdrop-filter 痕迹。

待删除：
- `frontend/src/components/LiquidGlassSurface.tsx`
- `frontend/src/components/LiquidGlassBackground.tsx`
- `frontend/src/components/LiquidGlassRendererMini.tsx`
- `frontend/src/components/LiquidCardSurface.tsx`
- `frontend/src/components/LiquidCardSurfaceLegacy.tsx`
- `frontend/src/hooks/useLiquidCardUniforms.ts`
- `frontend/src/utils/LiquidGlassConfig.ts`
- `frontend/src/utils/LiquidGlassGLUtils.ts`（被 GLUtils.ts 覆盖）
- `frontend/src/index.css` 中 `.lg-sidebar` 等相关 CSS

---

## 渲染管线（不变，直接复用）

```
requestAnimationFrame
├── bgPass (fragment-bg.glsl)
│     输入: u_bgTexture (bg.jpg)
│     输出: FBO texture (背景 + 阴影)
├── vBlurPass (fragment-bg-vblur.glsl)
│     输入: bgPass output
│     输出: 垂直模糊
├── hBlurPass (fragment-bg-hblur.glsl)
│     输入: vBlurPass output
│     输出: 水平模糊 = blurredBg
└── mainPass (fragment-main.glsl)
      输入: u_bg (bgPass) + u_blurredBg (hBlurPass)
      逻辑:
        - 玻璃内: 采样 blurredBg + 折射/菲涅尔/glare
        - 玻璃外: 采样 u_bg
```

---

## STEP 调试模式

| STEP | 内容 |
|------|------|
| 0 | SDF 可视化（黑白距离场） |
| 1 | SDF + 阴影等高线 |
| 2 | 法线可视化 |
| 3 | 边缘折射因子 |
| 4 | 边缘因子 × 法线 |
| 5 | 模糊背景 |
| 6 | 折射（无色散） |
| 7 | 折射 + 菲涅尔 |
| 8 | 折射 + 菲涅尔 + glare |
| **9** | **最终完整效果（默认）** |

调试验证时切换 `STEP: 9` → `STEP: 0` 逐步看效果。

---

## 待验证问题

1. 两个 sidebar 分别用两组 uniform 还是两个 render pass？两组 uniform 更省带宽。
2. WebGL 按钮点击检测：在 shader 中实现还是 TS 层做？
3. 右侧栏展开/收缩动画（`isBoardCollapsed`）如何同步到 WebGL？监听 store 变化，更新 `u_shapeWidth` uniform。
4. 文字纹理如何支持中文？Canvas2D 的 `ctx.fillText` 支持中文，无需特殊处理。

---

## 实现记录

### 2026-03-30 架构确认

- 确认方向：整个 UI 层 WebGL 化，DOM 只保留棋盘和扑克牌
- 确认原则：复制粘贴优先，不重写渲染器
- 发现问题：现有 `LiquidGlassRendererMini.tsx` 是重写的，未遵循复制粘贴原则
- 修复方向：直接复制 `App.tsx` 和 `GLUtils.ts`，在此基础上做最小适配

---

## 状态

- [x] 构思中
- [x] 验证中
- [x] Phase 1: 复制粘贴 App.tsx + GLUtils.ts ✅
- [x] Phase 1: 修 Maximum update depth 无限循环 ✅
- [x] Phase 1: Leva 参数调控面板接入 ✅
- [x] Phase 1: 参考项目原始参数（blurRadius=1, refThickness=20, refFactor=1.4） ✅
- [ ] Phase 2: 固定玻璃位置（替代鼠标拖动）— 进行中
- [ ] Phase 3: 双区域渲染
- [ ] Phase 4: WebGL 按钮
- [ ] Phase 5: 清理废弃组件

## 实现记录

### 2026-03-31 Phase 1 完成

- 直接复制 `liquid-glass-studio-main/src/utils/GLUtils.ts` → `frontend/src/utils/GLUtils.ts`
- 直接复制 `liquid-glass-studio-main/src/App.tsx` → `frontend/src/components/LiquidGlassApp.tsx`
- 删除 Leva GUI 外的所有不必要依赖（Leva 保留用于参数调控）
- 背景使用 `/bg.jpg`，默认 u_bgType=11
- 修复 React 无限循环：`controls` 从 `useState` 改为 `useControls`（Leva）直接驱动
- 接入 Leva 实时参数面板，可调节所有 25 个 shader uniform 参数
- 发现关键问题：参考项目默认 `blurRadius=1`（非 80），`refThickness=20`（非 80）
- 效果验证：玻璃有模糊折射感，glare 割裂感已通过降低 glareFactor 改善
