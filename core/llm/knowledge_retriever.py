"""
象棋知识库 - 张力导向检索

职责: 根据张力类型检索相关棋理原则
原则: 知识库不是用来"丰富输出"，而是参与假设的生成和验证

设计理念:
  - 每条原则来自经典棋书（橘中秘、梅花谱等）或公认棋理
  - 按张力类型 + 阶段 + 棋子组合多维索引
  - 原则包含适用条件和反例，防止LLM过度泛化

文档依据: docs/communication/GLM5_COACH_INTELLIGENCE_GUIDE.md
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Principle:
    """棋理原则"""
    content: str                    # 原则内容
    applies_when: str               # 适用条件
    counter_case: str = ""          # 反例/例外情况
    source: str = "经典棋理"         # 来源
    phase: str = ""                 # 适用阶段: opening/middlegame/endgame/all
    tags: List[str] = field(default_factory=list)  # 关联标签名

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "applies_when": self.applies_when,
            "counter_case": self.counter_case,
            "source": self.source,
            "phase": self.phase,
            "tags": self.tags,
        }


class ChessKnowledgeBase:
    """
    按张力类型组织的棋理知识库

    不是通用的 RAG，而是"张力导向检索"
    """

    # =========================================================================
    # 张力类型 → 对应的棋理原则（按张力分组，每组 6-10 条）
    # =========================================================================
    TENSION_PRINCIPLES = {
        # ── 子力 vs 攻势 ──────────────────────────────────────────────
        "material_vs_initiative": [
            Principle(
                content="多子一方应主动兑换，简化局面，消除对方攻势",
                applies_when="对方有攻势但己方子力占优时",
                counter_case="若对方攻势已形成直接将杀威胁，兑换可能来不及",
                source="《象棋中局研究》",
                phase="middlegame",
                tags=["favorable_exchange"],
            ),
            Principle(
                content="攻势方应保持局面复杂，避免简化",
                applies_when="己方子力处于劣势但有攻势时",
                counter_case="若自身防守也有严重漏洞，需先补救",
                source="《象棋谋略》",
                phase="middlegame",
                tags=["has_initiative"],
            ),
            Principle(
                content="子力优势需要时间兑现，攻势优势需要速度",
                applies_when="判断谁的计划更快时",
                source="《象棋战略》",
                phase="middlegame",
            ),
            Principle(
                content="有攻势的一方应该攻击，而不是防守——进攻是最好的防守",
                applies_when="有明确进攻线路时",
                counter_case="若进攻会导致自身防守崩溃，需先稳固",
                source="《橘中秘》",
                phase="middlegame",
                tags=["has_initiative"],
            ),
            Principle(
                content="少子方应首先考虑对攻，而非被动防守",
                applies_when="子力稍劣但对方有弱点时",
                source="《梅花谱》",
                phase="middlegame",
            ),
            Principle(
                content="一车换双（一车换马炮），在残局阶段通常亏损",
                applies_when="残局考虑子力交换时",
                counter_case="若马炮配合良好且对方将帅不安全，可能有利",
                source="《适情雅趣》",
                phase="endgame",
                tags=["favorable_exchange"],
            ),
            Principle(
                content="得子失先往往不如弃子争先——先手价值极高",
                applies_when="可以弃子夺取主动权时",
                source="《象棋基本战术》",
                phase="middlegame",
                tags=["has_initiative"],
            ),
        ],

        # ── 隐性失衡 ──────────────────────────────────────────────────
        "hidden_imbalance": [
            Principle(
                content="子力不协调往往比明显的子力劣势更危险",
                applies_when="引擎评分差异大但战术标签少时",
                counter_case="有时评分差异来自引擎的深层计算，人类难以即时判断",
                source="《象棋局面评估》",
                phase="all",
            ),
            Principle(
                content="位置优势会随时间转化为子力优势",
                applies_when="局面平稳但一方有明显位置优势时",
                source="《象棋战略》",
                phase="middlegame",
                tags=["has_space_advantage"],
            ),
            Principle(
                content="空间优势允许更灵活的子力调动，应激活消极棋子",
                applies_when="一方控制更多空间时",
                counter_case="空间过大可能导致子力分散，形成薄弱点",
                source="《象棋空间控制》",
                phase="middlegame",
                tags=["has_space_advantage", "has_active_pieces"],
            ),
            Principle(
                content="马炮价值随局势动态变化：开中局炮强于马（有架子），残局马强于炮（架子少）",
                applies_when="评估马炮交换是否合算时",
                source="经典棋理",
                phase="all",
            ),
            Principle(
                content="双相（象）完整时将帅安全系数大增，缺相则炮威力倍增",
                applies_when="评估防守方将帅安全时",
                source="《象棋残局大全》",
                phase="all",
                tags=["king_safety_good", "king_safety_critical"],
            ),
            Principle(
                content="车的活跃度是局面评估的第一要素——三步不出车，必定要输棋",
                applies_when="开局阶段车未出动时",
                counter_case="某些特殊布局可推迟出车，但需有明确理由",
                source="经典谚语",
                phase="opening",
                tags=["has_active_pieces"],
            ),
            Principle(
                content="子力协调比子力总价值更重要——分散的大子不如协同的小子",
                applies_when="进攻方子力分散在两翼时",
                source="《象棋配子艺术》",
                phase="middlegame",
                tags=["piece_coordination"],
            ),
        ],

        # ── 危机中有资源 ──────────────────────────────────────────────
        "crisis_with_resources": [
            Principle(
                content="被将时优先考虑反将或反攻，而非被动应将",
                applies_when="有反击机会时被将军",
                counter_case="若反击会导致更大损失，需谨慎",
                source="《象棋防守艺术》",
                phase="all",
                tags=["is_check"],
            ),
            Principle(
                content="无根子是战术组合的潜在目标——发现无根子就要想办法利用",
                applies_when="有无根子存在时",
                counter_case="有时无根子是诱饵陷阱",
                source="《象棋战术》",
                phase="all",
                tags=["piece_is_unprotected", "is_attack_unprotected"],
            ),
            Principle(
                content="活跃的子力可以弥补局部的薄弱",
                applies_when="子力活跃但存在薄弱点时",
                counter_case="若薄弱点是将帅本身，必须优先处理",
                source="《象棋攻防》",
                phase="middlegame",
                tags=["has_active_pieces"],
            ),
            Principle(
                content="逃跑时要带走威胁——退中有攻，是最高效的防守",
                applies_when="棋子被攻击需要撤退时",
                source="《象棋防守艺术》",
                phase="all",
                tags=["move_escapes_threat"],
            ),
            Principle(
                content="被牵制的棋子不是废棋——分析是否可以反牵制或用其他子解围",
                applies_when="有棋子被牵制时",
                source="《象棋战术组合》",
                phase="all",
                tags=["is_pinned"],
            ),
            Principle(
                content="在防守中寻找弃子解围的手段——弃子不意味着亏，化解危机才是目标",
                applies_when="局面被动但有弃子战术时",
                source="《梅花谱》",
                phase="middlegame",
                tags=["is_check", "king_safety_critical"],
            ),
            Principle(
                content="将帅危急时，防守棋子不能离开保护位——宁失子不失势",
                applies_when="将帅面临将杀威胁时",
                source="《橘中秘》",
                phase="all",
                tags=["king_safety_critical"],
            ),
        ],

        # ── 沉睡棋子 ──────────────────────────────────────────────────
        "sleeping_piece": [
            Principle(
                content="每步棋都应激活一个消极棋子，或改善其协调性",
                applies_when="存在明显消极棋子时",
                counter_case="有时消极棋子是防守的必要代价（如堵塞将门）",
                source="《象棋开局原理》",
                phase="opening",
                tags=["has_active_pieces"],
            ),
            Principle(
                content="车的活跃度决定局面的动态性——车要占领开放线和边线",
                applies_when="车处于消极位置时",
                source="《象棋中局战术》",
                phase="all",
                tags=["controls_open_file"],
            ),
            Principle(
                content="炮需要架子，没有架子的炮价值减半",
                applies_when="炮没有炮架时",
                counter_case="残局中炮可以借助对方棋子为架，灵活运用",
                source="《炮的用法》",
                phase="middlegame",
                tags=["cannon_has_platform"],
            ),
            Principle(
                content="马被蹩腿时要找机会疏通——马的价值在于灵活",
                applies_when="马脚被别无法跳出时",
                source="经典棋理",
                phase="all",
                tags=["horse_leg_blocked"],
            ),
            Principle(
                content="窝心马（占据将门中心的马）是大忌——阻塞将帅和士的出路",
                applies_when="马处于将帅宫中心时",
                source="经典棋理·炮镇窝心马",
                phase="middlegame",
            ),
            Principle(
                content="弃卒（兵）开路是常见的激活手段——不要舍不得兵",
                applies_when="兵碍事挡住己方大子时",
                source="《象棋弃子战术》",
                phase="opening",
            ),
        ],

        # ── 标签矛盾 ──────────────────────────────────────────────────
        "tag_contradiction": [
            Principle(
                content="主动权必须建立在安全的基础上——攻与守不可偏废",
                applies_when="同时有主动权标签和安全威胁标签时",
                source="《象棋攻防》",
                phase="all",
                tags=["has_initiative", "king_safety_critical"],
            ),
            Principle(
                content="虚假的主动权比没有主动权更危险——进攻无力反被反击",
                applies_when="进攻看似凌厉但无法构成实质威胁时",
                source="《象棋战略》",
                phase="middlegame",
            ),
            Principle(
                content="空间优势若无子力支撑则毫无意义——要把空间变成子力优势",
                applies_when="有空间优势但子力不活跃时",
                source="《象棋中局研究》",
                phase="middlegame",
                tags=["has_space_advantage", "has_active_pieces"],
            ),
            Principle(
                content="子力协同标签存在但缺乏攻击目标时，需要创造弱点",
                applies_when="子力协调好但无突破口时",
                source="《象棋战略》",
                phase="middlegame",
                tags=["piece_coordination"],
            ),
        ],

        # ── 阶段错配 ──────────────────────────────────────────────────
        "phase_mismatch": [
            Principle(
                content="开局阶段的意外子力损失需要改变策略——从优势战法转为实惠战法",
                applies_when="开局阶段子力严重失衡时",
                source="《象棋开局》",
                phase="opening",
            ),
            Principle(
                content="残局原则不适用于有大量棋子的局面——不要在中局过早简化",
                applies_when="阶段判断模糊时",
                source="《象棋阶段理论》",
                phase="all",
            ),
            Principle(
                content="进入残局前必须评估残局胜负——有些残局看似优势实则和棋",
                applies_when="考虑简化进入残局时",
                counter_case="若中局局势不利，简化也许是唯一选择",
                source="《象棋残局大全》",
                phase="middlegame",
                tags=["phase_endgame"],
            ),
            Principle(
                content="中局向残局转化时，车的价值最高——有车方通常占优",
                applies_when="中残局过渡阶段",
                source="经典棋理：有车压无车",
                phase="middlegame",
            ),
        ],

        # ── 攻杀相关 ──────────────────────────────────────────────────
        "attack_pattern": [
            Principle(
                content="马后炮是最经典的杀法——马控制将帅邻格，炮从远处将军",
                applies_when="马在对方将帅附近且有炮可配合时",
                source="《象棋杀法大全》",
                phase="all",
                tags=["checkmate_horse_back_cannon"],
            ),
            Principle(
                content="铁门栓杀法——车（或炮）控制将门，兵卒封锁退路",
                applies_when="对方将帅出宫无退路时",
                source="《象棋杀法大全》",
                phase="all",
                tags=["checkmate_iron_gate"],
            ),
            Principle(
                content="双车错杀——双车一左一右形成交叉将军，对方无处可逃",
                applies_when="双车配合进攻将帅时",
                source="《象棋杀法大全》",
                phase="all",
                tags=["checkmate_double_rook"],
            ),
            Principle(
                content="卧槽马最为致命——c9/g9位置的马控制将帅大半空间",
                applies_when="马可以占据卧槽位时",
                source="经典棋理",
                phase="all",
                tags=["checkmate_horse_corner"],
            ),
            Principle(
                content="白脸将（对面笑）——利用将帅不能对面的规则，形成绝杀",
                applies_when="双方将帅同列且中间可清空时",
                source="《象棋杀法大全》",
                phase="all",
                tags=["checkmate_bare_king", "kings_face_to_face"],
            ),
            Principle(
                content="重炮杀——两炮一前一后在同一条线上，前炮为后炮做架将军",
                applies_when="双炮在同一线上有机会形成重炮时",
                source="《象棋杀法大全》",
                phase="all",
                tags=["checkmate_double_cannon_battery", "cannon_battery"],
            ),
            Principle(
                content="海底捞月——车沉底将军，借将帅无法躲避的底线进行攻击",
                applies_when="车可以沉底且对方将帅在底线时",
                source="《象棋杀法大全》",
                phase="endgame",
                tags=["checkmate_sea_bottom_moon"],
            ),
            Principle(
                content="闪将（闪击）是最危险的战术——移开一子同时暴露另一子的攻击线",
                applies_when="有棋子可以通过移动暴露后方大子攻击线时",
                source="《象棋战术》",
                phase="all",
                tags=["is_discovered_check", "is_discovered_attack"],
            ),
            Principle(
                content="抽将得子——将军的同时移走的棋子攻击对方无根子，一举两得",
                applies_when="可以将军同时威胁其他棋子时",
                source="《象棋战术组合》",
                phase="all",
                tags=["is_double_attack_with_check"],
            ),
        ],

        # ── 开局原则 ──────────────────────────────────────────────────
        "opening_theory": [
            Principle(
                content="开局三步必出车——车是最强棋子，迟出车等于自废武功",
                applies_when="开局前三步",
                counter_case="某些特殊布局如飞相局可推迟一步",
                source="经典谚语",
                phase="opening",
            ),
            Principle(
                content="当头炮最为凶猛——炮二平五直指中路，逼对方应对",
                applies_when="红方首步选择时",
                source="《橘中秘》",
                phase="opening",
            ),
            Principle(
                content="屏风马是最稳健的应对中炮的方式——双马守中兵",
                applies_when="黑方面对中炮开局时",
                source="《梅花谱》",
                phase="opening",
            ),
            Principle(
                content="开局出子要讲究效率——不要同一个子反复移动",
                applies_when="开局阶段",
                source="《象棋布局学》",
                phase="opening",
                tags=["has_active_pieces"],
            ),
            Principle(
                content="中兵（卒）是战略要点——开局争夺中路是基本主题",
                applies_when="中兵受到威胁或考虑推进时",
                counter_case="有时弃中兵换取发展速度是可以的",
                source="《象棋开局原理》",
                phase="opening",
            ),
            Principle(
                content="飞相局稳健但被动——适合求稳和后发制人",
                applies_when="选择开局体系时",
                source="《象棋布局研究》",
                phase="opening",
            ),
            Principle(
                content="开局不宜过早出将（帅）——将帅暴露增加被攻击面",
                applies_when="开局阶段考虑将帅移动时",
                source="经典棋理",
                phase="opening",
                tags=["king_safety_good"],
            ),
        ],

        # ── 残局原则 ──────────────────────────────────────────────────
        "endgame_theory": [
            Principle(
                content="残局中不要轻易兑子——优势方棋子越少，越难赢",
                applies_when="残局阶段优势方考虑兑子时",
                counter_case="若兑换后剩余棋子形成必胜残局，则兑换有利",
                source="《象棋残局大全》",
                phase="endgame",
            ),
            Principle(
                content="单车不能胜士象全——除非有特殊将杀条件",
                applies_when="单车对双士双象残局时",
                source="经典残局定式",
                phase="endgame",
            ),
            Principle(
                content="马炮残局中，炮需要架子才能发挥——残局马一般优于炮",
                applies_when="残局中评估马炮价值时",
                counter_case="若对方有士象可做炮架，炮仍有大用",
                source="经典棋理",
                phase="endgame",
            ),
            Principle(
                content="过河卒顶半个车——过河兵卒在残局中威力巨大",
                applies_when="残局中兵卒已过河时",
                source="经典谚语",
                phase="endgame",
            ),
            Principle(
                content="残局中将帅应积极参与——将帅可以助攻或控制要点",
                applies_when="残局阶段将帅可以活动时",
                source="《象棋残局研究》",
                phase="endgame",
                tags=["kings_face_to_face"],
            ),
            Principle(
                content="三卒（兵）对四防士象可赢——三个过河卒的力量约等于一车",
                applies_when="己方有三个过河兵卒时",
                source="经典残局定式",
                phase="endgame",
            ),
        ],

        # ── 防守原则 ──────────────────────────────────────────────────
        "defense_pattern": [
            Principle(
                content="防守的最佳方式是消灭进攻的根源，而不是被动堵住",
                applies_when="面对对方进攻时",
                source="《象棋防守艺术》",
                phase="all",
            ),
            Principle(
                content="士象不能轻动——士象是将帅的贴身保镖，离开即暴露弱点",
                applies_when="考虑移动士象时",
                counter_case="某些进攻中支士可以配合炮做架",
                source="《象棋基本功》",
                phase="all",
                tags=["king_safety_good", "king_safety_critical"],
            ),
            Principle(
                content="失一象（相）则炮攻倍增——士象完整是安全的基础",
                applies_when="象被吃或考虑弃象时",
                source="经典棋理",
                phase="all",
            ),
            Principle(
                content="防守方应选择简化局面——兑子减少对方进攻资源",
                applies_when="防守方局势不利时",
                counter_case="若简化后残局不利，避免简化",
                source="《象棋攻防》",
                phase="middlegame",
            ),
            Principle(
                content="炮镇中路是最有效的防守之一——一炮守两翼",
                applies_when="中路空虚需要防守时",
                source="经典棋理",
                phase="middlegame",
                tags=["controls_open_file"],
            ),
        ],

        # ── 子力配合 ──────────────────────────────────────────────────
        "piece_coordination": [
            Principle(
                content="车马冷着（配合）——车控制线，马跳入对方阵地，威力极大",
                applies_when="车马配合进攻时",
                source="《象棋攻杀技巧》",
                phase="middlegame",
                tags=["piece_coordination"],
            ),
            Principle(
                content="车炮配合——车提供架子，炮远程打击，是最常见的攻杀组合",
                applies_when="车炮在同一线上配合时",
                source="《象棋攻杀技巧》",
                phase="all",
                tags=["cannon_has_platform", "piece_coordination"],
            ),
            Principle(
                content="马炮配合——马控近，炮控远，互补性极强",
                applies_when="马炮配合进攻将帅时",
                source="经典棋理",
                phase="all",
                tags=["piece_coordination"],
            ),
            Principle(
                content="连环马是安全的马阵——两马互保，难以被攻破",
                applies_when="两马可以形成互保时",
                counter_case="兵卒加车可以破连环马",
                source="经典棋理",
                phase="middlegame",
            ),
            Principle(
                content="空头炮直对将帅是致命威胁——对方不敢在炮前放子为架",
                applies_when="炮直线对准对方将帅无遮挡时",
                source="经典棋理：空心炮",
                phase="middlegame",
                tags=["cannon_battery"],
            ),
        ],
    }

    # =========================================================================
    # 通用棋理原则（与特定张力无关，任何局面可用）
    # =========================================================================
    GENERAL_PRINCIPLES = [
        Principle(
            content="将帅安全是第一位的——任何进攻都不能以自身安全为代价",
            applies_when="任何局面",
            source="《象棋基本原理》",
            phase="all",
            tags=["king_safety_good", "king_safety_critical"],
        ),
        Principle(
            content="先手是宝贵的——不要轻易放弃先手权",
            applies_when="握有先手时",
            counter_case="有时弃先争先更重要——弃小先争大先",
            source="《象棋先手理论》",
            phase="all",
            tags=["has_initiative"],
        ),
        Principle(
            content="控制中路是战略优势——中路是棋盘的脊梁",
            applies_when="中路控制权争夺时",
            counter_case="侧翼进攻可能绕过中路，不必执着于中路",
            source="《象棋中路控制》",
            phase="all",
        ),
        Principle(
            content="子力发展优于子力多少——出动比吃子更重要",
            applies_when="开局有吃子机会但会延误出子时",
            source="《象棋布局原理》",
            phase="opening",
            tags=["has_active_pieces"],
        ),
        Principle(
            content="看清对手的意图再走棋——每步棋都要思考对方上一步的目的",
            applies_when="任何局面",
            source="《象棋思考方法》",
            phase="all",
        ),
        Principle(
            content="不动无事棋——每步棋都要有目的，要么进攻，要么防守，要么改善",
            applies_when="选择走法时",
            source="经典棋理",
            phase="all",
        ),
        Principle(
            content="局面越复杂越应该保持冷静——计算准确比走得快更重要",
            applies_when="局面复杂多变时",
            source="《象棋心理学》",
            phase="all",
        ),
        Principle(
            content="吃子要看后果——不要被白送子迷惑，可能是陷阱",
            applies_when="对方送子时",
            source="经典棋理",
            phase="all",
            tags=["move_is_capture"],
        ),
    ]

    # 阶段名称映射（中文 → 英文）
    _PHASE_MAP = {
        "开局": "opening", "布局": "opening",
        "中局": "middlegame", "中盘": "middlegame",
        "残局": "endgame", "收官": "endgame",
    }

    def _normalize_phase(self, phase: str) -> str:
        """将中文阶段名统一为英文"""
        return self._PHASE_MAP.get(phase, phase)

    def query_for_tension(self, tension_type: str, phase: str = "中局") -> List[Principle]:
        """
        根据张力类型检索相关原则，按阶段过滤

        Args:
            tension_type: 张力类型
            phase: 局面阶段（中英文均可）

        Returns:
            相关原则列表（阶段匹配的优先）
        """
        principles = self.TENSION_PRINCIPLES.get(tension_type, [])
        if not principles:
            return []

        norm = self._normalize_phase(phase)
        # 阶段完全匹配或适用于 all 的排在前面
        matched = [p for p in principles if p.phase in (norm, "all", "")]
        others = [p for p in principles if p not in matched]
        return matched + others

    def query_by_tags(self, tags: List[str], phase: str = "") -> List[Principle]:
        """
        根据标签检索所有张力类型中匹配的原则

        Args:
            tags: 需要匹配的标签列表
            phase: 可选阶段筛选

        Returns:
            标签有交集的原则列表（去重）
        """
        tag_set = set(tags)
        norm = self._normalize_phase(phase) if phase else ""
        results: List[Principle] = []
        seen_content = set()

        for _cat, principles in self.TENSION_PRINCIPLES.items():
            for p in principles:
                if p.content in seen_content:
                    continue
                if not p.tags or not tag_set.intersection(p.tags):
                    continue
                if norm and p.phase not in (norm, "all", ""):
                    continue
                results.append(p)
                seen_content.add(p.content)

        # 通用原则也检查
        for p in self.GENERAL_PRINCIPLES:
            if p.content in seen_content:
                continue
            if p.tags and tag_set.intersection(p.tags):
                if not norm or p.phase in (norm, "all", ""):
                    results.append(p)
                    seen_content.add(p.content)

        return results

    def query_general_principles(self, count: int = 5) -> List[Principle]:
        """
        获取通用原则

        Args:
            count: 返回数量

        Returns:
            通用原则列表
        """
        return self.GENERAL_PRINCIPLES[:count]

    def get_principles_for_prompt(self, tension_type: str, phase: str = "中局") -> str:
        """
        获取用于Prompt的原则文本（最多5条）

        Args:
            tension_type: 张力类型
            phase: 局面阶段

        Returns:
            格式化的原则文本
        """
        principles = self.query_for_tension(tension_type, phase)

        if not principles:
            return ""

        lines = ["【相关棋理原则】"]
        for i, p in enumerate(principles[:5], 1):
            lines.append(f"{i}. {p.content}")
            lines.append(f"   适用：{p.applies_when}")
            if p.counter_case:
                lines.append(f"   例外：{p.counter_case}")
            if p.source:
                lines.append(f"   出处：{p.source}")

        return "\n".join(lines)


def get_knowledge_base() -> ChessKnowledgeBase:
    """获取知识库实例"""
    return ChessKnowledgeBase()


def query_principles_for_tension(tension_type: str, phase: str = "中局") -> List[Dict[str, Any]]:
    """
    便捷函数：根据张力类型查询原则

    Args:
        tension_type: 张力类型
        phase: 局面阶段

    Returns:
        原则字典列表
    """
    kb = ChessKnowledgeBase()
    principles = kb.query_for_tension(tension_type, phase)
    return [p.to_dict() for p in principles]


def get_principles_prompt(tension_type: str, phase: str = "中局") -> str:
    """
    便捷函数：获取用于Prompt的原则文本

    Args:
        tension_type: 张力类型
        phase: 局面阶段

    Returns:
        格式化的原则文本
    """
    kb = ChessKnowledgeBase()
    return kb.get_principles_for_prompt(tension_type, phase)
