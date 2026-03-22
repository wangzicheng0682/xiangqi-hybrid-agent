# 中国象棋AI - 基于LLM的智能对弈系统

一个基于大语言模型(LLM)的中国象棋AI系统，支持自我对弈、经验学习、ELO评分和Web界面。

## 功能特性

- 🤖 **LLM驱动的走法选择** - 使用大语言模型进行智能走法决策
- 🎮 **自我对弈** - 自动进行大量对局，积累经验
- 📚 **经验池系统** - 存储和检索历史对局经验
- 🔍 **相似局面检索** - 基于向量检索找到相似历史局面
- 📊 **ELO评分系统** - 评估和对比不同版本的Agent
- 🌐 **Web界面** - React前端，支持实时对弈、回放和ELO曲线
- ⚡ **WebSocket实时对弈** - 实时人机对弈体验

## 项目结构

```
xiangqi-llm-agent/
├── README.md
├── pyproject.toml
├── requirements.txt
├── .env.example
├── .gitignore
│
├── configs/                 # 配置文件
│   ├── llm.yaml
│   ├── self_play.yaml
│   ├── reward.yaml
│   ├── engine.yaml
│   └── retrieval.yaml
│
├── scripts/                 # 脚本
│   ├── run_self_play.py
│   ├── evaluate_agent.py
│   ├── import_human_games.py
│   └── cleanup_experience.py
│
├── src/
│   ├── main.py              # 主入口
│   ├── api/                 # API服务器
│   ├── game/                # 游戏逻辑
│   ├── llm/                 # LLM客户端
│   ├── memory/              # 经验池
│   ├── retrieval/           # 检索系统
│   ├── reward/              # 奖励评估
│   ├── self_play/           # 自我对弈
│   └── evaluation/           # 评估系统
│
└── frontend/                # React前端
    ├── src/
    └── public/
```

## 快速开始

### 1. 安装依赖

```bash
# 安装Python依赖
pip install -r requirements.txt

# 安装前端依赖
cd frontend
npm install
```

### 2. 配置环境

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入你的API密钥
# LLM_API_KEY=your_key_here
```

### 3. 运行自我对弈

```bash
# 运行10局自我对弈
python -m src.main self-play --num-games 10
```

### 4. 启动API服务器

```bash
# 启动后端API
python -m src.main api --host 0.0.0.0 --port 8000

# 启动前端（新终端）
cd frontend
npm start
```

访问 `http://localhost:3000` 查看Web界面。

## 使用指南

### 自我对弈

```bash
python -m src.main self-play \
  --num-games 100 \
  --output-dir data/games
```

### 评估Agent

```bash
python -m src.main evaluate \
  --agent-name MyAgent \
  --agent-version v1.0 \
  --num-games 20
```

### 导入人类对局

```bash
python -m src.main import-games \
  --file games.json \
  --format json
```

### 清理经验池

```bash
# 预览（不删除）
python -m src.main cleanup \
  --min-visits 5 \
  --dry-run

# 实际删除
python -m src.main cleanup \
  --min-visits 5
```

## 配置说明

所有配置都在 `configs/` 目录下的YAML文件中：

- `llm.yaml` - LLM客户端配置
- `self_play.yaml` - 自我对弈配置
- `reward.yaml` - 奖励评估配置
- `engine.yaml` - 象棋引擎配置
- `retrieval.yaml` - 检索系统配置

## 开发

```bash
# 运行测试
pytest

# 代码格式化
black src/

# 类型检查
mypy src/
```

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！
