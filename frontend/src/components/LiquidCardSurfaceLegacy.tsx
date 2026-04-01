/**
 * LiquidCardSurface Component
 *
 * WebGL-powered liquid glass card surface.
 * Provides the shader-based visual layer for expert cards.
 *
 * Usage:
 * ```tsx
 * <motion.div className="card-shell">
 *   <LiquidCardSurface
 *     width={130}
 *     height={175}
 *     expertType="tactics"
 *     hover={isHovered ? 1 : 0}
 *     flip={flipProgress}
 *     morph={morphProgress}
 *     glow={glowProgress}
 *     phase={phase}
 *   />
 *   <CardContent /> {/* DOM layer on top *\/}
 * </motion.div>
 * ```
 */

import { useRef, useEffect, useCallback } from 'react';
import { CardPhase, ExpertType, EXPERT_ACCENT_COLORS } from '../hooks/useLiquidCardUniforms';

// ========================================
// Types
// ========================================

export interface LiquidCardSurfaceProps {
  width: number;
  height: number;
  expertType: ExpertType;
  hover?: number;      // 0-1
  flip?: number;       // 0-1
  morph?: number;      // 0-1
  glow?: number;       // 0-1
  phase?: CardPhase;
  className?: string;
  style?: React.CSSProperties;
}

// ========================================
// Phase intensity mapping
// ========================================

function getPhaseIntensity(phase: CardPhase): number {
  switch (phase) {
    case CardPhase.Idle: return 0.20;
    case CardPhase.Stacking: return 0.35;
    case CardPhase.Flipped: return 0.75;
    case CardPhase.Morphing: return 0.85;
    case CardPhase.OrbMoving: return 1.00;
    case CardPhase.CardsLanding: return 0.60;
    case CardPhase.CardsLanded: return 0.35;
    case CardPhase.Streaming: return 0.15;
    default: return 0.20;
  }
}

// ========================================
// Shader sources (embedded)
// ========================================

const VERTEX_SHADER_SOURCE = `
attribute vec2 aPosition;
varying vec2 vUv;

void main() {
    vUv = aPosition * 0.5 + 0.5;
    gl_Position = vec4(aPosition, 0.0, 1.0);
}
`;

const FRAGMENT_SHADER_SOURCE = `
precision highp float;

varying vec2 vUv;

uniform vec2 uResolution;
uniform float uTime;
uniform float uHover;
uniform float uFlip;
uniform float uMorph;
uniform float uGlow;
uniform float uIntensity;
uniform vec3 uAccent;
uniform vec2 uPointer;

#define PI 3.14159265359

float sdRoundRect(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + r;
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
}

struct EdgeResult {
    float outer;
    float inner;
    float middle;
};

EdgeResult calcEdge(float d) {
    EdgeResult e;
    e.outer = 1.0 - smoothstep(0.0, 0.025, abs(d));
    e.inner = smoothstep(0.035, 0.0, abs(d));
    e.middle = smoothstep(0.015, 0.005, abs(d));
    return e;
}

float liquidSpec(vec2 uv, float t, float hover) {
    float spec1 = pow(max(0.0, 1.0 - uv.y), 3.0) * 0.6;
    float topBand = smoothstep(0.7, 0.95, 1.0 - uv.y) * 0.35;
    float diag = smoothstep(0.3, 0.7, uv.x + (1.0 - uv.y) * 0.5) * 0.2;
    float shimmer = sin(t * 3.0 + uv.x * 8.0 + uv.y * 6.0) * 0.5 + 0.5;
    float hoverShimmer = shimmer * hover * 0.15;
    return spec1 + topBand + diag + hoverShimmer;
}

vec3 iridescence(vec2 uv, float t, float saturation) {
    float a = sin(uv.x * 16.0 + t * 1.1);
    float b = sin(uv.y * 12.0 - t * 0.7);
    float c = sin((uv.x + uv.y) * 10.0 + t * 0.9);
    float d = sin((uv.x - uv.y) * 8.0 + t * 0.5);
    vec3 col = 0.5 + 0.5 * cos(vec3(0.0, 2.1, 4.2) + (a + b + c + d) * 1.2);
    float gray = dot(col, vec3(0.299, 0.587, 0.114));
    col = mix(vec3(gray), col, saturation);
    return col;
}

vec2 fakeRefraction(vec2 uv, float strength, float t) {
    float dx = sin(uv.y * 6.0 + t * 1.2) * strength;
    float dy = cos(uv.x * 6.0 + t * 0.8) * strength;
    return clamp(uv + vec2(dx, dy), 0.0, 1.0);
}

float hoverGlow(vec2 uv, vec2 pointer, float hover) {
    float dist = length(uv - pointer);
    return smoothstep(0.4, 0.0, dist) * hover * 0.25;
}

float cornerHighlight(vec2 uv, float intensity) {
    float d = length(vec2(max(0.0, 0.15 - uv.x), max(0.0, 0.15 - uv.y)));
    return smoothstep(0.25, 0.0, d) * intensity * 0.3;
}

void main() {
    vec2 aspect = vec2(uResolution.x / uResolution.y, 1.0);
    vec2 p = (vUv - 0.5) * aspect * 2.0;
    p.x /= 0.743;

    vec2 cardSize = vec2(0.9, 1.2);
    float radius = 0.06;
    float d = sdRoundRect(p, cardSize, radius);

    float mask = 1.0 - smoothstep(-0.01, 0.01, d);
    EdgeResult edge = calcEdge(d);

    vec2 refractedUv = fakeRefraction(vUv, uMorph * 0.015, uTime);
    float spec = liquidSpec(vUv, uTime, uHover);
    vec3 rainbow = iridescence(refractedUv, uTime, 0.55);
    float hGlow = hoverGlow(vUv, uPointer, uHover);
    float corner = cornerHighlight(vUv, uIntensity);

    vec3 baseColor = vec3(0.96, 0.96, 0.98);
    vec3 color = baseColor;

    color = mix(color, vec3(1.0), edge.outer * 0.65);
    color = mix(color, vec3(0.15), edge.inner * 0.12);
    color = mix(color, vec3(1.0), edge.middle * 0.35);

    vec3 specCol = spec * (1.0 + uAccent * 0.25);
    color += specCol * uIntensity * 0.5;

    float rainbowMix = uFlip * uIntensity;
    color = mix(color, rainbow, rainbowMix * 0.30);

    color += hGlow * uAccent * 1.2;
    color += corner * (1.0 + uAccent * 0.2);
    color += uGlow * 0.08;

    float rim = 1.0 - smoothstep(-0.015, 0.035, d);
    color += rim * uAccent * 0.18 * uIntensity;

    float alpha = mask;
    alpha = max(alpha, rim * 0.25);

    gl_FragColor = vec4(color, alpha);
}
`;

// ========================================
// WebGL Helper Functions
// ========================================

function createShader(gl: WebGLRenderingContext, source: string, type: number): WebGLShader | null {
  const shader = gl.createShader(type);
  if (!shader) return null;

  gl.shaderSource(shader, source);
  gl.compileShader(shader);

  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    console.error('Shader compile error:', gl.getShaderInfoLog(shader));
    gl.deleteShader(shader);
    return null;
  }

  return shader;
}

function createProgram(gl: WebGLRenderingContext, vs: WebGLShader, fs: WebGLShader): WebGLProgram | null {
  const program = gl.createProgram();
  if (!program) return null;

  gl.attachShader(program, vs);
  gl.attachShader(program, fs);
  gl.linkProgram(program);

  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    console.error('Program link error:', gl.getProgramInfoLog(program));
    gl.deleteProgram(program);
    return null;
  }

  return program;
}

// ========================================
// Component
// ========================================

export const LiquidCardSurface: React.FC<LiquidCardSurfaceProps> = ({
  width,
  height,
  expertType,
  hover = 0,
  flip = 0,
  morph = 0,
  glow = 0,
  phase = CardPhase.Idle,
  className,
  style,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const glRef = useRef<WebGLRenderingContext | null>(null);
  const programRef = useRef<WebGLProgram | null>(null);
  const bufferRef = useRef<WebGLBuffer | null>(null);
  const startTimeRef = useRef<number>(performance.now());
  const frameRef = useRef<number>(0);
  const pointerRef = useRef<[number, number]>([0.5, 0.5]);
  const uniformsRef = useRef<{ [key: string]: WebGLUniformLocation | null }>({});

  // Initialize WebGL
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const gl = canvas.getContext('webgl', {
      alpha: true,
      premultipliedAlpha: false,
      antialias: true,
    });

    if (!gl) {
      console.error('WebGL not supported');
      return;
    }

    glRef.current = gl;

    // Compile shaders
    const vs = createShader(gl, VERTEX_SHADER_SOURCE, gl.VERTEX_SHADER);
    const fs = createShader(gl, FRAGMENT_SHADER_SOURCE, gl.FRAGMENT_SHADER);

    if (!vs || !fs) return;

    const program = createProgram(gl, vs, fs);
    if (!program) return;

    programRef.current = program;

    // Get uniform locations
    const uniformNames = ['uResolution', 'uTime', 'uHover', 'uFlip', 'uMorph', 'uGlow', 'uIntensity', 'uAccent', 'uPointer'];
    uniformNames.forEach((name) => {
      uniformsRef.current[name] = gl.getUniformLocation(program, name);
    });

    // Create buffer
    const buffer = gl.createBuffer();
    bufferRef.current = buffer;
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);

    return () => {
      if (buffer) gl.deleteBuffer(buffer);
      if (program) gl.deleteProgram(program);
      if (vs) gl.deleteShader(vs);
      if (fs) gl.deleteShader(fs);
    };
  }, []);

  // Resize canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    const gl = glRef.current;
    if (!canvas || !gl) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    gl.viewport(0, 0, canvas.width, canvas.height);
  }, [width, height]);

  // Handle mouse move
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    pointerRef.current = [
      (e.clientX - rect.left) / rect.width,
      1.0 - (e.clientY - rect.top) / rect.height,
    ];
  }, []);

  // Animation loop
  useEffect(() => {
    const gl = glRef.current;
    const program = programRef.current;
    const buffer = bufferRef.current;
    if (!gl || !program || !buffer) return;

    const accent = EXPERT_ACCENT_COLORS[expertType];
    const intensity = getPhaseIntensity(phase);
    const posLoc = gl.getAttribLocation(program, 'aPosition');

    const render = () => {
      const elapsed = (performance.now() - startTimeRef.current) / 1000;
      gl.useProgram(program);

      // Set uniforms
      const setUniform = (name: string, value: number | number[]) => {
        const loc = uniformsRef.current[name];
        if (!loc) return;
        if (typeof value === 'number') {
          gl.uniform1f(loc, value);
        } else if (value.length === 2) {
          gl.uniform2fv(loc, value);
        } else if (value.length === 3) {
          gl.uniform3fv(loc, value);
        }
      };

      setUniform('uResolution', [width, height]);
      setUniform('uTime', elapsed);
      setUniform('uHover', hover);
      setUniform('uFlip', flip);
      setUniform('uMorph', morph);
      setUniform('uGlow', glow);
      setUniform('uIntensity', intensity);
      setUniform('uAccent', accent);
      setUniform('uPointer', pointerRef.current);

      // Draw
      gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
      gl.enableVertexAttribArray(posLoc);
      gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

      frameRef.current = requestAnimationFrame(render);
    };

    frameRef.current = requestAnimationFrame(render);

    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    };
  }, [width, height, expertType, hover, flip, morph, glow, phase]);

  return (
    <canvas
      ref={canvasRef}
      className={className}
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        pointerEvents: hover > 0 ? 'auto' : 'none',
        ...style,
      }}
      onMouseMove={handleMouseMove}
    />
  );
};

export default LiquidCardSurface;
