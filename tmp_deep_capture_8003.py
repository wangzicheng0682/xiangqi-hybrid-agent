import json
import requests

fen = "r1bakab1r/9/1cn4c1/p1p1p1p1p/9/2P6/P3P1P1P/1C2C1N2/9/RNBAKAB1R w - - 0 5"
params = {
    "fen": fen,
    "question": "请像比赛答辩中的教学系统一样，先说明局面主导矛盾、双方计划、风险点，再给出结论；禁止空话，尽量引用证据。",
    "show_thinking": "true",
    "debug": "true",
}
url = "http://127.0.0.1:8003/api/analyze/deep-stream"
resp = requests.get(url, params=params, stream=True, timeout=(30, 600))
print(f"STATUS {resp.status_code}")
resp.raise_for_status()
events = []
for raw in resp.iter_lines(decode_unicode=True):
    if not raw:
        continue
    if raw.startswith("data: "):
        payload = raw[6:]
        try:
            obj = json.loads(payload)
        except Exception:
            obj = {"type": "raw", "payload": payload}
        events.append(obj)
        kind = obj.get("type", "unknown")
        if kind in {"expert_start", "expert_result", "expert_step_start", "expert_step_end", "synthesis_step_start", "synthesis_step_end", "orchestrator_subtitle", "error", "result", "debug_log"}:
            print(json.dumps(obj, ensure_ascii=False))

out_path = r"d:\xiangqi-hybrid-agent\logs\deep_analysis_capture_8003.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(events, f, ensure_ascii=False, indent=2)
print(f"SAVED {out_path}")
