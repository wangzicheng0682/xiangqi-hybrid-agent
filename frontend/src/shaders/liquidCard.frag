/**
 * Liquid Card Fragment Shader
 *
 * Apple-style liquid glass material for card surfaces.
 * Provides edge thickness, liquid highlights, iridescent back, and hover effects.
 *
 * Layers:
 * 1. Rounded rectangle SDF - card shape
 * 2. Edge thickness - outer bright / inner dark / middle glow
 * 3. Liquid specular - directional light + top band
 * 4. Iridescent back - thin-film interference colors
 * 5. Fake refraction - local UV displacement
 * 6. Hover response - pointer-following glow
 */

precision highp float;

varying vec2 vUv;

// ========================================
// Uniforms
// ========================================
uniform vec2 uResolution;      // Canvas resolution
uniform float uTime;           // Animation time
uniform float uHover;          // Hover intensity [0, 1]
uniform float uFlip;           // Flip progress [0, 1]
uniform float uMorph;          // Morph intensity [0, 1]
uniform float uGlow;           // Global glow [0, 1]
uniform float uIntensity;      // Phase intensity [0, 1]
uniform vec3 uAccent;          // Expert accent color (RGB)
uniform vec2 uPointer;         // Mouse position (normalized)

// ========================================
// Constants
// ========================================
#define PI 3.14159265359
#define CARD_ASPECT 0.743      // 130/175 ≈ card width/height

// ========================================
// Module 1: Rounded Rectangle SDF
// ========================================
/**
 * Signed distance function for rounded rectangle
 * @param p Point in card space [-1, 1]
 * @param b Half-extents of rectangle
 * @param r Corner radius
 */
float sdRoundRect(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + r;
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
}

// ========================================
// Module 2: Edge Thickness (Three Layers)
// ========================================
struct EdgeResult {
    float outer;    // Outer bright rim
    float inner;    // Inner dark edge
    float middle;   // Middle subtle glow
};

EdgeResult calcEdge(float d) {
    EdgeResult e;
    // Outer bright line (outside edge)
    e.outer = 1.0 - smoothstep(0.0, 0.020, abs(d));
    // Inner dark line (just inside)
    e.inner = smoothstep(0.030, 0.0, abs(d));
    // Middle soft glow (between)
    e.middle = smoothstep(0.012, 0.004, abs(d));
    return e;
}

// ========================================
// Module 3: Liquid Specular Highlight
// ========================================
/**
 * Computes liquid-like specular highlights
 * - Main directional light from top-left
 * - Soft top band highlight
 * - Hover-driven shimmer
 */
float liquidSpec(vec2 uv, float t, float hover) {
    // Main directional light (from top-left)
    float spec1 = pow(max(0.0, 1.0 - uv.y), 3.0) * 0.6;

    // Top band soft highlight
    float topBand = smoothstep(0.6, 0.95, 1.0 - uv.y) * 0.35;

    // Diagonal highlight sweep
    float diag = smoothstep(0.3, 0.7, uv.x + (1.0 - uv.y) * 0.5) * 0.2;

    // Hover shimmer effect
    float shimmer = sin(t * 3.0 + uv.x * 8.0 + uv.y * 6.0) * 0.5 + 0.5;
    float hoverShimmer = shimmer * hover * 0.15;

    return spec1 + topBand + diag + hoverShimmer;
}

// ========================================
// Module 4: Iridescent Back (Thin-Film)
// ========================================
/**
 * Creates thin-film interference rainbow effect
 * @param uv Texture coordinates
 * @param t Time for animation
 * @param saturation Color saturation [0, 1]
 */
vec3 iridescence(vec2 uv, float t, float saturation) {
    // Multi-frequency interference pattern
    float a = sin(uv.x * 16.0 + t * 1.1);
    float b = sin(uv.y * 12.0 - t * 0.7);
    float c = sin((uv.x + uv.y) * 10.0 + t * 0.9);
    float d = sin((uv.x - uv.y) * 8.0 + t * 0.5);

    // RGB phase-shifted interference
    vec3 col = 0.5 + 0.5 * cos(vec3(0.0, 2.1, 4.2) + (a + b + c + d) * 1.2);

    // Control saturation (0 = grayscale, 1 = full color)
    float gray = dot(col, vec3(0.299, 0.587, 0.114));
    col = mix(vec3(gray), col, saturation);

    return col;
}

// ========================================
// Module 5: Fake Refraction (UV Displacement)
// ========================================
/**
 * Creates fake refraction effect via UV displacement
 * Does not sample real background - just distorts internal patterns
 */
vec2 fakeRefraction(vec2 uv, float strength, float t) {
    float dx = sin(uv.y * 6.0 + t * 1.2) * strength;
    float dy = cos(uv.x * 6.0 + t * 0.8) * strength;
    return clamp(uv + vec2(dx, dy), 0.0, 1.0);
}

// ========================================
// Module 6: Hover Response
// ========================================
/**
 * Creates glow effect following pointer position
 */
float hoverGlow(vec2 uv, vec2 pointer, float hover) {
    float dist = length(uv - pointer);
    return smoothstep(0.4, 0.0, dist) * hover * 0.25;
}

// ========================================
// Module 7: Corner Highlight
// ========================================
/**
 * Extra highlight at top-left corner (light source direction)
 */
float cornerHighlight(vec2 uv, float intensity) {
    float d = length(vec2(max(0.0, 0.15 - uv.x), max(0.0, 0.15 - uv.y)));
    return smoothstep(0.25, 0.0, d) * intensity * 0.3;
}

// ========================================
// Main
// ========================================
void main() {
    // Aspect-corrected coordinates
    vec2 aspect = vec2(uResolution.x / uResolution.y, 1.0);
    vec2 p = (vUv - 0.5) * aspect * 2.0;
    p.x /= CARD_ASPECT;  // Correct for card aspect ratio

    // Card size (in [-1,1] space)
    vec2 cardSize = vec2(0.9, 1.2);
    float radius = 0.06;
    float d = sdRoundRect(p, cardSize, radius);

    // Rounded rect mask
    float mask = 1.0 - smoothstep(-0.005, 0.005, d);

    // Edge effects
    EdgeResult edge = calcEdge(d);

    // Refracted UVs for internal patterns
    vec2 refractedUv = fakeRefraction(vUv, uMorph * 0.015, uTime);

    // Liquid specular highlight
    float spec = liquidSpec(vUv, uTime, uHover);

    // Iridescent back (visible when flipped)
    vec3 rainbow = iridescence(refractedUv, uTime, 0.55);

    // Hover glow following pointer
    float hGlow = hoverGlow(vUv, uPointer, uHover);

    // Corner highlight
    float corner = cornerHighlight(vUv, uIntensity);

    // ========================================
    // Color Composition
    // ========================================

    // Base color (warm white glass)
    vec3 baseColor = vec3(0.96, 0.96, 0.98);
    vec3 color = baseColor;

    // Edge thickness (three layers)
    color = mix(color, vec3(1.0), edge.outer * 0.65);      // Outer bright
    color = mix(color, vec3(0.15), edge.inner * 0.12);     // Inner dark
    color = mix(color, vec3(1.0), edge.middle * 0.35);     // Middle glow

    // Liquid specular (tinted by accent color)
    vec3 specCol = spec * (1.0 + uAccent * 0.25);
    color += specCol * uIntensity * 0.5;

    // Iridescent back (mixed based on flip progress)
    float rainbowMix = uFlip * uIntensity;
    color = mix(color, rainbow, rainbowMix * 0.30);

    // Hover glow (accent colored)
    color += hGlow * uAccent * 1.2;

    // Corner highlight
    color += corner * (1.0 + uAccent * 0.2);

    // Global glow boost
    color += uGlow * 0.08;

    // Accent rim light
    float rim = 1.0 - smoothstep(-0.015, 0.035, d);
    color += rim * uAccent * 0.18 * uIntensity;

    // Alpha: mask + soft rim
    float alpha = mask;
    alpha = max(alpha, rim * 0.25);

    gl_FragColor = vec4(color, alpha);
}
