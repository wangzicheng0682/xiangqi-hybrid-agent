"""
测试深度分析监控系统

演示如何使用记录器查看完整的LLM分析上下文
"""
import json
from core.llm.analysis_recorder import AnalysisRecorder


def test_recorder_basic():
    """测试记录器基本功能"""
    print("=" * 60)
    print("测试1: 记录器基本功能")
    print("=" * 60)
    
    recorder = AnalysisRecorder()
    
    # 启动记录
    record_id = recorder.start_record("test-001")
    print(f"启动记录: {record_id}")
    
    # 记录输入
    recorder.record_input(
        fen="rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
        question="请分析当前局面",
        move="炮2平5",
        tag_summary=["is_attack_unprotected: 红车攻击黑马"],
        engine_eval={"cp": 50, "best": "炮2平5"},
        tensions=[{"tension_type": "子力vs主动权"}]
    )
    
    # 记录prompt
    recorder.record_system_prompt("# 你是象棋教练\n\n你不能凭空编造...")
    recorder.record_user_message("【当前局面】FEN: ...\n【问题】请分析")
    
    # 模拟LLM调用
    recorder.start_llm_round(0)
    recorder.record_llm_request([{"role": "system", "content": "..."}])
    recorder.record_llm_chunk("我初步判断")
    recorder.record_llm_chunk("这里有子力优势")
    recorder.record_llm_response(
        content="我初步判断这里有子力优势",
        tool_calls=[{"name": "get_piece_defenders", "arguments": '{"piece": "红车"}'}],
        finish_reason="tool_calls"
    )
    
    # 模拟工具调用
    recorder.start_tool_call("get_piece_defenders")
    recorder.record_tool_args({"piece": "红车"})
    recorder.record_tool_result({
        "success": True,
        "data": {"defenders": [], "is_unprotected": True}
    })
    
    # 完成记录
    saved_path = recorder.finish_record()
    print(f"记录已保存: {saved_path}")
    
    return record_id


def test_list_and_load_records():
    """测试列出和加载记录"""
    print("\n" + "=" * 60)
    print("测试2: 列出和加载记录")
    print("=" * 60)
    
    records = AnalysisRecorder.get_records(limit=5)
    print(f"最近 {len(records)} 条记录:")
    for r in records:
        print(f"  - {r['record_id']} ({r['size_bytes']} bytes)")
    
    if records:
        record_id = records[0]['record_id']
        record = AnalysisRecorder.load_record(record_id)
        print(f"\n加载记录 {record_id}:")
        print(f"  - FEN: {record['input']['fen'][:50]}...")
        print(f"  - 问题: {record['input']['question']}")
        print(f"  - 轮数: {len(record['rounds'])}")
        for i, round_info in enumerate(record['rounds']):
            print(f"    Round {i}: {round_info['finish_reason']}, {len(round_info.get('tool_calls', []))} tool calls")


def main():
    print("深度分析监控系统测试")
    print("=" * 60)
    
    # 测试基本功能
    record_id = test_recorder_basic()
    
    # 测试列出和加载
    test_list_and_load_records()
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
    print(f"""
使用方法:
1. 启动后端服务: python -m uvicorn api.main:app --port 8000
2. 点击前端"深度分析"按钮
3. 查看记录: GET http://localhost:8000/api/debug/records
4. 查看完整JSON: GET http://localhost:8000/api/debug/record/{{record_id}}
5. 或直接查看文件: logs/deep_analysis/{{timestamp}}_{{id}}.json
""")


if __name__ == "__main__":
    main()
