/**
 * Liquid Glass Configuration
 *
 * Configuration types and presets for different UI regions
 */

// ============================================
// Types
// ============================================

export interface LiquidGlassConfig {
  // Shape
  shapeRadius: number;      // Corner radius (0-50)
  shapeRoundness: number;   // Superellipse exponent (1-4), higher = squarer corners

  // Refraction
  refThickness: number;     // Edge refraction thickness in pixels (10-80)
  refFactor: number;        // Refractive index (1.0-2.0)
  refDispersion: number;    // RGB dispersion strength (0-1)

  // Fresnel
  fresnelRange: number;     // Effect range (100-800)
  fresnelFactor: number;    // Intensity (0-1)
  fresnelHardness: number;  // Hardness (0-1)

  // Glare
  glareRange: number;       // Geometric range (100-600)
  glareFactor: number;      // Intensity (0-1)
  glareAngle: number;       // Angle in degrees (0-360)
  glareConvergence: number; // Convergence (0-1)
  glareHardness: number;    // Hardness (0-1)
  glareOppositeFactor: number; // Opposite side glare factor (0-1)

  // Color
  tintR: number;            // Tint R (0-1)
  tintG: number;            // Tint G (0-1)
  tintB: number;            // Tint B (0-1)
  tintAlpha: number;        // Tint opacity (0-0.5)

  // Shadow
  shadowExpand: number;     // Shadow expansion (10-100)
  shadowFactor: number;     // Shadow intensity (0-1)
  shadowPositionX: number;  // Shadow X offset
  shadowPositionY: number;  // Shadow Y offset

  // Blur
  blurRadius: number;       // Blur radius (0-200)
  blurEdge: boolean;        // Edge blur flag

  // Shape
  mergeRate: number;        // Shape merge rate (0-0.5)

  // Text Color (computed)
  textColorLight: string;   // Text color for light background
  textColorDark: string;    // Text color for dark background
}

export type GlassRegion =
  | 'sidebar-left'
  | 'sidebar-right'
  | 'card-hero'
  | 'card-dock'
  | 'panel-popup'
  | 'button-primary'
  | 'button-secondary'
  | 'input'
  | 'status-card'
  | 'chart-bg';

// ============================================
// Default Config
// ============================================

export const DEFAULT_GLASS_CONFIG: LiquidGlassConfig = {
  shapeRadius: 80,
  shapeRoundness: 5.0,
  refThickness: 80,
  refFactor: 1.8,
  refDispersion: 0.6,
  fresnelRange: 30,
  fresnelFactor: 0.9,
  fresnelHardness: 0.12,
  glareRange: 250,
  glareFactor: 1.0,
  glareAngle: 45,
  glareConvergence: 0.6,
  glareHardness: 0.08,
  glareOppositeFactor: 0.9,
  tintR: 1.0,
  tintG: 1.0,
  tintB: 1.0,
  tintAlpha: 0.0,
  shadowExpand: 25,
  shadowFactor: 0.15,
  shadowPositionX: 0,
  shadowPositionY: -10,
  blurRadius: 1,
  blurEdge: true,
  mergeRate: 0.05,
  textColorLight: 'rgba(0, 0, 0, 0.85)',
  textColorDark: 'rgba(255, 255, 255, 0.95)',
};

// ============================================
// Region Configurations
// ============================================

export const GLASS_REGION_CONFIGS: Record<GlassRegion, Partial<LiquidGlassConfig>> = {
  // Left Sidebar - Soft, stable, background feel
  'sidebar-left': {
    shapeRadius: 40,
    refThickness: 80,
    refFactor: 1.8,
    refDispersion: 0.6,
    fresnelRange: 30,
    fresnelFactor: 0.9,
    fresnelHardness: 0.12,
    glareRange: 250,
    glareFactor: 1.0,
    glareAngle: 45,
    glareConvergence: 0.6,
    glareHardness: 0.08,
    glareOppositeFactor: 0.9,
    tintAlpha: 0.0,
    blurRadius: 80,
    mergeRate: 0.05,
  },

  // Right Analysis Panel - Slightly stronger, highlight analysis area
  'sidebar-right': {
    shapeRadius: 20,
    refThickness: 60,
    refFactor: 1.5,
    refDispersion: 0.65,
    fresnelRange: 30,
    fresnelFactor: 0.75,
    fresnelHardness: 0.15,
    glareRange: 220,
    glareFactor: 0.9,
    glareAngle: 150,
    glareConvergence: 0.65,
    glareHardness: 0.08,
    glareOppositeFactor: 0.9,
    tintAlpha: 0.15,
    mergeRate: 0.04,
  },

  // Expert Card - Main visual focus, strongest effect
  'card-hero': {
    shapeRadius: 18,
    shapeRoundness: 2.5,
    refThickness: 50,
    refFactor: 1.6,
    refDispersion: 0.6,
    fresnelRange: 30,
    fresnelFactor: 0.7,
    glareRange: 300,
    glareFactor: 0.7,
    glareAngle: 45,
    tintAlpha: 0.12,
  },

  // Expert Dock - Small card, refined but not excessive
  'card-dock': {
    shapeRadius: 14,
    refThickness: 35,
    refFactor: 1.4,
    refDispersion: 0.4,
    fresnelFactor: 0.55,
    glareFactor: 0.5,
    glareAngle: 45,
    tintAlpha: 0.1,
  },

  // Popup Panel - Premium feel, focused
  'panel-popup': {
    shapeRadius: 24,
    shapeRoundness: 2.5,
    refThickness: 45,
    refFactor: 1.5,
    refDispersion: 0.5,
    fresnelFactor: 0.6,
    glareFactor: 0.55,
    glareAngle: 60,
    tintAlpha: 0.1,
  },

  // Primary Button - Prominent, strong clickability
  'button-primary': {
    shapeRadius: 10,
    refThickness: 25,
    refFactor: 1.4,
    refDispersion: 0.35,
    fresnelFactor: 0.5,
    glareFactor: 0.6,
    glareAngle: 45,
    tintR: 0.85,
    tintG: 0.75,
    tintB: 0.6,
    tintAlpha: 0.15,
    textColorLight: 'rgba(80, 60, 40, 0.95)',
    textColorDark: 'rgba(255, 230, 200, 0.95)',
  },

  // Secondary Button - Soft, not attention-grabbing
  'button-secondary': {
    shapeRadius: 8,
    refThickness: 20,
    refFactor: 1.3,
    refDispersion: 0.25,
    fresnelFactor: 0.4,
    glareFactor: 0.4,
    glareAngle: 45,
    tintAlpha: 0.08,
  },

  // Input - Lightest
  'input': {
    shapeRadius: 6,
    refThickness: 15,
    refFactor: 1.2,
    refDispersion: 0.2,
    fresnelFactor: 0.3,
    glareFactor: 0.25,
    tintAlpha: 0.05,
  },

  // Status Card - Information display
  'status-card': {
    shapeRadius: 12,
    refThickness: 25,
    refFactor: 1.35,
    refDispersion: 0.3,
    fresnelFactor: 0.45,
    glareFactor: 0.35,
    glareAngle: 30,
    tintAlpha: 0.08,
  },

  // Chart Background - Lightest, provides depth
  'chart-bg': {
    shapeRadius: 16,
    refThickness: 20,
    refFactor: 1.25,
    refDispersion: 0.2,
    fresnelFactor: 0.35,
    glareFactor: 0.2,
    glareAngle: 90,
    tintAlpha: 0.06,
  },
};

// ============================================
// Helper Functions
// ============================================

export function getRegionConfig(region: GlassRegion): LiquidGlassConfig {
  const regionConfig = GLASS_REGION_CONFIGS[region] || {};
  return { ...DEFAULT_GLASS_CONFIG, ...regionConfig };
}

export function getAutoTextColor(config: LiquidGlassConfig): string {
  const luminance = config.tintR * 0.299 + config.tintG * 0.587 + config.tintB * 0.114;
  const perceivedLuminance = luminance * config.tintAlpha + 0.5 * (1 - config.tintAlpha);

  if (perceivedLuminance > 0.6) {
    return config.textColorLight;
  } else if (perceivedLuminance < 0.4) {
    return config.textColorDark;
  }
  return 'rgba(0, 0, 0, 0.7)';
}

