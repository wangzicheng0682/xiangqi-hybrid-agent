/**
 * webgl-ui.ts — 纯函数 WebGL 按钮渲染工具
 *
 * 从 WebGLButton.tsx 提取的渲染逻辑，不依赖 React。
 * 供 LiquidGlassApp RAF 循环调用。
 */

// ========================================
// Shader 源码
// ========================================

export const buttonVertexShader = `#version 300 es
precision highp float;
in vec2 a_position;
in vec2 a_texCoord;
out vec2 v_texCoord;
void main() {
  gl_Position = vec4(a_position, 0.0, 1.0);
  v_texCoord = a_texCoord;
}`;

export const buttonFragmentShader = `#version 300 es
precision highp float;
in vec2 v_texCoord;
out vec4 fragColor;

uniform vec2 u_resolution;
uniform vec2 u_btnPos;      // 按钮左下角（物理像素）
uniform vec2 u_btnSize;     // 按钮尺寸（物理像素）
uniform float u_radius;     // 圆角半径
uniform vec4 u_bgColor;     // 玻璃底色（近透明，仅微调色相）
uniform vec4 u_borderColor; // 边缘高光色
uniform float u_hover;       // 0-1
uniform float u_active;      // 0-1
uniform float u_glareFactor; // 顶部光泽条强度
uniform float u_innerLight;  // 内壁高光强度
uniform float u_edgeGlow;    // 外边缘辉光强度
uniform sampler2D u_textTexture;
uniform float u_textWidth;
uniform float u_textHeight;
uniform float u_textEnabled;

// ── SDF ───────────────────────────────────────────────────────────────────────
float roundedRectSDF(vec2 center, vec2 halfSize, float radius) {
  vec2 d = abs(center) - halfSize + vec2(radius);
  return min(max(d.x, d.y), 0.0) + length(max(d, 0.0)) - radius;
}

// ── 内壁高光：边缘最亮，向内线性衰减 ─────────────────────────────────────────
float innerBorderGlow(vec2 bc, vec2 sz, float strength) {
  float aa = 2.0;
  // 左内壁：x=0 最亮，随 x 增大而衰减
  float left  = (1.0 - smoothstep(0.0, 12.0, bc.x)) * strength;
  // 右内壁
  float right = (1.0 - smoothstep(0.0, 12.0, sz.x - bc.x)) * strength * 0.6;
  // 上内壁（强）
  float top   = (1.0 - smoothstep(0.0, 10.0, bc.y)) * strength * 1.2;
  // 下内壁（弱）
  float bot   = (1.0 - smoothstep(0.0, 10.0, sz.y - bc.y)) * strength * 0.5;
  return left + right + top + bot;
}

// ── 外边缘辉光：紧贴边缘向外扩散 ─────────────────────────────────────────────
float outerEdgeGlow(float dist, float strength) {
  return (1.0 - smoothstep(0.0, 8.0, dist)) * strength;
}

// ── 顶部光泽条 ────────────────────────────────────────────────────────────────
float topGlareStrip(vec2 bc, vec2 sz, float factor) {
  float h = max(4.0, sz.y * 0.06);
  float t = smoothstep(h + 2.0, h - 1.0, bc.y);
  t *= (1.0 - smoothstep(h - 1.0, h + 2.0, bc.y));
  return t * factor;
}

// ── 中央微光（玻璃内部光泽）─────────────────────────────────────────────────
float centralSheen(vec2 bc, vec2 sz, float strength) {
  vec2 n = bc / sz; // 0..1 normalized
  // 从顶部到底部的柔和渐变（模拟顶部光源）
  float grad = smoothstep(0.0, 1.0, n.y) * (1.0 - n.y * 0.5);
  // 中央略亮
  float cx = 1.0 - abs(n.x - 0.5) * 0.6;
  return grad * cx * strength;
}

void main() {
  vec2 pixelCoord = v_texCoord * u_resolution;

  // 按钮坐标系（u_btnPos 为左下角）
  vec2 btnCoord = pixelCoord - u_btnPos;
  vec2 halfSize = u_btnSize * 0.5;
  vec2 center   = btnCoord - halfSize;

  float dist   = roundedRectSDF(center, halfSize, u_radius);
  float aa      = 1.0;
  float shapeMask = 1.0 - smoothstep(-aa, aa, dist);

  if (shapeMask < 0.01) discard;

  float h = u_hover;
  float a = u_active;

  // ── 透明玻璃底（近透明，让背景透出）──────────────────────────────────────
  float baseAlpha = u_bgColor.a + h * 0.08 - a * 0.05;

  // ── 内壁高光（定义玻璃厚度感）─────────────────────────────────────────────
  float ib = innerBorderGlow(btnCoord, u_btnSize, u_innerLight * (1.0 + h * 1.5));

  // ── 外边缘辉光（边缘柔和晕开）─────────────────────────────────────────────
  float oe = outerEdgeGlow(dist, u_edgeGlow * (1.0 + h * 1.2));

  // ── 顶部光泽条（top-glare，Apple 标志性效果）───────────────────────────────
  float tg = topGlareStrip(btnCoord, u_btnSize, u_glareFactor * (1.0 + h * 0.8));

  // ── 中央微光 ──────────────────────────────────────────────────────────────
  float cs = centralSheen(btnCoord, u_btnSize, u_innerLight * 0.25);

  // 合并所有光效到 alpha 通道
  float totalAlpha = baseAlpha
    + ib * 0.45
    + oe * 0.35
    + tg * 0.9
    + cs * 0.15;
  totalAlpha = clamp(totalAlpha, 0.0, 0.88);

  // 最终颜色 = 高光色叠加到底盘色
  vec3 baseColor = u_bgColor.rgb;
  vec3 finalRgb = baseColor
    + u_borderColor.rgb * ib
    + u_borderColor.rgb * oe
    + vec3(tg)
    + u_borderColor.rgb * cs;
  // hover 加亮，active 略暗
  finalRgb += h * 0.06;
  finalRgb -= a * 0.04;

  // ── 文字 ────────────────────────────────────────────────────────────────
  vec4 textColor = vec4(0.0);
  if (u_textEnabled > 0.5) {
    vec2 textOrigin = vec2(
      u_btnPos.x + (u_btnSize.x - u_textWidth) * 0.5,
      u_btnPos.y + (u_btnSize.y - u_textHeight) * 0.5
    );
    vec2 textUV = (pixelCoord - textOrigin) / vec2(u_textWidth, u_textHeight);
    if (textUV.x >= 0.0 && textUV.x <= 1.0 && textUV.y >= 0.0 && textUV.y <= 1.0) {
      textColor = texture(u_textTexture, textUV);
    }
  }

  vec4 btn = vec4(finalRgb, totalAlpha * shapeMask);
  if (u_textEnabled > 0.5 && textColor.a > 0.01) {
    btn = vec4(mix(btn.rgb, textColor.rgb, textColor.a), max(btn.a, textColor.a));
  }
  fragColor = btn;
}`;

// ========================================
// Variant 颜色配置
// ========================================

export type ButtonVariant = 'default' | 'primary' | 'gold';

interface ButtonStyle {
  bg: [number, number, number, number];   // 近透明底色
  border: [number, number, number, number]; // 边缘高光色
  glareFactor: number;  // 顶部光泽条强度
  innerLight: number;    // 内壁高光强度
  edgeGlow: number;      // 外边缘辉光强度
}

const VARIANT_STYLES: Record<ButtonVariant, ButtonStyle> = {
  default: {
    // 透明玻璃底 + 纯白边缘高光 = Apple 毛玻璃质感
    bg:          [1.0,  1.0,  1.0,  0.06],  // 仅6%透明度，让背景微透
    border:      [1.0,  1.0,  1.0,  0.90],  // 高亮白边
    glareFactor: 0.60,
    innerLight:  0.55,
    edgeGlow:    0.30,
  },
  primary: {
    bg:          [1.0,  0.95, 0.80, 0.08],  // 暖白微光底
    border:      [1.0,  0.92, 0.60, 0.80],
    glareFactor: 0.65,
    innerLight:  0.50,
    edgeGlow:    0.28,
  },
  gold: {
    // 透明底 + 金色边缘高光 = 金色液态玻璃
    bg:          [1.0,  0.85, 0.40, 0.08],  // 微金底色
    border:      [1.0,  0.90, 0.40, 0.95],  // 强金色边
    glareFactor: 0.80,
    innerLight:  0.70,
    edgeGlow:    0.40,
  },
};

// ========================================
// 文字纹理
// ========================================

export function renderTextToCanvas(
  text: string,
  fontSize: number,
  color: string = 'rgba(255,255,255,0.95)',
): { canvas: HTMLCanvasElement; width: number; height: number } {
  const padding = Math.ceil(fontSize * 0.8);
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d')!;
  ctx.font = `${Math.round(fontSize * 0.9)}px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`;
  const metrics = ctx.measureText(text);
  const width = Math.ceil(metrics.width) + padding * 2;
  const height = Math.ceil(fontSize * 1.5) + padding * 2;
  canvas.width = width;
  canvas.height = height;
  ctx.clearRect(0, 0, width, height);
  ctx.font = `${Math.round(fontSize * 0.9)}px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`;
  ctx.fillStyle = color;
  ctx.textBaseline = 'middle';
  ctx.textAlign = 'center';
  ctx.fillText(text, width / 2, height / 2);
  return { canvas, width, height };
}

// ========================================
// WebGL 工具函数
// ========================================

export function compileShader(gl: WebGL2RenderingContext, type: number, source: string): WebGLShader {
  const shader = gl.createShader(type)!;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const info = gl.getShaderInfoLog(shader);
    gl.deleteShader(shader);
    throw new Error(`Shader compile error: ${info}`);
  }
  return shader;
}

export function linkProgram(gl: WebGL2RenderingContext, vs: WebGLShader, fs: WebGLShader): WebGLProgram {
  const prog = gl.createProgram()!;
  gl.attachShader(prog, vs);
  gl.attachShader(prog, fs);
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
    const info = gl.getProgramInfoLog(prog);
    gl.deleteProgram(prog);
    throw new Error(`Program link error: ${info}`);
  }
  return prog;
}

// ========================================
// 按钮状态
// ========================================

export interface UIButtonState {
  id: string;
  label: string;
  x: number;        // 相对左侧栏（px）
  y: number;        // 相对左侧栏（px）
  width: number;
  height: number;
  variant: ButtonVariant;
  active: boolean;   // 当前是否激活（如当前选中的模式）
  onClick: () => void;
}

export interface UIRenderContext {
  gl: WebGL2RenderingContext;
  program: WebGLProgram;
  vao: WebGLVertexArrayObject;
  dpr: number;
  leftSidebarOffsetX: number;   // 左侧栏在视口中的 X 偏移（0 = 紧贴左侧）
  leftSidebarOffsetY: number;   // 左侧栏在视口中的 Y 偏移
  textTextureCache: Map<string, WebGLTexture>;
  hoveredId: string | null;
  pressedId: string | null;
}

// ========================================
// 渲染单个按钮
// ========================================

function setUniforms(
  gl: WebGL2RenderingContext,
  program: WebGLProgram,
  btn: UIButtonState,
  ctx: UIRenderContext,
) {
  const dpr = ctx.dpr;
  const style = VARIANT_STYLES[btn.variant];

  const px = (ctx.leftSidebarOffsetX + btn.x) * dpr;
  const py = (ctx.leftSidebarOffsetY + btn.y) * dpr;
  const pw = btn.width * dpr;
  const ph = btn.height * dpr;

  const isHovered = ctx.hoveredId === btn.id;

  gl.uniform2f(gl.getUniformLocation(program, 'u_resolution'), gl.canvas.width, gl.canvas.height);
  gl.uniform2f(gl.getUniformLocation(program, 'u_btnPos'), px, gl.canvas.height - py - ph);
  gl.uniform2f(gl.getUniformLocation(program, 'u_btnSize'), pw, ph);
  gl.uniform1f(gl.getUniformLocation(program, 'u_radius'), Math.min(pw, ph) * 0.22);
  gl.uniform4f(gl.getUniformLocation(program, 'u_bgColor'), ...style.bg);
  gl.uniform4f(gl.getUniformLocation(program, 'u_borderColor'), ...style.border);
  gl.uniform1f(gl.getUniformLocation(program, 'u_hover'), isHovered ? 1.0 : 0.0);
  gl.uniform1f(gl.getUniformLocation(program, 'u_active'), btn.active ? 1.0 : 0.0);
  gl.uniform1f(gl.getUniformLocation(program, 'u_glareFactor'), style.glareFactor);
  gl.uniform1f(gl.getUniformLocation(program, 'u_innerLight'), style.innerLight);
  gl.uniform1f(gl.getUniformLocation(program, 'u_edgeGlow'), style.edgeGlow);

  // 文字纹理
  if (!ctx.textTextureCache.has(btn.id)) {
    const { canvas } = renderTextToCanvas(btn.label, 13 * dpr);
    const tex = gl.createTexture()!;
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, canvas);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    ctx.textTextureCache.set(btn.id, tex);
  }

  const tex = ctx.textTextureCache.get(btn.id)!;
  gl.activeTexture(gl.TEXTURE0);
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.uniform1i(gl.getUniformLocation(program, 'u_textTexture'), 0);
  gl.uniform1f(gl.getUniformLocation(program, 'u_textWidth'), btn.width * dpr);
  gl.uniform1f(gl.getUniformLocation(program, 'u_textHeight'), btn.height * dpr);
  gl.uniform1f(gl.getUniformLocation(program, 'u_textEnabled'), 1.0);
}

// ========================================
// 主渲染函数
// ========================================

export function renderUIButtons(ctx: UIRenderContext, buttons: UIButtonState[]): void {
  const { gl, program, vao } = ctx;

  gl.useProgram(program);
  gl.bindVertexArray(vao);
  gl.enable(gl.BLEND);
  gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

  for (const btn of buttons) {
    setUniforms(gl, program, btn, ctx);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }
}

// ========================================
// 鼠标检测（判断哪个按钮被命中）
// ========================================

export function detectButtonAt(
  clientX: number,
  clientY: number,
  ctx: UIRenderContext,
  buttons: UIButtonState[],
): string | null {
  const canvas = ctx.gl.canvas as HTMLCanvasElement;
  const cssX = clientX - canvas.getBoundingClientRect().left;
  const cssY = clientY - canvas.getBoundingClientRect().top;
  const dpr = ctx.dpr;
  // WebGL 物理像素坐标系：Y 从 canvas 底部算起
  // CSS Y 从 viewport 顶部算起，需要翻转
  const glY = canvas.height - cssY * dpr;
  const offsetX = ctx.leftSidebarOffsetX * dpr;
  const offsetY = ctx.leftSidebarOffsetY * dpr;

  for (const btn of buttons) {
    const bx = offsetX + btn.x * dpr;
    const by = offsetY + (canvas.height / dpr - btn.y - btn.height) * dpr;
    const bw = btn.width * dpr;
    const bh = btn.height * dpr;
    if (cssX * dpr >= bx && cssX * dpr <= bx + bw && glY >= by && glY <= by + bh) {
      return btn.id;
    }
  }
  return null;
}
