import { useState } from 'react';
import { useGameStore } from '../store/useGameStore';

export default function PGNPanel() {
  const [pgnText, setPgnText] = useState('');
  const [loading, setLoading] = useState(false);
  
  const { loadGameFromPGN } = useGameStore();

  const handleLoadPGN = async () => {
    if (!pgnText.trim()) return;
    setLoading(true);
    try {
      await loadGameFromPGN(pgnText);
    } catch (e) {
      console.error('加载PGN失败:', e);
    }
    setLoading(false);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        const content = event.target?.result as string;
        setPgnText(content);
      };
      reader.readAsText(file);
    }
  };

  return (
    <div style={{
      background: 'rgba(245,245,220,0.95)',
      borderRadius: 8,
      padding: 15,
      boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
    }}>
      <h3 style={{ color: '#C41E3A', marginBottom: 15, fontSize: 16 }}>
        📄 导入PGN棋谱
      </h3>
      
      <div style={{ marginBottom: 10 }}>
        <label style={{
          display: 'block',
          padding: '15px',
          border: '2px dashed #ccc',
          borderRadius: 6,
          textAlign: 'center',
          cursor: 'pointer',
          fontSize: 13,
          color: '#666'
        }}>
          <input
            type="file"
            accept=".pgn,.pgns,.txt"
            onChange={handleFileUpload}
            style={{ display: 'none' }}
          />
          📁 点击选择PGN文件
        </label>
      </div>

      <textarea
        value={pgnText}
        onChange={(e) => setPgnText(e.target.value)}
        placeholder="或粘贴PGN内容..."
        style={{
          width: '100%',
          height: 120,
          padding: 10,
          borderRadius: 6,
          border: '1px solid #ccc',
          fontSize: 11,
          fontFamily: 'monospace',
          resize: 'vertical',
          outline: 'none'
        }}
      />

      <button
        onClick={handleLoadPGN}
        disabled={!pgnText.trim() || loading}
        style={{
          width: '100%',
          marginTop: 10,
          padding: '10px',
          borderRadius: 6,
          border: 'none',
          background: pgnText.trim() && !loading ? '#D4AF37' : '#ccc',
          color: '#fff',
          fontWeight: 'bold',
          cursor: pgnText.trim() && !loading ? 'pointer' : 'not-allowed',
          fontSize: 13
        }}
      >
        {loading ? '加载中...' : '加载棋谱'}
      </button>
    </div>
  );
}
