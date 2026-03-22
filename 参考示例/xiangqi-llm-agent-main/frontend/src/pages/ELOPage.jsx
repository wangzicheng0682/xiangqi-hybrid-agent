import React, { useState, useEffect } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';
import './ELOPage.css';

// 注册Chart.js组件
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

/**
 * ELO曲线页面
 */
const ELOPage = () => {
  const [leaderboard, setLeaderboard] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [eloHistory, setEloHistory] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadLeaderboard();
  }, []);

  useEffect(() => {
    if (selectedAgent) {
      loadEloHistory(selectedAgent);
    }
  }, [selectedAgent]);

  const loadLeaderboard = async () => {
    try {
      setLoading(true);
      const response = await fetch('/elo/leaderboard?limit=50');
      const data = await response.json();
      setLeaderboard(data.leaderboard || []);
    } catch (error) {
      console.error('加载排行榜失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadEloHistory = async (agentId) => {
    try {
      setLoading(true);
      const response = await fetch(`/elo/history/${agentId}`);
      if (!response.ok) {
        throw new Error('获取ELO历史失败');
      }
      const data = await response.json();
      setEloHistory(data);
    } catch (error) {
      console.error('加载ELO历史失败:', error);
      alert('加载ELO历史失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const getChartData = () => {
    if (!eloHistory || !eloHistory.history || eloHistory.history.length === 0) {
      return null;
    }

    const labels = eloHistory.history.map((_, index) => `对局 ${index + 1}`);
    const eloData = eloHistory.history.map(h => h.elo);

    return {
      labels,
      datasets: [
        {
          label: `${eloHistory.name} v${eloHistory.version} ELO`,
          data: eloData,
          borderColor: 'rgb(75, 192, 192)',
          backgroundColor: 'rgba(75, 192, 192, 0.2)',
          tension: 0.1,
          pointRadius: 3,
          pointHoverRadius: 5
        }
      ]
    };
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'ELO分数变化曲线'
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            const index = context.dataIndex;
            const history = eloHistory.history[index];
            return [
              `ELO: ${context.parsed.y.toFixed(1)}`,
              `结果: ${history.result}`,
              `对手: ${history.opponent}`
            ];
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: false,
        title: {
          display: true,
          text: 'ELO分数'
        }
      },
      x: {
        title: {
          display: true,
          text: '对局序号'
        }
      }
    }
  };

  return (
    <div className="elo-page">
      <div className="elo-header">
        <h1>ELO评分系统</h1>
        <button onClick={loadLeaderboard} disabled={loading}>
          {loading ? '加载中...' : '刷新'}
        </button>
      </div>

      <div className="elo-content">
        <div className="leaderboard-section">
          <h2>排行榜</h2>
          <div className="leaderboard-table">
            <table>
              <thead>
                <tr>
                  <th>排名</th>
                  <th>名称</th>
                  <th>版本</th>
                  <th>ELO</th>
                  <th>对局数</th>
                  <th>胜率</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.map((agent, index) => (
                  <tr
                    key={agent.agent_id}
                    className={selectedAgent === agent.agent_id ? 'selected' : ''}
                    onClick={() => setSelectedAgent(agent.agent_id)}
                  >
                    <td>{agent.rank}</td>
                    <td>{agent.name}</td>
                    <td>v{agent.version}</td>
                    <td className="elo-score">{agent.elo.toFixed(1)}</td>
                    <td>{agent.games_played}</td>
                    <td>{(agent.win_rate * 100).toFixed(1)}%</td>
                    <td>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedAgent(agent.agent_id);
                        }}
                      >
                        查看曲线
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="chart-section">
          {selectedAgent && eloHistory ? (
            <>
              <h2>
                {eloHistory.name} v{eloHistory.version} - ELO曲线
              </h2>
              {getChartData() ? (
                <div className="chart-container">
                  <Line data={getChartData()} options={chartOptions} />
                </div>
              ) : (
                <div className="no-data">暂无ELO历史数据</div>
              )}
              <div className="agent-stats">
                <div className="stat-item">
                  <span className="stat-label">当前ELO:</span>
                  <span className="stat-value">
                    {eloHistory.history.length > 0
                      ? eloHistory.history[eloHistory.history.length - 1].elo.toFixed(1)
                      : 'N/A'}
                  </span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">最高ELO:</span>
                  <span className="stat-value">
                    {eloHistory.history.length > 0
                      ? Math.max(...eloHistory.history.map(h => h.elo)).toFixed(1)
                      : 'N/A'}
                  </span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">最低ELO:</span>
                  <span className="stat-value">
                    {eloHistory.history.length > 0
                      ? Math.min(...eloHistory.history.map(h => h.elo)).toFixed(1)
                      : 'N/A'}
                  </span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">总对局数:</span>
                  <span className="stat-value">{eloHistory.history.length}</span>
                </div>
              </div>
            </>
          ) : (
            <div className="no-selection">
              <p>请从左侧排行榜选择一个Agent查看ELO曲线</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ELOPage;

