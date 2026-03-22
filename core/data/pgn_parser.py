"""
PGN解析器
将19万局PGN解析为FEN局面+走子序列+胜负标签
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Iterator, Dict, Any
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PositionRecord:
    """单局面记录"""
    fen: str                            # 局面FEN
    move_number: int                    # 回合数
    side_to_move: str                   # 行棋方 ("red"/"black")
    last_move: Optional[str] = None     # 上一步走法
    
    def __repr__(self):
        return f"PositionRecord(move={self.move_number}, side={self.side_to_move})"


@dataclass
class GameRecord:
    """单局游戏记录"""
    game_id: str                        # 对局ID
    event: Optional[str] = None         # 赛事
    site: Optional[str] = None          # 地点
    date: Optional[str] = None          # 日期
    round: Optional[str] = None         # 轮次
    red_player: Optional[str] = None    # 红方
    black_player: Optional[str] = None  # 黑方
    result: Optional[str] = None        # 结果 ("1-0", "0-1", "1/2-1/2", "*")
    moves: List[str] = field(default_factory=list)           # 走法列表
    positions: List[PositionRecord] = field(default_factory=list)  # 局面列表
    
    def __repr__(self):
        return f"GameRecord({self.red_player} vs {self.black_player}, {len(self.moves)} moves)"
    
    @property
    def winner(self) -> Optional[str]:
        """获取胜者"""
        if self.result == "1-0":
            return "red"
        elif self.result == "0-1":
            return "black"
        else:
            return None  # 和棋或未知


class PGNParser:
    """
    PGN解析器
    
    支持中国象棋PGN格式，解析赛事信息、玩家、走法和局面
    """
    
    # 初始FEN（中国象棋标准起始局面）
    INITIAL_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
    
    def __init__(self):
        self.games: List[GameRecord] = []
    
    def parse_file(self, filepath: Path) -> List[GameRecord]:
        """
        解析PGN文件
        
        Args:
            filepath: PGN文件路径
            
        Returns:
            List[GameRecord]: 解析出的对局列表
        """
        logger.info(f"解析PGN文件: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        games = self.parse_content(content)
        logger.info(f"成功解析 {len(games)} 局对局")
        return games
    
    def parse_content(self, content: str) -> List[GameRecord]:
        """
        解析PGN内容
        
        Args:
            content: PGN文件内容
            
        Returns:
            List[GameRecord]: 解析出的对局列表
        """
        games = []
        
        # 分割多个对局（以[Event开头）
        game_blocks = re.split(r'\n\s*\n(?=\[Event)', content)
        
        for i, block in enumerate(game_blocks):
            block = block.strip()
            if not block or not block.startswith('['):
                continue
            
            try:
                game = self._parse_game_block(block, i)
                if game and len(game.moves) > 0:
                    games.append(game)
            except Exception as e:
                logger.warning(f"解析第 {i+1} 局失败: {e}")
                continue
        
        return games
    
    def _parse_game_block(self, block: str, index: int) -> Optional[GameRecord]:
        """解析单个对局块"""
        game = GameRecord(game_id=f"game_{index}")
        
        # 解析标签部分
        tag_pattern = r'\[(\w+)\s+"([^"]*)"\]'
        tags = dict(re.findall(tag_pattern, block))
        
        game.event = tags.get('Event')
        game.site = tags.get('Site')
        game.date = tags.get('Date')
        game.round = tags.get('Round')
        game.red_player = tags.get('Red') or tags.get('White')
        game.black_player = tags.get('Black')
        game.result = tags.get('Result')
        
        # 提取走法部分（标签之后的内容）
        moves_start = block.find(']') + 1
        moves_text = block[moves_start:].strip()
        
        # 移除注释和变着
        moves_text = self._clean_moves_text(moves_text)
        
        # 解析走法
        game.moves = self._parse_moves(moves_text)
        
        # 生成局面序列
        game.positions = self._generate_positions(game.moves)
        
        return game
    
    def _clean_moves_text(self, text: str) -> str:
        """清理走法文本，移除注释和变着"""
        # 移除注释 { ... }
        text = re.sub(r'\{[^}]*\}', '', text)
        # 移除变着 ( ... )
        text = re.sub(r'\([^)]*\)', '', text)
        # 移除 $数字 注解
        text = re.sub(r'\$\d+', '', text)
        # 移除结果标记
        text = re.sub(r'1-0|0-1|1/2-1/2|\*', '', text)
        # 清理多余空白
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _parse_moves(self, moves_text: str) -> List[str]:
        """解析走法列表"""
        moves = []
        
        # 分割走法（支持多种格式）
        # 格式1: 1. 炮二平五 马8进7
        # 格式2: 1.炮二平五 马8进7
        tokens = moves_text.split()
        
        for token in tokens:
            # 跳过回合数标记（如 "1.", "2."）
            if re.match(r'^\d+\.$', token):
                continue
            # 跳过空token
            if not token:
                continue
            # 只保留中文字符和数字（中国象棋走法）
            if re.match(r'^[车马炮兵仕相帅将士卒象马炮一二三四五六七八九123456789平进退上下]+$',
                       token):
                moves.append(token)
        
        return moves
    
    def _generate_positions(self, moves: List[str]) -> List[PositionRecord]:
        """
        根据走法序列生成局面列表
        
        注意：这里使用简化实现，实际应该使用象棋规则引擎来应用走法
        """
        positions = []
        
        # 添加初始局面
        positions.append(PositionRecord(
            fen=self.INITIAL_FEN,
            move_number=0,
            side_to_move="red",
            last_move=None
        ))
        
        # TODO: 使用规则引擎应用走法，生成每个局面的FEN
        # 这里暂时只记录走法，FEN需要通过引擎计算
        
        return positions
    
    def parse_move(self, move_text: str) -> Optional[Dict[str, Any]]:
        """
        解析单个走法文本
        
        Args:
            move_text: 走法文本，如 "炮二平五", "马8进7"
            
        Returns:
            Dict: 解析结果，包含piece, from_file, to_file等信息
        """
        # 中国象棋走法格式解析
        # 完整格式: [棋子][原位置][动作][目标位置]
        # 示例: 炮二平五, 马8进7, 车1进1
        
        pattern = r'([车马炮兵仕相帅将士卒象马炮])([一二三四五六七八九123456789])([平进退上下])([一二三四五六七八九123456789]?)'
        match = re.match(pattern, move_text)
        
        if not match:
            return None
        
        piece = match.group(1)
        from_pos = match.group(2)
        action = match.group(3)
        to_pos = match.group(4)
        
        # 转换中文数字
        chinese_nums = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
                       '六': 6, '七': 7, '八': 8, '九': 9}
        
        if from_pos in chinese_nums:
            from_pos = str(chinese_nums[from_pos])
        if to_pos in chinese_nums:
            to_pos = str(chinese_nums[to_pos])
        
        return {
            'piece': piece,
            'from_pos': from_pos,
            'action': action,
            'to_pos': to_pos,
            'raw': move_text
        }


def parse_all_pgn_files(data_dir: Path) -> List[GameRecord]:
    """
    解析目录下所有PGN文件
    
    Args:
        data_dir: 数据目录
        
    Returns:
        List[GameRecord]: 所有对局记录
    """
    parser = PGNParser()
    all_games = []
    
    pgn_files = list(data_dir.glob("*.pgn*"))  # 支持 .pgn 和 .pgns
    logger.info(f"找到 {len(pgn_files)} 个PGN文件")
    
    for pgn_file in pgn_files:
        try:
            games = parser.parse_file(pgn_file)
            all_games.extend(games)
            logger.info(f"  {pgn_file.name}: {len(games)} 局")
        except Exception as e:
            logger.error(f"解析 {pgn_file} 失败: {e}")
    
    logger.info(f"总计: {len(all_games)} 局对局")
    return all_games


if __name__ == "__main__":
    # 测试解析
    data_dir = Path("data/init_data")
    games = parse_all_pgn_files(data_dir)
    
    if games:
        print(f"\n示例对局:")
        game = games[0]
        print(f"  赛事: {game.event}")
        print(f"  红方: {game.red_player}")
        print(f"  黑方: {game.black_player}")
        print(f"  结果: {game.result}")
        print(f"  走法数: {len(game.moves)}")
        print(f"  前10步: {game.moves[:10]}")
