/**
 * Liquid Card Vertex Shader
 *
 * Simple fullscreen quad vertex shader for 2D card effects.
 * Passes through position and generates UV coordinates.
 */

attribute vec2 aPosition;

varying vec2 vUv;

void main() {
    // Convert clip space [-1, 1] to UV [0, 1]
    vUv = aPosition * 0.5 + 0.5;
    gl_Position = vec4(aPosition, 0.0, 1.0);
}
