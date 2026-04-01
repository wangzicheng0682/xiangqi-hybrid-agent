/**
 * WebGLButton - 纯 WebGL 渲染的按钮
 *
 * 使用 SDF 圆角矩形 + Canvas2D 文字渲染
 */

import { useRef, useEffect, useCallback, useState } from 'react';

// ========================================
// Types
// ========================================

export interface WebGLButtonProps {
  width: number;
  height: number;
  label: string;
  onClick?: () => void;
  disabled?: boolean;
  variant?: 'default' | 'primary' | 'gold';
  className?: string;
  style?: React.CSSProperties;
}

// ========================================
// Shaders
// ========================================

const vertexShaderSource = `#version 300 es
precision highp float;
in vec2 a_position;
in vec2 a_texCoord;
out vec2 v_texCoord;
void main() {
  gl_Position = vec4(a_position, 0.0, 1.0);
  v_texCoord = a_texCoord;
}`;

const fragmentShaderSource = `#version 300 es
precision highp float;
in vec2 v_texCoord;
out vec4 fragColor;

uniform vec2 u_resolution;
uniform float u_borderRadius;
uniform vec4 u_buttonColor;
uniform vec4 u_borderColor;
uniform float u_borderWidth;
uniform float u_hover;  // 0-1 hover intensity
uniform float u_pressed; // 0-1 pressed intensity

float roundedRectSDF(vec2 center, vec2 halfSize, float radius) {
  vec2 d = abs(center) - halfSize + vec2(radius);
  return min(max(d.x, d.y), 0.0) + length(max(d, 0.0)) - radius;
}

void main() {
  vec2 uv = v_texCoord;
  vec2 pixelCoord = uv * u_resolution;

  // Button background SDF
  vec2 center = pixelCoord - u_resolution * 0.5;
  vec2 halfSize = u_resolution * 0.5;
  float dist = roundedRectSDF(center, halfSize, u_borderRadius);

  // Anti-aliased edge
  float aa = 1.0;
  float bgAlpha = 1.0 - smoothstep(-aa, aa, dist);

  if (bgAlpha < 0.01) {
    discard;
  }

  // Hover/pressed effects
  float hoverFactor = u_hover * 0.15;
  float pressFactor = u_pressed * 0.1;
  vec4 bgColor = u_buttonColor;
  bgColor.rgb += hoverFactor - pressFactor;

  // Border
  float borderDist = dist + u_borderWidth;
  float borderAlpha = smoothstep(-aa, aa, -borderDist) * (1.0 - smoothstep(-aa, aa, dist));

  float verticalLight = (1.0 - uv.y) * 0.18;
  float centerGlow = smoothstep(0.85, 0.0, distance(uv, vec2(0.5, 0.45))) * 0.16;
  float specular = smoothstep(0.28, 0.0, distance(uv, vec2(0.28, 0.12))) * (0.18 + u_hover * 0.08);
  float rim = smoothstep(0.0, 0.18, uv.y) * 0.08 + smoothstep(1.0, 0.76, uv.y) * 0.05;

  // Combine
  vec4 finalColor = mix(bgColor, u_borderColor, borderAlpha * u_borderColor.a);
  finalColor.rgb += verticalLight + centerGlow + specular + rim;
  finalColor.a = max(bgAlpha, borderAlpha);

  fragColor = finalColor;
}`;

// ========================================
// Utility Functions
// ========================================

function createShader(gl: WebGL2RenderingContext, type: number, source: string): WebGLShader {
  const shader = gl.createShader(type)!;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    console.error('Shader compile error:', gl.getShaderInfoLog(shader));
    gl.deleteShader(shader);
    throw new Error('Shader compilation failed');
  }
  return shader;
}

function createProgram(gl: WebGL2RenderingContext, vertexShader: WebGLShader, fragmentShader: WebGLShader): WebGLProgram {
  const program = gl.createProgram()!;
  gl.attachShader(program, vertexShader);
  gl.attachShader(program, fragmentShader);
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    console.error('Program link error:', gl.getProgramInfoLog(program));
    gl.deleteProgram(program);
    throw new Error('Program linking failed');
  }
  return program;
}

// ========================================
// Component
// ========================================

export const WebGLButton: React.FC<WebGLButtonProps> = ({
  width,
  height,
  label,
  onClick,
  disabled = false,
  variant = 'default',
  className,
  style,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const glRef = useRef<WebGL2RenderingContext | null>(null);
  const programRef = useRef<WebGLProgram | null>(null);
  const vaoRef = useRef<WebGLVertexArrayObject | null>(null);
  const frameRef = useRef<number>(0);

  const [hover, setHover] = useState(0);
  const [pressed, setPressed] = useState(0);

  const hoverRef = useRef(0);
  const pressedRef = useRef(0);

  // Update refs
  useEffect(() => { hoverRef.current = hover; }, [hover]);
  useEffect(() => { pressedRef.current = pressed; }, [pressed]);

  // Initialize WebGL
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
    glRef.current = gl;

    // Create shaders and program
    const vertexShader = createShader(gl, gl.VERTEX_SHADER, vertexShaderSource);
    const fragmentShader = createShader(gl, gl.FRAGMENT_SHADER, fragmentShaderSource);
    const program = createProgram(gl, vertexShader, fragmentShader);
    programRef.current = program;

    // Create VAO
    const vao = gl.createVertexArray()!;
    vaoRef.current = vao;
    gl.bindVertexArray(vao);

    // Create geometry (fullscreen quad)
    const positions = new Float32Array([
      -1, -1, 0, 0,
       1, -1, 1, 0,
      -1,  1, 0, 1,
       1,  1, 1, 1,
    ]);
    const buffer = gl.createBuffer()!;
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, positions, gl.STATIC_DRAW);

    const posLoc = gl.getAttribLocation(program, 'a_position');
    const texLoc = gl.getAttribLocation(program, 'a_texCoord');
    gl.enableVertexAttribArray(posLoc);
    gl.enableVertexAttribArray(texLoc);
    gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 16, 0);
    gl.vertexAttribPointer(texLoc, 2, gl.FLOAT, false, 16, 8);

    return () => {
      gl.deleteProgram(program);
      gl.deleteShader(vertexShader);
      gl.deleteShader(fragmentShader);
      gl.deleteBuffer(buffer);
      gl.deleteVertexArray(vao);
    };
  }, []);

  // Animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    const gl = glRef.current;
    const program = programRef.current;
    const vao = vaoRef.current;
    if (!canvas || !gl || !program || !vao) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;

    const render = () => {
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.useProgram(program);

      // Get uniform locations
      const uResolution = gl.getUniformLocation(program, 'u_resolution');
      const uBorderRadius = gl.getUniformLocation(program, 'u_borderRadius');
      const uButtonColor = gl.getUniformLocation(program, 'u_buttonColor');
      const uBorderColor = gl.getUniformLocation(program, 'u_borderColor');
      const uBorderWidth = gl.getUniformLocation(program, 'u_borderWidth');
      const uHover = gl.getUniformLocation(program, 'u_hover');
      const uPressed = gl.getUniformLocation(program, 'u_pressed');

      // Set uniforms
      gl.uniform2f(uResolution, canvas.width, canvas.height);
      gl.uniform1f(uBorderRadius, Math.min(width, height) * 0.28);
      gl.uniform1f(uHover, hoverRef.current);
      gl.uniform1f(uPressed, pressedRef.current);

      // Button colors based on variant
      let bgColor = [0.14, 0.25, 0.39, 0.62];
      let borderColor = [0.88, 0.96, 1.0, 0.34];
      let borderWidth = 1.2;

      if (variant === 'primary') {
        bgColor = [0.09, 0.55, 0.76, 0.70];
        borderColor = [0.91, 0.98, 1.0, 0.42];
      } else if (variant === 'gold') {
        bgColor = [0.82, 0.62, 0.20, 0.78];
        borderColor = [1.0, 0.92, 0.66, 0.48];
        borderWidth = 1.4;
      }

      if (disabled) {
        bgColor[0] *= 0.5;
        bgColor[1] *= 0.5;
        bgColor[2] *= 0.5;
        bgColor[3] *= 0.7;
      }

      gl.uniform4f(uButtonColor, bgColor[0], bgColor[1], bgColor[2], bgColor[3]);
      gl.uniform4f(uBorderColor, borderColor[0], borderColor[1], borderColor[2], borderColor[3]);
      gl.uniform1f(uBorderWidth, borderWidth);

      gl.bindVertexArray(vao);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

      frameRef.current = requestAnimationFrame(render);
    };

    frameRef.current = requestAnimationFrame(render);
    return () => cancelAnimationFrame(frameRef.current);
  }, [width, height, variant, disabled]);

  // Event handlers
  const handlePointerEnter = useCallback(() => {
    if (!disabled) setHover(1);
  }, [disabled]);

  const handlePointerLeave = useCallback(() => {
    setHover(0);
    setPressed(0);
  }, []);

  const handlePointerDown = useCallback(() => {
    if (!disabled) setPressed(1);
  }, [disabled]);

  const handlePointerUp = useCallback(() => {
    if (!disabled && pressed) {
      onClick?.();
    }
    setPressed(0);
  }, [disabled, pressed, onClick]);

  const labelColor =
    disabled
      ? 'rgba(244, 241, 222, 0.42)'
      : variant === 'gold'
        ? 'rgba(44, 28, 8, 0.92)'
        : 'rgba(248, 246, 236, 0.96)';

  const labelStyle: React.CSSProperties = {
    position: 'absolute',
    inset: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '0 10px',
    color: labelColor,
    fontSize: width <= 56 ? 11 : height >= 44 ? 13 : 12,
    fontWeight: 600,
    letterSpacing: width > 100 ? '0.01em' : '0',
    lineHeight: 1,
    textShadow: variant === 'gold' ? '0 1px 0 rgba(255,255,255,0.18)' : '0 1px 10px rgba(8, 22, 40, 0.32)',
    userSelect: 'none',
    pointerEvents: 'none',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    transform: pressed ? 'translateY(0.5px)' : 'translateY(0)',
    transition: 'transform 120ms ease',
  };

  return (
    <div
      ref={containerRef}
      className={className}
      style={{
        position: 'relative',
        display: 'block',
        width,
        height,
        cursor: disabled ? 'not-allowed' : 'pointer',
        ...style,
      }}
      onPointerEnter={handlePointerEnter}
      onPointerLeave={handlePointerLeave}
      onPointerDown={handlePointerDown}
      onPointerUp={handlePointerUp}
    >
      <canvas
        ref={canvasRef}
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          display: 'block',
        }}
      />
      <span style={labelStyle}>{label}</span>
    </div>
  );
};

export default WebGLButton;
