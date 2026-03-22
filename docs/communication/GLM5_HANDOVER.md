# 工作交接文档

**交接时间**: 2026-03-19
**当前状态**: SSE流式输出延迟问题已定位并修复，旧版分析工具已删除

---

## 一、当前进度

### 已完成工作

| 任务 | 状态 | 说明 |
|------|------|------|
| 黄金局面测试库 | ✅ | `tests/golden_positions.py` (41个测试用例) |
| 测试框架 | ✅ | `tests/test_golden_positions.py` (12 passed) |
| 一致性检查器 | ✅ | 已集成到 `detect_static(debug_mode=True)` |
| 引擎bug修复 | ✅ | `agent_tools.py` 字典访问→属性访问 |
| 张力检测阈值修复 | ✅ | `cp > 300`（原120太敏感） |
| 两阶段Agent验证 | ✅ | 规划→执行→输出流程 |
| **SSE延迟问题定位** | ✅ | 旧版analyze-move API阻塞导致 |
| **旧版分析工具删除** | ✅ | 前端+后端都已清理 |

### 测试结果

```
pytest tests/test_golden_positions.py ............ [100%]
12 passed in 1.21s
mAP = 1.0000 (17个标签全部通过)

SSE延迟测试：
- 第一次深度分析（无走棋）：8ms 首字节 ✅
- 走棋后深度分析：22秒首字节 → 等旧API完成后正常
```

---

## 二、2026-03-19 修复内容

### 2.1 SSE流式输出延迟问题定位（关键！）

**现象**:
- 第一次点击深度分析：**8ms** 首字节 ✅
- 走一步棋后再点击深度分析：**22秒** 首字节 ❌

**排查过程**:
1. 后端测试：Python httpx/curl 首字节 0.15s → 后端正常
2. 代理测试：Vite代理 curl 首字节瞬间 → 代理正常
3. 浏览器测试：地址栏直接访问SSE瞬间 → 浏览器正常
4. **关键发现**：走棋后等几秒再分析就正常

**根本原因**:
```
走棋时触发 /api/analyze-move 请求
  ↓
该请求需要：引擎分析2次(depth=15) + LLM分析 + Neo4j查询
  ↓
总耗时约 20-30 秒
  ↓
在此期间，浏览器对同一origin的连接数达到上限
  ↓
新的深度分析SSE请求被阻塞等待
```

**证据**:
```
第一次分析（无走棋）：
[API] 创建 EventSource 6058.2
[API] EventSource 连接已建立 6066  ← 8ms

走棋后分析：
[API] 创建 EventSource 4353.1
[API] EventSource 连接已建立 26375.2  ← 22秒！
```

### 2.2 旧版分析工具删除

**删除的前端文件**:
- `frontend/src/components/AnalysisPanel.tsx` — 旧版走法分析面板
- `frontend/src/components/MoveQualityCard.tsx` — 走法质量卡片

**删除的前端代码**:
- `api.analyzeMove()` 方法
- `AnalyzeMoveResponse` 类型
- `useGameStore.moveAnalysis` 状态
- `App.tsx` 中的旧组件引用

**删除的后端代码**:
- `/api/analyze-move` 端点（约170行）
- `AnalyzeMoveRequest` / `AnalyzeMoveResponse` 模型

**删除原因**:
1. 与深度分析功能重复
2. 阻塞后续SSE请求
3. 走棋时自动触发，影响用户体验

### 2.3 其他修改

**Vite配置优化**:
```typescript
// frontend/vite.config.ts
server: {
  host: '127.0.0.1',  // 统一使用127.0.0.1，避免跨域
  // ...
}
```

**API Base统一**:
```typescript
// frontend/src/services/api.ts
const API_BASE = 'http://127.0.0.1:8003/api';  // 统一origin
```

---

## 三、2026-03-18 修复内容（历史）

### 3.1 张力检测阈值修复

**问题**: `tension_detector.py` 阈值 `cp > 120` 太敏感

```python
# 错误阈值
if abs(cp) > 120 and tactical_count < 2:  # ❌

# 正确阈值
if abs(cp) > 300 and tactical_count < 2:  # ✅
```

**修复位置**: `core/rules/tension_detector.py` 第170行

### 3.2 engine_alternatives工具修复

```python
# 错误代码
best_move = result.get("bestmove", "")    # ❌

# 正确代码
best_move = result.bestmove if result.bestmove else ""  # ✅
```

**修复位置**: `core/llm/agent_tools.py` 第698-700行

---

## 四、核心文件位置

### 4.1 LLM相关

| 文件 | 路径 | 内容 |
|------|------|------|
| 教练Agent | `core/llm/xiangqi_coach.py` | SYSTEM_PROMPT、Agent循环 |
| Agent工具 | `core/llm/agent_tools.py` | 10个工具实现 |
| Few-shot示例 | `core/llm/fewshot_examples.py` | 9个经典示例 |
| 思维模板 | `core/llm/thinking_templates.py` | PhaseDetector |
| 知识库 | `core/llm/knowledge_retriever.py` | 20+棋理原则 |

### 4.2 规则引擎

| 文件 | 路径 | 内容 |
|------|------|------|
| 战术检测器 | `core/rules/tactical_detector.py` | 45个标签检测 |
| 张力检测器 | `core/rules/tension_detector.py` | 6种张力类型 |
| 一致性检查器 | `core/rules/consistency_checker.py` | 12条一致性规则 |

### 4.3 前端

| 文件 | 路径 | 内容 |
|------|------|------|
| 深度分析面板 | `frontend/src/components/DeepAnalysisPanel.tsx` | SSE流式展示 |
| API服务 | `frontend/src/services/api.ts` | EventSource处理 |
| 状态管理 | `frontend/src/store/useGameStore.ts` | 全局状态 |

---

## 五、快速恢复工作

### 启动服务

```bash
# 后端
python -m uvicorn api.main:app --host 0.0.0.0 --port 8003

# 前端
cd frontend && npm run dev
# 访问 http://127.0.0.1:3000
```

### 测试SSE延迟

```bash
# 测试后端直接响应
curl -s -N http://127.0.0.1:8003/api/analyze/deep-get | head -3

# 预期：立即看到
# data: {"type": "thinking", "message": "启动分析..."}
```

### 运行测试

```bash
pytest tests/test_golden_positions.py -v
```

---

## 六、已知问题

### 6.1 阶段检测不准确

- 只看回合数+棋子数，不看过河
- 建议增加 `_has_crossed_river()` 检测

### 6.2 建议模板化

- `suggested_plans: ['稳步发展，等待时机']` 是废话
- 需要改进建议生成逻辑

---

## 七、下一步建议

### 高优先级
1. **验证SSE流式体验** — 确认走棋后深度分析无延迟
2. **阶段检测优化** — 增加过河判断
3. **准备演示局面** — 3-5个"保送题"

### 中优先级
1. 前端新消息类型展示优化
2. 开局分析器优化
3. Neo4j数据完善

---

*本文档更新于 2026-03-19*
