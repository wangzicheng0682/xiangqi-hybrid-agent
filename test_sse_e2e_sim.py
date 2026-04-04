"""
端到端前端模拟测试 —— 完全模拟前端 App.tsx 的消息路由逻辑。
验证：
1. 专家悬浮卡片的 thinkingContent 是否实时累积
2. 协调者时间线步骤是否实时出现（而非批量）
3. 计时证明实时性
"""
import time, json, re, requests

BASE = "http://127.0.0.1:8005"
FEN = "r1bakab1r/9/2n1c2c1/p1p1p1p1p/9/2P6/P3P1P1P/2N1C2C1/9/R1BAKAB1R w - - 0 5"

# === 模拟前端 Store ===
class FakeStore:
    def __init__(self):
        self.experts = {
            'tactics': {'thinkingContent': '', 'status': 'idle', 'finding': ''},
            'strategy': {'thinkingContent': '', 'status': 'idle', 'finding': ''},
            'engine': {'thinkingContent': '', 'status': 'idle', 'finding': ''},
        }
        self.orch_steps = {}  # stepId -> {title, content, status}
        # 模拟 App.tsx 的 ref
        self.live_step_ref = {'tactics': None, 'strategy': None, 'engine': None}
        self.round_ref = {'tactics': 0, 'strategy': 0, 'engine': 0}
        # 跟踪时间
        self.thinking_timeline = []  # (elapsed, expert, content_len)
        self.orch_timeline = []      # (elapsed, step_id, content_len)

def get_expert_step_id(expert, round_num):
    OFFSET = {'tactics': 1000, 'strategy': 2000, 'engine': 3000}
    return OFFSET[expert] + round_num

def main():
    store = FakeStore()
    t0 = time.time()

    url = f"{BASE}/api/analyze/deep-stream"
    params = {"fen": FEN, "question": "请分析当前局面", "show_thinking": "true"}

    print(f"[模拟前端] 连接 {url} ...")

    resp = requests.get(url, params=params, stream=True, timeout=180)
    event_count = 0

    for line in resp.iter_lines(decode_unicode=True, chunk_size=1):
        if not line or not line.startswith("data: "):
            continue
        try:
            msg = json.loads(line[6:])
        except json.JSONDecodeError:
            continue

        event_count += 1
        elapsed = time.time() - t0
        etype = msg.get("type", "")

        # --- 提取 expert 类型（模拟 App.tsx 逻辑）---
        expert = msg.get("expert")
        if not expert and etype:
            m = re.match(r'^expert_(tactics|strategy|engine)_', etype)
            if m:
                expert = m.group(1)

        if not expert or expert not in ('tactics', 'strategy', 'engine'):
            continue

        # --- 路由逻辑（完全模拟 App.tsx）---
        if etype == 'expert_start':
            store.experts[expert]['status'] = 'thinking'
            # 创建实时步骤
            round_num = store.round_ref[expert]
            step_id = get_expert_step_id(expert, round_num)
            store.live_step_ref[expert] = step_id
            store.orch_steps[step_id] = {'title': f'{expert} · 分析中', 'content': '', 'status': 'thinking'}

        elif etype == 'expert_result':
            live = store.live_step_ref[expert]
            if live is not None and live in store.orch_steps:
                store.orch_steps[live]['status'] = 'completed'
            store.live_step_ref[expert] = None
            store.experts[expert]['status'] = 'completed'
            store.experts[expert]['finding'] = msg.get('finding', msg.get('summary', ''))

        elif etype in (f'expert_{expert}_thinking', f'expert_{expert}_chunk', f'expert_{expert}_reasoning'):
            chunk = msg.get('message', '')
            store.experts[expert]['thinkingContent'] += chunk
            store.experts[expert]['status'] = 'thinking'
            # 记录时间线
            store.thinking_timeline.append((elapsed, expert, len(store.experts[expert]['thinkingContent'])))

            # 同时推入协调者步骤
            live = store.live_step_ref[expert]
            if live is not None and live in store.orch_steps and chunk:
                store.orch_steps[live]['content'] += chunk
                store.orch_timeline.append((elapsed, live, len(store.orch_steps[live]['content'])))

        elif etype == f'expert_{expert}_tool':
            live = store.live_step_ref[expert]
            if live is not None and live in store.orch_steps:
                store.orch_steps[live]['status'] = 'completed'
            store.round_ref[expert] += 1
            new_id = get_expert_step_id(expert, store.round_ref[expert])
            store.live_step_ref[expert] = new_id
            store.orch_steps[new_id] = {'title': f'{expert} · tool', 'content': '', 'status': 'thinking'}

        elif etype == f'expert_{expert}_tool_result':
            live = store.live_step_ref[expert]
            if live is not None and live in store.orch_steps:
                store.orch_steps[live]['status'] = 'completed'
            store.round_ref[expert] += 1
            new_id = get_expert_step_id(expert, store.round_ref[expert])
            store.live_step_ref[expert] = new_id
            store.orch_steps[new_id] = {'title': f'{expert} · 分析中', 'content': '', 'status': 'thinking'}

    total_time = time.time() - t0
    print(f"\n{'='*70}")
    print(f"总事件: {event_count}, 耗时: {total_time:.1f}s")

    # === 报告 1: 专家悬浮卡片 thinkingContent 实时性 ===
    print(f"\n{'='*70}")
    print(f"[报告1] 专家悬浮卡片 thinkingContent 累积时间线:")
    for expert in ('tactics', 'strategy', 'engine'):
        items = [(t, l) for (t, e, l) in store.thinking_timeline if e == expert]
        if not items:
            print(f"  {expert}: 无数据")
            continue
        first_t = items[0][0]
        last_t = items[-1][0]
        final_len = items[-1][1]
        # 采样：每5秒的内容长度
        print(f"  {expert}: {len(items)} 次更新, 首个={first_t:.2f}s, 末个={last_t:.2f}s, 最终长度={final_len}")
        samples = []
        for sec in range(0, int(last_t) + 5, 3):
            # 找这个时间点之前最近的长度
            best = 0
            for (t, l) in items:
                if t <= sec:
                    best = l
            samples.append((sec, best))
        print(f"    按时间增长: ", " | ".join(f"{s}s:{l}字" for s, l in samples))

    # === 报告 2: 协调者步骤实时性 ===
    print(f"\n{'='*70}")
    print(f"[报告2] 协调者时间线步骤内容累积:")
    for step_id, step in sorted(store.orch_steps.items()):
        items = [(t, l) for (t, sid, l) in store.orch_timeline if sid == step_id]
        if not items:
            print(f"  步骤 {step_id} ({step['title']}): 无实时内容, 最终长度={len(step['content'])}")
            continue
        first_t = items[0][0]
        last_t = items[-1][0]
        print(f"  步骤 {step_id} ({step['title']}): {len(items)} 次更新, {first_t:.2f}s-{last_t:.2f}s, 最终长度={len(step['content'])}")

    # === 报告 3: 实时性证明 ===
    print(f"\n{'='*70}")
    print(f"[报告3] 实时性证明:")
    for expert in ('tactics', 'strategy', 'engine'):
        items = [(t, l) for (t, e, l) in store.thinking_timeline if e == expert]
        if not items:
            continue
        # 检查：内容应该渐进增长，不能一口气全出来
        # 如果最终长度在首次到达的 2 秒内就全部到达 → 非实时
        first_t = items[0][0]
        final_len = items[-1][1]
        # 计算内容在前 50% 时间到达的百分比
        mid_t = first_t + (items[-1][0] - first_t) / 2
        mid_len = 0
        for (t, l) in items:
            if t <= mid_t:
                mid_len = l
        ratio = mid_len / max(final_len, 1) * 100

        # 检查最大间隔
        max_gap = 0
        for i in range(1, len(items)):
            gap = items[i][0] - items[i-1][0]
            if gap > max_gap:
                max_gap = gap

        all_at_once = items[-1][0] - first_t < 1.0 and final_len > 100
        print(f"  {expert}:")
        print(f"    内容持续时间: {items[-1][0] - first_t:.2f}s")
        print(f"    中位时间到达比: {ratio:.0f}%")
        print(f"    最大更新间隔: {max_gap:.2f}s")
        print(f"    最终内容长度: {final_len}")
        if all_at_once:
            print(f"    ✗ 实时性差: 内容在不到1秒内全部到达")
        else:
            print(f"    ✓ 实时性好: 内容渐进到达")

    print()


if __name__ == "__main__":
    main()
