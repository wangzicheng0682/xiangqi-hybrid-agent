# 作品安装说明

## 一、环境要求

### 1.1 软件要求
| 软件 | 版本要求 |
|------|----------|
| 操作系统 | Windows 10/11 |
| Python | 3.10+ |
| Node.js | 18+ |
| Git | 2.30+ |

### 1.2 可选软件
| 软件 | 用途 | 必需 |
|------|------|------|
| Neo4j | 棋谱数据库 | 否 |
| Chrome | 浏览器 | 是 |
| Pikafish | 中国象棋引擎 | 是（已内置） |
| ChromaDB | RAG向量数据库 | 是（自动安装） |

---

## 二、快速安装

### 2.1 克隆项目
```bash
cd d:\
git clone https://github.com/wangzicheng0682/xiangqi-hybrid-agent.git
```

### 2.2 安装Python依赖
```bash
cd d:\xiangqi-hybrid-agent
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

### 2.3 安装前端依赖
```bash
cd d:\xiangqi-hybrid-agent\frontend
npm install
```

---

## 三、启动项目

### 3.1 启动后端
```bash
# 新开终端
cd d:\xiangqi-hybrid-agent
venv\Scripts\activate.bat
python -m uvicorn api.main:app --host 0.0.0.0 --port 8002
```

### 3.2 启动前端
```bash
# 新开终端
cd d:\xiangqi-hybrid-agent\frontend
npm run dev
```

### 3.3 访问系统
```
浏览器打开: http://localhost:3001
```

---

## 四、环境变量配置

### 4.1 创建 .env 文件

在项目根目录创建 `d:\xiangqi-hybrid-agent\.env`：

```bash
# API 配置（阿里云 DashScope）
ALIYUN_API_KEY=your_api_key_here
ALIYUN_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1

# LLM 模型配置
COACH_MODEL=qwen-plus
EXPERT_MODEL=qwen-plus
SYNTHESIZER_MODEL=qwen-plus

# 并发控制（默认4路并发）
LLM_MAX_PARALLEL_REQUESTS=4

# 引擎配置
PIKAFISH_PATH=data/engine/pikafish.exe
PIKAFISH_DEPTH=20

# RAG 配置（ChromaDB 自动初始化）
RAG_PERSIST_DIR=data/chroma_db

# Neo4j（可选）
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

### 4.2 关键配置代码解析

**LLM 并发控制** — 使用信号量限制并发数，避免 API 限流：
```python
# core/llm/reliable_client.py:57-64
class ReliableLLMClient:
    _semaphore_lock = threading.Lock()
    _request_semaphore = None

    @classmethod
    def _ensure_semaphore(cls) -> None:
        with cls._semaphore_lock:
            target = max(1, int(os.getenv("LLM_MAX_PARALLEL_REQUESTS", "4")))
            if cls._request_semaphore is None:
                semaphore = threading.BoundedSemaphore(target)
                cls._request_semaphore = semaphore
```

**熔断器机制** — 连续12次失败自动熔断，跳过后续请求：
```python
# core/llm/reliable_client.py:99-108
@classmethod
def _circuit_open(cls) -> bool:
    with cls._failure_lock:
        return cls._consecutive_failures >= 12
```

**指数退避重试** — 429/5xx 错误自动重试：
```python
# core/llm/reliable_client.py:81-88
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

def _should_retry(self, status_code, exception, attempt):
    if attempt >= self.max_retries:  # 默认最多2次
        return False
    if status_code in RETRYABLE_STATUS_CODES:
        return True
    return True  # 异常也重试
```

---

## 五、核心模块启动顺序

### 5.1 后端模块依赖图

```
api.main:app (FastAPI)
    ├── TacticalDetector (战术检测器)      # 预导入，延迟加载
    ├── TensionDetector (张力检测器)        # 预导入，延迟加载
    ├── EnginePool (引擎连接池)             # 单例，按需启动
    ├── MultiAgentOrchestrator (协调器)    # 按需创建
    ├── XiangqiCoachAgent (教练Agent)      # 按需创建
    ├── ChromaDB (向量数据库)               # 惰性初始化
    └── Neo4j (图数据库)                   # 可选，按需连接
```

### 5.2 引擎预加载

Pikafish 引擎启动耗时约200ms，通过单例池复用避免每次请求重复初始化：
```python
# core/engine/pool.py:23-28
@classmethod
def get_pool(cls) -> "EnginePool":
    if cls._instance is None:
        with cls._lock:                    # 双重检查锁
            if cls._instance is None:
                cls._instance = cls()
    return cls._instance
```

### 5.3 RAG 惰性初始化

向量数据库首次访问时才索引棋理原则，后台静默完成：
```python
# core/llm/knowledge_retriever.py
# ChromaDB collection 在第一次检索时才初始化
# 索引内容：80+ 棋理原则 + 14万开局摘要
```

---

## 六、验证安装

### 6.1 测试后端API
```bash
curl http://localhost:8002/api/health
# 应返回: {"status": "ok", "service": "xiangqi-api"}
```

### 6.2 测试战术标签检测
```bash
curl -X POST http://localhost:8002/api/tactical-tags \
  -H "Content-Type: application/json" \
  -d '{"fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/6P2/P1P1P3P/1C5C1/9/RNBAKABNR w - - 0 3"}'
# 应返回45个标签的检测结果
```

### 6.3 运行测试
```bash
cd d:\xiangqi-hybrid-agent
venv\Scripts\activate.bat
python -m pytest tests/ -q
# 应显示: 300+ passed
```

### 6.4 测试 SSE 流式输出
```bash
curl "http://localhost:8002/api/analyze/deep-get?fen=rnbakabnr/9/1c5c1/p1p1p1p1p/9/6P2/P1P1P3P/1C5C1/9/RNBAKABNR%20w%20-%20-%200%203&question=%E5%88%86%E6%9E%90%E5%B1%80%E9%9D%A2"
# 应实时看到 SSE 流式输出
```

---

## 七、WebGL 液态玻璃配置

### 7.1 参数说明

液态玻璃使用 Zustand Store 持久化，参数文件保存在 `data/glass_params.json`：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| refThickness | 20 | 折射厚度 |
| refFactor | 1.4 | 折射强度 |
| refDispersion | 0.6 | 色散系数 |
| fresnelRange | 0.3 | 菲涅尔范围 |
| glareFactor | 0.15 | 炫光强度 |

### 7.2 渲染管线

液态玻璃采用五遍渲染（Five-Pass）：

```
Pass 1: 渲染背景到 FBO
Pass 2: 竖向高斯模糊（refraction prep）
Pass 3: 横向高斯模糊（refraction prep）
Pass 4: 渲染 shape1（左玻璃层）
Pass 5: 渲染 shape3（右侧栏玻璃）
```

WebGL 着色器文件位于 `frontend/src/shaders/liquidglass/`：
- `vertex.glsl` — 全屏顶点着色器
- `fragment-bg.glsl` — 背景片段着色器
- `fragment-bg-vblur.glsl` — 竖向模糊
- `fragment-bg-hblur.glsl` — 横向模糊
- `fragment-main.glsl` — 主玻璃层（含折射+色散+菲涅尔+炫光）

---

## 八、常见问题

### 8.1 pip安装失败
```bash
# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 8.2 npm安装慢
```bash
npm install --registry=https://registry.npmmirror.com
```

### 8.3 引擎不可用
确认 `data/engine/pikafish.exe` 存在，或从 https://github.com/official-pikafish/pikafish/releases 下载。
```bash
# 手动测试引擎
python -c "from core.engine.pool import get_engine; e = get_engine(); print(e.analyze('rnbakabnr/9/1c5c1/p1p1p1p1p/9/6P2/P1P1P3P/1C5C1/9/RNBAKABNR w - - 0 3', depth=10))"
```

### 8.4 RAG检索失败
首次访问RAG功能时会自动索引棋理原则，请确保首次启动时网络通畅。

### 8.5 多专家并行超时
`LLM_MAX_PARALLEL_REQUESTS=4` 可调整并发数，降低可避免超时：
```bash
# 串行模式（最稳定）
export LLM_MAX_PARALLEL_REQUESTS=1
```

### 8.6 前端 WebGL 不显示
检查浏览器是否支持 WebGL 2.0（Chrome 56+ / Edge 79+），并确保显卡驱动已更新。

### 8.7 SSE 连接断开
后端 SSE 在无活动时每0.5秒发送心跳包，保持连接活跃。如浏览器代理拦截 SSE，切换到 GET 版本的 `/api/analyze/deep-get` 端点。
