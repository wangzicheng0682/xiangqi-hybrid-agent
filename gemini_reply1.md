收到！很高兴能以前端设计的身份加入这个项目，与你和 Kimi 协作。

打造一个“天天象棋级别”的商业级应用是一个非常棒的目标。考虑到目前距离计算机设计大赛的作品提交大约还有一个月的时间，而且通常这种开发是由两三个人的核心小团队来推进，我们需要在**高性能**和**高开发效率**之间找到完美的平衡。

这里有一个关键的架构修正：**现代前端（浏览器环境）是无法直接调用 Python `core/` 模块的**。为了实现前后端分离并保证响应时间 < 3秒，**必须由后端（Kimi）提供 REST API 或 WebSocket 服务**（强烈推荐使用 FastAPI，它性能极高且支持异步，非常适合配合大模型和 Pikafish 引擎）。

以下是我为我们的象棋 AI 混合代理系统设计的前端方案：

---

## 1. 技术栈选择

为了在一个月内高效交付并保证 60fps 的流畅体验，我选择以下现代前端技术栈：

* **核心框架**: **React 18 + TypeScript + Vite**。Vite 提供极速的冷启动和热更新，React 的组件化非常适合构建复杂的棋盘交互，TypeScript 能严格定义从后端传来的 FEN 和 FEN 解析数据，避免低级 Bug。
* **状态管理**: **Zustand**。比 Redux 轻量得多，非常适合管理棋盘当前的二维数组状态、历史记录（ICCS 走法）和多模式切换。
* **样式方案**: **Tailwind CSS + Framer Motion**。Tailwind 可以快速实现你要求的中国风主题色，Framer Motion 用于实现棋子平滑移动的 60fps 动画。
* **图表库**: **Apache ECharts**。用于“复盘分析”模式下的胜率曲线图绘制，性能优异且支持丰富的标注（如转折点、劣着）。
* **网络请求**: **Axios + SWR (或 React Query)**。用于处理 API 请求和数据缓存。

## 2. 目录结构

建议采用按功能模块划分的扁平化目录结构：

```text
src/
├── assets/            # 静态资源 (宣纸背景图, 3D棋子图片/SVG)
├── components/        # 公共组件
│   ├── ChessBoard/    # 棋盘核心组件 (Board, Piece, Grid)
│   ├── Analysis/      # 分析面板组件
│   ├── Charts/        # ECharts 胜率曲线组件
│   └── UI/            # 按钮、弹窗等基础UI (鎏金边框等)
├── hooks/             # 自定义 Hooks (useGameLogic, useEngine)
├── store/             # Zustand 状态管理 (gameStore.ts)
├── services/          # 后端 API 请求封装 (api.ts)
├── views/             # 三大核心页面 (模式)
│   ├── PgnMode/       # 下棋谱模式
│   ├── PlayMode/      # 人机对战模式
│   └── ReviewMode/    # 复盘分析模式
├── styles/            # 全局样式与 Tailwind 配置
├── utils/             # 工具函数 (FEN解析, ICCS转换)
└── App.tsx            # 根组件与路由

```

## 3. 核心组件代码

### 3.1 ChessBoard.tsx

为了保证动画性能和中国风的精准渲染，棋盘采用 CSS Grid 布局叠加绝对定位的棋子。

```tsx
import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useGameStore } from '../store/gameStore';
import { Piece } from './Piece';

interface ChessBoardProps {
  onMove: (from: string, to: string) => void;
  interactive?: boolean;
}

export const ChessBoard: React.FC<ChessBoardProps> = ({ onMove, interactive = true }) => {
  const { board, legalMoves } = useGameStore();
  const [selectedPos, setSelectedPos] = useState<string | null>(null);

  const handleSquareClick = (row: number, col: number) => {
    if (!interactive) return;
    
    const pos = `${String.fromCharCode(97 + col)}${9 - row}`; // e.g., 'h2'
    
    // 如果已经选中了己方棋子，且点击的是合法目标位置
    if (selectedPos && legalMoves.includes(pos)) {
      onMove(selectedPos, pos);
      setSelectedPos(null);
    } else {
      // 否则选中该位置（需要增加逻辑判断是否为己方棋子）
      setSelectedPos(pos);
    }
  };

  return (
    <div className="relative w-[450px] h-[500px] bg-[#F5F5DC] bg-paper-texture border-4 border-[#D4AF37] shadow-2xl">
      {/* 棋盘网格绘制 (省略具体SVG连线代码，这里用CSS Grid示意) */}
      <div className="grid grid-cols-9 grid-rows-10 w-full h-full absolute inset-0">
        {board.map((row, rowIndex) => 
          row.map((piece, colIndex) => (
            <div 
              key={`${rowIndex}-${colIndex}`}
              className="relative flex items-center justify-center cursor-pointer"
              onClick={() => handleSquareClick(rowIndex, colIndex)}
            >
              {piece && (
                <Piece 
                  type={piece} 
                  isSelected={selectedPos === `${String.fromCharCode(97 + colIndex)}${9 - rowIndex}`} 
                />
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

```

### 3.2 AnalysisPanel.tsx

用于展示 Qwen 的 Markdown 讲解、引擎数据和图谱胜率。

```tsx
import React from 'react';
import ReactMarkdown from 'react-markdown';
import { useGameStore } from '../store/gameStore';

export const AnalysisPanel: React.FC = () => {
  const { analysisResult, isLoading } = useGameStore();

  if (isLoading) return <div className="text-[#C41E3A] animate-pulse">大模型与引擎深度分析中...</div>;
  if (!analysisResult) return <div className="text-[#2C3E50]">等待对局数据...</div>;

  return (
    <div className="p-4 bg-white/80 rounded border-2 border-[#D4AF37] h-full overflow-y-auto font-serif">
      <h3 className="text-xl font-bold text-[#C41E3A] mb-4 border-b-2 border-[#C41E3A] pb-2">
        局面深度解析
      </h3>
      
      {/* 引擎与图谱数据 */}
      <div className="flex gap-4 mb-4 text-sm text-[#2C3E50]">
        <div className="bg-[#F5F5DC] p-2 rounded">
          <span className="font-bold">推荐走法:</span> {analysisResult.engine_result.bestmove}
        </div>
        <div className="bg-[#F5F5DC] p-2 rounded">
          <span className="font-bold">局面评分:</span> {analysisResult.engine_result.score}
        </div>
        <div className="bg-[#F5F5DC] p-2 rounded">
          <span className="font-bold">开局库:</span> {analysisResult.kg_result.opening_name} ({analysisResult.kg_result.win_rate}% 胜率)
        </div>
      </div>

      {/* AI Markdown 讲解 */}
      <div className="prose prose-red text-[#2C3E50]">
        <ReactMarkdown>{analysisResult.explanation}</ReactMarkdown>
      </div>
    </div>
  );
};

```

## 4. 样式文件

在 `tailwind.config.js` 中配置主题色，确保中国风的统一性：

```javascript
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        'china-red': '#C41E3A',    // 朱红
        'ink-black': '#2C3E50',    // 墨黑
        'gilt-gold': '#D4AF37',    // 鎏金
        'paper-white': '#F5F5DC',  // 宣纸白
      },
      backgroundImage: {
        'paper-texture': "url('/src/assets/paper-texture.png')", // 需要准备一张轻微的宣纸纹理图
      },
      fontFamily: {
        'serif': ['"Noto Serif SC"', 'STZhongsong', 'simsun', 'serif'], // 传统衬线字体
      }
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}

```

## 5. 状态管理

使用 Zustand 管理全局共享状态（`src/store/gameStore.ts`）：

```typescript
import { create } from 'zustand';

interface GameState {
  board: string[][];
  iccsHistory: string[];
  currentMode: 'pgn' | 'play' | 'review';
  analysisResult: any | null;
  isLoading: boolean;
  legalMoves: string[];
  
  // Actions
  setMode: (mode: 'pgn' | 'play' | 'review') => void;
  makeMove: (from: string, to: string) => void;
  fetchAnalysis: (fen: string) => Promise<void>;
}

export const useGameStore = create<GameState>((set, get) => ({
  board: initialBoard, // 导入初始 10x9 数组
  iccsHistory: [],
  currentMode: 'play',
  analysisResult: null,
  isLoading: false,
  legalMoves: [],

  setMode: (mode) => set({ currentMode: mode }),
  
  makeMove: (from, to) => {
    // 1. 更新前端棋盘数组逻辑 (此处省略具体转换细节)
    // 2. 触发 API 调用验证或获取 AI 回应
  },
  
  fetchAnalysis: async (fen) => {
    set({ isLoading: true });
    try {
      // 调用 API 集成部分的接口
      const data = await window.api.analyzePosition(fen);
      set({ analysisResult: data, isLoading: false });
    } catch (error) {
      console.error(error);
      set({ isLoading: false });
    }
  }
}));

```

## 6. API集成

如前所述，前端不能直接 `import core.agent`。后端（Kimi）需要将 Python 代码包装成 REST API。前端的 `services/api.ts` 将这样调用：

```typescript
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api'; // 后端 FastAPI 地址

export const api = {
  // 对应 2.1 Agent分析API
  analyzePosition: async (fen: string, board: string[][], lastMove: any) => {
    const response = await axios.post(`${API_BASE}/analyze`, {
      fen,
      board,
      last_move_info: lastMove,
      use_vision: true
    });
    return response.data;
  },

  // 对应 2.2 复盘报告API
  generateReview: async (gameData: any) => {
    const response = await axios.post(`${API_BASE}/review`, gameData);
    return response.data;
  },

  // 对应 2.3 规则引擎API
  getLegalMoves: async (board: string[][], pos: string) => {
    const response = await axios.post(`${API_BASE}/legal-moves`, { board, pos });
    return response.data; // 返回 ['h2', 'e2', ...] 格式
  }
};

```

---

为了让我们的协作顺利推进，我们需要后端配合将现有的 Python 脚本转化为 Web 接口。**需要我为你和 Kimi 起草一份详细的 FastAPI 接口契约（API Schema 代码）吗？** 这样我们可以确保前后端联调一次通过！