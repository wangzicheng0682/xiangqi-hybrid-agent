# 前端 AI Coding 指南

> 本项目是 AI 辅助开发项目。本文档指导如何与 AI 协作开发前端。

---

## 🤖 AI Coding 工作流

### 1. 启动新对话

```
第一步：阅读文档
1. docs/frontend/FRONTEND_DNA.md    ← 必须先读
2. docs/frontend/API_CONTRACT.md     ← 必须先读
3. docs/frontend/COMPONENT_GUIDE.md  ← 视工作内容选择阅读
```

### 2. 提出需求

向 AI 描述你的需求：

```
❌ 不好的描述：
"帮我做个棋盘组件"

✅ 好的描述：
"帮我做一个 ChessBoard 组件，规格如下：
- 使用 TypeScript + React
- Props 接口：board (string[][]), onMove (function), lastMove
- 10x9 棋盘，点击格子触发 onMove
- 遵循 docs/frontend/COMPONENT_GUIDE.md 中的规范
- 不要直接调用 API，通过 useGameStore 管理状态"
```

### 3. AI 实现后

- 检查生成的代码是否符合规范
- 验证功能是否符合预期
- 运行 `npm run dev` 测试

---

## 📁 文件修改权限

| 目录/文件 | AI 权限 | 说明 |
|-----------|---------|------|
| `frontend/src/components/` | ✅ 可修改 | 前端组件 |
| `frontend/src/store/` | ✅ 可修改 | 状态管理 |
| `frontend/src/services/` | ⚠️ 只读 | API 接口已定义 |
| `frontend/src/hooks/` | ✅ 可新增 | 自定义 Hooks |
| `api/` | ❌ 禁止修改 | 后端代码 |
| `core/` | ❌ 禁止修改 | 核心逻辑 |

---

## 🔧 常用命令

```bash
# 安装依赖
npm install

# 开发模式
npm run dev

# 构建生产版本
npm run build

# 类型检查
npm run typecheck

# 代码检查
npm run lint
```

---

## 🚨 遇到问题怎么办

### 问题：AI 生成的代码不符合预期

```
1. 指出具体问题
2. 提供参考资料（docs/frontend/下的文档）
3. 要求重新生成

示例：
"这个组件直接调用了 api.analyze()，违反了分层原则。
应该通过 useGameStore 管理状态，参考 STATE_MANAGEMENT.md"
```

### 问题：需要后端支持但接口不存在

```
1. 提出接口需求
2. 等待后端实现
3. 前端只修改 frontend/

不要自己实现后端逻辑！
```

---

## 📋 提交流程

1. 确保所有修改在 `frontend/` 目录下
2. 运行 `npm run build` 确认无构建错误
3. 更新 `docs/frontend/STATE.md`
4. Git 提交

---

## 📚 参考文档

| 文档 | 何时阅读 |
|------|----------|
| FRONTEND_DNA.md | 每次新对话开始时 |
| API_CONTRACT.md | 调用 API 时 |
| COMPONENT_GUIDE.md | 开发组件时 |
| STATE_MANAGEMENT.md | 涉及状态管理时 |

---

**最后更新**: 2026-03-19
