/**
 * useLiquidGlass Hook — iOS 26 液态玻璃效果
 *
 * 功能：
 * 1. 鼠标坐标追踪 → 动态高光折射
 * 2. 弹簧物理动画 → 丝滑过渡
 *
 * 使用：
 *   const { style, onMouseMove, onMouseLeave } = useLiquidGlass();
 *   <div style={style} onMouseMove={onMouseMove} onMouseLeave={onMouseLeave}>
 */

import { useState, useCallback, useRef, useEffect } from 'react';

interface LiquidGlassOptions {
  /** 弹簧刚度，默认 0.15 */
  springStiffness?: number;
}

interface LiquidGlassReturn {
  /** 应用于元素的 style 对象 */
  style: React.CSSProperties;
  /** 鼠标移动事件处理器 */
  onMouseMove: (e: React.MouseEvent<HTMLElement>) => void;
  /** 鼠标离开事件处理器 */
  onMouseLeave: () => void;
  /** 当前 CSS 变量（用于调试） */
  cssVars: {
    mouseX: string;
    mouseY: string;
  };
}

export function useLiquidGlass(options: LiquidGlassOptions = {}): LiquidGlassReturn {
  const { springStiffness = 0.15 } = options;

  // 当前状态
  const [cssVars, setCssVars] = useState({
    mouseX: '50%',
    mouseY: '50%',
  });

  // 目标值（弹簧动画用）
  const targetRef = useRef({ x: 0.5, y: 0.5 });
  // 当前值（弹簧动画用）
  const currentRef = useRef({ x: 0.5, y: 0.5 });
  // 动画帧 ID
  const rafRef = useRef<number | null>(null);

  // 弹簧动画循环
  useEffect(() => {
    const animate = () => {
      const target = targetRef.current;
      const current = currentRef.current;

      // 弹簧物理
      const dx = target.x - current.x;
      const dy = target.y - current.y;

      // 应用弹簧力
      current.x += dx * springStiffness;
      current.y += dy * springStiffness;

      // 更新状态（只有变化足够大时才触发重渲染）
      const threshold = 0.001;
      if (Math.abs(dx) > threshold || Math.abs(dy) > threshold) {
        setCssVars({
          mouseX: `${current.x * 100}%`,
          mouseY: `${current.y * 100}%`,
        });
      }

      rafRef.current = requestAnimationFrame(animate);
    };

    rafRef.current = requestAnimationFrame(animate);

    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, [springStiffness]);

  // 鼠标移动：计算坐标
  const onMouseMove = useCallback((e: React.MouseEvent<HTMLElement>) => {
    const rect = (e.target as HTMLElement).getBoundingClientRect();

    // 归一化坐标 [0, 1]
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;

    // 更新目标值
    targetRef.current = { x, y };
  }, []);

  // 鼠标离开：回到中心
  const onMouseLeave = useCallback(() => {
    targetRef.current = { x: 0.5, y: 0.5 };
  }, []);

  // 组装 style 对象
  const style: React.CSSProperties = {
    '--mouse-x': cssVars.mouseX,
    '--mouse-y': cssVars.mouseY,
  } as React.CSSProperties;

  return {
    style,
    onMouseMove,
    onMouseLeave,
    cssVars,
  };
}
