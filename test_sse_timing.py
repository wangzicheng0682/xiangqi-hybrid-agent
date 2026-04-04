"""
SSE 实时性诊断脚本 —— 连接后端 deep-stream 端点，记录每个事件的到达时间。
用于诊断"专家内容延迟"和"协调者步骤批量出现"问题。
"""
import time
import json
import sys
import requests

BASE = "http://127.0.0.1:8005"
FEN = "r1bakab1r/9/2n1c2c1/p1p1p1p1p/9/2P6/P3P1P1P/2N1C2C1/9/R1BAKAB1R w - - 0 5"

def main():
    # 输出到文件避免编码问题
    import io
    log = open("sse_timing_log.txt", "w", encoding="utf-8")
    def p(s):
        print(s)
        log.write(s + "\n")
        log.flush()

    url = f"{BASE}/api/analyze/deep-stream"
    params = {
        "fen": FEN,
        "question": "请分析当前局面",
        "show_thinking": "true",
    }

    p(f"[{time.strftime('%H:%M:%S')}] 连接 {url}")
    t0 = time.time()

    # 统计
    event_count = 0
    expert_chunks = {}  # expert_name -> list of (elapsed, len)
    step_events = []     # (elapsed, type, preview)
    last_event_at = t0

    try:
        resp = requests.get(url, params=params, stream=True, timeout=120)
        resp.raise_for_status()

        for line in resp.iter_lines(decode_unicode=True, chunk_size=1):
            if not line or not line.startswith("data: "):
                continue

            now = time.time()
            elapsed = now - t0
            gap = now - last_event_at
            last_event_at = now

            data_str = line[6:]
            try:
                evt = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            event_count += 1
            etype = evt.get("type", "?")
            msg = evt.get("message", "")
            preview = (msg[:60] + "...") if len(msg) > 60 else msg

            # 分类记录
            is_expert_chunk = False
            for expert in ("tactics", "strategy", "engine"):
                for suffix in ("_chunk", "_thinking", "_reasoning"):
                    if etype == f"expert_{expert}{suffix}":
                        is_expert_chunk = True
                        if expert not in expert_chunks:
                            expert_chunks[expert] = []
                        expert_chunks[expert].append((elapsed, len(msg)))

            is_step = "step" in etype
            if is_step:
                step_events.append((elapsed, etype, preview))

            # 实时输出
            tag = ""
            if is_expert_chunk:
                tag = " [CHUNK]"
            elif is_step:
                tag = " [STEP]"
            elif "tool" in etype:
                tag = " [TOOL]"
            elif etype in ("expert_start", "expert_result"):
                tag = f" [{'START' if 'start' in etype else 'RESULT'}]"
            elif "result" in etype:
                tag = " [RESULT]"

            gap_warn = " GAP!" if gap > 2.0 else ""
            p(f"  +{elapsed:6.2f}s (gap {gap:.3f}s){gap_warn}{tag} {etype}: {preview}")

    except KeyboardInterrupt:
        pass
    except Exception as e:
        p(f"\nERROR: {e}")

    total = time.time() - t0
    p(f"\n{'='*70}")
    p(f"总计: {event_count} 事件, 耗时 {total:.1f}s")

    # 每个专家的 chunk 时间线
    p(f"\n--- 专家 Chunk 分布 ---")
    for expert, chunks in sorted(expert_chunks.items()):
        if not chunks:
            continue
        first_t = chunks[0][0]
        last_t = chunks[-1][0]
        total_chars = sum(c[1] for c in chunks)
        max_gap = 0
        max_gap_at = 0
        for i in range(1, len(chunks)):
            g = chunks[i][0] - chunks[i-1][0]
            if g > max_gap:
                max_gap = g
                max_gap_at = chunks[i][0]

        p(f"  {expert}: {len(chunks)} chunks, first={first_t:.2f}s, last={last_t:.2f}s, "
              f"total_chars={total_chars}, max_gap={max_gap:.2f}s(at +{max_gap_at:.2f}s)")

    # Step 事件时间线
    if step_events:
        p(f"\n--- Step 事件到达时间 ---")
        for (t, typ, preview) in step_events:
            p(f"  +{t:6.2f}s  {typ}: {preview}")

        # 检测批量
        batch_count = 0
        for i in range(1, len(step_events)):
            gap = step_events[i][0] - step_events[i-1][0]
            if gap < 0.05:
                batch_count += 1
        p(f"  BATCH count: {batch_count}/{len(step_events)} step events arrived in batch (<50ms apart)")

    p("")
    log.close()


if __name__ == "__main__":
    main()
