import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { useGameStore } from '../store/useGameStore';

interface PieceData {
  piece_id: string;
  side: string;
  piece_type: string;
  piece_name: string;
  position: number[];
  legal_moves: Array<{ to: number[]; type: string; status: string; note?: string }>;
  attacks: string[];
  mobility: { legal_count: number; attack_count: number; activity_score: number };
  constraints: Array<{ kind: string; target?: number[]; note?: string; block_piece?: string }>;
  geometric_tags: string[];
  positional_tags: string[];
  tactical_patterns: string[];
  material_value: number;
}

interface AnalysisData {
  analysis_structured: {
    board_fen: string;
    turn: string;
    pieces: PieceData[];
    global_patterns: any[];
    pressure_map: Record<string, string[]>;
    retrieval_info: {
      tags: string[];
      query_hints: string[];
    };
    summary: {
      red_piece_count: number;
      black_piece_count: number;
      red_material: number;
      black_material: number;
      material_balance: number;
      total_legal_moves_red: number;
      total_legal_moves_black: number;
      is_check: boolean;
      check_by: string | null;
      is_checkmate: boolean;
    };
  };
  analysis_text: {
    analysis_text: string;
    retrieval_tags: string[];
    retrieval_hints: string[];
  };
}

export default function PositionAnalysisPanel() {
  const { fen } = useGameStore();
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'pieces' | 'tags'>('overview');

  useEffect(() => {
    if (!fen) return;
    setLoading(true);
    api.getPositionAnalysis(fen)
      .then((data: any) => setAnalysis(data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [fen]);

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loadingState}>
          <div style={styles.loadingIcon}>⏳</div>
          <div>局面分析中...</div>
        </div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div style={styles.container}>
        <div style={styles.emptyState}>
          <div style={styles.emptyIcon}>📊</div>
          <div>等待局面分析</div>
        </div>
      </div>
    );
  }

  const { analysis_structured, analysis_text } = analysis;
  const { summary, pieces, turn } = analysis_structured;
  const { retrieval_tags, retrieval_hints, analysis_text: textContent } = analysis_text;

  const activePieces = pieces.filter(p => p.mobility && p.mobility.legal_count > 0);
  const blockedPieces = pieces.filter(p => p.constraints && p.constraints.length > 0);
  const attackingPieces = pieces.filter(p => p.attacks && p.attacks.length > 0);
  const tacticalPieces = pieces.filter(p => p.tactical_patterns && p.tactical_patterns.length > 0);

  function posToStr(pos: number[]): string {
    if (!pos || pos.length < 2) return '?';
    const col = String.fromCharCode(97 + pos[1]);
    const row = 9 - pos[0];
    return `${col}${row}`;
  }

  return (
    <div style={styles.container}>
      {/* 局面总览 */}
      <div style={styles.overviewCard}>
        <h3 style={styles.sectionTitle}>🏰 局面总览</h3>

        <div style={styles.badgeRow}>
          <span style={{
            ...styles.badge,
            background: turn === 'red' ? '#C41E3A' : '#2C3E50',
          }}>
            {turn === 'red' ? '红方行棋' : '黑方行棋'}
          </span>
          <span style={styles.phaseBadge}>
            {summary.red_material > 40 && summary.black_material > 40 ? '开局' :
             summary.red_material < 30 || summary.black_material < 30 ? '残局' : '中局'}
          </span>
          <span style={{
            ...styles.scoreBadge,
            background: summary.material_balance > 0 ? '#22C55E' : summary.material_balance < 0 ? '#EF4444' : '#666',
          }}>
            {summary.material_balance > 0 ? '+' : ''}{summary.material_balance.toFixed(0)}分
          </span>
        </div>

        {summary.is_check && (
          <div style={styles.alertBox}>
            <span style={styles.alertIcon}>⚠️</span>
            <span>{turn === 'red' ? '红方' : '黑方'}被将军！</span>
          </div>
        )}

        <div style={styles.statsGrid}>
          <div style={styles.statItem}>
            <span style={styles.statValue}>{summary.red_piece_count}</span>
            <span style={styles.statLabel}>红子</span>
          </div>
          <div style={styles.statItem}>
            <span style={styles.statValue}>{summary.black_piece_count}</span>
            <span style={styles.statLabel}>黑子</span>
          </div>
          <div style={styles.statItem}>
            <span style={styles.statValue}>{activePieces.length}</span>
            <span style={styles.statLabel}>活跃</span>
          </div>
          <div style={styles.statItem}>
            <span style={styles.statValue}>{blockedPieces.length}</span>
            <span style={styles.statLabel}>受限</span>
          </div>
        </div>
      </div>

      {/* 标签页 */}
      <div style={styles.tabBar}>
        {(['overview', 'pieces', 'tags'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              ...styles.tab,
              ...(activeTab === tab ? styles.tabActive : {})
            }}
          >
            {tab === 'overview' ? '摘要' : tab === 'pieces' ? '棋子' : '标签'}
          </button>
        ))}
      </div>

      {/* 标签页内容 */}
      <div style={styles.tabContent}>
        {activeTab === 'overview' && (
          <div style={styles.overviewText}>
            {textContent || '暂无分析'}
          </div>
        )}

        {activeTab === 'pieces' && (
          <div style={styles.piecesList}>
            {attackingPieces.length > 0 && (
              <div style={styles.pieceGroup}>
                <div style={styles.groupTitle}>⚔️ 攻击棋子</div>
                {attackingPieces.map(p => (
                  <div key={p.piece_id} style={styles.pieceCard}>
                    <div style={styles.pieceHeader}>
                      <strong>{p.piece_name}</strong>
                      <span style={styles.piecePos}>@{posToStr(p.position)}</span>
                    </div>
                    <div style={styles.pieceDetail}>
                      可攻击: {p.attacks.join(', ')}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {tacticalPieces.length > 0 && (
              <div style={styles.pieceGroup}>
                <div style={styles.groupTitleGold}>🎯 战术棋子</div>
                {tacticalPieces.map(p => (
                  <div key={p.piece_id} style={styles.pieceCardGold}>
                    <div style={styles.pieceHeader}>
                      <strong>{p.piece_name}</strong>
                      <span style={styles.piecePos}>@{posToStr(p.position)}</span>
                    </div>
                    <div style={styles.pieceDetailGold}>
                      {p.tactical_patterns.join(', ')}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {blockedPieces.length > 0 && (
              <div style={styles.pieceGroup}>
                <div style={styles.groupTitleMuted}>🚫 受限棋子</div>
                {blockedPieces.slice(0, 6).map(p => (
                  <div key={p.piece_id} style={styles.pieceCardMuted}>
                    <div style={styles.pieceHeader}>
                      <strong>{p.piece_name}</strong>
                      <span style={styles.piecePos}>@{posToStr(p.position)}</span>
                    </div>
                    {p.constraints.map((c, i) => (
                      <div key={i} style={styles.constraintItem}>
                        • {c.note || c.kind}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}

            {attackingPieces.length === 0 && tacticalPieces.length === 0 && blockedPieces.length === 0 && (
              <div style={styles.emptyPieces}>
                暂无特殊状态棋子
              </div>
            )}
          </div>
        )}

        {activeTab === 'tags' && (
          <div style={styles.tagsContent}>
            <div style={styles.tagSection}>
              <div style={styles.tagSectionTitle}>🏷️ 检索标签</div>
              <div style={styles.tagCloud}>
                {retrieval_tags && retrieval_tags.length > 0 ? retrieval_tags.map((tag, i) => (
                  <span key={i} style={styles.tag}>
                    {tag}
                  </span>
                )) : (
                  <span style={styles.noTags}>暂无标签</span>
                )}
              </div>
            </div>

            {retrieval_hints && retrieval_hints.length > 0 && (
              <div style={styles.hintsSection}>
                <div style={styles.hintsTitle}>💡 查询提示</div>
                {retrieval_hints.map((hint, i) => (
                  <div key={i} style={styles.hintItem}>
                    {hint}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },

  loadingState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 40,
    color: 'var(--apple-text-secondary)',
    gap: 12,
  },
  loadingIcon: {
    fontSize: 28,
  },

  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 40,
    color: 'var(--apple-text-secondary)',
    gap: 8,
  },
  emptyIcon: {
    fontSize: 40,
    marginBottom: 8,
    opacity: 0.35,
  },

  // 总览卡片
  overviewCard: {
    background: 'rgba(0,0,0,0.025)',
    borderRadius: 'var(--radius-md)',
    padding: 14,
    border: '1px solid rgba(0,0,0,0.05)',
  },
  sectionTitle: {
    color: 'rgba(212,175,55,0.85)',
    fontSize: 13,
    marginBottom: 12,
    margin: 0,
    fontWeight: '600',
  },

  // 徽章行
  badgeRow: {
    display: 'flex',
    gap: 6,
    flexWrap: 'wrap',
    marginBottom: 12,
  },
  badge: {
    padding: '4px 10px',
    color: '#fff',
    borderRadius: 'var(--radius-full)',
    fontSize: 11,
    fontWeight: '600',
  },
  phaseBadge: {
    padding: '4px 10px',
    background: 'rgba(212,175,55,0.75)',
    color: '#fff',
    borderRadius: 'var(--radius-full)',
    fontSize: 11,
    fontWeight: '600',
  },
  scoreBadge: {
    padding: '4px 10px',
    color: '#fff',
    borderRadius: 'var(--radius-full)',
    fontSize: 11,
    fontWeight: '600',
  },

  // 警告框
  alertBox: {
    padding: 10,
    background: 'rgba(239,68,68,0.1)',
    border: '1px solid rgba(239,68,68,0.18)',
    borderRadius: 'var(--radius-md)',
    marginBottom: 12,
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    color: 'rgba(239,68,68,0.85)',
    fontSize: 12,
  },
  alertIcon: {
    fontSize: 14,
  },

  // 统计网格
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: 8,
  },
  statItem: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: 10,
    background: 'rgba(0,0,0,0.03)',
    borderRadius: 'var(--radius-sm)',
  },
  statValue: {
    fontSize: 18,
    fontWeight: '600',
    color: 'var(--apple-text)',
  },
  statLabel: {
    fontSize: 10,
    color: 'var(--apple-text-tertiary)',
    marginTop: 2,
  },

  // 标签页
  tabBar: {
    display: 'flex',
    gap: 4,
    background: 'rgba(0,0,0,0.04)',
    borderRadius: 'var(--radius-md)',
    padding: 3,
  },
  tab: {
    flex: 1,
    padding: '7px 12px',
    background: 'transparent',
    border: 'none',
    borderRadius: 'var(--radius-sm)',
    color: 'var(--apple-text-secondary)',
    fontSize: 11,
    cursor: 'pointer',
    transition: 'all 0.18s cubic-bezier(0.16, 1, 0.3, 1)',
  },
  tabActive: {
    background: 'rgba(212,175,55,0.12)',
    color: 'rgba(212,175,55,0.85)',
    fontWeight: '600',
  },
  tabContent: {
    maxHeight: 300,
    overflow: 'auto',
  },

  // 概览文本
  overviewText: {
    fontSize: 12,
    lineHeight: 1.8,
    color: 'var(--apple-text-secondary)',
    whiteSpace: 'pre-wrap',
    padding: 8,
  },

  // 棋子列表
  piecesList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  pieceGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
  },
  groupTitle: {
    fontSize: 11,
    color: 'rgba(196,30,58,0.85)',
    fontWeight: '600',
  },
  groupTitleGold: {
    fontSize: 11,
    color: 'rgba(212,175,55,0.85)',
    fontWeight: '600',
  },
  groupTitleMuted: {
    fontSize: 11,
    color: 'var(--apple-text-tertiary)',
    fontWeight: '600',
  },
  pieceCard: {
    padding: 10,
    background: 'rgba(196,30,58,0.06)',
    borderRadius: 'var(--radius-md)',
    border: '1px solid rgba(196,30,58,0.12)',
  },
  pieceCardGold: {
    padding: 10,
    background: 'rgba(212,175,55,0.06)',
    borderRadius: 'var(--radius-md)',
    border: '1px solid rgba(212,175,55,0.12)',
  },
  pieceCardMuted: {
    padding: 8,
    background: 'rgba(0,0,0,0.03)',
    borderRadius: 'var(--radius-md)',
  },
  pieceHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
    fontSize: 12,
    color: 'var(--apple-text)',
  },
  piecePos: {
    color: 'var(--apple-text-tertiary)',
    fontFamily: 'SF Mono, JetBrains Mono, Consolas, monospace',
    fontSize: 10,
  },
  pieceDetail: {
    fontSize: 10,
    color: 'rgba(196,30,58,0.8)',
  },
  pieceDetailGold: {
    fontSize: 10,
    color: 'rgba(212,175,55,0.8)',
  },
  constraintItem: {
    fontSize: 10,
    color: 'var(--apple-text-tertiary)',
    paddingLeft: 8,
    marginTop: 2,
  },
  emptyPieces: {
    textAlign: 'center',
    padding: 20,
    color: 'var(--apple-text-secondary)',
    fontSize: 12,
  },

  // 标签内容
  tagsContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: 14,
  },
  tagSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  tagSectionTitle: {
    fontSize: 11,
    color: 'var(--apple-text-secondary)',
    fontWeight: '600',
  },
  tagCloud: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 4,
  },
  tag: {
    padding: '4px 10px',
    background: 'rgba(212,175,55,0.12)',
    backdropFilter: 'blur(8px)',
    color: 'rgba(160,120,20,0.9)',
    borderRadius: 'var(--radius-full)',
    fontSize: 10,
    fontWeight: '600',
    border: '1px solid rgba(212,175,55,0.2)',
  },
  noTags: {
    fontSize: 12,
    color: 'var(--apple-text-secondary)',
  },
  hintsSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
  },
  hintsTitle: {
    fontSize: 11,
    color: 'var(--apple-text-secondary)',
    fontWeight: '600',
  },
  hintItem: {
    padding: 8,
    background: 'rgba(0,0,0,0.03)',
    borderRadius: 'var(--radius-sm)',
    fontSize: 11,
    color: 'var(--apple-text-secondary)',
  },
};
