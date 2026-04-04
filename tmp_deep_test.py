import urllib.request, urllib.parse, json, time, sys

OUTPUT_FILE = "tmp_deep_test_output.txt"
_orig_stdout = sys.stdout
_fout = open(OUTPUT_FILE, "w", encoding="utf-8")

class Tee:
    def write(self, msg):
        _orig_stdout.write(msg)
        _fout.write(msg)
    def flush(self):
        _orig_stdout.flush()
        _fout.flush()

sys.stdout = Tee()

# 典型中局：红方多子压制，黑方有无根马
fen = "r1bakabr1/4n4/1cn1b1n1p/p1p1p3p/6p2/2P3P2/P1P1P3P/1C2BAN2/4A4/R3KABR1 w"
question = "请分析当前局面，红方有哪些关键威胁？"

params = urllib.parse.urlencode({
    "fen": fen,
    "question": question,
    "debug": "false"
})

url = "http://127.0.0.1:8002/api/analyze/deep-stream?" + params
print("Calling API...")
start = time.time()

events = []
first_seen = {}
try:
    req = urllib.request.Request(url, headers={"Accept": "text/event-stream"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        for raw in resp:
            line = raw.decode("utf-8").strip()
            if not line.startswith("data: "):
                continue
            data_str = line[6:]
            if data_str == "[DONE]":
                print(f"[{time.time()-start:.2f}s] [DONE]")
                break
            try:
                data = json.loads(data_str)
                events.append(data)
                etype = data.get("type", "")
                if etype not in first_seen:
                    first_seen[etype] = time.time() - start
                if etype == "dispatch_info":
                    print(f"[{time.time()-start:.2f}s] [dispatch_info] {json.dumps(data, ensure_ascii=False)[:300]}")
                elif etype in ("thinking", "orchestrator_subtitle"):
                    print(f"[{time.time()-start:.2f}s] [{etype}] {json.dumps(data, ensure_ascii=False)[:200]}")
                elif etype.startswith("expert_") and (etype.endswith("_thinking") or etype.endswith("_chunk") or etype.endswith("_tool") or etype.endswith("_tool_result")):
                    print(f"[{time.time()-start:.2f}s] [{etype}] {json.dumps(data, ensure_ascii=False)[:220]}")
                elif etype == "expert_step":
                    expert = data.get("expert", "")
                    step = data.get("step", "")
                    content = data.get("content", "")[:100]
                    print(f"[{time.time()-start:.2f}s] [expert_step] {expert} | {step} | {content}")
                elif etype == "synthesis_step":
                    content = data.get("content", "")[:150]
                    print(f"[{time.time()-start:.2f}s] [synthesis_step] {content}")
                elif etype == "result":
                    # 字段是 explanation，不是 result
                    result = data.get("explanation") or data.get("result", "")
                    print(f"\n{'='*60}")
                    print(f"FINAL RESULT ({time.time()-start:.2f}s)")
                    print("="*60)
                    print(result if result else f"[EMPTY] full event: {json.dumps(data, ensure_ascii=False)[:300]}")
                    print("="*60)
                elif etype == "error":
                    print(f"[{time.time()-start:.2f}s] [ERROR] {json.dumps(data, ensure_ascii=False)}")
                elif etype == "expert_result":
                    expert = data.get("expert", "")
                    content = data.get("content", "")
                    print(f"[{time.time()-start:.2f}s] [expert_result] {expert}: {repr(content[:300])}")
                elif etype == "synthesis_step_content":
                    content = data.get("content", "")
                    print(f"[{time.time()-start:.2f}s] [synthesis_content] {repr(content[:300])}")
                elif etype == "chunk":
                    pass  # too noisy
            except Exception as e:
                pass
except Exception as e:
    print(f"Request failed: {e}")

print(f"\nTotal events: {len(events)}")
type_counts = {}
for e in events:
    t = e.get("type", "unknown")
    type_counts[t] = type_counts.get(t, 0) + 1
print(f"Event type breakdown: {type_counts}")
print(f"First seen timestamps: {first_seen}")
