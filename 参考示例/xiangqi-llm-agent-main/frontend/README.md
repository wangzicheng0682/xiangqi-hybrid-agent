# 中国象棋AI - 前端应用

## 功能特性

1. **实时对弈页面** (`/game`)
   - WebSocket 实时对弈
   - 交互式棋盘
   - 走法历史显示
   - 游戏状态管理

2. **对弈回放页面** (`/replay`)
   - 加载历史对局
   - 步进播放
   - 自动播放（可调速度）
   - 走法列表导航

3. **ELO曲线页面** (`/elo`)
   - ELO排行榜
   - ELO历史曲线
   - 多版本Agent对比
   - 统计信息展示

## 安装和运行

```bash
# 安装依赖
npm install

# 启动开发服务器
npm start

# 构建生产版本
npm run build
```

## 技术栈

- React 18
- React Router 6
- Chart.js (ELO曲线)
- WebSocket (实时对弈)

## API端点

前端需要连接到后端API（默认 `http://localhost:8000`）：

- `GET /legal_moves?fen=...` - 获取合法走法
- `GET /games/{game_id}` - 获取对局记录
- `GET /elo/leaderboard` - 获取ELO排行榜
- `GET /elo/history/{agent_id}` - 获取ELO历史
- `WS /ws/game/{game_id}` - WebSocket实时对弈

## 配置

在 `package.json` 中配置代理（如果需要）：

```json
{
  "proxy": "http://localhost:8000"
}
```

