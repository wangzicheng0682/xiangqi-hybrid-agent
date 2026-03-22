"""
象棋开局识别库

支持识别常见开局：
- 中炮开局系列
- 飞相局系列
- 起马局系列
- 特殊开局：铁滑车、下马威等

Reference: PRD 3.1
"""

from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass


@dataclass
class OpeningInfo:
    name: str
    category: str
    description: str
    evaluation: str
    key_moves: List[str]


OPENING_BOOK: Dict[str, OpeningInfo] = {
    "C2-5": OpeningInfo(
        name="中炮开局",
        category="炮类开局",
        description="炮二平五，最流行的开局，攻击性强",
        evaluation="进攻型开局，红方先手攻势猛烈，历史悠久，变化丰富",
        key_moves=["h2e2"]
    ),
    "C2-6": OpeningInfo(
        name="过宫炮",
        category="炮类开局",
        description="炮二平六，集中火力于一翼",
        evaluation="稳健型开局，子力集中但需注意协调",
        key_moves=["h2f2"]
    ),
    "C2-4": OpeningInfo(
        name="士角炮",
        category="炮类开局",
        description="炮二平四，灵活多变",
        evaluation="灵活型开局，可转化为多种阵型",
        key_moves=["h2d2"]
    ),
    "C8-5": OpeningInfo(
        name="过宫炮（反向）",
        category="炮类开局",
        description="炮八平五，右路进攻",
        evaluation="与中炮镜像，但实战变化不同",
        key_moves=["b2e2"]
    ),
    "E3-5": OpeningInfo(
        name="飞相局",
        category="相类开局",
        description="相三进五，稳健防守",
        evaluation="防守反击型，稳健但需耐心",
        key_moves=["g0e2"]
    ),
    "E7-5": OpeningInfo(
        name="飞相局（反向）",
        category="相类开局",
        description="相七进五",
        evaluation="与飞相局类似，方向相反",
        key_moves=["c0e2"]
    ),
    "N2-3": OpeningInfo(
        name="起马局",
        category="马类开局",
        description="马二进三，出子为先",
        evaluation="稳健型开局，灵活多变",
        key_moves=["h0g2"]
    ),
    "R1-1": OpeningInfo(
        name="铁滑车",
        category="特殊开局",
        description="车一进一，快速出车",
        evaluation="冷门开局，出其不意，但正统应法可获优势",
        key_moves=["i0i1"]
    ),
    "R9-1": OpeningInfo(
        name="铁滑车（反向）",
        category="特殊开局",
        description="车九进一，左路出车",
        evaluation="冷门开局，与铁滑车镜像",
        key_moves=["a0a1"]
    ),
    "N2-4": OpeningInfo(
        name="下马威",
        category="特殊开局",
        description="马二进四，跳到士角",
        evaluation="冷门开局，意在快速出子但位置不佳",
        key_moves=["h0f1"]
    ),
    "C2-7": OpeningInfo(
        name="金钩炮",
        category="炮类开局",
        description="炮二平七，攻击边路",
        evaluation="冷门开局，针对性攻击",
        key_moves=["h2c2"]
    ),
    "C2-3": OpeningInfo(
        name="兵底炮",
        category="炮类开局",
        description="炮二平三，针对三路兵",
        evaluation="冷门开局，意在破坏对方部署",
        key_moves=["h2g2"]
    ),
    "P7-1": OpeningInfo(
        name="挺兵局",
        category="兵类开局",
        description="兵七进一，活通马路",
        evaluation="灵活型开局，可转化为多种阵型",
        key_moves=["g3g4"]
    ),
    "P3-1": OpeningInfo(
        name="挺兵局（反向）",
        category="兵类开局",
        description="兵三进一",
        evaluation="与挺兵局类似",
        key_moves=["c3c4"]
    ),
}

OPENING_SEQUENCES: List[Tuple[List[str], OpeningInfo]] = [
    (["h2e2", "h9g7", "c3c4"], OpeningInfo(
        name="中炮进七兵对屏风马",
        category="中炮系列",
        description="红方中炮挺七兵，黑方屏风马应对",
        evaluation="主流开局，变化丰富，双方机会均等",
        key_moves=["h2e2", "h9g7", "c3c4"]
    )),
    (["h2e2", "h9g7", "h0g2"], OpeningInfo(
        name="中炮对屏风马",
        category="中炮系列",
        description="红方中炮正马，黑方屏风马",
        evaluation="经典开局，攻防变化多端",
        key_moves=["h2e2", "h9g7", "h0g2"]
    )),
    (["h2e2", "b7e7"], OpeningInfo(
        name="中炮对反宫马",
        category="中炮系列",
        description="红方中炮，黑方反架中炮",
        evaluation="对攻型开局，双方对攻激烈",
        key_moves=["h2e2", "b7e7"]
    )),
    (["h2e2", "b9c7"], OpeningInfo(
        name="中炮对屏风马",
        category="中炮系列",
        description="红方中炮，黑方屏风马",
        evaluation="主流开局，攻防均衡",
        key_moves=["h2e2", "b9c7"]
    )),
    (["g0e2", "b9c7"], OpeningInfo(
        name="飞相局对屏风马",
        category="飞相系列",
        description="红方飞相，黑方屏风马应对",
        evaluation="稳健开局，红方略优",
        key_moves=["g0e2", "b9c7"]
    )),
    (["h0g2", "b9c7"], OpeningInfo(
        name="起马局对屏风马",
        category="起马系列",
        description="红方起马，黑方屏风马应对",
        evaluation="灵活开局，可转化为多种阵型",
        key_moves=["h0g2", "b9c7"]
    )),
    (["i0i1"], OpeningInfo(
        name="铁滑车",
        category="特殊开局",
        description="红方首着车一进一",
        evaluation="冷门开局，出其不意，正统应法可获优势",
        key_moves=["i0i1"]
    )),
    (["a0a1"], OpeningInfo(
        name="铁滑车（反向）",
        category="特殊开局",
        description="红方首着车九进一",
        evaluation="冷门开局，与铁滑车镜像",
        key_moves=["a0a1"]
    )),
    (["h0f1"], OpeningInfo(
        name="下马威",
        category="特殊开局",
        description="红方马二进四跳士角",
        evaluation="冷门开局，马的位置不佳但出其不意",
        key_moves=["h0f1"]
    )),
    (["b0d1"], OpeningInfo(
        name="下马威（反向）",
        category="特殊开局",
        description="红方马八进六跳士角",
        evaluation="冷门开局，与下马威镜像",
        key_moves=["b0d1"]
    )),
]


def normalize_move(move: str) -> str:
    if not move:
        return ""
    move = move.strip().lower()
    if len(move) >= 4 and move[0].isalpha() and move[1].isdigit():
        return move[:4]
    return move


def convert_chinese_move_to_iccs(chinese_move: str) -> str:
    PIECE_MAP = {
        "炮": "c", "车": "r", "马": "n", "相": "b", "象": "b",
        "仕": "a", "士": "a", "帅": "k", "将": "k", "兵": "p", "卒": "p"
    }
    NUM_MAP = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5",
               "六": "6", "七": "7", "八": "8", "九": "9"}
    DIR_MAP = {"进": "-", "退": "+", "平": ""}
    
    if len(chinese_move) < 4:
        return chinese_move
    
    piece = PIECE_MAP.get(chinese_move[0], "")
    if not piece:
        return chinese_move
    
    return chinese_move


def identify_opening(moves: List[str]) -> Optional[OpeningInfo]:
    if not moves:
        return None
    
    normalized = [normalize_move(m) for m in moves if m]
    
    for seq_moves, info in OPENING_SEQUENCES:
        if len(normalized) >= len(seq_moves):
            match = True
            for i, seq_move in enumerate(seq_moves):
                if i < len(normalized) and seq_move != normalized[i]:
                    match = False
                    break
            if match:
                return info
    
    if normalized:
        first_move = normalized[0]
        for key, info in OPENING_BOOK.items():
            if first_move in info.key_moves:
                return info
    
    return None


def get_opening_evaluation(moves: List[str]) -> str:
    opening = identify_opening(moves)
    if opening:
        return f"**{opening.name}** ({opening.category})\n\n{opening.description}\n\n**评价**: {opening.evaluation}"
    return "开局阶段，暂无识别信息"


def get_opening_name(moves: List[str]) -> str:
    opening = identify_opening(moves)
    if opening:
        return opening.name
    if not moves:
        return "未开局"
    if len(moves) <= 4:
        return "开局阶段"
    return "中局"


def identify_position_type(fen: str) -> Tuple[str, str]:
    if not fen:
        return "未知局面", "无法分析"
    
    board = fen.split()[0] if " " in fen else fen
    
    red_cannons = board.count("C")
    black_cannons = board.count("c")
    red_rooks = board.count("R")
    black_rooks = board.count("r")
    red_horses = board.count("N")
    black_horses = board.count("n")
    
    total_cannons = red_cannons + black_cannons
    total_rooks = red_rooks + black_rooks
    total_horses = red_horses + black_horses
    
    if total_rooks == 4 and total_cannons == 4 and total_horses == 4:
        return "开局", "双方子力齐全，处于开局阶段"
    
    if total_rooks >= 2 and total_cannons >= 2:
        return "中局", "子力活跃，战斗激烈"
    
    if total_rooks <= 1 and total_cannons <= 1:
        return "残局", "大子较少，进入残局阶段"
    
    if total_horses == 0 and total_cannons == 0:
        return "车兵残局", "无马炮，车兵类残局"
    
    if total_rooks == 0:
        return "马炮残局", "无车，马炮类残局"
    
    return "中局", "对弈进行中"
