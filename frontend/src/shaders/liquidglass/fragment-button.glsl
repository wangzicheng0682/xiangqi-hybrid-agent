#version 300 es
// Button Fragment Shader
// Renders liquid-glass buttons (refraction + fresnel + glare) on top of the blurred sidebar background.
// Each button is a rounded-rect SDF. Uses the same optical model as fragment-main.glsl.
// Inputs: u_blurredBg (hBlurPass texture), uniforms for button rects + optical params.

precision highp float;

#define PI 3.14159265359
const float N_R = 1.0 - 0.02;
const float N_G = 1.0;
const float N_B = 1.0 + 0.02;

// ─── Uniforms ─────────────────────────────────────────────────────────────────

in vec2 v_uv;

uniform vec2  u_resolution;
uniform float u_dpr;         // device pixel ratio

// Blurred background texture from hBlurPass
uniform sampler2D u_blurredBg;
uniform sampler2D u_bg;

// ─── Button geometry (7 buttons, CSS-pixel coords → converted to physical px) ───
// Each button: x, y, width, height, cornerRadius
// In shader: stored as vec4(x_physical, y_physical, w_physical, h_physical)
// y is measured from TOP of canvas in CSS pixels, converted to WebGL Y-down coords below.
// We store raw CSS pixel values here; the TS side converts to physical pixels.
uniform vec4 u_btn0;   // x, y(CSS-top), w, h
uniform vec4 u_btn1;
uniform vec4 u_btn2;
uniform vec4 u_btn3;
uniform vec4 u_btn4;
uniform vec4 u_btn5;
uniform vec4 u_btn6;
uniform float u_btnRadius;  // corner radius in CSS px (same for all)

// Tint per button: 0=normal, 1=primary(amber)
uniform float u_btnTint0;
uniform float u_btnTint1;
uniform float u_btnTint2;
uniform float u_btnTint3;
uniform float u_btnTint4;
uniform float u_btnTint5;
uniform float u_btnTint6;

// Active (pressed) button index; -1 = none
uniform int u_activeBtn;

// ─── Optical / liquid-glass params (mirrors fragment-main.glsl) ───────────────
uniform float u_refThickness;
uniform float u_refFactor;
uniform float u_refDispersion;
uniform float u_refFresnelRange;
uniform float u_refFresnelHardness;
uniform float u_refFresnelFactor;
uniform float u_glareRange;
uniform float u_glareHardness;
uniform float u_glareConvergence;
uniform float u_glareOppositeFactor;
uniform float u_glareFactor;
uniform float u_glareAngle;

// ─── dashersw-style corner boost + ripple (enhanced refraction) ─────────────
uniform float u_cornerBoost;     // corner refraction enhancement (default 0.02)
uniform float u_rippleEffect;    // surface ripple strength (default 0.1)

out vec4 fragColor;

// ─── SDF helpers (from fragment-main.glsl) ────────────────────────────────────

float superellipseCornerSDF(vec2 p, float r, float n) {
  p = abs(p);
  float v = pow(pow(p.x, n) + pow(p.y, n), 1.0 / n);
  return v - r;
}

float roundedRectSDF(vec2 p, vec2 center, float w, float h, float cr, float n) {
  p -= center;
  float crPx = cr;  // already in physical pixels from TS side
  vec2 d = abs(p) - vec2(w, h) * 0.5;
  float dist;
  if (d.x > -crPx && d.y > -crPx) {
    vec2 cornerCenter = sign(p) * (vec2(w, h) * 0.5 - vec2(crPx));
    vec2 cornerP = p - cornerCenter;
    dist = superellipseCornerSDF(cornerP, crPx, n);
  } else {
    dist = min(max(d.x, d.y), 0.0) + length(max(d, 0.0));
  }
  return dist;
}

// ─── Button SDF — returns vec2(dist_to_edge, button_index) ─────────────────────
// p: physical pixel position from TOP-left (y-down, matches gl_FragCoord)
// Returns vec2(distance, button_index) where distance < 0 means inside button
vec2 buttonSDF(vec2 p) {
  float bestDist = 1e10;
  float bestIdx = -1.0;

  vec4 btnArr[7];
  btnArr[0] = u_btn0; btnArr[1] = u_btn1; btnArr[2] = u_btn2;
  btnArr[3] = u_btn3; btnArr[4] = u_btn4; btnArr[5] = u_btn5; btnArr[6] = u_btn6;

  for (int i = 0; i < 7; i++) {
    vec4 b = btnArr[i];
    if (p.x >= b.x && p.x <= b.x + b.z && p.y >= b.y && p.y <= b.y + b.w) {
      float d = roundedRectSDF(p, vec2(b.x + b.z * 0.5, b.y + b.w * 0.5), b.z, b.w, u_btnRadius, 2.0);
      if (d < bestDist) {
        bestDist = d;
        bestIdx = float(i);
      }
    }
  }

  return vec2(bestDist, bestIdx);
}

// ─── Color-space helpers (from fragment-main.glsl) ────────────────────────────

const vec3 D65_WHITE = vec3(0.95045592705, 1.0, 1.08905775076);
vec3 WHITE = D65_WHITE;
const mat3 RGB_TO_XYZ_M = mat3(
  0.4124, 0.3576, 0.1805,
  0.2126, 0.7152, 0.0722,
  0.0193, 0.1192, 0.9505
);
const mat3 XYZ_TO_RGB_M = mat3(
   3.2406255, -1.537208 , -0.4986286,
  -0.9689307,  1.8757561,  0.0415175,
   0.0557101, -0.2040211,  1.0569959
);
float UNCOMPAND_SRGB(float a) {
  return a > 0.04045 ? pow((a + 0.055) / 1.055, 2.4) : a / 12.92;
}
float COMPAND_RGB(float a) {
  return a <= 0.0031308 ? 12.92 * a : 1.055 * pow(a, 0.41666666666) - 0.055;
}
vec3 SRGB_TO_RGB(vec3 srgb) {
  return vec3(UNCOMPAND_SRGB(srgb.x), UNCOMPAND_SRGB(srgb.y), UNCOMPAND_SRGB(srgb.z));
}
vec3 RGB_TO_SRGB(vec3 rgb) {
  return vec3(COMPAND_RGB(rgb.x), COMPAND_RGB(rgb.y), COMPAND_RGB(rgb.z));
}
vec3 SRGB_TO_LCH(vec3 srgb) {
  vec3 xyz = srgb * RGB_TO_XYZ_M;
  vec3 xyz_scaled = xyz / WHITE;
  const float Lf = 0.206897, Li = 0.128418;
  vec3 scaledLab = vec3(
    xyz_scaled.x > 0.008856 ? pow(xyz_scaled.x, 0.3333) : 7.787 * xyz_scaled.x + 0.137931,
    xyz_scaled.y > 0.008856 ? pow(xyz_scaled.y, 0.3333) : 7.787 * xyz_scaled.y + 0.137931,
    xyz_scaled.z > 0.008856 ? pow(xyz_scaled.z, 0.3333) : 7.787 * xyz_scaled.z + 0.137931
  );
  vec3 Lab = vec3(116.0 * scaledLab.y - 16.0, 500.0 * (scaledLab.x - scaledLab.y), 200.0 * (scaledLab.y - scaledLab.z));
  float C = sqrt(dot(Lab.yz, Lab.yz));
  float H = atan(Lab.z, Lab.y) * 57.2957795;
  return vec3(Lab.x, C, H);
}
vec3 LCH_TO_SRGB(vec3 lch) {
  float a = lch.y * cos(lch.z * 0.01745329251);
  float b = lch.y * sin(lch.z * 0.01745329251);
  vec3 xyz_scaled = vec3(
    (lch.x + 16.0) / 116.0 + a / 500.0,
    (lch.x + 16.0) / 116.0,
    (lch.x + 16.0) / 116.0 - b / 200.0
  );
  vec3 xyz = vec3(
    xyz_scaled.x > 0.206897 ? xyz_scaled.x * xyz_scaled.x * xyz_scaled.x : (xyz_scaled.x - 0.137931) / 7.787,
    xyz_scaled.y > 0.206897 ? xyz_scaled.y * xyz_scaled.y * xyz_scaled.y : (xyz_scaled.y - 0.137931) / 7.787,
    xyz_scaled.z > 0.206897 ? xyz_scaled.z * xyz_scaled.z * xyz_scaled.z : (xyz_scaled.z - 0.137931) / 7.787
  );
  xyz *= WHITE;
  vec3 rgb = xyz * XYZ_TO_RGB_M;
  return RGB_TO_SRGB(clamp(rgb, 0.0, 1.0));
}

vec4 getTextureDispersion(
  sampler2D tex1, sampler2D tex2, float mixRate,
  vec2 offset, float factor
) {
  float bgR = texture(tex1, v_uv + offset * (1.0 - (N_R - 1.0) * factor)).r;
  float bgG = texture(tex1, v_uv + offset * (1.0 - (N_G - 1.0) * factor)).g;
  float bgB = texture(tex1, v_uv + offset * (1.0 - (N_B - 1.0) * factor)).b;
  float blurR = texture(tex2, v_uv + offset * (1.0 - (N_R - 1.0) * factor)).r;
  float blurG = texture(tex2, v_uv + offset * (1.0 - (N_G - 1.0) * factor)).g;
  float blurB = texture(tex2, v_uv + offset * (1.0 - (N_B - 1.0) * factor)).b;
  return vec4(mix(bgR, blurR, mixRate), mix(bgG, blurG, mixRate), mix(bgB, blurB, mixRate), 1.0);
}

float vec2ToAngle(vec2 v) {
  float angle = atan(v.y, v.x);
  if (angle < 0.0) angle += 2.0 * PI;
  return angle;
}

// ─── Get button tint LCH color ─────────────────────────────────────────────────
vec3 getButtonTintLCH(float tintFlag, float idx) {
  if (tintFlag < 0.5) {
    // Normal button: cool blue-white glass tint
    return vec3(96.0, 4.0, 220.0);   // light blue-gray
  } else {
    // Primary button: warm amber/gold
    return vec3(82.0, 52.0, 75.0);   // amber gold
  }
}

float getButtonTintFlag(float idx) {
  if (idx < 0.5) return u_btnTint0;
  if (idx < 1.5) return u_btnTint1;
  if (idx < 2.5) return u_btnTint2;
  if (idx < 3.5) return u_btnTint3;
  if (idx < 4.5) return u_btnTint4;
  if (idx < 5.5) return u_btnTint5;
  return u_btnTint6;
}

// ─── Main ─────────────────────────────────────────────────────────────────────

void main() {
  // Physical pixel position from top-left (matches gl_FragCoord)
  vec2 physPos = gl_FragCoord.xy;

  vec2 btnResult = buttonSDF(physPos);
  float dist = btnResult.x;
  float btnIdx = btnResult.y;

  // Outside all buttons → transparent
  if (btnIdx < 0.0 || dist > 0.5) {
    fragColor = vec4(0.0);
    return;
  }

  // ── Inside a button — render liquid glass effect ──
  vec2 u_resolution1x = u_resolution.xy / u_dpr;

  // Distance in physical pixels from edge (negative = deep inside)
  float nmerged = -1.0 * (dist * u_resolution1x.y);

  // ── dashersw-style corner boost + ripple (enhanced refraction) ──────────────
  // cornerBoost: extra refraction near corners
  float distFromLeft = v_uv.x;
  float distFromRight = 1.0 - v_uv.x;
  float distFromTop = v_uv.y;
  float distFromBottom = 1.0 - v_uv.y;
  float cornerDistX = min(distFromLeft, distFromRight);
  float cornerDistY = min(distFromTop, distFromBottom);
  float cornerDist = max(cornerDistX, cornerDistY);  // 0 at corners, 0.5 at center
  float cornerBoost = exp(-cornerDist * u_resolution1x.y * 0.3) * u_cornerBoost;

  // rippleEffect: perpendicular surface ripple texture
  float normalizedDist = -nmerged;  // 0 at edge, positive inside
  float rippleWave = sin(normalizedDist * 30.0) * u_rippleEffect;
  // Use perpendicular direction to normal for ripple direction
  vec2 normalDir2d = normalize(vec2(
    buttonSDF(physPos + vec2(1.0, 0.0)).x - buttonSDF(physPos - vec2(1.0, 0.0)).x,
    buttonSDF(physPos + vec2(0.0, 1.0)).x - buttonSDF(physPos - vec2(0.0, 1.0)).x
  ));
  vec2 ripplePerp = vec2(-normalDir2d.y, normalDir2d.x);
  // rippleFactor peaks at mid-edge, fades at center and deep inside
  float rippleFactor = abs(rippleWave) * exp(-normalizedDist * 2.0);

  // Refraction
  float x_R_ratio = 1.0 - nmerged / u_refThickness;
  float thetaI = asin(clamp(pow(x_R_ratio, 2.0), 0.0, 1.0));
  float thetaT = asin(clamp(1.0 / u_refFactor * sin(thetaI), -1.0, 1.0));
  float edgeFactor = -1.0 * tan(thetaT - thetaI);
  if (nmerged >= u_refThickness) { edgeFactor = 0.0; }

  // Fake normal from SDF gradient (finite difference)
  float eps = 1.0;
  float dL = buttonSDF(physPos + vec2(-eps, 0.0)).x;
  float dR = buttonSDF(physPos + vec2( eps, 0.0)).x;
  float dU = buttonSDF(physPos + vec2(0.0, -eps)).x;
  float dD = buttonSDF(physPos + vec2(0.0,  eps)).x;
  vec2 normal = normalize(vec2(dR - dL, dD - dU));

  // Tint color
  float tintFlag = getButtonTintFlag(btnIdx);
  vec3 tintSRGB = tintFlag > 0.5
    ? vec3(0.72, 0.50, 0.22)   // amber for primary
    : vec3(0.80, 0.85, 0.92);  // cool glass for normal
  vec3 tintLCH = SRGB_TO_LCH(tintSRGB);

  // Fresnel
  float fresnelFactor = clamp(
    pow(1.0 + dist * u_resolution1x.y / 1500.0 * pow(500.0 / u_refFresnelRange, 2.0) + u_refFresnelHardness, 5.0),
    0.0, 1.0
  );

  // Glare geometry factor
  float glareGeoFactor = clamp(
    pow(1.0 + dist * u_resolution1x.y / 1500.0 * pow(500.0 / u_glareRange, 2.0) + u_glareHardness, 5.0),
    0.0, 1.0
  );

  // Glare angle
  float glareAngle = (vec2ToAngle(normalize(normal)) - PI / 4.0 + u_glareAngle) * 2.0;
  bool glareFarside = (glareAngle > PI * 1.5 || glareAngle < -PI * 0.5);
  float glareAngleFactor =
    (0.5 + sin(glareAngle) * 0.5) *
    (glareFarside ? 1.2 * u_glareOppositeFactor : 1.2) *
    u_glareFactor;
  glareAngleFactor = clamp(pow(glareAngleFactor, 0.1 + u_glareConvergence * 2.0), 0.0, 1.0);

  // Active press darkening
  bool isActive = (int(btnIdx) == u_activeBtn);
  float pressDim = isActive ? 0.80 : 1.0;

  // Composite color
  vec4 outColor;

  if (edgeFactor <= 0.0) {
    // Center of button: no refraction, just blurred bg + tint
    outColor = texture(u_blurredBg, v_uv);
    outColor = mix(outColor, vec4(tintSRGB, 1.0), tintLCH.y / 80.0 * 0.3);
  } else {
    // Edge: refraction + tint
    float edgeH = nmerged / u_refThickness;
    vec2 uvUnit = vec2(u_resolution.y / (u_resolution1x.x * u_dpr), 1.0);
    // Base refraction offset
    vec2 refractOffset = -normal * edgeFactor * 0.05 * u_dpr * uvUnit;
    // cornerBoost: extra refraction at corners
    refractOffset += -normal * cornerBoost * 0.02 * u_dpr * uvUnit;
    // rippleEffect: perpendicular surface ripple
    refractOffset += ripplePerp * rippleFactor * 0.008 * u_dpr * uvUnit;

    vec4 blurredPixel = getTextureDispersion(
      u_bg, u_blurredBg,
      1.0,  // full blur at edge
      refractOffset,
      u_refDispersion
    );

    outColor = mix(blurredPixel, vec4(tintSRGB, 1.0), tintLCH.y / 80.0 * 0.4);
  }

  // Apply press dimming
  outColor.rgb *= pressDim;

  // Fresnel highlight
  vec3 fresnelTintLCH = SRGB_TO_LCH(mix(tintSRGB, vec3(1.0), 0.5));
  fresnelTintLCH.x += 20.0 * fresnelFactor * u_refFresnelFactor;
  fresnelTintLCH.x = clamp(fresnelTintLCH.x, 0.0, 100.0);
  outColor = mix(outColor, vec4(LCH_TO_SRGB(fresnelTintLCH), 1.0), fresnelFactor * u_refFresnelFactor * 0.7 * length(normal));

  // Glare sweep
  vec3 glareTintLCH = SRGB_TO_LCH(tintSRGB);
  glareTintLCH.x += 150.0 * glareAngleFactor * glareGeoFactor;
  glareTintLCH.y += 30.0 * glareAngleFactor * glareGeoFactor;
  glareTintLCH.x = clamp(glareTintLCH.x, 0.0, 120.0);
  outColor = mix(outColor, vec4(LCH_TO_SRGB(glareTintLCH), 1.0), glareAngleFactor * glareGeoFactor * length(normal));

  // Smooth button edge
  float px = 1.0 / u_resolution1x.y;
  float edgeAlpha = 1.0 - smoothstep(-0.5 * px, 1.5 * px, dist);

  fragColor = vec4(outColor.rgb, edgeAlpha);
}
