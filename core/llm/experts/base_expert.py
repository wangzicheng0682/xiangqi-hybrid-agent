"""
专家Agent基类 - 共享逻辑

提供三个专家共用的基础设施：
- LLM API调用（含流式）
- 棋盘布局生成
- 工具执行
- 共享上下文构建
"""

import json
import os
import requests
from typing import Dict, List, Any, Callable, Optional, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from core.llm.agent_tools import AgentTools, ToolResult

from core.llm.agent_tools import AgentTools, ToolResult


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ExpertResult:
    """专家分析结果"""
    expert_name: str
    finding: str  # 专家的核心发现
    details: str  # 详细分析内容
    tool_calls: List[Dict] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None


@dataclass
class ExpertConfig:
    """专家配置"""
    name: str  # 英文名，如 "tactics"
    display_name: str  # 中文显示名，如 "战术专家"
    role: str  # 角色描述
    system_prompt: str  # 专家System Prompt
    tools: List[Dict]  # 该专家可用的工具Schema
    tool_names: List[str]  # 该专家可用的工具名列表
    max_rounds: int = 3  # 最大Agent循环轮次
    max_tokens: int = 512  # 最大输出token


class BaseExpert:
    """专家Agent基类"""

    PIECE_NAMES = {
        'K': '红帅', 'k': '黑将',
        'A': '红仕', 'a': '黑士',
        'B': '红相', 'b': '黑象',
        'N': '红马', 'n': '黑马',
        'R': '红车', 'r': '黑车',
        'C': '红炮', 'c': '黑炮',
        'P': '红兵', 'p': '黑卒',
    }

    def __init__(self, api_key: str = None, model: str = "glm-5",
                 base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"):
        self.api_key = api_key or os.getenv("ALIYUN_API_KEY")
        self.base_url = base_url
        self.model = model
        self.tools = AgentTools()

        self._tool_functions = {
            "get_piece_attacks": self.tools.get_piece_attacks,
            "get_piece_defenders": self.tools.get_piece_defenders,
            "get_threats_to_piece": self.tools.get_threats_to_piece,
            "get_piece_relations": self.tools.get_piece_relations,
            "analyze_move": self.tools.analyze_move,
            "compare_moves": self.tools.compare_moves,
            "get_forcing_sequence": self.tools.get_forcing_sequence,
            "engine_deep_analysis": self.tools.engine_deep_analysis,
            "engine_alternatives": self.tools.engine_alternatives,
            "analyze_position_strategy": self.tools.analyze_position_strategy,
        }

    def _generate_board_layout(self, fen: str) -> str:
        """生成棋盘布局的可读格式"""
        try:
            board_part = fen.split()[0]
            rows = board_part.split('/')

            red_pieces = []
            black_pieces = []

            for row_idx, row in enumerate(rows):
                col_idx = 0
                for char in row:
                    if char.isdigit():
                        col_idx += int(char)
                    else:
                        x = col_idx + 1
                        y = 10 - row_idx
                        piece_name = self.PIECE_NAMES.get(char, char)
                        if char.isupper():
                            red_pieces.append(f"{piece_name}-({x},{y})")
                        else:
                            black_pieces.append(f"{piece_name}-({x},{y})")
                        col_idx += 1

            layout = "【红方棋子】\n"
            layout += "、".join(red_pieces) if red_pieces else "无"
            layout += "\n\n【黑方棋子】\n"
            layout += "、".join(black_pieces) if black_pieces else "无"
            return layout
        except Exception as e:
            return f"解析棋盘失败: {str(e)}"

    def _build_shared_context(
        self,
        fen: str,
        tag_summary: str,
        primary_tension: Dict,
        phase_info,
        question: str,
        move: str = None,
    ) -> str:
        """构建共享上下文（注入给每个专家）"""
        board_layout = self._generate_board_layout(fen)

        context = f"【当前局面】FEN: {fen}\n\n"
        context += f"【棋盘布局 - 只能使用以下棋子】\n{board_layout}\n\n"

        if tag_summary:
            tag_str = "\n".join(tag_summary) if isinstance(tag_summary, list) else tag_summary
            context += f"【局面事实 - 必须基于此分析】\n{tag_str}\n\n"

        if primary_tension:
            context += f"""【张力检测 - 已自动识别】
⚡ 主要张力：{primary_tension.get('tension_type', '')}（优先级：{primary_tension.get('priority', '')}）
❓ 核心问题：{primary_tension.get('question', '')}
💡 初始假设：{primary_tension.get('hypothesis', '')}

"""

        if move:
            context += f"【刚走的棋】{move}\n\n"

        context += f"【问题】{question}"

        return context

    def _call_api(
        self,
        messages: List[Dict],
        tools: List[Dict] = None,
    ) -> Dict:
        """调用LLM API（非流式）"""
        if not self.api_key:
            return {"content": "API Key未配置", "tool_calls": [], "finish_reason": "error"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 512,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            session = requests.Session()
            session.trust_env = False
            response = session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120,
            )

            if response.status_code == 200:
                result = response.json()
                choice = result.get("choices", [{}])[0]
                message = choice.get("message", {})
                return {
                    "content": message.get("content", ""),
                    "tool_calls": message.get("tool_calls", []),
                    "finish_reason": choice.get("finish_reason", "stop"),
                }
            else:
                return {"content": f"API错误: {response.status_code}", "tool_calls": [], "finish_reason": "error"}
        except Exception as e:
            return {"content": f"请求失败: {str(e)}", "tool_calls": [], "finish_reason": "error"}

    def _call_expert(
        self,
        system_prompt: str,
        user_content: str,
        config: ExpertConfig,
        fen: str = None,
        on_thinking: Callable[[str, str], None] = None,
    ) -> ExpertResult:
        """
        通用专家分析流程：构建消息 → Agent循环 → 返回结论

        子类通过 config 提供专家特定的 system_prompt 和 tools
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        tool_calls_log = []

        for round_num in range(config.max_rounds):
            if on_thinking:
                on_thinking(f"{config.name}_thinking", f"[{config.display_name}] 第{round_num + 1}轮分析...")

            response = self._call_api(messages, tools=config.tools)

            if response["finish_reason"] == "error":
                return ExpertResult(
                    expert_name=config.name,
                    finding="分析失败",
                    details=response["content"],
                    success=False,
                    error=response["content"],
                )

            content = response["content"]
            tool_calls = response.get("tool_calls", [])

            if on_thinking and content:
                on_thinking(f"{config.name}_chunk", content)

            # 工具调用循环
            if tool_calls:
                messages.append({"role": "assistant", "content": content or ""})
                assistant_tool_calls = []
                for tc in tool_calls:
                    tool_calls_log.append({
                        "round": round_num,
                        "name": tc["function"]["name"],
                        "arguments": json.loads(tc["function"]["arguments"]),
                    })

                    if on_thinking:
                        on_thinking(f"{config.name}_tool", f"调用工具: {tc['function']['name']}")

                    result = self._execute_tool(tc["function"]["name"], json.loads(tc["function"]["arguments"]), fen)
                    tool_msg = json.dumps(result, ensure_ascii=False)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": tool_msg,
                    })

                    if on_thinking:
                        msg_preview = result.get("message", str(result)[:80])
                        on_thinking(f"{config.name}_tool_result", f"{tc['function']['name']}: {msg_preview}")

                    assistant_tool_calls.append({
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": tc["function"]["arguments"],
                        }
                    })

                messages[-1]["tool_calls"] = assistant_tool_calls
            else:
                # 无工具调用，分析完成
                return ExpertResult(
                    expert_name=config.name,
                    finding=self._extract_finding(content, config.name),
                    details=content,
                    tool_calls=tool_calls_log,
                    success=True,
                )

        # 达到最大轮数，强制结束
        final_response = self._call_api(messages, tools=None)
        return ExpertResult(
            expert_name=config.name,
            finding=self._extract_finding(final_response["content"], config.name),
            details=final_response["content"],
            tool_calls=tool_calls_log,
            success=True,
        )

    def _execute_tool(self, tool_name: str, arguments: Dict, fen: str) -> Dict:
        """执行工具"""
        func = self._tool_functions.get(tool_name)
        if not func:
            return {"error": f"未知工具: {tool_name}"}

        try:
            args = dict(arguments)  # 复制，不修改原始
            args["fen"] = fen     # 注入 fen（与 XiangqiCoachAgent 对齐）
            result = func(**args)

            if isinstance(result, ToolResult):
                return {
                    "success": result.success,
                    "data": result.data,
                    "message": result.message,
                }
            return result
        except Exception as e:
            return {"error": str(e)}

    def _extract_finding(self, content: str, expert_name: str) -> str:
        """从分析内容中提取核心发现（一句话摘要）"""
        if not content:
            return "无分析内容"
        # 取前100字作为发现摘要
        finding = content.strip()[:100]
        if len(content) > 100:
            finding += "..."
        return finding


# ═══════════════════════════════════════════════════════════════════════════════
# 自适应决策器 - 判断是否启用多Agent
# ═══════════════════════════════════════════════════════════════════════════════

def should_use_multi_agent(
    tensions: List[Dict],
    phase_name: str,
    user_request: str,
) -> bool:
    """
    判断是否使用多Agent并行分析

    简单局面 → 单Agent快速分析
    复杂局面 → 多Agent并行分析
    """
    # 强制深度模式
    if "深度" in user_request or "详细" in user_request:
        return True

    # 简单开局，无张力 → 单Agent
    if phase_name == "开局" and len(tensions) == 0:
        return False

    # 张力复杂度判断
    if tensions:
        primary = tensions[0]
        priority = primary.get("priority", "")

        if priority == "CRITICAL":
            return True
        if len(tensions) >= 3:
            return True

    return False
