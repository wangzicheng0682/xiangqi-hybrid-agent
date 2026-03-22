"""
测试深度分析API - 展示完整上下文和LLM输出
"""
import sys
import json
import requests
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 经典中局局面 - 红方有攻势
CLASSIC_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"

# 一个更有趣的中局局面
MIDDLEGAME_FEN = "r1bakab1r/9/1cn3nc1/p1p1p1p1p/9/9/P1P1P1P1P/1C2N1NC1/9/R1BAKAB1R w - - 0 1"

# 一个有张力的局面
TENSION_FEN = "rnbakab1r/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"

def test_deep_analysis(fen: str, move: str = None):
    print("=" * 80)
    print(f"测试深度分析 API")
    print(f"FEN: {fen}")
    print(f"Move: {move}")
    print("=" * 80)
    
    url = "http://localhost:8000/api/analyze/deep"
    
    payload = {
        "fen": fen,
        "move": move,
        "question": "请分析当前局面的主要矛盾和最佳走法",
        "show_thinking": True
    }
    
    print("\n📤 请求体:")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    
    print("\n📥 SSE 流式响应:")
    print("-" * 80)
    
    try:
        response = requests.post(url, json=payload, stream=True, timeout=120)
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])
                        msg_type = data.get('type', 'unknown')
                        
                        if msg_type == 'thinking':
                            stage = data.get('stage', '')
                            message = data.get('message', '')
                            print(f"\n[思考阶段 {stage}] {message}")
                            
                        elif msg_type == 'tension_detected':
                            print(f"\n⚡ [张力检测] {data.get('message', '')}")
                            
                        elif msg_type == 'primary_contradiction':
                            print(f"\n🎯 [主要矛盾]")
                            print(data.get('message', ''))
                            
                        elif msg_type == 'tool_call':
                            print(f"\n🔧 [工具调用] {data.get('message', '')}")
                            
                        elif msg_type == 'tool_result':
                            print(f"\n📊 [工具结果] {data.get('message', '')[:200]}...")
                            
                        elif msg_type == 'result':
                            print(f"\n✅ [最终结果]")
                            print(f"置信度: {data.get('confidence', 'unknown')}")
                            print(f"讲解:\n{data.get('explanation', '')}")
                            
                        elif msg_type == 'error':
                            print(f"\n❌ [错误] {data.get('message', '')}")
                            
                        else:
                            print(f"\n[{msg_type}] {json.dumps(data, ensure_ascii=False)[:300]}")
                            
                    except json.JSONDecodeError:
                        print(f"解析失败: {line_str}")
                        
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        
    print("\n" + "=" * 80)


def test_tactical_tags(fen: str):
    print("\n" + "=" * 80)
    print("测试战术标签检测")
    print("=" * 80)
    
    url = "http://localhost:8000/api/tactical-tags"
    
    payload = {"fen": fen}
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        data = response.json()
        
        print(f"\n检测到 {len(data.get('tags', []))} 个标签:")
        
        for category, tags in data.get('tags_by_category', {}).items():
            print(f"\n【{category}】")
            for tag in tags:
                print(f"  - {tag['name']}: {tag['description']}")
                if tag.get('bind_pieces'):
                    print(f"    绑定棋子: {tag['bind_pieces']}")
                    
    except Exception as e:
        print(f"错误: {e}")


def test_quick_analysis(fen: str):
    print("\n" + "=" * 80)
    print("测试快速分析")
    print("=" * 80)
    
    url = "http://localhost:8000/api/analyze/quick"
    
    payload = {
        "fen": fen,
        "mode": "replay"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        data = response.json()
        
        print(f"\n响应时间: {data.get('response_time_ms', 0):.1f}ms")
        print(f"\nEvidence Map:")
        print(json.dumps(data.get('evidence_map', {}), ensure_ascii=False, indent=2))
        print(f"\n讲解: {data.get('explanation', '')}")
        
    except Exception as e:
        print(f"错误: {e}")


if __name__ == "__main__":
    # 使用经典开局局面
    test_fen = CLASSIC_FEN
    
    # 测试战术标签
    test_tactical_tags(test_fen)
    
    # 测试快速分析
    test_quick_analysis(test_fen)
    
    # 测试深度分析
    test_deep_analysis(test_fen)
