import React, { useState, useEffect } from 'react';
import ChessBoard from '../components/ChessBoard';
import './ReplayPage.css';

/**
 * 对弈回放页面
 */
const ReplayPage = () => {
  const [gameId, setGameId] = useState('');
  const [gameRecord, setGameRecord] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1000); // 毫秒

  useEffect(() => {
    // 从URL获取game_id
    const params = new URLSearchParams(window.location.search);
    const id = params.get('game_id');
    if (id) {
      setGameId(id);
      loadGameRecord(id);
    }
  }, []);

  const loadGameRecord = async (id) => {
    try {
      const response = await fetch(`/games/${id}`);
      if (!response.ok) {
        throw new Error('对局记录未找到');
      }
      const data = await response.json();
      setGameRecord(data);
      setCurrentStep(0);
    } catch (error) {
      console.error('加载对局记录失败:', error);
      alert('加载对局记录失败: ' + error.message);
    }
  };

  const getCurrentFen = () => {
    if (!gameRecord || !gameRecord.steps || gameRecord.steps.length === 0) {
      return 'rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1';
    }

    if (currentStep === 0) {
      return gameRecord.steps[0].board_before_fen;
    }

    if (currentStep <= gameRecord.steps.length) {
      return gameRecord.steps[currentStep - 1].board_after_fen;
    }

    return gameRecord.steps[gameRecord.steps.length - 1].board_after_fen;
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleNext = () => {
    if (gameRecord && currentStep < gameRecord.steps.length) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePlay = () => {
    if (!gameRecord) return;

    setIsPlaying(true);
    const interval = setInterval(() => {
      setCurrentStep(prev => {
        if (prev >= gameRecord.steps.length) {
          setIsPlaying(false);
          clearInterval(interval);
          return prev;
        }
        return prev + 1;
      });
    }, playbackSpeed);

    // 存储interval以便停止
    return () => clearInterval(interval);
  };

  const handlePause = () => {
    setIsPlaying(false);
  };

  const handleReset = () => {
    setCurrentStep(0);
    setIsPlaying(false);
  };

  if (!gameRecord && gameId) {
    return (
      <div className="replay-page">
        <div className="loading">加载中...</div>
      </div>
    );
  }

  if (!gameRecord) {
    return (
      <div className="replay-page">
        <div className="replay-header">
          <h1>对弈回放</h1>
          <div className="game-selector">
            <input
              type="text"
              placeholder="输入对局ID"
              value={gameId}
              onChange={(e) => setGameId(e.target.value)}
            />
            <button onClick={() => loadGameRecord(gameId)}>加载</button>
          </div>
        </div>
      </div>
    );
  }

  const currentStepData = gameRecord.steps[currentStep - 1];
  const totalSteps = gameRecord.steps.length;

  return (
    <div className="replay-page">
      <div className="replay-header">
        <h1>对弈回放</h1>
        <div className="game-info">
          <div>红方: {gameRecord.red_player}</div>
          <div>黑方: {gameRecord.black_player}</div>
          <div>结果: {gameRecord.result}</div>
          <div>总步数: {totalSteps}</div>
        </div>
      </div>

      <div className="replay-content">
        <div className="board-section">
          <ChessBoard
            fen={getCurrentFen()}
            interactive={false}
            showCoordinates={true}
          />
        </div>

        <div className="controls-section">
          <div className="playback-controls">
            <button onClick={handleReset} disabled={currentStep === 0}>
              ⏮ 开始
            </button>
            <button onClick={handlePrevious} disabled={currentStep === 0}>
              ⏪ 上一步
            </button>
            {!isPlaying ? (
              <button onClick={handlePlay} disabled={currentStep >= totalSteps}>
                ▶ 播放
              </button>
            ) : (
              <button onClick={handlePause}>⏸ 暂停</button>
            )}
            <button onClick={handleNext} disabled={currentStep >= totalSteps}>
              ⏩ 下一步
            </button>
            <button onClick={() => setCurrentStep(totalSteps)} disabled={currentStep >= totalSteps}>
              ⏭ 结束
            </button>
          </div>

          <div className="step-info">
            <div className="step-counter">
              步数: {currentStep} / {totalSteps}
            </div>
            <input
              type="range"
              min="0"
              max={totalSteps}
              value={currentStep}
              onChange={(e) => setCurrentStep(parseInt(e.target.value))}
              className="step-slider"
            />
          </div>

          <div className="speed-control">
            <label>播放速度:</label>
            <select value={playbackSpeed} onChange={(e) => setPlaybackSpeed(parseInt(e.target.value))}>
              <option value="500">快速 (0.5s)</option>
              <option value="1000">正常 (1s)</option>
              <option value="2000">慢速 (2s)</option>
              <option value="3000">很慢 (3s)</option>
            </select>
          </div>

          {currentStepData && (
            <div className="step-details">
              <h3>当前步信息</h3>
              <div>玩家: {currentStepData.player}</div>
              <div>走法: {currentStepData.move}</div>
              <div>步数: {currentStepData.step_number}</div>
            </div>
          )}

          <div className="move-list">
            <h3>走法列表</h3>
            <div className="moves">
              {gameRecord.steps.map((step, index) => (
                <div
                  key={index}
                  className={`move-item ${index === currentStep - 1 ? 'active' : ''}`}
                  onClick={() => setCurrentStep(index + 1)}
                >
                  {step.step_number}. {step.move} ({step.player})
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReplayPage;

