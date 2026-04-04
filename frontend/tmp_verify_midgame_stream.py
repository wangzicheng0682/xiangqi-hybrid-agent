import json, time, requests
url = 'http://127.0.0.1:8004/api/analyze/deep-stream'
params = {
    'fen': 'r1bakab1r/4n4/1cn1c1p1p/p1p1p3P/6P2/2P1C1N2/P3P4/1C4C2/4A4/RNBAKAB1R b - - 0 1',
    'question': '这步为什么难下，应该先看什么矛盾？',
}
start = time.perf_counter()
with requests.get(url, params=params, stream=True, timeout=120) as resp:
    print('status', resp.status_code)
    current_event = None
    for raw in resp.iter_lines(decode_unicode=True):
        if not raw:
            continue
        if raw.startswith('event: '):
            current_event = raw[7:]
            continue
        if not raw.startswith('data: '):
            continue
        payload = raw[6:]
        try:
            data = json.loads(payload)
        except Exception:
            data = payload
        t = time.perf_counter() - start
        if current_event in {'dispatch_info','orchestrator_subtitle','expert_start','expert_step_start','expert_step_content','expert_step_end','expert_tactics_chunk','expert_strategy_chunk','expert_engine_chunk','result','error'}:
            if isinstance(data, dict):
                snippet = data.get('content') or data.get('subtitle') or data.get('expert') or data.get('result') or data.get('message') or data
            else:
                snippet = data
            text = str(snippet).replace('\n', ' ')[:180]
            print(f'{t:7.3f}s | {current_event:20} | {text}')
        if current_event in {'result','error'}:
            break
