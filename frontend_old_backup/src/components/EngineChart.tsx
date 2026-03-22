import { useMemo, useEffect, useRef } from 'react';
import { motion, useMotionValue } from 'framer-motion';
import { useGameStore } from '../store/useGameStore';

interface EngineChartProps {
  compact?: boolean;
}

// Convert centipawn to win probability (approximate)
const cpToWinRate = (cp: number): number => {
  return 1 / (1 + Math.pow(10, -cp / 400));
};

export const EngineChart: React.FC<EngineChartProps> = ({ compact = false }) => {
  const { evalHistory } = useGameStore();
  const width = compact ? 480 : 400;
  const height = compact ? 80 : 120;
  const padding = { top: 8, right: 8, bottom: 20, left: 8 };

  const data = evalHistory.slice(-20); // last 20 points

  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  const minCp = useMemo(() => Math.min(...data.map(d => d.cp), -500), [data]);
  const maxCp = useMemo(() => Math.max(...data.map(d => d.cp), 500), [data]);
  const range = maxCp - minCp || 1;

  const getX = (i: number) => padding.left + (i / Math.max(data.length - 1, 1)) * chartWidth;
  const getY = (cp: number) => padding.top + chartHeight - ((cp - minCp) / range) * chartHeight;

  // Win rate area path
  const areaPath = useMemo(() => {
    if (data.length < 2) return '';
    return data.map((d, i) => {
      const x = getX(i);
      const wr = cpToWinRate(d.cp);
      const y = padding.top + (1 - wr) * chartHeight;
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
    }).join(' ');
  }, [data, chartWidth, chartHeight]);

  const linePath = useMemo(() => {
    if (data.length < 2) return '';
    return data.map((d, i) => {
      const x = getX(i);
      const y = getY(d.cp);
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
    }).join(' ');
  }, [data, chartWidth, chartHeight, minCp, range]);

  // Current score highlight
  const currentScore = data.length > 0 ? data[data.length - 1].cp : 0;
  const currentScoreDisplay = useMemo(() => {
    if (currentScore === 0) return '0';
    return currentScore > 0 ? `+${(currentScore / 100).toFixed(2)}` : `${(currentScore / 100).toFixed(2)}`;
  }, [currentScore]);

  const isRedAdvantage = currentScore > 0;
  const scoreColor = currentScore === 0 ? '#888' : isRedAdvantage ? '#ef4444' : '#3b82f6';

  const pathLengthRef = useRef<SVGPathElement | null>(null);
  const pathLength = useMotionValue(0);

  useEffect(() => {
    if (pathLengthRef.current) {
      pathLength.set(pathLengthRef.current.getTotalLength());
    }
  }, [data]);

  if (data.length === 0) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <span style={styles.icon}>📈</span>
          <span style={styles.title}>引擎评分</span>
        </div>
        <div style={{ ...styles.emptyChart, height }}>
          <span style={styles.emptyText}>分析开始后显示评分曲线</span>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.icon}>📈</span>
        <span style={styles.title}>引擎评分</span>
        <div style={styles.scoreBadge}>
          <motion.span
            key={currentScore}
            initial={{ scale: 1.4, color: scoreColor }}
            animate={{ scale: 1, color: scoreColor }}
            transition={{ type: 'spring', stiffness: 500, damping: 20 }}
            style={styles.scoreValue}
          >
            {currentScoreDisplay}
          </motion.span>
        </div>
      </div>

      <svg width={width} height={height} style={styles.svg}>
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((frac, i) => (
          <line
            key={i}
            x1={padding.left}
            y1={padding.top + frac * chartHeight}
            x2={width - padding.right}
            y2={padding.top + frac * chartHeight}
            stroke="rgba(255,255,255,0.05)"
            strokeWidth={1}
          />
        ))}

        {/* Center line (0 cp) */}
        <line
          x1={padding.left}
          y1={getY(0)}
          x2={width - padding.right}
          y2={getY(0)}
          stroke="rgba(255,255,255,0.15)"
          strokeWidth={1}
          strokeDasharray="4 4"
        />

        {/* Win rate area fill */}
        {areaPath && (
          <motion.path
            d={areaPath + ` L ${getX(data.length - 1)} ${padding.top + chartHeight} L ${padding.left} ${padding.top + chartHeight} Z`}
            fill={`url(#winRateGradient)`}
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.15 }}
            transition={{ duration: 0.5 }}
          />
        )}

        {/* Evaluation line */}
        {linePath && (
          <motion.path
            ref={pathLengthRef as any}
            d={linePath}
            fill="none"
            stroke={scoreColor}
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
          />
        )}

        {/* Data points */}
        {data.map((d, i) => (
          <motion.circle
            key={i}
            cx={getX(i)}
            cy={getY(d.cp)}
            r={i === data.length - 1 ? 4 : 2}
            fill={d.cp > 0 ? '#ef4444' : d.cp < 0 ? '#3b82f6' : '#888'}
            initial={{ opacity: 0, scale: 0 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{
              duration: 0.3,
              delay: i * 0.03,
              type: 'spring',
              stiffness: 400,
              damping: 25,
            }}
          />
        ))}

        {/* Current point highlight */}
        {data.length > 0 && (
          <motion.circle
            cx={getX(data.length - 1)}
            cy={getY(data[data.length - 1].cp)}
            r={8}
            fill={scoreColor}
            opacity={0.2}
            animate={{ r: [8, 12, 8], opacity: [0.2, 0.4, 0.2] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          />
        )}

        {/* Gradient definition */}
        <defs>
          <linearGradient id="winRateGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#ef4444" />
            <stop offset="50%" stopColor="#888" />
            <stop offset="100%" stopColor="#3b82f6" />
          </linearGradient>
        </defs>
      </svg>

      {/* Labels */}
      <div style={{ ...styles.labels, width }}>
        <span style={styles.labelText}>红优</span>
        <span style={styles.labelText}>均势</span>
        <span style={styles.labelText}>黑优</span>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
  icon: {
    fontSize: 12,
  },
  title: {
    fontSize: 11,
    color: '#888',
    fontWeight: 500,
  },
  scoreBadge: {
    marginLeft: 'auto',
    padding: '2px 8px',
    background: 'rgba(255,255,255,0.05)',
    borderRadius: 6,
    border: '1px solid rgba(255,255,255,0.08)',
  },
  scoreValue: {
    fontSize: 12,
    fontWeight: 700,
    fontFamily: 'monospace',
  },
  svg: {
    display: 'block',
    overflow: 'visible',
  },
  emptyChart: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'rgba(0,0,0,0.2)',
    borderRadius: 8,
    border: '1px solid rgba(255,255,255,0.04)',
  },
  emptyText: {
    fontSize: 10,
    color: '#555',
    fontStyle: 'italic',
  },
  labels: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '0 8px',
  },
  labelText: {
    fontSize: 9,
    color: '#555',
  },
};

export default EngineChart;
