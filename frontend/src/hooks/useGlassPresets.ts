/**
 * useGlassPresets — 预设管理 hook
 *
 * 预设存储在 frontend/src/presets/*.json
 * 每个预设包含组件类型和参数，Git 版本控制
 */

export interface GlassPreset {
  name: string;
  component: string;
  params: {
    blurRadius: number;
    refThickness: number;
    refFactor: number;
    refDispersion: number;
    refFresnelRange: number;
    refFresnelHardness: number;
    refFresnelFactor: number;
    glareRange: number;
    glareFactor: number;
    glareAngle: number;
    glareHardness: number;
    glareConvergence: number;
    glareOppositeFactor: number;
    shapeWidth: number;
    shapeHeight: number;
    shapeRadius: number;
    shapeRoundness: number;
    mergeRate: number;
    tint: { r: number; g: number; b: number; a: number };
    shadowExpand: number;
    shadowFactor: number;
    blurEdge: boolean;
    shapePosX: number;
    shapePosY: number;
  };
}

// Vite: import all JSON files in presets/ at build time
const presetModules = import.meta.glob('../presets/*.json', { eager: true }) as Record<string, { default: GlassPreset }>;

export const ALL_PRESETS: GlassPreset[] = Object.values(presetModules).map(m => m.default);

export function getPresetsByComponent(component: string): GlassPreset[] {
  return ALL_PRESETS.filter(p => p.component === component);
}

export function exportPreset(preset: GlassPreset, filename?: string): void {
  const jsonStr = JSON.stringify(preset, null, 2);
  const blob = new Blob([jsonStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename ?? `${preset.component}.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function importPresetFromFile(file: File): Promise<GlassPreset> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const content = e.target?.result as string;
        const preset = JSON.parse(content) as GlassPreset;
        if (!preset.component || !preset.params) {
          reject(new Error('Invalid preset format'));
          return;
        }
        resolve(preset);
      } catch {
        reject(new Error('Failed to parse preset JSON'));
      }
    };
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsText(file);
  });
}
