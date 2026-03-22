# 语义分析模块已归档重构，请勿引用旧代码
# Archive Reason: 核心分析模块存在致命逻辑错误
# - 炮攻击逻辑错误（未检查炮架）
# - 马腿判断错误（己方棋子错误标记为障碍）
# - 防御检测错误（"无根子"标签泛滥）
# - 标签生成泛滥（错误标签污染分析结果）
#
# 所有旧代码已移至 _archived_module/core/semantic/
# 新实现请遵循 docs/03_DEVELOPMENT_GUIDE/ 中的设计规范

"""
语义分析模块 - 重构中

⚠️ 警告：此模块正在重构中，请勿使用旧代码

历史归档：
- position_analyzer.py (800+行，包含三大致命错误)
- position_analysis_schema.py (错误标签生成器)
- board_structure_parser.py
- conflict_detector_v1.py
- enhanced_piece_analyzer.py
- label_generator.py
- semantic_state_v1.py

新架构方向：
1. 规则检查器：仅做合法性校验，不计算攻击/防御
2. 事实识别器：基于引擎真值(bestmove/score/pv)，不自研攻击计算
"""

__all__ = []
