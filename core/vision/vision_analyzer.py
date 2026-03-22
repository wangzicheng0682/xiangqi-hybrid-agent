"""
Vision Analyzer for Xiangqi Board Recognition

使用Qwen-VL多模态模型识别棋盘图片，生成FEN字符串

Reference: PRD 4.3, TECH 5.5
"""

import os
import base64
from typing import Optional, Dict, Any
from dataclasses import dataclass
import requests
from PIL import Image
import io


@dataclass
class VisionConfig:
    provider: str = "aliyun"
    api_key: str = ""
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model: str = "qwen-vl-max"


@dataclass
class VisionResult:
    fen: str
    description: str
    confidence: float
    pieces_detected: int


PIECE_MAP = {
    "红帅": "K", "红将": "K", "帅": "K", "将": "K",
    "红仕": "A", "红士": "A", "仕": "A", "士": "A",
    "红相": "B", "红象": "B", "相": "B", "象": "B",
    "红车": "R", "红車": "R", "车": "R", "車": "R",
    "红马": "N", "红馬": "N", "马": "N", "馬": "N",
    "红炮": "C", "红砲": "C", "炮": "C", "砲": "C",
    "红兵": "P", "兵": "P",
    "黑将": "k", "黑帅": "k",
    "黑士": "a", "黑仕": "a",
    "黑象": "b", "黑相": "b",
    "黑车": "r", "黑車": "r",
    "黑马": "n", "黑馬": "n",
    "黑炮": "c", "黑砲": "c",
    "黑卒": "p", "卒": "p",
}


class VisionAnalyzer:
    def __init__(self, config: VisionConfig = None):
        self.config = config or VisionConfig()
        self.api_key = self.config.api_key or os.getenv("ALIYUN_API_KEY", "sk-689ac793ca22414da28ce80d23b78e2d")
        self.base_url = self.config.base_url
        self.model = self.config.model
    
    def _encode_image(self, image: Image.Image) -> str:
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_bytes = buffered.getvalue()
        return base64.b64encode(img_bytes).decode('utf-8')
    
    def analyze_image(self, image: Image.Image) -> Optional[VisionResult]:
        if not self.api_key:
            return None
        
        try:
            img_base64 = self._encode_image(image)
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            
            prompt = """这是一张中国象棋棋盘图片。请仔细识别图片中的棋子位置，并按以下格式输出：

1. 首先描述你看到的棋盘情况（红方在下，黑方在上）
2. 然后输出FEN字符串，格式如下：
   - 棋盘部分：每行用/分隔，空格用数字表示
   - 红方棋子用大写字母：K=帅, A=仕, B=相, R=车, N=马, C=炮, P=兵
   - 黑方棋子用小写字母：k=将, a=士, b=象, r=车, n=马, c=炮, p=卒
   
示例输出格式：
【棋盘描述】红方在下，黑方在上。红方当头炮，黑方屏风马...
【FEN】rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1

请识别这张图片："""

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{img_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 1024,
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                return self._parse_response(content)
            else:
                print(f"Vision API error: {response.status_code} - {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"Vision analysis failed: {e}")
            return None
    
    def _parse_response(self, content: str) -> VisionResult:
        fen = ""
        description = ""
        
        if "【FEN】" in content:
            fen_start = content.find("【FEN】") + 5
            fen_end = content.find("\n", fen_start)
            if fen_end == -1:
                fen_end = len(content)
            fen = content[fen_start:fen_end].strip()
        
        if "【棋盘描述】" in content:
            desc_start = content.find("【棋盘描述】") + 7
            desc_end = content.find("【FEN】", desc_start)
            if desc_end == -1:
                desc_end = len(content)
            description = content[desc_start:desc_end].strip()
        
        if not fen:
            fen = self._extract_fen_from_text(content)
        
        pieces_detected = self._count_pieces(fen)
        
        return VisionResult(
            fen=fen,
            description=description or content[:200],
            confidence=0.8 if fen else 0.0,
            pieces_detected=pieces_detected
        )
    
    def _extract_fen_from_text(self, text: str) -> str:
        import re
        fen_pattern = r'[rnbakabnrRNBAKABNR0-9/]+\s+[wb]\s+-\s+-\s+\d+\s+\d+'
        match = re.search(fen_pattern, text)
        if match:
            return match.group(0)
        
        board_pattern = r'[rnbakabnrRNBAKABNR0-9/]+'
        matches = re.findall(board_pattern, text)
        for m in matches:
            if '/' in m and len(m) > 20:
                return m + " w - - 0 1"
        
        return ""
    
    def _count_pieces(self, fen: str) -> int:
        if not fen:
            return 0
        board = fen.split()[0] if ' ' in fen else fen
        count = 0
        for c in board:
            if c.isalpha():
                count += 1
        return count
    
    def image_to_fen(self, image_path: str) -> Optional[VisionResult]:
        try:
            image = Image.open(image_path)
            return self.analyze_image(image)
        except Exception as e:
            print(f"Failed to load image: {e}")
            return None
    
    def analyze_board_image(self, image: Image.Image, bestmove: str = None, 
                            score: float = None, last_move_info: Dict = None) -> str:
        if not self.api_key:
            return "视觉分析不可用"
        
        try:
            img_base64 = self._encode_image(image)
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            
            prompt_parts = ["""你是一位专业的象棋教练。请分析这张棋盘图片。

【任务】
1. 描述当前局面特点（子力对比、阵型、攻防态势）
2. 分析刚才的走法（如果有）
3. 解释引擎推荐的着法

【输出要求】
- 用简洁的中文回答
- 2-3句话概括关键点
- 不要编造不存在的情况
"""]
            
            if last_move_info:
                player = last_move_info.get("player", "")
                piece = last_move_info.get("piece", "")
                from_coord = last_move_info.get("from", "")
                to_coord = last_move_info.get("to", "")
                captured = last_move_info.get("captured", "")
                
                move_desc = f"\n【刚才的走法】{player}走了 {piece} 从 {from_coord} 到 {to_coord}"
                if captured:
                    move_desc += f"，吃掉了{captured}"
                prompt_parts.append(move_desc)
            
            if bestmove and len(bestmove) >= 4:
                prompt_parts.append(f"\n【引擎推荐着法】{bestmove}")
            
            if score is not None:
                if abs(score) < 30:
                    prompt_parts.append(f"\n【局面评估】均势")
                elif score > 0:
                    prompt_parts.append(f"\n【局面评估】红方优势 (+{score:.1f})")
                else:
                    prompt_parts.append(f"\n【局面评估】黑方优势 ({score:.1f})")
            
            prompt = ''.join(prompt_parts)
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{img_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 512,
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                return content
            else:
                return f"视觉分析失败: {response.status_code}"
                
        except Exception as e:
            return f"视觉分析异常: {str(e)[:50]}"
