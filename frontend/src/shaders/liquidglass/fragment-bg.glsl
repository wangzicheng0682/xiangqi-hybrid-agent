#version 300 es

precision highp float;

in vec2 v_uv;
out vec4 fragColor;

uniform vec2 u_resolution;
uniform float u_dpr;
uniform vec2 u_mouse;
uniform vec2 u_mouseSpring;
uniform float u_time;
uniform float u_mergeRate;
uniform float u_shapeWidth;
uniform float u_shapeHeight;
uniform float u_shapeRadius;
uniform float u_shapeRoundness;
uniform float u_shadowExpand;
uniform float u_shadowFactor;
uniform vec2 u_shadowPosition;
uniform int u_bgType;
uniform sampler2D u_bgTexture;
uniform float u_bgTextureRatio;
uniform int u_bgTextureReady;
uniform int u_showShape1;
uniform int u_showShape3;
uniform float u_shape3PosX;
uniform float u_shape3PosY;
uniform float u_shape3Width;
uniform float u_shape3Height;
uniform float u_shape3Radius;
uniform float u_shape3Roundness;
// shape3 独立阴影参数
uniform float u_shape3ShadowExpand;
uniform float u_shape3ShadowFactor;
uniform vec2 u_shape3ShadowPosition;  // 默认 {0, -10}

float chessboard(vec2 uv, float size, int mode) {
  float yBars = step(size * 2.0, mod(uv.y * 2.0, size * 4.0));
  float xBars = step(size * 2.0, mod(uv.x * 2.0, size * 4.0));

  if (mode == 0) {
    return yBars;
  } else if (mode == 1) {
    return xBars;
  } else {
    return abs(yBars - xBars);
  }
}

float halfColor(vec2 uv) {
  if (uv.y > 0.5) {
    return 1.0;
  } else {
    return 0.0;
  }
}

float sdCircle(vec2 p, float r) {
  return length(p) - r;
}

float superellipseCornerSDF(vec2 p, float r, float n) {
  p = abs(p);
  float v = pow(pow(p.x, n) + pow(p.y, n), 1.0 / n);
  return v - r;
}

float roundedRectSDF(vec2 p, vec2 center, float width, float height, float cornerRadius, float n) {
  p -= center;

  float cr = cornerRadius * u_dpr;
  vec2 d = abs(p) - vec2(width * u_dpr, height * u_dpr) * 0.5;

  float dist;

  if (d.x > -cr && d.y > -cr) {
    vec2 cornerCenter = sign(p) * (vec2(width * u_dpr, height * u_dpr) * 0.5 - vec2(cr));
    vec2 cornerP = p - cornerCenter;
    dist = superellipseCornerSDF(cornerP, cr, n);
  } else {
    dist = min(max(d.x, d.y), 0.0) + length(max(d, 0.0));
  }

  return dist;
}

float smin(float a, float b, float k) {
  float h = clamp(0.5 + 0.5 * (b - a) / k, 0.0, 1.0);
  return mix(b, a, h) - k * h * (1.0 - h);
}

float mainSDF(vec2 p1, vec2 p2, vec2 p3, vec2 p) {
  vec2 p1n = p1 + p / u_resolution.y;
  vec2 p2n = p2 + p / u_resolution.y;
  vec2 p3n = p3 + p / u_resolution.y;
  float d1 = u_showShape1 == 1 ? sdCircle(p1n, 100.0 * u_dpr / u_resolution.y) : 1.0;
  float d2 = roundedRectSDF(
    p2n,
    vec2(0.0),
    u_shapeWidth / u_resolution.y,
    u_shapeHeight / u_resolution.y,
    u_shapeRadius / u_resolution.y,
    u_shapeRoundness
  );
  float d3 = u_showShape3 == 1 ? roundedRectSDF(
    p3n,
    vec2(0.0),
    u_shape3Width / u_resolution.y,
    u_shape3Height / u_resolution.y,
    u_shape3Radius / u_resolution.y,
    u_shape3Roundness
  ) : 1.0;
  float d = smin(d1, d2, u_mergeRate);
  d = smin(d, d3, u_mergeRate * 0.5);
  return d;
}

vec2 getCoverUV(vec2 uv, float canvasAspect, float textureAspect) {
  if (canvasAspect > textureAspect) {
    float scale = textureAspect / canvasAspect;
    uv.y = uv.y * scale + 0.5 - 0.5 * scale;
  } else {
    float scale = canvasAspect / textureAspect;
    uv.x = uv.x * scale + 0.5 - 0.5 * scale;
  }
  return uv;
}

void main() {
  vec2 u_resolution1x = u_resolution.xy / u_dpr;
  vec3 bgColor = vec3(1.0);

  if (u_bgType <= 0) {
    bgColor = vec3(1.0 - chessboard(gl_FragCoord.xy / u_dpr, 20.0, 2) / 4.0);
  } else if (u_bgType <= 1) {
    if (v_uv.x < 0.5 && v_uv.y > 0.5) {
      bgColor = vec3(chessboard(gl_FragCoord.xy / u_dpr, 10.0, 0));
    } else if (v_uv.x > 0.5 && v_uv.y < 0.5) {
      bgColor = vec3(chessboard(gl_FragCoord.xy / u_dpr, 10.0, 1));
    } else if (v_uv.x < 0.5 && v_uv.y < 0.5) {
      bgColor = vec3(0.0);
    }
  } else if (u_bgType <= 2) {
    bgColor = vec3(halfColor(gl_FragCoord.xy / u_resolution) * 0.6 + 0.3);
  } else if (u_bgType <= 11) {
    if (u_bgTextureReady != 1) {
      bgColor = vec3(1.0 - chessboard(gl_FragCoord.xy / u_dpr, 20.0, 2) / 4.0);
    } else {
      vec2 uv = getCoverUV(v_uv, u_resolution.x / u_resolution.y, u_bgTextureRatio);
      bgColor = texture(u_bgTexture, uv).rgb;
    }
  }

  // draw shadow — shape2/shape3 各自独立阴影
  vec2 p2 = (vec2(0, 0) - u_mouseSpring + vec2(u_shadowPosition.x * u_dpr, u_shadowPosition.y * u_dpr)) / u_resolution.y;
  float d2 = roundedRectSDF(p2 + gl_FragCoord.xy / u_resolution.y, vec2(0.0),
    u_shapeWidth / u_resolution.y, u_shapeHeight / u_resolution.y,
    u_shapeRadius / u_resolution.y, u_shapeRoundness);
  float shadow2 = exp(-1.0 / u_shadowExpand * abs(d2) * u_resolution1x.y) * 0.6 * u_shadowFactor;

  vec2 p3 = (vec2(0, 0) - vec2(u_shape3PosX, u_shape3PosY) + vec2(u_shape3ShadowPosition.x * u_dpr, u_shape3ShadowPosition.y * u_dpr)) / u_resolution.y;
  float d3 = roundedRectSDF(p3 + gl_FragCoord.xy / u_resolution.y, vec2(0.0),
    u_shape3Width / u_resolution.y, u_shape3Height / u_resolution.y,
    u_shape3Radius / u_resolution.y, u_shape3Roundness);
  float shadow3 = u_showShape3 == 1
    ? exp(-1.0 / u_shape3ShadowExpand * abs(d3) * u_resolution1x.y) * 0.6 * u_shape3ShadowFactor
    : 0.0;

  float shadow = clamp(shadow2 + shadow3, 0.0, 1.0);
  fragColor = vec4(bgColor - vec3(shadow), 1.0);
}
