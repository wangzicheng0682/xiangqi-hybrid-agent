import React from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  sub?: string;
}

export const StatCard: React.FC<StatCardProps> = ({ title, value, sub }) => {
  return (
    <div className="bg-paper-white/90 rounded border-2 border-gilt-gold p-3 shadow-sm">
      <div className="text-xs text-ink-black/60 mb-1">{title}</div>
      <div className="text-2xl font-bold text-china-red">{value}</div>
      {sub && <div className="text-xs text-ink-black/60">{sub}</div>}
    </div>
  );
};
