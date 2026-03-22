"""
LLM Client for Xiangqi Analysis

Supports:
- Aliyun Bailian (Qwen series)
- OpenAI compatible APIs

Reference: PRD 3.1, TECH 5.4
"""

import os
from typing import Optional, List, Dict
from dataclasses import dataclass
import requests

from core.utils.board_text import (
    create_llm_context,
    generate_position_description,
    get_material_balance,
    fen_to_board,
)


@dataclass
class LLMConfig:
    provider: str = "bigmodel"
    api_key: str = "715cf7368e134716a8a032dd5e7fcbd2.7zAqa1crDYHcbiWx"
    base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    model: str = "glm-5"


class LLMClient:
    def __init__(self, config: LLMConfig = None):
        self.config = config or LLMConfig()
        self.api_key = self.config.api_key or os.getenv("ALIYUN_API_KEY")
        self.base_url = self.config.base_url
        self.model = self.config.model
    
    def chat(self, messages: List[Dict[str, str]], 
             temperature: float = 0.7,
             max_tokens: int = 1024) -> Optional[str]:
        if not self.api_key:
            return None
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "thinking": {"type": "disabled"},
        }
        
        try:
            session = requests.Session()
            session.trust_env = False
            response = session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                print(f"LLM API error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"LLM request failed: {e}")
            return None
    
    def analyze_position(self, fen: str, bestmove: str = None, 
                         kg_stats: Dict = None) -> str:
        context = create_llm_context(fen, bestmove)
        
        if kg_stats:
            context += f"\n\n【历史数据】{kg_stats.get('total_games', 0)}局，红方胜率{kg_stats.get('red_win_rate', 0):.1f}%"
        
        messages = [{"role": "user", "content": context}]
        return self.chat(messages, max_tokens=512)
    
    def explain_move(self, fen: str, move: str, last_move_info: Dict = None, 
                     piece_name: str = None) -> str:
        context = create_llm_context(fen, move, last_move_info=last_move_info)
        
        context += "\n\n请重点解释这步推荐着法的战术目的和后续思路。"
        
        messages = [{"role": "user", "content": context}]
        return self.chat(messages, max_tokens=256)
    
    def generate_review(self, moves: List[str], result: str) -> str:
        prompt = f"""你是一位专业的象棋教练。请对这盘棋进行简要复盘：

对局记录: {' '.join(moves[:20])}...
结果: {result}

请用简洁的中文分析：
1. 开局阶段
2. 关键转折点
3. 胜负原因

回复控制在300字以内。"""
        
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, max_tokens=512)
