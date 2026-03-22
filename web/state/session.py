"""
会话状态管理

职责: 管理用户会话、模式切换、设置

文档依据: JOINT_REFACTOR_ARCHITECTURE.md 状态管理
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class ModeType(Enum):
    """模式类型"""
    PGN = "pgn"
    PLAY = "play"
    REVIEW = "review"


@dataclass
class SessionState:
    """
    会话状态

    字段:
        current_mode: 当前模式
        ai_difficulty: AI难度（1-10）
        ai_mode: AI模式（analysis/battle）
        audio_enabled: 音效开关
        audio_volume: 音量（0.0-1.0）
        animation_enabled: 动画开关
    """
    current_mode: ModeType = ModeType.PLAY
    ai_difficulty: int = 10
    ai_mode: str = "analysis"  # analysis | battle
    audio_enabled: bool = True
    audio_volume: float = 0.7
    animation_enabled: bool = True

    def switch_mode(self, mode: ModeType) -> None:
        """
        切换模式

        Args:
            mode: 目标模式
        """
        self.current_mode = mode

    def set_ai_difficulty(self, difficulty: int) -> None:
        """
        设置AI难度

        Args:
            difficulty: 难度等级（1-10）
        """
        self.ai_difficulty = max(1, min(10, difficulty))

    def set_ai_mode(self, mode: str) -> None:
        """
        设置AI模式

        Args:
            mode: AI模式（analysis/battle）
        """
        if mode in ["analysis", "battle"]:
            self.ai_mode = mode

    def toggle_audio(self) -> bool:
        """
        切换音效开关

        Returns:
            当前音效状态
        """
        self.audio_enabled = not self.audio_enabled
        return self.audio_enabled

    def set_audio_volume(self, volume: float) -> None:
        """
        设置音量

        Args:
            volume: 音量值（0.0-1.0）
        """
        self.audio_volume = max(0.0, min(1.0, volume))

    def toggle_animation(self) -> bool:
        """
        切换动画开关

        Returns:
            当前动画状态
        """
        self.animation_enabled = not self.animation_enabled
        return self.animation_enabled
