import { useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { useGameStore } from '../store/useGameStore';

interface EngineChartProps {
  compact?: boolean;
  fluid?: boolean;
}

interface DisplayPoint {
  cp: number;
  depth: number;
  move: string;
  index: number;
  synthetic?: boolean;
}

const cpToWinRate = (cp: number): number => 1 / (1 + Math.pow(10, -cp / 400));

const formatCp = (cp: number): string => {
  if (cp === 0) return '0.00';
  const score = (cp / 100).toFixed(2);
  return cp > 0 ? `+${score}` : score;
};

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

export const EngineChart: React.FC<EngineChartProps> = ({ compact = false, fluid = false }) => {
  const { evalHistory, enginePanel } = useGameStore();
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<HTMLDivElement>(null);

  const [shellSize, setShellSize] = useState({ width: compact ? 520 : 440, height: compact ? 188 : 252 });
  const [chartSize, setChartSize] = useState({ width: compact ? 520 : 440, height: compact ? 92 : 116 });
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const update = () => {
      const node = containerRef.current;
      if (!node) return;
      setShellSize({ width: node.clientWidth || (compact ? 520 : 440), height: node.clientHeight || (compact ? 188 : 252) });
    };

    update();
    const ro = new ResizeObserver(update);
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, [compact, fluid]);

  useEffect(() => {
    if (!chartRef.current) return;

    const update = () => {
      const node = chartRef.current;
      if (!node) return;
      setChartSize({ width: node.clientWidth || (compact ? 520 : 440), height: node.clientHeight || (compact ? 92 : 116) });
    };

    update();
    const ro = new ResizeObserver(update);
    ro.observe(chartRef.current);
    return () => ro.disconnect();
  }, [compact, fluid]);

  const rawData = evalHistory.slice(-24);
  const fallbackPoint = enginePanel.bestmove
    ? {
        cp: Math.round(enginePanel.score * 100),
        depth: enginePanel.depth,
        move: enginePanel.bestmove,
      }
    : null;

  const sourceData = rawData.length > 0 ? rawData : fallbackPoint ? [fallbackPoint] : [];
  const data = useMemo<DisplayPoint[]>(() => {
    if (sourceData.length === 0) return [];
    if (sourceData.length === 1) {
      const point = sourceData[0];
      return [
        { ...point, index: 0, synthetic: true },
        { ...point, index: 1 },
      ];
    }
    return sourceData.map((point, index) => ({ ...point, index }));
  }, [sourceData]);

  const latestPoint = sourceData[sourceData.length - 1];
  const latestCp = latestPoint?.cp ?? Math.round(enginePanel.score * 100);
  const latestWinRate = cpToWinRate(latestCp) * 100;
  const blackWinRate = 100 - latestWinRate;
  const bestMove = enginePanel.bestmove || latestPoint?.move || '暂无';
  const advantageLabel = latestCp === 0 ? '局面均势' : latestCp > 0 ? '红优' : '黑优';
  const advantageValue = Math.abs(latestCp);

  const innerWidth = Math.max(48, chartSize.width);
  const innerHeight = Math.max(72, chartSize.height);
  const minCp = Math.min(...data.map((point) => point.cp), -240);
  const maxCp = Math.max(...data.map((point) => point.cp), 240);
  const range = Math.max(1, maxCp - minCp);

  const getX = (index: number) => (data.length <= 1 ? innerWidth / 2 : (index / (data.length - 1)) * innerWidth);
  const getY = (cp: number) => innerHeight - ((cp - minCp) / range) * innerHeight;

  const linePath = useMemo(() => {
    if (data.length === 0) return '';
    return data.map((point, index) => `${index === 0 ? 'M' : 'L'} ${getX(index)} ${getY(point.cp)}`).join(' ');
  }, [data, innerHeight, innerWidth, maxCp, minCp, range]);

  const areaPath = useMemo(() => {
    if (data.length === 0) return '';
    return `${linePath} L ${getX(data.length - 1)} ${innerHeight} L 0 ${innerHeight} Z`;
  }, [data.length, innerHeight, linePath]);

  const hoverTargetIndex = hoverIndex === null ? data.length - 1 : hoverIndex;
  const hoverPoint = data[hoverTargetIndex] ?? null;
  const hoverX = hoverPoint ? getX(hoverTargetIndex) : innerWidth / 2;
  const hoverY = hoverPoint ? getY(hoverPoint.cp) : innerHeight / 2;
  const tooltipLeft = clamp(hoverX - 72, 8, Math.max(8, innerWidth - 148));
  const tooltipTop = clamp(hoverY - 72, 8, Math.max(8, innerHeight - 84));
  const scoreColor = latestCp === 0 ? '#d0c8ba' : latestCp > 0 ? '#ff9a88' : '#89b9ff';
  const shellHeight = fluid ? '100%' : compact ? 188 : 252;

  if (enginePanel.isLoading && sourceData.length === 0) {
    return (
      <div ref={containerRef} style={{ ...styles.shell, width: fluid ? '100%' : shellSize.width, height: shellHeight }} className="glass-panel">
        <div style={styles.emptyStage}>
          <div style={styles.emptyTitle}>Pikafish 分析中</div>
          <div style={styles.emptyText}>正在计算当前局面的评分、最佳着法和变化序列。</div>
        </div>
      </div>
    );
  }

  if (enginePanel.error && sourceData.length === 0) {
    return (
      <div ref={containerRef} style={{ ...styles.shell, width: fluid ? '100%' : shellSize.width, height: shellHeight }} className="glass-panel">
        <div style={styles.emptyStage}>
          <div style={styles.emptyTitle}>引擎不可用</div>
          <div style={styles.emptyText}>{enginePanel.error}</div>
        </div>
      </div>
    );
  }

  if (sourceData.length === 0) {
    return (
      <div ref={containerRef} style={{ ...styles.shell, width: fluid ? '100%' : shellSize.width, height: shellHeight }} className="glass-panel">
        <div style={styles.emptyStage}>
          <div style={styles.emptyTitle}>引擎栏待机中</div>
          <div style={styles.emptyText}>分析时显示胜率走势与评估分。</div>
        </div>
      </div>
    );
  }

  return (
    <div ref={containerRef} style={{ ...styles.shell, width: fluid ? '100%' : shellSize.width, height: shellHeight }} className="glass-panel">
      <div style={styles.headlineRow}>
        <div>
          <div style={styles.headlineKicker}>局面评估</div>
          <div style={styles.headlineValue}>
            {latestCp === 0 ? '均势' : `${advantageLabel} ${advantageValue} 分`}
          </div>
        </div>
        <div style={styles.headlineMeta}>
          <span style={styles.headlineMetaItem}>红 {latestWinRate.toFixed(0)}%</span>
          <span style={styles.headlineMetaDot}>/</span>
          <span style={styles.headlineMetaItem}>黑 {blackWinRate.toFixed(0)}%</span>
        </div>
      </div>

      {/* 折线图占主体 */}
      <div ref={chartRef} style={styles.chartArea} onMouseLeave={() => setHoverIndex(null)}>
        <svg width="100%" height="100%" viewBox={`0 0 ${innerWidth} ${innerHeight}`} preserveAspectRatio="none" style={{ display: 'block', overflow: 'visible' }}>
          {[0, 0.25, 0.5, 0.75, 1].map((fraction, index) => {
            const y = fraction * innerHeight;
            return <line key={index} x1={0} y1={y} x2={innerWidth} y2={y} stroke="rgba(255,255,255,0.06)" strokeWidth={1} />;
          })}

          <line x1={0} y1={getY(0)} x2={innerWidth} y2={getY(0)} stroke="rgba(212,175,55,0.20)" strokeWidth={1} strokeDasharray="4 4" />

          <defs>
            <linearGradient id="engineWinRateGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="rgba(255,154,136,0.48)" />
              <stop offset="52%" stopColor="rgba(217,198,164,0.18)" />
              <stop offset="100%" stopColor="rgba(137,185,255,0.36)" />
            </linearGradient>
            <linearGradient id="engineScoreGradient" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#9adfff" />
              <stop offset="45%" stopColor="#e9dbc0" />
              <stop offset="100%" stopColor="#ff9a88" />
            </linearGradient>
          </defs>

          <motion.path
            d={areaPath}
            fill="url(#engineWinRateGradient)"
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.34 }}
            transition={{ duration: 0.45 }}
          />

          <motion.path
            d={linePath}
            fill="none"
            stroke="url(#engineScoreGradient)"
            strokeWidth={3}
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ filter: 'drop-shadow(0 0 6px rgba(255,255,255,0.14))' }}
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
          />

          {data.map((point, index) => {
            const active = hoverTargetIndex === index || index === data.length - 1;
            return (
              <g key={`${point.index}-${index}`} onMouseEnter={() => setHoverIndex(index)}>
                <circle cx={getX(index)} cy={getY(point.cp)} r={active ? 4 : 2.2} fill={point.cp > 0 ? '#ff9a88' : point.cp < 0 ? '#89b9ff' : '#d0c8ba'} opacity={point.synthetic ? 0.45 : active ? 1 : 0.78} />
                <circle cx={getX(index)} cy={getY(point.cp)} r={11} fill="transparent" stroke="rgba(255,255,255,0)" strokeWidth={12} />
              </g>
            );
          })}

          <motion.circle
            cx={hoverX}
            cy={hoverY}
            r={8}
            fill={scoreColor}
            opacity={0.18}
            animate={{ r: [8, 12, 8], opacity: [0.18, 0.32, 0.18] }}
            transition={{ duration: 1.8, repeat: Infinity }}
          />
        </svg>

        {hoverPoint && (
          <div style={{ ...styles.tooltip, left: tooltipLeft, top: tooltipTop }}>
            <div style={styles.tooltipTitle}>第 {Math.min(hoverPoint.index + 1, sourceData.length)} 手</div>
            <div style={styles.tooltipLine}>评估分 {formatCp(hoverPoint.cp)}</div>
            <div style={styles.tooltipLine}>红方胜率 {(cpToWinRate(hoverPoint.cp) * 100).toFixed(1)}%</div>
            <div style={styles.tooltipLine}>深度 {hoverPoint.depth}</div>
          </div>
        )}
      </div>

      {/* 底部：胜率条 + 元信息合并为一行 */}
      <div style={styles.bottomBar}>
        <div style={styles.bottomBarLeft}>
          <div style={styles.miniRail}>
            <motion.div style={styles.miniRed} animate={{ width: `${latestWinRate}%` }} transition={{ type: 'spring', stiffness: 260, damping: 26 }} />
            <motion.div style={styles.miniBlack} animate={{ width: `${blackWinRate}%` }} transition={{ type: 'spring', stiffness: 260, damping: 26 }} />
          </div>
          <span style={styles.bottomLabel}>红 {latestWinRate.toFixed(0)}%</span>
        </div>
        <div style={styles.bottomBarRight}>
          <span style={styles.metaItem}><strong style={{ ...styles.metaStrong, color: scoreColor }}>{formatCp(latestCp)}</strong></span>
          <span style={styles.metaDot}>·</span>
          <span style={styles.metaItem}>{bestMove}</span>
          <span style={styles.metaDot}>·</span>
          <span style={styles.metaItem}>D{enginePanel.depth || latestPoint?.depth || 0}</span>
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  shell: {
    display: 'flex',
    flexDirection: 'column',
    width: '100%',
    minHeight: 224,
    padding: '10px 14px 8px',
    gap: 8,
    background: 'rgba(12, 18, 31, 0.18)',
  },
  headlineRow: {
    display: 'flex',
    alignItems: 'flex-end',
    justifyContent: 'space-between',
    gap: 10,
    flexShrink: 0,
  },
  headlineKicker: {
    fontSize: 10,
    color: 'rgba(244, 241, 222, 0.42)',
    letterSpacing: '0.12em',
    textTransform: 'uppercase',
    marginBottom: 4,
  },
  headlineValue: {
    color: 'rgba(244, 241, 222, 0.96)',
    fontSize: 28,
    lineHeight: 1,
    letterSpacing: '-0.04em',
    fontWeight: 620,
  },
  headlineMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    paddingBottom: 2,
    flexShrink: 0,
  },
  headlineMetaItem: {
    color: 'rgba(244, 241, 222, 0.56)',
    fontSize: 11,
    whiteSpace: 'nowrap',
  },
  headlineMetaDot: {
    color: 'rgba(244, 241, 222, 0.22)',
    fontSize: 11,
  },
  chartArea: {
    position: 'relative',
    flex: 1,
    minHeight: 0,
  },
  bottomBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 10,
    flexShrink: 0,
  },
  bottomBarLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    minWidth: 0,
  },
  bottomBarRight: {
    display: 'flex',
    alignItems: 'center',
    gap: 5,
    flexShrink: 0,
  },
  miniRail: {
    display: 'flex',
    width: 72,
    height: 8,
    borderRadius: 999,
    overflow: 'hidden',
    background: 'rgba(255,255,255,0.06)',
    border: '1px solid rgba(255,255,255,0.06)',
    flexShrink: 0,
  },
  miniRed: {
    height: '100%',
    background: 'linear-gradient(90deg, rgba(255,135,110,0.72) 0%, rgba(255,185,130,0.94) 100%)',
  },
  miniBlack: {
    height: '100%',
    background: 'linear-gradient(90deg, rgba(92,154,255,0.96) 0%, rgba(15,76,198,0.72) 100%)',
  },
  bottomLabel: {
    color: 'rgba(244, 241, 222, 0.52)',
    fontSize: 11,
    whiteSpace: 'nowrap',
  },
  metaItem: {
    color: 'rgba(244, 241, 222, 0.58)',
    fontSize: 11,
    letterSpacing: '0.04em',
    whiteSpace: 'nowrap',
  },
  metaStrong: {
    color: 'rgba(244, 241, 222, 0.92)',
    fontWeight: 600,
  },
  metaDot: {
    color: 'rgba(244, 241, 222, 0.22)',
    fontSize: 11,
  },
  metricStrip: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 12,
    alignItems: 'end',
  },
  metricCard: {
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'flex-end',
    minWidth: 0,
  },
  metricLabel: {
    color: 'rgba(244, 241, 222, 0.48)',
    fontSize: 12,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    marginBottom: 6,
  },
  metricValue: {
    color: 'rgba(244, 241, 222, 0.94)',
    fontSize: 18,
    lineHeight: 1,
    letterSpacing: '-0.02em',
    fontWeight: 600,
  },
  metricSubtle: {
    marginTop: 4,
    color: 'rgba(244, 241, 222, 0.44)',
    fontSize: 11,
  },
  probabilityRail: {
    position: 'relative',
    display: 'flex',
    width: '100%',
    height: 14,
    borderRadius: 999,
    overflow: 'hidden',
    background: 'rgba(255,255,255,0.06)',
    border: '1px solid rgba(255,255,255,0.08)',
    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.12)',
  },
  probabilityRed: {
    height: '100%',
    background: 'linear-gradient(90deg, rgba(255,135,110,0.72) 0%, rgba(255,185,130,0.94) 100%)',
  },
  probabilityBlack: {
    height: '100%',
    background: 'linear-gradient(90deg, rgba(92,154,255,0.96) 0%, rgba(15,76,198,0.72) 100%)',
  },
  probabilityDivider: {
    position: 'absolute',
    top: 1,
    bottom: 1,
    left: '50%',
    width: 1,
    background: 'rgba(255,255,255,0.5)',
    transform: 'translateX(-0.5px)',
  },
  tooltip: {
    position: 'absolute',
    width: 140,
    padding: '10px 12px',
    borderRadius: 16,
    border: '1px solid rgba(255,255,255,0.10)',
    background: 'rgba(9, 15, 29, 0.82)',
    boxShadow: '0 10px 28px rgba(0,0,0,0.24)',
    pointerEvents: 'none',
    backdropFilter: 'blur(20px)',
  },
  tooltipTitle: {
    color: 'rgba(212, 175, 55, 0.92)',
    fontSize: 12,
    marginBottom: 6,
  },
  tooltipLine: {
    color: 'rgba(244, 241, 222, 0.84)',
    fontSize: 12,
    lineHeight: 1.6,
  },
  emptyStage: {
    display: 'flex',
    flex: 1,
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    borderRadius: 18,
    background: 'linear-gradient(180deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%)',
    border: '1px solid rgba(255,255,255,0.05)',
  },
  emptyTitle: {
    fontSize: 18,
    color: 'rgba(244, 241, 222, 0.82)',
  },
  emptyText: {
    fontSize: 12,
    color: 'rgba(244, 241, 222, 0.42)',
  },
};

export default EngineChart;
