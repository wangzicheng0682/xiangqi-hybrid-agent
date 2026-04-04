import json
import time
import urllib.parse
import urllib.request

fen = "r1bakabr1/4n4/1cn1b1n1p/p1p1p3p/6p2/2P3P2/P1P1P3P/1C2BAN2/4A4/R3KABR1 w"
params = urllib.parse.urlencode({
    "fen": fen,
    "question": "请分析当前局面，红方有哪些关键威胁？",
    "debug": "false",
})
url = "http://127.0.0.1:8004/api/analyze/deep-stream?" + params
req = urllib.request.Request(url, headers={"Accept": "text/event-stream"})

start = time.time()
first = {}
count = 0
with urllib.request.urlopen(req, timeout=180) as resp:
    for raw in resp:
        line = raw.decode("utf-8").strip()
        if not line.startswith("data: "):
            continue
        payload = line[6:]
        if payload == "[DONE]":
            print("DONE", round(time.time() - start, 2))
            break
        event = json.loads(payload)
        event_type = event.get("type", "")
        count += 1
        if event_type not in first:
            first[event_type] = round(time.time() - start, 2)
        if event_type in ("error", "result"):
            print("FINAL", event_type, round(time.time() - start, 2), json.dumps(event, ensure_ascii=False)[:300])
            break

print("FIRST", json.dumps(first, ensure_ascii=False, sort_keys=True))
print("COUNT", count)
