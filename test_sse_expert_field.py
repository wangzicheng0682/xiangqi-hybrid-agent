"""
验证 SSE chunk 事件是否包含 expert 字段 —— 这是前端路由的关键。
只检查前 30 个 expert chunk/thinking/reasoning 事件。
"""
import time, json, requests

BASE = "http://127.0.0.1:8005"
FEN = "r1bakab1r/9/2n1c2c1/p1p1p1p1p/9/2P6/P3P1P1P/2N1C2C1/9/R1BAKAB1R w - - 0 5"

def main():
    url = f"{BASE}/api/analyze/deep-stream"
    params = {"fen": FEN, "question": "请分析当前局面", "show_thinking": "true"}

    print(f"连接 {url} ...")
    t0 = time.time()
    chunk_events = []
    ok_count = 0
    missing_count = 0

    resp = requests.get(url, params=params, stream=True, timeout=120)
    for line in resp.iter_lines(decode_unicode=True, chunk_size=1):
        if not line or not line.startswith("data: "):
            continue

        evt = json.loads(line[6:])
        etype = evt.get("type", "")

        # 只检查 expert chunk/thinking/reasoning/tool 事件
        if any(etype.startswith(f"expert_{e}_") for e in ("tactics", "strategy", "engine")):
            if etype.endswith("_start") or etype == "expert_result":
                continue  # 这些不是我们关心的

            elapsed = time.time() - t0
            expert_field = evt.get("expert", None)
            msg_preview = (evt.get("message", ""))[:40]

            if expert_field:
                ok_count += 1
                status = "OK"
            else:
                missing_count += 1
                status = "MISSING expert field!"

            chunk_events.append((elapsed, etype, expert_field, status, msg_preview))

            if len(chunk_events) >= 30:
                break

    print(f"\n检查了 {len(chunk_events)} 个专家事件:")
    for (t, typ, exp, status, preview) in chunk_events:
        print(f"  +{t:5.2f}s {status:30s} type={typ:35s} expert={exp}  msg={preview}")

    print(f"\n结果: {ok_count} OK, {missing_count} MISSING")
    if missing_count == 0:
        print("✓ 所有专家 chunk 事件都包含 expert 字段 — 前端可以正确路由")
    else:
        print("✗ 有事件缺少 expert 字段 — 前端会丢弃这些事件!")


if __name__ == "__main__":
    main()
