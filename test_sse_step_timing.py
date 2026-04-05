"""
SSE步骤实时性诊断: 精确测量每个步骤事件到前端的到达时间
"""
import requests
import time
import json
import sys

BASE_URL = "http://localhost:8002"
# 中局FEN — 会触发三专家完整链路
FEN = "r1bakab2/9/2n1c2r1/p3p1p1p/2p6/6P2/P1P1P3P/2N1C1N2/9/R1BAKAB1R w - - 0 1"

def test_sse_timing():
    url = f"{BASE_URL}/api/analyze/deep-stream"
    params = {
        "fen": FEN,
        "question": "请分析当前局面",
        "show_thinking": "true",
    }
    
    print("=" * 70)
    print("SSE 步骤实时性诊断")
    print("=" * 70)
    
    t0 = time.time()
    step_events = []  # (time, type, title/expert/message)
    all_events = []
    
    try:
        resp = requests.get(url, params=params, stream=True, timeout=180)
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            
            elapsed = time.time() - t0
            raw = line[6:]
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            
            evt_type = msg.get("type", "")
            all_events.append((elapsed, evt_type))
            
            # 关注能在前端产生"步骤"的事件
            is_step_creator = evt_type in (
                "expert_start", "expert_result",
                "dispatch_info",
                "synthesis_step_start", "synthesis_step_end",
            ) or "_tool" in evt_type
            
            # 也记录chunk事件的时间（用于验证实时性）
            is_chunk = "chunk" in evt_type or "thinking" in evt_type and evt_type != "thinking"
            
            if is_step_creator:
                expert = msg.get("expert", "")
                title = msg.get("title", msg.get("message", ""))
                if isinstance(title, str) and len(title) > 60:
                    title = title[:60] + "..."
                step_events.append((elapsed, evt_type, expert, title))
                marker = ">>>"
            elif is_chunk:
                marker = "   "
            else:
                marker = "   "
            
            # 只打印步骤创建事件和关键里程碑
            if is_step_creator or evt_type in ("expert_start", "expert_result", "result"):
                print(f"  [{elapsed:7.2f}s] {marker} {evt_type:<30} expert={msg.get('expert','-'):<10} title={str(title)[:50] if is_step_creator else ''}")
            
            if evt_type == "result":
                break
    
    except Exception as e:
        print(f"\nERROR: {e}")
    
    total = time.time() - t0
    
    print("\n" + "=" * 70)
    print(f"总耗时: {total:.1f}s | 总事件: {len(all_events)} | 步骤事件: {len(step_events)}")
    print("=" * 70)
    
    # 步骤到达时间间隔分析
    print("\n--- 步骤到达时间线 ---")
    prev_t = 0
    for i, (t, etype, expert, title) in enumerate(step_events):
        gap = t - prev_t
        gap_indicator = "🟢" if gap < 2.0 else "🟡" if gap < 5.0 else "🔴"
        print(f"  Step {i+1:2d} | {t:7.2f}s | +{gap:5.2f}s {gap_indicator} | {etype:<26} | {expert:<10} | {str(title)[:45]}")
        prev_t = t
    
    # 批量检测: 如果多个步骤在0.1s内到达 = 批量
    print("\n--- 批量检测 ---")
    batch_count = 0
    for i in range(1, len(step_events)):
        gap = step_events[i][0] - step_events[i-1][0]
        if gap < 0.1:
            if batch_count == 0:
                print(f"  批量起始: Step {i} @ {step_events[i-1][0]:.2f}s")
            batch_count += 1
    
    if batch_count == 0:
        print("  ✅ 未检测到步骤批量到达！所有步骤间隔 > 0.1s")
    else:
        print(f"  ⚠️ 检测到 {batch_count} 对步骤间隔 < 0.1s（可能批量到达）")
    
    # chunk事件计数
    chunk_types = {}
    for t, etype in all_events:
        if "chunk" in etype:
            chunk_types[etype] = chunk_types.get(etype, 0) + 1
    
    print("\n--- Chunk事件统计 ---")
    for k, v in sorted(chunk_types.items()):
        print(f"  {k}: {v}次")
    
    return step_events

if __name__ == "__main__":
    test_sse_timing()
