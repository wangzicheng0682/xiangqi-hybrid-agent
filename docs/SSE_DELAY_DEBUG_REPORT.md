# SSE 流式输出延迟问题调试报告

**日期**: 2026-03-18
**问题**: 深度分析功能点击后需要等待 20 秒才开始显示内容

---

## 1. 问题现象

用户点击"开始深度分析"按钮后，需要等待约 **20 秒** 才能看到第一个字出现。

### 用户日志
```
[DEBUG] 点击按钮，开始分析 5257.3
[DEBUG] 准备发送请求 5257.9
[API] 开始fetch请求 5258.1
[API] fetch返回 24544.6 200        ← 延迟 19.3 秒！
[API] 收到第一个数据块 24545.2
[DEBUG] 收到消息 24545.6 thinking 启动分析...
```

---

## 2. 调试过程

### 2.1 后端测试

| 测试方式 | 首字节延迟 | 结论 |
|---------|----------|------|
| Python httpx POST | 0.14s | ✅ 正常 |
| Python httpx GET | 0.15s | ✅ 正常 |
| curl GET | 瞬间 | ✅ 正常 |
| 原始 TCP socket | 0.002s | ✅ 正常 |

**结论**: 后端完全没有延迟，第一个 yield 在 **7ms** 内完成。

### 2.2 代理测试

| 测试方式 | 首字节延迟 | 结论 |
|---------|----------|------|
| 直接访问 127.0.0.1:8003 | 0.15s | ✅ 正常 |
| 通过 Vite 代理 (curl) | 瞬间 | ✅ 正常 |
| 通过 Vite 代理 (Python httpx) | 瞬间 | ✅ 正常 |

**结论**: Vite 代理本身没有延迟。

### 2.3 浏览器测试

| 测试方式 | 首字节延迟 | 结论 |
|---------|----------|------|
| 浏览器地址栏直接访问 GET SSE | 瞬间 | ✅ 正常 |
| 浏览器 fetch API (POST) | 20s | ❌ 延迟 |
| 浏览器 fetch API (GET) | 20s | ❌ 延迟 |
| 浏览器 EventSource API | 20s | ❌ 延迟 |

**结论**: **问题在于浏览器中的 JavaScript API**，与请求方法无关。

---

## 3. 排除的因素

### 3.1 已排除
- ❌ 后端处理延迟 (实际 7ms)
- ❌ Vite 代理缓冲 (curl 测试瞬间)
- ❌ CORS preflight (GET 请求同样延迟)
- ❌ DNS 解析 (127.0.0.1 无需解析)
- ❌ Windows 代理设置 (系统无代理)
- ❌ VPN/安全软件 (未检测到)
- ❌ API 实现方式 (fetch/EventSource 都延迟)

### 3.2 可能原因

1. **浏览器安全检查**
   - Chrome/Edge 可能对 SSE 请求有特殊的安全检查
   - 可能与内容安全策略 (CSP) 相关

2. **浏览器扩展干扰**
   - 广告拦截器、安全扩展可能拦截/缓冲请求
   - 需要在隐身模式测试

3. **浏览器连接管理**
   - 浏览器可能对并发连接数有限制
   - 可能等待其他请求完成

4. **React/状态更新阻塞**
   - 虽然不太可能，但 flushSync 可能有影响

---

## 4. 关键代码

### 4.1 后端 SSE 端点
```python
# api/main.py
@app.get("/api/analyze/deep-stream")
async def analyze_deep_stream(fen: str, move: Optional[str] = None, ...):
    async def generate():
        # 第一个 yield 在 7ms 内完成
        yield f"data: {json.dumps({'type': 'thinking', 'message': '启动分析...'})}\n\n"
        # ... 更多处理

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )
```

### 4.2 前端 API 调用
```typescript
// frontend/src/services/api.ts
analyzeDeep: async (data, onThinking, onResult, onError) => {
    // EventSource 方式
    const url = `/api/analyze/deep-stream?${params.toString()}`;
    const eventSource = new EventSource(url);

    eventSource.onmessage = (event) => {
        const json = JSON.parse(event.data);
        onThinking(json);
    };
}
```

---

## 5. 建议的后续排查步骤

### 5.1 用户测试
1. **隐身模式测试**
   - 按 `Ctrl+Shift+N` 打开隐身窗口
   - 访问 http://localhost:3001 测试
   - 如果正常，说明是扩展问题

2. **检查浏览器扩展**
   - 打开 `chrome://extensions/`
   - 禁用所有扩展
   - 重新测试

3. **检查 CSP 策略**
   - 打开 F12 -> Console
   - 查看是否有 CSP 相关警告

4. **尝试不同浏览器**
   - Firefox
   - Edge
   - Safari

### 5.2 代码层面
1. **使用 WebSocket 替代 SSE**
   - WebSocket 是全双工协议，可能有更好的浏览器支持

2. **轮询模式**
   - 前端定期请求进度
   - 虽然不是真正的流式，但可以避免 SSE 的问题

3. **Server-Sent Events polyfill**
   - 使用第三方库如 `eventsource` 或 `sse.js`

---

## 6. 环境信息

| 项目 | 信息 |
|------|------|
| 操作系统 | Windows 11 Home China |
| 浏览器 | Chrome/Edge (未确认具体版本) |
| 后端框架 | FastAPI + Uvicorn |
| 前端框架 | React + Vite |
| 后端端口 | 8003 |
| 前端端口 | 3000/3001 |

---

## 7. 总结

**核心问题**: 浏览器中的 JavaScript API (fetch/EventSource) 在访问 SSE 端点时有 20 秒延迟，但直接在地址栏访问或使用命令行工具测试则没有延迟。

**推测原因**: 浏览器安全机制或扩展干扰，与后端代码无关。

**建议**: 在隐身模式测试，如果正常则逐个启用扩展找出问题扩展。

---

*报告生成时间: 2026-03-18*
