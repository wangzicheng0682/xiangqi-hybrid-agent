/**
 * useWebGL Hook
 *
 * Lightweight WebGL 1.0 setup hook for 2D shader effects.
 * Creates a fullscreen quad and manages the shader program lifecycle.
 */

import { useRef, useEffect, useCallback, useMemo } from 'react';

// Simple attribute position type
type AttributeLocation = number;
type UniformLocation = WebGLUniformLocation | null;

export interface WebGLContext {
  gl: WebGLRenderingContext;
  program: WebGLProgram;
  attributes: {
    position: AttributeLocation;
  };
  uniforms: {
    [key: string]: UniformLocation;
  };
  setUniform: (name: string, value: UniformValue) => void;
  render: () => void;
  resize: (width: number, height: number) => void;
}

export type UniformValue =
  | number
  | number[]
  | Float32Array
  | Int32Array;

interface UseWebGLOptions {
  vertexShader: string;
  fragmentShader: string;
  uniforms: string[];
  onRender?: (gl: WebGLRenderingContext) => void;
}

/**
 * Creates and manages a WebGL context with a simple fullscreen quad
 */
export function useWebGL(
  canvasRef: React.RefObject<HTMLCanvasElement>,
  options: UseWebGLOptions
): WebGLContext | null {
  const { vertexShader, fragmentShader, uniforms: uniformNames } = options;

  const glRef = useRef<WebGLRenderingContext | null>(null);
  const programRef = useRef<WebGLProgram | null>(null);
  const locationsRef = useRef<{
    attributes: { position: AttributeLocation };
    uniforms: { [key: string]: UniformLocation };
  }>({
    attributes: { position: -1 },
    uniforms: {},
  });
  const bufferRef = useRef<WebGLBuffer | null>(null);

  // Compile shader
  const compileShader = useCallback(
    (gl: WebGLRenderingContext, source: string, type: number): WebGLShader | null => {
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
    },
    []
  );

  // Create program
  const createProgram = useCallback(
    (gl: WebGLRenderingContext, vs: WebGLShader, fs: WebGLShader): WebGLProgram | null => {
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
    },
    []
  );

  // Initialize WebGL
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Get WebGL context
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
    const vs = compileShader(gl, vertexShader, gl.VERTEX_SHADER);
    const fs = compileShader(gl, fragmentShader, gl.FRAGMENT_SHADER);

    if (!vs || !fs) {
      console.error('Failed to compile shaders');
      return;
    }

    // Create program
    const program = createProgram(gl, vs, fs);
    if (!program) {
      console.error('Failed to create program');
      return;
    }

    programRef.current = program;

    // Get attribute locations
    const positionLoc = gl.getAttribLocation(program, 'aPosition');
    locationsRef.current.attributes.position = positionLoc;

    // Get uniform locations
    uniformNames.forEach((name) => {
      locationsRef.current.uniforms[name] = gl.getUniformLocation(program, name);
    });

    // Create fullscreen quad buffer
    const buffer = gl.createBuffer();
    bufferRef.current = buffer;

    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([
        -1, -1,
         1, -1,
        -1,  1,
         1,  1,
      ]),
      gl.STATIC_DRAW
    );

    // Cleanup
    return () => {
      gl.deleteBuffer(buffer);
      gl.deleteProgram(program);
      gl.deleteShader(vs);
      gl.deleteShader(fs);
    };
  }, [canvasRef, vertexShader, fragmentShader, uniformNames, compileShader, createProgram]);

  // Set uniform helper
  const setUniform = useCallback((name: string, value: UniformValue) => {
    const gl = glRef.current;
    const program = programRef.current;
    const location = locationsRef.current.uniforms[name];

    if (!gl || !program || location === null) return;

    gl.useProgram(program);

    if (typeof value === 'number') {
      gl.uniform1f(location, value);
    } else if (value instanceof Float32Array) {
      if (value.length === 2) {
        gl.uniform2fv(location, value);
      } else if (value.length === 3) {
        gl.uniform3fv(location, value);
      } else if (value.length === 4) {
        gl.uniform4fv(location, value);
      }
    } else if (Array.isArray(value)) {
      if (value.length === 2) {
        gl.uniform2fv(location, value);
      } else if (value.length === 3) {
        gl.uniform3fv(location, value);
      } else if (value.length === 4) {
        gl.uniform4fv(location, value);
      }
    }
  }, []);

  // Render function
  const render = useCallback(() => {
    const gl = glRef.current;
    const program = programRef.current;
    const buffer = bufferRef.current;
    const positionLoc = locationsRef.current.attributes.position;

    if (!gl || !program || !buffer || positionLoc < 0) return;

    gl.useProgram(program);

    // Set up attribute
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.enableVertexAttribArray(positionLoc);
    gl.vertexAttribPointer(positionLoc, 2, gl.FLOAT, false, 0, 0);

    // Draw
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }, []);

  // Resize function
  const resize = useCallback((width: number, height: number) => {
    const gl = glRef.current;
    const canvas = canvasRef.current;
    if (!gl || !canvas) return;

    // Handle high DPI
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;

    gl.viewport(0, 0, canvas.width, canvas.height);
  }, [canvasRef]);

  // Return memoized context
  return useMemo(() => {
    const gl = glRef.current;
    const program = programRef.current;

    if (!gl || !program) return null;

    return {
      gl,
      program,
      attributes: locationsRef.current.attributes,
      uniforms: locationsRef.current.uniforms,
      setUniform,
      render,
      resize,
    };
  }, [setUniform, render, resize]);
}

export default useWebGL;
