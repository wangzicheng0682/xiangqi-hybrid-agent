import requests
import json

fen = 'rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1'

r = requests.post('http://localhost:8002/api/position-analysis', json={'fen': fen}, timeout=30)
if r.status_code == 200:
    data = r.json()
    tags = data['analysis_text']['retrieval_tags']
    hints = data['analysis_text']['retrieval_hints']
    print("=== 检索标签 ===")
    for t in tags:
        print(f"  - {t}")
    print("\n=== 查询提示 ===")
    for h in hints:
        print(f"  - {h}")
    
    print("\n=== 检查炮的攻击 ===")
    for p in data['analysis_structured']['pieces']:
        if p['piece_type'] == 'cannon':
            print(f"  {p['piece_name']} @ {p['position']}")
            print(f"    attacks: {p['attacks']}")
            print(f"    legal_moves (captures): {[m for m in p['legal_moves'] if m.get('move_type') == 'capture']}")
