/**
 * useNoiseTexture Hook — Canvas 预渲染物理噪点
 *
 * 核心原理：
 * - 使用 Canvas 生成随机灰度噪点
 * - 返回 base64 DataURL 作为背景图
 * - 比 SVG feTurbulence 更细腻、更随机
 *
 * 使用：
 *   const noiseUrl = useNoiseTexture(128, 0.02);
 *   <div style={{ backgroundImage: `url(${noiseUrl})` }} />
 */

import { useMemo } from 'react';

export function useNoiseTexture(size: number = 128, opacity: number = 0.02): string {
  return useMemo(() => {
    // 创建离屏 Canvas
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = size;
    const ctx = canvas.getContext('2d');

    if (!ctx) {
      console.warn('Canvas context not available');
      return '';
    }

    // 获取像素数据
    const imageData = ctx.createImageData(size, size);
    const data = imageData.data;

    // 生成随机灰度噪点
    for (let i = 0; i < data.length; i += 4) {
      const val = Math.random() * 255; // 随机灰度值
      data[i] = val;     // R
      data[i + 1] = val; // G
      data[i + 2] = val; // B
      data[i + 3] = 255; // Alpha (完全不透明，由 CSS opacity 控制透明度)
    }

    // 写入像素数据
    ctx.putImageData(imageData, 0, 0);

    // 返回 base64 DataURL
    return canvas.toDataURL();
  }, [size, opacity]);
}

/**
 * 将噪点应用到 DOM 元素
 */
export function applyNoiseToElement(
  element: HTMLElement | null,
  noiseUrl: string
): void {
  if (!element) return;
  element.style.backgroundImage = `url(${noiseUrl})`;
}
