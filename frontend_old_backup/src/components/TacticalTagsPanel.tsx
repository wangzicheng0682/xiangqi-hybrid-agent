import { useEffect, useState } from 'react';
import { useGameStore } from '../store/useGameStore';

interface TacticalTag {
  name: string;
  category: string;
  description: string;
  confidence: number;
  bind_pieces: string[];
  metadata: Record<string, any>;
}

interface TacticalTagsData {
  fen: string;
  tags: TacticalTag[];
  tags_by_category: Record<string, TacticalTag[]>;
}

const CATEGORY_INFO: Record<string, { label: string; icon: string; color: string }> = {
  '将杀困毙层': { label: '将杀困毙', icon: '⚔️', color: '#C41E3A' },
  '捉子层': { label: '捉子', icon: '🎯', color: '#D4AF37' },
  '闪击抽将层': { label: '闪击抽将', icon: '⚡', color: '#EF4444' },
  '牵制串打层': { label: '牵制串打', icon: '🔗', color: '#8B5CF6' },
  '标准杀法层': { label: '标准杀法', icon: '👑', color: '#22C55E' },
  '子力状态层': { label: '子力状态', icon: '📊', color: '#3B82F6' },
  '局面语义层': { label: '局面语义', icon: '🧠', color: '#F59E0B' },
};

const TAG_LABELS: Record<string, string> = {
  'is_check': '被将军',
  'is_checkmate': '将死',
  'is_stalemate': '困毙',
  'is_attack_unprotected': '攻无根',
  'is_mutual_attack': '互吃',
  'is_attack_king_adjacent': '攻将邻',
  'is_discovered_check': '闪将',
  'is_double_attack_with_check': '抽将',
  'is_discovered_attack': '闪击',
  'is_pinned': '被牵制',
  'is_cannon_double_attack': '炮串打',
  'checkmate_horse_back_cannon': '马后炮',
  'checkmate_iron_gate': '铁门栓',
  'checkmate_double_rook': '双车错',
  'checkmate_horse_corner': '卧槽马',
  'checkmate_bare_king': '白脸将',
  'checkmate_double_cannon_battery': '重炮杀',
  'checkmate_sea_bottom_moon': '海底捞月',
  'checkmate_side_tiger': '侧面虎',
  'piece_is_unprotected': '子无根',
  'cannon_has_platform': '炮有架',
  'phase_opening': '开局阶段',
  'phase_middlegame': '中局阶段',
  'phase_endgame': '残局阶段',
  'king_safety_critical': '将帅危急',
  'has_initiative': '握有主动权',
  'is_forcing_move': '强制手段',
  'horse_leg_blocked': '马脚被别',
  'kings_face_to_face': '双将对面',
  'cannon_battery': '重炮阵型',
  'favorable_exchange': '有利兑换',
};

function parsePiecePosition(pieceStr: string): { row: number; col: number } | null {
  if (!pieceStr || pieceStr.length < 2) return null;
  const colChar = pieceStr.charAt(0).toLowerCase();
  const rowChar = pieceStr.charAt(1);
  const col = colChar.charCodeAt(0) - 'a'.charCodeAt(0);
  const row = 9 - parseInt(rowChar);
  if (col < 0 || col > 8 || row < 0 || row > 9) return null;
  return { row, col };
}

function getConnectionType(tagName: string): 'attack' | 'defense' | 'pin' {
  if (tagName.includes('pinned') || tagName.includes('牵制')) return 'pin';
  if (tagName.includes('attack') || tagName.includes('攻')) return 'attack';
  return 'defense';
}

export default function TacticalTagsPanel() {
  const { fen, setHighlightedPieces, setConnectionLines, clearHighlights } = useGameStore();
  const [data, setData] = useState<TacticalTagsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTag, setActiveTag] = useState<string | null>(null);

  useEffect(() => {
    if (!fen) return;

    setLoading(true);
    setError(null);

    fetch('/api/tactical-tags', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fen })
    })
      .then(res => res.json())
      .then(setData)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [fen]);

  const handleTagHover = (tag: TacticalTag) => {
    setActiveTag(tag.name);
    const pieces: { row: number; col: number; type: 'attack' | 'target' | 'defense' }[] = [];
    const lines: { from: { row: number; col: number }; to: { row: number; col: number }; type: 'attack' | 'defense' | 'pin' }[] = [];
    
    const connectionType = getConnectionType(tag.name);
    
    tag.bind_pieces.forEach((pieceStr, index) => {
      const pos = parsePiecePosition(pieceStr);
      if (pos) {
        pieces.push({ ...pos, type: index === 0 ? 'attack' : 'target' });
      }
    });

    if (tag.bind_pieces.length >= 2) {
      const from = parsePiecePosition(tag.bind_pieces[0]);
      const to = parsePiecePosition(tag.bind_pieces[1]);
      if (from && to) {
        lines.push({ from, to, type: connectionType });
      }
    }

    if (tag.metadata?.attacker && tag.metadata?.target) {
      const from = parsePiecePosition(tag.metadata.attacker);
      const to = parsePiecePosition(tag.metadata.target);
      if (from && to) {
        lines.push({ from, to, type: 'attack' });
        pieces.push({ ...from, type: 'attack' });
        pieces.push({ ...to, type: 'target' });
      }
    }

    setHighlightedPieces(pieces);
    setConnectionLines(lines);
  };

  const handleTagLeave = () => {
    setActiveTag(null);
    clearHighlights();
  };

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loadingState}>
          <div style={styles.loadingIcon}>🔍</div>
          <div>检测战术标签...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.container}>
        <div style={styles.errorState}>
          <div style={styles.errorIcon}>❌</div>
          <div>检测失败</div>
          <div style={styles.errorMessage}>{error}</div>
        </div>
      </div>
    );
  }

  if (!data || data.tags.length === 0) {
    return (
      <div style={styles.container}>
        <div style={styles.emptyState}>
          <div style={styles.emptyIcon}>🏷️</div>
          <div>暂无战术标签</div>
          <div style={styles.emptyHint}>走棋后自动检测</div>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* 标题 */}
      <div style={styles.header}>
        <h3 style={styles.title}>🏷️ 战术标签</h3>
        <span style={styles.countBadge}>{data.tags.length}</span>
      </div>

      {/* 分类标签 */}
      {Object.entries(data.tags_by_category).map(([category, tags]) => {
        const catInfo = CATEGORY_INFO[category] || { label: category, icon: '📌', color: '#666' };

        return (
          <div key={category} style={styles.categorySection}>
            <div style={styles.categoryHeader}>
              <span style={styles.categoryIcon}>{catInfo.icon}</span>
              <span style={{ ...styles.categoryLabel, color: catInfo.color }}>
                {catInfo.label}
              </span>
              <span style={styles.categoryCount}>({tags.length})</span>
            </div>

            <div style={styles.tagGrid}>
              {tags.map((tag, i) => (
                <div
                  key={i}
                  style={{
                    ...styles.tagItem,
                    borderColor: `${catInfo.color}40`,
                    background: activeTag === tag.name ? `${catInfo.color}30` : `${catInfo.color}15`,
                    boxShadow: activeTag === tag.name ? `0 0 8px ${catInfo.color}50` : 'none',
                  }}
                  title={`${tag.description}\n绑定: ${tag.bind_pieces.join(', ') || '无'}`}
                  onMouseEnter={() => handleTagHover(tag)}
                  onMouseLeave={handleTagLeave}
                >
                  {TAG_LABELS[tag.name] || tag.name}
                </div>
              ))}
            </div>
          </div>
        );
      })}

      {/* 杀法高亮 */}
      {data.tags_by_category['标准杀法层'] && data.tags_by_category['标准杀法层'].length > 0 && (
        <div style={styles.checkmateBox}>
          <div style={styles.checkmateTitle}>🎉 检测到杀法！</div>
          {data.tags_by_category['标准杀法层'].map((tag, i) => (
            <div key={i} style={styles.checkmateItem}>
              <strong>{TAG_LABELS[tag.name] || tag.name}</strong>
              <span style={styles.checkmatePieces}>
                {tag.bind_pieces.join(' → ')}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* 局面语义 */}
      {data.tags_by_category['局面语义层'] && (
        <div style={styles.semanticSection}>
          <div style={styles.semanticTitle}>📊 局面分析</div>
          <div style={styles.semanticBadges}>
            {data.tags_by_category['局面语义层']
              .filter(t => t.name.startsWith('phase_'))
              .map((tag, i) => (
                <span key={i} style={styles.phaseBadge}>
                  {TAG_LABELS[tag.name]}
                </span>
              ))}

            {data.tags_by_category['局面语义层']
              .filter(t => t.name === 'has_initiative')
              .map((_, i) => (
                <span key={i} style={styles.initiativeBadge}>
                  握有主动权
                </span>
              ))}

            {data.tags_by_category['局面语义层']
              .filter(t => t.name === 'king_safety_critical')
              .map((_, i) => (
                <span key={i} style={styles.dangerBadge}>
                  ⚠️ 将帅危急
                </span>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },

  // 加载状态
  loadingState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 40,
    color: '#888',
    gap: 12,
  },
  loadingIcon: {
    fontSize: 32,
  },

  // 错误状态
  errorState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 40,
    color: '#EF4444',
    gap: 8,
  },
  errorIcon: {
    fontSize: 32,
  },
  errorMessage: {
    fontSize: 11,
    color: '#666',
    marginTop: 4,
  },

  // 空状态
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 40,
    color: '#666',
    gap: 8,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 8,
    opacity: 0.5,
  },
  emptyHint: {
    fontSize: 11,
    color: '#444',
  },

  // 头部
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  title: {
    fontSize: 13,
    color: '#D4AF37',
    margin: 0,
  },
  countBadge: {
    padding: '2px 8px',
    background: 'rgba(212,175,55,0.2)',
    color: '#D4AF37',
    borderRadius: 10,
    fontSize: 11,
    fontWeight: 'bold',
  },

  // 分类区块
  categorySection: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    padding: 12,
    background: 'rgba(255,255,255,0.03)',
    borderRadius: 8,
    border: '1px solid rgba(255,255,255,0.06)',
  },
  categoryHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
  categoryIcon: {
    fontSize: 14,
  },
  categoryLabel: {
    fontSize: 12,
    fontWeight: 'bold',
  },
  categoryCount: {
    fontSize: 10,
    color: '#555',
  },

  // 标签网格
  tagGrid: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 4,
  },
  tagItem: {
    padding: '5px 10px',
    borderRadius: 4,
    fontSize: 11,
    color: '#ddd',
    cursor: 'pointer',
    transition: 'all 0.2s',
    border: '1px solid',
  },

  // 杀法高亮
  checkmateBox: {
    padding: 14,
    background: 'linear-gradient(135deg, rgba(34,197,94,0.15), rgba(34,197,94,0.05))',
    border: '1px solid rgba(34,197,94,0.3)',
    borderRadius: 8,
  },
  checkmateTitle: {
    color: '#22C55E',
    fontSize: 13,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  checkmateItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '6px 0',
    fontSize: 12,
    color: '#ccc',
    borderBottom: '1px solid rgba(255,255,255,0.05)',
  },
  checkmatePieces: {
    color: '#888',
    fontSize: 11,
  },

  // 局面语义
  semanticSection: {
    padding: 12,
    background: 'rgba(255,255,255,0.03)',
    borderRadius: 8,
    border: '1px solid rgba(255,255,255,0.06)',
  },
  semanticTitle: {
    fontSize: 11,
    color: '#888',
    marginBottom: 10,
  },
  semanticBadges: {
    display: 'flex',
    gap: 6,
    flexWrap: 'wrap',
  },
  phaseBadge: {
    padding: '5px 12px',
    background: '#F59E0B',
    color: '#fff',
    borderRadius: 12,
    fontSize: 11,
    fontWeight: 'bold',
  },
  initiativeBadge: {
    padding: '5px 12px',
    background: '#22C55E',
    color: '#fff',
    borderRadius: 12,
    fontSize: 11,
    fontWeight: 'bold',
  },
  dangerBadge: {
    padding: '5px 12px',
    background: '#EF4444',
    color: '#fff',
    borderRadius: 12,
    fontSize: 11,
    fontWeight: 'bold',
  },
};
