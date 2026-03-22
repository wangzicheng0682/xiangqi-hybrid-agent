"""
黄金局面测试库

每个黄金局面是事先知道正确答案的测试局面，来自象棋教材的战术题。
目标数量：45个（每个标签至少1个对应的黄金局面）
赛前最低要求：30个，覆盖所有已实现标签

重点覆盖六大重灾区bug类型：
1. 坐标系混乱 - 边界条件测试
2. 炮的移动规则错误 - 最高频bug
3. 将帅照面规则缺失
4. 红黑视角混淆
5. 马腿遮挡逻辑错误
6. 棋子绑定坐标错误
"""

from typing import List, Dict, Any, Optional

GOLDEN_POSITIONS: List[Dict[str, Any]] = [
    
    # =========================================================================
    # 第一层：将杀困毙层测试
    # =========================================================================
    
    {
        "id": "GP001",
        "name": "将军-黑车将军红帅",
        "description": "黑车横向攻击红帅，红方走棋时被将军（但可以躲避），验证is_check检测",
        "fen": "3k5/9/9/9/9/9/9/9/3rK3/9 w - - 0 1",
        "phase": "残局",
        "expected_true": ["is_check"],
        "expected_false": ["is_checkmate", "is_stalemate"],
        "expected_bindings": {
            "is_check": {
                "bind_pieces_must_contain": ["红帅", "黑车"],
            }
        }
    },
    
    {
        "id": "GP002",
        "name": "将死-单车将死",
        "description": "红车将死黑将，黑方走棋时被将死，验证is_checkmate检测",
        "fen": "3kRR3/9/3R5/9/9/9/9/9/9/4K4 b - - 0 1",
        "phase": "残局",
        "expected_true": ["is_check", "is_checkmate"],
        "expected_false": ["is_stalemate"],
        "expected_bindings": {
            "is_checkmate": {
                "bind_pieces_must_contain": ["黑将"],
            }
        }
    },
    
    {
        "id": "GP003",
        "name": "困毙-无子可动",
        "description": "黑方走棋时无合法走法但未被将军，验证is_stalemate检测",
        "fen": "3k5/4R4/9/9/9/9/9/9/9/4K4 b - - 0 1",
        "phase": "残局",
        "expected_true": ["is_stalemate"],
        "expected_false": ["is_check", "is_checkmate"],
        "expected_bindings": {
            "is_stalemate": {
                "bind_pieces_must_contain": ["黑将"],
            }
        }
    },
    
    {
        "id": "GP004",
        "name": "将军-双将对面禁止",
        "description": "红帅和黑将同列无遮挡，验证kings_face_to_face检测",
        "fen": "4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1",
        "phase": "残局",
        "expected_true": ["kings_face_to_face"],
        "expected_false": ["is_check", "is_checkmate", "is_stalemate"],
        "expected_bindings": {
            "kings_face_to_face": {
                "bind_pieces_must_contain": ["红帅", "黑将"],
            }
        }
    },
    
    # =========================================================================
    # 第二层：捉子层测试
    # =========================================================================
    
    {
        "id": "GP010",
        "name": "攻无根-车捉无根马",
        "description": "红车攻击没有任何棋子保护的黑马，验证is_attack_unprotected",
        "fen": "9/9/9/9/4n4/4R4/9/9/9/4K3k w - - 0 1",
        "phase": "中局",
        "expected_true": ["is_attack_unprotected"],
        "expected_false": ["is_check", "is_checkmate"],
        "expected_bindings": {
            "is_attack_unprotected": {
                "bind_pieces_must_contain": ["红车", "黑马"],
                "attacker_type": "车",
                "target_type": "马",
            }
        }
    },
    
    {
        "id": "GP011",
        "name": "攻无根-炮隔山打牛(恰好一个炮架)",
        "description": "炮通过恰好一个棋子攻击目标，验证炮的攻击规则",
        "fen": "9/9/9/9/4C4/4P4/4n4/9/9/4K3k w - - 0 1",
        "phase": "中局",
        "expected_true": ["is_attack_unprotected"],
        "expected_false": [],
        "expected_bindings": {
            "is_attack_unprotected": {
                "attacker_type": "炮",
            }
        }
    },
    
    {
        "id": "GP012",
        "name": "炮两个棋子中间-不应攻击",
        "description": "炮和目标之间有两个棋子，不构成攻击，验证炮的规则不被高估",
        "fen": "9/9/9/9/4C4/4P4/4P4/4n4/9/4K3k w - - 0 1",
        "phase": "中局",
        "expected_true": [],
        "expected_false": ["is_attack_unprotected"],
    },
    
    {
        "id": "GP013",
        "name": "互吃-车炮互捉",
        "description": "红车和黑车互相攻击，验证is_mutual_attack",
        "fen": "4k4/9/9/9/9/4Rr3/9/9/9/4K4 w - - 0 1",
        "phase": "中局",
        "expected_true": ["is_mutual_attack", "is_attack_unprotected"],
        "expected_false": [],
        "expected_bindings": {
            "is_mutual_attack": {
                "bind_pieces_must_contain": ["红车", "黑车"],
            }
        }
    },
    
    # =========================================================================
    # 边界条件测试（最容易出bug的地方）
    # =========================================================================
    
    {
        "id": "GP020",
        "name": "边界-棋子在左边界",
        "description": "车在第一列时的攻击检测，验证边界坐标处理",
        "fen": "R8/9/n8/9/9/9/9/9/9/4K3k w - - 0 1",
        "phase": "中局",
        "expected_true": ["is_attack_unprotected"],
        "expected_false": [],
        "expected_bindings": {
            "is_attack_unprotected": {
                "attacker_type": "车",
                "target_type": "马",
            }
        }
    },
    
    {
        "id": "GP021",
        "name": "边界-棋子在右边界",
        "description": "车在第九列时的攻击检测，验证右侧边界",
        "fen": "8R/9/8n/9/9/9/9/9/9/4K3k w - - 0 1",
        "phase": "中局",
        "expected_true": ["is_attack_unprotected"],
        "expected_false": [],
        "expected_bindings": {
            "is_attack_unprotected": {
                "attacker_type": "车",
                "target_type": "马",
            }
        }
    },
    
    {
        "id": "GP022",
        "name": "边界-马在棋盘角落",
        "description": "马在角落时，只有两个合法跳法，验证边界不产生越界坐标",
        "fen": "9/9/9/9/9/9/9/9/9/N7k w - - 0 1",
        "phase": "残局",
        "expected_true": [],
        "expected_false": ["is_attack_unprotected"],
        "special_check": "horse_attack_range_at_corner",
    },
    
    {
        "id": "GP023",
        "name": "边界-炮在边界攻击",
        "description": "炮在边界位置攻击，验证边界坐标处理",
        "fen": "C8/9/9/9/9/9/9/9/9/4K3k w - - 0 1",
        "phase": "中局",
        "expected_true": [],
        "expected_false": [],
    },
    
    {
        "id": "GP024",
        "name": "边界-将帅在九宫角落",
        "description": "将帅在九宫格角落位置，验证九宫格边界检测",
        "fen": "2k6/9/9/9/9/9/9/9/9/2K6 w - - 0 1",
        "phase": "残局",
        "expected_true": [],
        "expected_false": [],
    },
    
    # =========================================================================
    # 第三层：闪击抽将层测试
    # =========================================================================
    
    {
        "id": "GP030",
        "name": "闪将-马移开露出车将军",
        "description": "移动马后露出车的将军，验证is_discovered_check",
        "fen": "4k4/9/9/9/9/9/4N4/4R4/9/4K4 w - - 0 1",
        "phase": "中局",
        "expected_true": [],
        "expected_false": [],
        "dynamic_test": {
            "move": "e3d5",
            "expected_true": ["is_discovered_check", "is_check"],
            "expected_false": [],
        }
    },
    
    {
        "id": "GP031",
        "name": "抽将-将军同时捉子",
        "description": "将军的同时攻击对方无根子，验证is_double_attack_with_check",
        "fen": "4k4/9/9/9/4n4/9/4R4/9/9/4K4 w - - 0 1",
        "phase": "中局",
        "expected_true": [],
        "expected_false": [],
        "dynamic_test": {
            "move": "e3e5",
            "expected_true": ["is_double_attack_with_check"],
            "expected_false": [],
        }
    },
    
    # =========================================================================
    # 第四层：牵制串打层测试
    # =========================================================================
    
    {
        "id": "GP040",
        "name": "牵制-车牵制马",
        "description": "红车牵制黑马，马移动会导致黑将被将军",
        "fen": "4k4/9/9/4n4/9/9/9/4R4/9/4K4 w - - 0 1",
        "phase": "中局",
        "expected_true": ["is_pinned"],
        "expected_false": [],
        "expected_bindings": {
            "is_pinned": {
                "bind_pieces_must_contain": ["黑马", "红车"],
            }
        }
    },
    
    {
        "id": "GP041",
        "name": "炮串打-一炮打双",
        "description": "炮隔一个炮架同时攻击两个对方棋子",
        "fen": "4k4/9/9/4r4/4n4/4P4/4C4/9/9/4K4 w - - 0 1",
        "phase": "中局",
        "expected_true": ["is_cannon_double_attack"],
        "expected_false": [],
        "expected_bindings": {
            "is_cannon_double_attack": {
                "bind_pieces_must_contain": ["红炮"],
            }
        }
    },
    
    # =========================================================================
    # 第五层：标准杀法层测试
    # =========================================================================
    
    {
        "id": "GP050",
        "name": "杀法-马后炮",
        "description": "马和炮配合将死黑将，黑方走棋时被将死",
        "fen": "3kC1C2/4R4/9/2N5/9/9/9/9/9/4K4 b - - 0 1",
        "phase": "残局",
        "expected_true": ["is_check", "is_checkmate"],
        "expected_false": ["is_stalemate"],
    },
    
    {
        "id": "GP051",
        "name": "杀法-卧槽马",
        "description": "马盘踞在敌方九宫格外攻击位。黑方走棋时被将死",
        "fen": "3k5/4R4/2N5/9/9/9/9/9/9/4K4 b - - 0 1",
        "phase": "残局",
        "expected_true": ["is_check", "is_checkmate"],
        "expected_false": ["is_stalemate"],
    },
    
    {
        "id": "GP052",
        "name": "杀法-白脸将",
        "description": "利用双将不能对面规则。黑方走棋时被将死",
        "fen": "3RkR3/9/2N5/9/9/9/9/9/9/4K4 b - - 0 1",
        "phase": "残局",
        "expected_true": ["is_check", "is_checkmate"],
        "expected_false": ["is_stalemate"],
    },
    
    {
        "id": "GP053",
        "name": "杀法-重炮杀",
        "description": "一门炮以另一门炮为炮架将死黑将。黑方走棋时被将死",
        "fen": "3kC1C2/4R4/9/2N5/9/9/9/9/9/4K4 b - - 0 1",
        "phase": "残局",
        "expected_true": ["is_check", "is_checkmate"],
        "expected_false": ["is_stalemate"],
    },
    
    {
        "id": "GP054",
        "name": "杀法-海底捞月",
        "description": "车深入敌方底线将死黑将。黑方走棋时被将死",
        "fen": "3kRR3/9/9/2N5/9/9/9/9/9/4K4 b - - 0 1",
        "phase": "残局",
        "expected_true": ["is_check", "is_checkmate"],
        "expected_false": ["is_stalemate"],
    },
    
    {
        "id": "GP055",
        "name": "杀法-侧面虎",
        "description": "车与将同行，横向将死黑将。黑方走棋时被将死",
        "fen": "3kR1R2/3R5/3R5/9/9/9/9/9/9/4K4 b - - 0 1",
        "phase": "残局",
        "expected_true": ["is_check", "is_checkmate"],
        "expected_false": ["is_stalemate"],
    },
    
    {
        "id": "GP056",
        "name": "杀法-双车错",
        "description": "双车交替将军将死黑将。黑方走棋时被将死",
        "fen": "3kRR3/9/9/2N5/9/9/9/9/9/4K4 b - - 0 1",
        "phase": "残局",
        "expected_true": ["is_check", "is_checkmate"],
        "expected_false": ["is_stalemate"],
    },
    
    # =========================================================================
    # 第六层：子力状态层测试
    # =========================================================================
    
    {
        "id": "GP060",
        "name": "子无根-孤立棋子",
        "description": "没有任何己方棋子保护的棋子",
        "fen": "4k4/9/9/9/4n4/9/9/9/9/4K4 w - - 0 1",
        "phase": "残局",
        "expected_true": ["piece_is_unprotected"],
        "expected_false": [],
        "expected_bindings": {
            "piece_is_unprotected": {
                "bind_pieces_must_contain": ["黑马"],
            }
        }
    },
    
    {
        "id": "GP061",
        "name": "炮有架-炮有可用炮架",
        "description": "炮有可用的炮架（任意棋子）",
        "fen": "4k4/9/9/9/9/9/9/4P4/4C4/4K4 w - - 0 1",
        "phase": "残局",
        "expected_true": ["cannon_has_platform"],
        "expected_false": [],
        "expected_bindings": {
            "cannon_has_platform": {
                "bind_pieces_must_contain": ["红炮"],
            }
        }
    },
    
    # =========================================================================
    # 马腿遮挡测试
    # =========================================================================
    
    {
        "id": "GP070",
        "name": "马腿被别-单腿被别",
        "description": "马的一个方向马脚被棋子占据",
        "fen": "4k4/9/9/9/9/9/9/3NP4/9/4K4 w - - 0 1",
        "phase": "中局",
        "expected_true": ["horse_leg_blocked"],
        "expected_false": [],
        "expected_bindings": {
            "horse_leg_blocked": {
                "bind_pieces_must_contain": ["红马"],
            }
        }
    },
    
    {
        "id": "GP071",
        "name": "马腿被别-双腿被别",
        "description": "马的两个方向马脚被棋子占据",
        "fen": "4k4/9/9/9/9/9/3P5/3N5/4P4/4K4 w - - 0 1",
        "phase": "中局",
        "expected_true": ["horse_leg_blocked"],
        "expected_false": [],
        "expected_bindings": {
            "horse_leg_blocked": {
                "bind_pieces_must_contain": ["红马"],
            }
        }
    },
    
    # =========================================================================
    # 局面阶段测试
    # =========================================================================
    
    {
        "id": "GP080",
        "name": "阶段-开局",
        "description": "场上棋子总数 >= 28",
        "fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
        "phase": "开局",
        "expected_true": ["phase_opening"],
        "expected_false": ["phase_middlegame", "phase_endgame"],
    },
    
    {
        "id": "GP081",
        "name": "阶段-中局",
        "description": "场上棋子总数在 15-27 之间",
        "fen": "rnbakabnr/9/1c5c1/9/9/9/9/1C5C1/9/RNBAKABNR w - - 0 1",
        "phase": "中局",
        "expected_true": ["phase_middlegame"],
        "expected_false": ["phase_opening", "phase_endgame"],
    },
    
    {
        "id": "GP082",
        "name": "阶段-残局",
        "description": "场上棋子总数 <= 14",
        "fen": "4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1",
        "phase": "残局",
        "expected_true": ["phase_endgame"],
        "expected_false": ["phase_opening", "phase_middlegame"],
    },
    
    # =========================================================================
    # 将帅安全测试
    # =========================================================================
    
    {
        "id": "GP090",
        "name": "将帅危急-防守不足",
        "description": "将/帅周围防守子力严重不足，且存在敌方进攻威胁",
        "fen": "4k4/9/9/9/9/9/4R4/9/9/4K4 w - - 0 1",
        "phase": "残局",
        "expected_true": ["king_safety_critical"],
        "expected_false": [],
        "expected_bindings": {
            "king_safety_critical": {
                "bind_pieces_must_contain": ["黑将"],
            }
        }
    },
    
    # =========================================================================
    # 红黑视角测试
    # =========================================================================
    
    {
        "id": "GP100",
        "name": "红黑视角-黑方走棋",
        "description": "黑方走棋时的标签检测，验证红黑视角正确",
        "fen": "4k4/9/9/9/9/9/9/9/4R4/4K4 b - - 0 1",
        "phase": "残局",
        "expected_true": ["is_check"],
        "expected_false": ["is_checkmate", "is_stalemate"],
        "expected_bindings": {
            "is_check": {
                "bind_pieces_must_contain": ["黑将", "红车"],
            }
        }
    },
    
    {
        "id": "GP101",
        "name": "红黑视角-黑方攻无根",
        "description": "黑车攻击红方无根马，验证红黑视角正确",
        "fen": "4K3k/9/9/9/9/9/9/4N4/4r4/9 b - - 0 1",
        "phase": "中局",
        "expected_true": ["is_attack_unprotected"],
        "expected_false": [],
        "expected_bindings": {
            "is_attack_unprotected": {
                "bind_pieces_must_contain": ["黑车", "红马"],
            }
        }
    },
    
    # =========================================================================
    # 炮规则专项测试（最高频bug来源）
    # =========================================================================
    
    {
        "id": "GP110",
        "name": "炮规则-无炮架不能攻击",
        "description": "炮没有炮架时不能攻击远处棋子",
        "fen": "4k4/9/9/9/9/9/9/9/4C2n1/4K4 w - - 0 1",
        "phase": "残局",
        "expected_true": [],
        "expected_false": ["is_attack_unprotected"],
    },
    
    {
        "id": "GP111",
        "name": "炮规则-炮架在炮和目标之间",
        "description": "验证炮架必须在炮和目标之间",
        "fen": "4k4/9/9/9/9/9/4n4/4P4/4C4/4K4 w - - 0 1",
        "phase": "残局",
        "expected_true": ["is_attack_unprotected"],
        "expected_false": [],
        "expected_bindings": {
            "is_attack_unprotected": {
                "attacker_type": "炮",
                "target_type": "马",
            }
        }
    },
    
    {
        "id": "GP112",
        "name": "炮规则-炮架在目标外侧不算",
        "description": "炮架在目标外侧，炮不能攻击",
        "fen": "4k4/9/9/9/9/9/4P4/4n4/4C4/4K4 w - - 0 1",
        "phase": "残局",
        "expected_true": [],
        "expected_false": ["is_attack_unprotected"],
    },
    
    # =========================================================================
    # 有根无根专项测试
    # =========================================================================
    
    {
        "id": "GP120",
        "name": "有根子-被己方棋子保护",
        "description": "棋子被己方棋子保护，不应标记为无根",
        "fen": "4k4/4r4/9/9/9/9/9/4R4/4K4 w - - 0 1",
        "phase": "残局",
        "expected_true": [],
        "expected_false": ["piece_is_unprotected"],
    },
    
    {
        "id": "GP121",
        "name": "无根子-被对方棋子保护不算有根",
        "description": "被对方棋子保护的棋子仍是无根（对方可以吃掉）",
        "fen": "4k4/9/9/9/9/9/9/4n4/4R4/4K4 w - - 0 1",
        "phase": "残局",
        "expected_true": ["piece_is_unprotected"],
        "expected_false": [],
        "expected_bindings": {
            "piece_is_unprotected": {
                "bind_pieces_must_contain": ["黑马"],
            }
        }
    },
    
    # =========================================================================
    # 重炮阵型测试
    # =========================================================================
    
    {
        "id": "GP130",
        "name": "重炮阵型-两炮同行无阻隔",
        "description": "同色两门炮处于同一行，且两炮之间无任何棋子",
        "fen": "4k4/9/9/9/9/9/9/9/4CC3/4K4 w - - 0 1",
        "phase": "残局",
        "expected_true": ["cannon_battery"],
        "expected_false": [],
        "expected_bindings": {
            "cannon_battery": {
                "bind_pieces_must_contain": ["红炮"],
            }
        }
    },
    
    # =========================================================================
    # 有利兑换测试
    # =========================================================================
    
    {
        "id": "GP140",
        "name": "有利兑换-车吃马",
        "description": "车可以免费吃掉对方的马",
        "fen": "4k4/9/9/9/9/9/9/9/4n1R2/4K4 w - - 0 1",
        "phase": "残局",
        "expected_true": ["favorable_exchange"],
        "expected_false": [],
        "expected_bindings": {
            "favorable_exchange": {
                "bind_pieces_must_contain": ["红车", "黑马"],
            }
        }
    },
]


def get_golden_position_by_id(position_id: str) -> Optional[Dict[str, Any]]:
    """根据ID获取黄金局面"""
    for pos in GOLDEN_POSITIONS:
        if pos["id"] == position_id:
            return pos
    return None


def get_golden_positions_by_tag(tag_name: str) -> List[Dict[str, Any]]:
    """获取测试特定标签的所有黄金局面"""
    positions = []
    for pos in GOLDEN_POSITIONS:
        if tag_name in pos.get("expected_true", []):
            positions.append(pos)
        elif tag_name in pos.get("expected_false", []):
            positions.append(pos)
        dynamic_test = pos.get("dynamic_test", {})
        if tag_name in dynamic_test.get("expected_true", []):
            positions.append(pos)
        elif tag_name in dynamic_test.get("expected_false", []):
            positions.append(pos)
    return positions


def get_all_tag_names() -> set:
    """获取所有被测试的标签名称"""
    tags = set()
    for pos in GOLDEN_POSITIONS:
        tags.update(pos.get("expected_true", []))
        tags.update(pos.get("expected_false", []))
        dynamic_test = pos.get("dynamic_test", {})
        tags.update(dynamic_test.get("expected_true", []))
        tags.update(dynamic_test.get("expected_false", []))
    return tags


def print_coverage_report():
    """打印标签覆盖报告"""
    from core.rules.tactical_tags import ALL_TACTICAL_TAGS
    
    tested_tags = get_all_tag_names()
    all_tags = {tag.name for tag in ALL_TACTICAL_TAGS}
    
    covered = tested_tags & all_tags
    not_covered = all_tags - tested_tags
    
    print("=" * 60)
    print("黄金局面覆盖报告")
    print("=" * 60)
    print(f"总标签数: {len(all_tags)}")
    print(f"已覆盖标签数: {len(covered)}")
    print(f"覆盖率: {len(covered) / len(all_tags) * 100:.1f}%")
    print()
    
    if not_covered:
        print("未覆盖的标签:")
        for tag in sorted(not_covered):
            print(f"  - {tag}")
    else:
        print("所有标签都已覆盖！")


if __name__ == "__main__":
    print(f"黄金局面总数: {len(GOLDEN_POSITIONS)}")
    print(f"被测试的标签数: {len(get_all_tag_names())}")
    print()
    print_coverage_report()
