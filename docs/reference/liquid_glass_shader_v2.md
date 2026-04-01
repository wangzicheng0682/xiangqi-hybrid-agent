# Liquid Glass Shader 重构方案 v2

> 本文档记录液态玻璃 shader 的完整病灶分析与重构方案。
> 状态：**分析进行中，部分修复已应用**

---

## 已修复

### 修复 1：DPR 单位混乱（`roundedRectSDF`）
- **文件**: `fragment-bg.glsl`, `fragment-main.glsl`
- **问题**: 调用处已归一化（`/ u_resolution.y`），函数内部又乘 `u_dpr`，导致形状大了 DPR 倍
- **修复**: 函数内部去掉 `* u_dpr`，输入已归一化

### 修复 2：边界 mix 死亡地带（`fragment-main.glsl`）
- **文件**: `fragment-main.glsl`
- **问题**: 最后一行 `mix(outColor, texture(u_bg), smoothstep(-0.001, 0.001, merged))` 在边界处把玻璃效果混回背景，抹掉折射/光晕
- **修复**: 移入 else 分支，只在 SDF 外部做平滑过渡

---

## 待修复

### 病灶四（核心）：`p1` 是常量而非逐像素坐标 ✅ 已修复

**修复文件**：`fragment-main.glsl`、`fragment-bg.glsl`

```glsl
// 原代码 fragment-main.glsl:
void main() {
  vec2 p1 = (vec2(0, 0) - u_resolution.xy * 0.5) / u_resolution.y;  // ← 常量！
  vec2 p2 = (vec2(0, 0) - u_mouseSpring) / u_resolution.y;              // ← 常量！
```

**`p1` 和 `p2` 都是常量**——它们不包含 `gl_FragCoord`，所以对所有片元值相同。

正确的应该是：
```glsl
void main() {
  // 当前片元在坐标系B中的位置（以画布高度为单位，原点=画布中心）
  vec2 fragPos = (gl_FragCoord.xy - u_resolution.xy * 0.5) / u_resolution.y;
  // shapeCenter: 形状中心在坐标系B中的位置
  vec2 shapeCenter = (u_mouseSpring - u_resolution.xy * 0.5) / u_resolution.y;
  float merged = mainSDF(fragPos, shapeCenter);
}
```

对应的 `mainSDF` 需要重构：
```glsl
float mainSDF(vec2 fragPos, vec2 shapeCenter) {
  vec2 localPos = fragPos - shapeCenter;
  // roundedRectSDF 的 center 参数传入 vec2(0) 即可
  float d = roundedRectSDF(
    localPos,
    vec2(0.0),
    u_shapeWidth / u_resolution.y,
    u_shapeHeight / u_resolution.y,
    u_shapeRadius / u_resolution.y,
    u_shapeRoundness
  );
  return d;
}
```

---

### 病灶五：坐标系单位混乱完整链路

三个坐标系同时存在：

| 坐标系 | 原点 | 单位 | 变量 |
|--------|------|------|------|
| A: 设备像素 | 画布左下角 | 物理像素 | `gl_FragCoord.xy`, `u_resolution.xy` |
| B: 归一化高度 | 画布中心 | 1.0 = 画布高度 | `p`, `fragPos` |
| C: UV | 画布左下角 | [0,1] | `v_uv` |

正确转换：
```
A→B: (gl_FragCoord.xy - u_resolution.xy * 0.5) / u_resolution.y
B→A: p * u_resolution.y + u_resolution.xy * 0.5
A→C: gl_FragCoord.xy / u_resolution.xy
```

---

### 病灶六：UV Y轴翻转

```glsl
// WebGL 纹理坐标系 Y轴朝上（图像坐标系）
// WebGL gl_FragCoord Y轴朝下（屏幕坐标系）
// 需要根据实际上下文判断是否翻转
vec2 screenUV = gl_FragCoord.xy / u_resolution.xy;
// 如果图像上传时用了 UNPACK_FLIP_Y_WEBGL = true（浏览器默认）：
// screenUV.y = 1.0 - screenUV.y;
```

---

### 病灶七：SDF 梯度计算

现有有限差分法需 4 次额外 SDF 调用，建议改为**解析梯度**：

```glsl
vec2 roundedRectGradient(vec2 p, vec2 center, vec2 halfSize, float cr) {
  vec2 local = p - center;
  vec2 d = abs(local) - halfSize;
  vec2 s = sign(local);

  if (cr > 1e-5 && d.x > -cr && d.y > -cr) {
    vec2 cornerCenter = s * (halfSize - vec2(cr));
    vec2 toCorner = local - cornerCenter;
    return normalize(toCorner);
  } else if (d.x > d.y) {
    return vec2(s.x, 0.0);
  } else {
    return vec2(0.0, s.y);
  }
}
```

---

### 病灶八：折射强度分布

现有方案在整个形状内部均匀施加折射，正确方案应该是**边缘强、中心弱**：

```glsl
// 折射只在边缘附近生效，中心几乎透明
float refractionMask = exp(-max(0.0, -merged) * refractionDecayK * u_resolution.y);
// merged 越接近 0（边界），mask 越接近 1
// 深入内部，mask 指数衰减
```

---

### 病灶九：菲涅尔效应

现有实现用固定的 `vec2(0.0, 1.0)` 代替视线方向，对于 2D 平面永远返回接近 0 的值。正确做法是用 SDF 值代理入射角：

```glsl
// 用 SDF 深度近似"边缘斜面"的入射角
float glassThicknessB = u_glassThickness / cssHeight;
float cosTheta = smoothstep(0.0, -glassThicknessB, sdf);
float fresnel = F0 + (1.0 - F0) * pow(1.0 - cosTheta, 5.0);
```

---

### 病灶十：高光方向性

现有 `glow = exp(-merged * u_glowFalloff)` 是各向同性，错误。应该加入光源方向：

```glsl
vec2 lightDir = normalize(u_lightDir);
float diffuse = max(0.0, dot(normal, lightDir));
vec2 halfVec = normalize(lightDir + vec2(0.0, 1.0));
float specular = pow(max(0.0, dot(normal, halfVec)), u_specularPower);
float edgeMask = exp(-abs(merged) * glowFalloffB * cssHeight);
float highlight = (diffuse * u_diffuseIntensity + specular * u_specularIntensity) * edgeMask;
```

---

### 病灶十一：背景模糊 sigma 单位

```glsl
// 错误：sigma 是 CSS 像素，但直接当设备像素用
vec2 stepUV = u_direction * u_sigma;  // ← 单位错误

// 正确：CSS 像素 → 设备像素 → UV 空间
vec2 sigmaUV = vec2(
  u_sigma * u_dpr / u_resolution.x,  // 横向 sigma 在 UV 空间的偏移
  u_sigma * u_dpr / u_resolution.y   // 纵向
);
vec2 stepUV = u_direction * sigmaUV;
```

---

### 病灶十二：`smoothUnion` k 参数单位

```glsl
// JavaScript 传入 CSS 像素，shader 直接用
float merged = smoothUnion(d1, d2, u_blendRadius);  // ← 单位混淆

// 正确：shader 内转换
float k = u_blendRadius / u_resolution.y;
float merged = smoothUnion(d1, d2, k);
```

---

## 坐标系核心总结

原代码最根本的错误：**所有计算都在两个常量（`p1`、`p2`）和另一个逐像素值（`gl_FragCoord`）之间进行**，而两个 shader（bg 和 main）对 `p1`、`p2` 的计算方式完全相同但又各自独立，导致坐标系混乱。

正确架构：
```
gl_FragCoord.xy  →  fragPos（逐像素，归一化坐标）  →  SDF计算  →  渲染分支
                              ↑
                        shapeCenter（从 u_mouseSpring 算出）
```

---

*文档状态：分析完成约 60%，病灶 1-4 已定位，灶 5-12 待继续分析*
