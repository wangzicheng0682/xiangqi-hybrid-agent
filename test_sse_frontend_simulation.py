"""
SSE步骤实时性验证 — 模拟前端chunk驱动步骤生成器效果
连接真实后端，模拟App.tsx的applyStreamMessage逻辑，计算最终时间线。
"""
import requests
import time
import json
import sys

BASE_URL = "http://localhost:8002"
FEN = "r1bakab2/9/2n1c2r1/p3p1p1p/2p6/6P2/P1P1P3P/2N1C1N2/9/R1BAKAB1R w - - 0 1"

STEP_INTERVAL_S = 4.0  # 与App.tsx的STEP_INTERVAL_MS=4000匹配

EXPERT_THINKING_PHASES = {
    'tactics': ['扫描战术威胁', '检测强制序列', '分析子力交换', '评估战术组合', '验证战术结论', '深入分析变化'],
    'strategy': ['评估局面形势', '分析阵型结构', '检测位置弱点', '审视子力协调', '整理战略建议', '综合评判局面'],
    'engine': ['启动深度算路', '计算候选变化', '评估最佳着法', '验证引擎判断'],
}
EXPERT_NAME = {'tactics': '战术专家', 'strategy': '战略专家', 'engine': '引擎专家'}


def simulate():
    url = f"{BASE_URL}/api/analyze/deep-stream"
    params = {"fen": FEN, "question": "请分析当前局面", "show_thinking": "true"}

    t0 = time.time()
    # 前端状态模拟
    expert_last_step_time = {'tactics': 0, 'strategy': 0, 'engine': 0}
    expert_phase_index = {'tactics': 0, 'strategy': 0, 'engine': 0}
    expert_round = {'tactics': 0, 'strategy': 0, 'engine': 0}
    expert_live_step = {'tactics': None, 'strategy': None, 'engine': None}
    synthesis_step_time = 0
    synthesis_phase = 0
    SYNTHESIS_TRANSITIONS = ['整合专家观点', '梳理分析要点', '生成教学讲解']

    timeline = []  # (elapsed, source, label)
    chunk_counts = {}

    def record_step(elapsed, source, label):
        timeline.append((elapsed, source, label))
        print(f"  [{elapsed:7.2f}s] 🔵 {source:<20s} | {label}")

    print("=" * 70)
    print("SSE 前端步骤模拟 — 验证chunk驱动步骤生成器")
    print("=" * 70)

    resp = requests.get(url, params=params, stream=True, timeout=180)
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        elapsed = time.time() - t0
        try:
            msg = json.loads(line[6:])
        except json.JSONDecodeError:
            continue

        mtype = msg.get('type', '')
        expert = msg.get('expert', '')

        # 从type中提取expert
        if not expert:
            import re
            m = re.match(r'^expert_(tactics|strategy|engine)_', mtype)
            if m:
                expert = m.group(1)

        # --- 模拟App.tsx applyStreamMessage ---

        if mtype == 'dispatch_info':
            record_step(elapsed, 'dispatch_info', '调度策略确认')

        elif mtype == 'expert_start' and expert:
            phases = EXPERT_THINKING_PHASES[expert]
            expert_phase_index[expert] = 0
            expert_last_step_time[expert] = elapsed
            expert_live_step[expert] = f"{expert}_0"
            record_step(elapsed, 'expert_start', f"{EXPERT_NAME[expert]} · {phases[0]}")

        elif mtype == 'expert_result' and expert:
            expert_live_step[expert] = None
            record_step(elapsed, 'expert_result', f"{EXPERT_NAME[expert]} · 分析完成 ✓")
            # 检查是否所有专家完成
            all_started = any(t > 0 for t in expert_last_step_time.values())
            all_done = all_started and all(
                expert_last_step_time[e] == 0 or expert_live_step[e] is None
                for e in ['tactics', 'strategy', 'engine']
            )
            if all_done and synthesis_step_time == 0:
                record_step(elapsed, 'transition', '协调者正在综合各路见解')
                synthesis_step_time = elapsed

        elif '_chunk' in mtype and expert:
            chunk_counts[mtype] = chunk_counts.get(mtype, 0) + 1
            # chunk驱动步骤生成
            last_t = expert_last_step_time.get(expert, 0)
            if last_t > 0 and (elapsed - last_t) >= STEP_INTERVAL_S:
                # finalize + 创建新步骤
                phases = EXPERT_THINKING_PHASES[expert]
                idx = expert_phase_index[expert]
                next_idx = (idx + 1) % len(phases)
                expert_phase_index[expert] = next_idx
                expert_round[expert] += 1
                expert_last_step_time[expert] = elapsed
                record_step(elapsed, 'chunk_driven', f"{EXPERT_NAME[expert]} · {phases[next_idx]}")

        elif mtype == 'expert_step_start' and expert:
            # expert_step_start 也驱动时间步骤（弥补chunk停止后的空白期）
            title = msg.get('title', '')
            if title:
                last_t = expert_last_step_time.get(expert, 0)
                if last_t > 0 and (elapsed - last_t) >= STEP_INTERVAL_S:
                    expert_round[expert] += 1
                    expert_last_step_time[expert] = elapsed
                    record_step(elapsed, 'step_driven', f"{EXPERT_NAME[expert]} · {title}")

        elif '_tool' in mtype and 'result' not in mtype and expert:
            tool_label = msg.get('message', 'tool')
            record_step(elapsed, 'expert_tool', f"{EXPERT_NAME[expert]} · {tool_label}")

        elif '_tool_result' in mtype and expert:
            record_step(elapsed, 'tool_result', f"{EXPERT_NAME[expert]} · 分析中")

        elif mtype == 'synthesis_step_start':
            # 关闭综合等待过渡步骤
            if synthesis_step_time > 0:
                synthesis_step_time = 0
            title = msg.get('title', '综合分析')
            record_step(elapsed, 'synthesis', title)

        elif mtype == 'synthesis_step_end':
            title = msg.get('title', '')
            record_step(elapsed, 'synthesis_done', f"{title} ✓")

        elif mtype == 'synthesis_chunk':
            chunk_counts['synthesis_chunk'] = chunk_counts.get('synthesis_chunk', 0) + 1
            # synthesis_chunk 驱动过渡步骤
            if synthesis_step_time > 0 and (elapsed - synthesis_step_time) >= STEP_INTERVAL_S:
                next_phase = (synthesis_phase + 1) % len(SYNTHESIS_TRANSITIONS)
                synthesis_phase = next_phase
                synthesis_step_time = elapsed
                record_step(elapsed, 'synth_transition', SYNTHESIS_TRANSITIONS[next_phase])

        elif mtype == 'thinking':
            # thinking 心跳驱动综合等待过渡步骤
            WAITING_PHASES = ['汇总证据链', '比对专家分歧', '构建讲解框架', '准备综合分析']
            if synthesis_step_time > 0 and (elapsed - synthesis_step_time) >= STEP_INTERVAL_S:
                next_phase = (synthesis_phase + 1) % len(WAITING_PHASES)
                synthesis_phase = next_phase
                synthesis_step_time = elapsed
                record_step(elapsed, 'wait_transition', WAITING_PHASES[next_phase])

    total_time = time.time() - t0
    print()
    print("=" * 70)
    print(f"总耗时: {total_time:.1f}s | 总步骤数: {len(timeline)}")
    print("=" * 70)

    # 统计
    sources = {}
    for _, src, _ in timeline:
        sources[src] = sources.get(src, 0) + 1
    print("\n--- 步骤来源统计 ---")
    for src, count in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"  {src:<20s} : {count}")

    print(f"\n--- Chunk统计 ---")
    for k, v in sorted(chunk_counts.items()):
        print(f"  {k}: {v}")

    # 间隔分析
    print(f"\n--- 步骤间隔分析 ---")
    max_gap = 0
    for i in range(1, len(timeline)):
        gap = timeline[i][0] - timeline[i-1][0]
        if gap > max_gap:
            max_gap = gap
    print(f"  最大间隔: {max_gap:.2f}s")

    gaps_over_5 = sum(1 for i in range(1, len(timeline)) if (timeline[i][0] - timeline[i-1][0]) > 5)
    gaps_over_3 = sum(1 for i in range(1, len(timeline)) if (timeline[i][0] - timeline[i-1][0]) > 3)
    print(f"  间隔>5s的: {gaps_over_5}")
    print(f"  间隔>3s的: {gaps_over_3}")

    avg_gap = total_time / max(len(timeline) - 1, 1)
    print(f"  平均间隔: {avg_gap:.2f}s")

    # 质量判定
    print()
    if len(timeline) >= 15 and max_gap <= 6 and gaps_over_5 <= 2:
        print("✅ 通过! 步骤数量充足，间隔合理，体验达标")
    elif len(timeline) >= 10:
        print("⚠️ 基本可接受，但仍有改进空间")
    else:
        print("❌ 步骤太少，体验不达标")


if __name__ == '__main__':
    simulate()
