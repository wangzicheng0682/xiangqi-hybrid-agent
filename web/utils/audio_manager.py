"""
音效管理器 - 商业级沉浸体验

用途：管理走棋音效、将军音效、胜利失败音效
"""

import os
from typing import Dict, Optional


class AudioManager:
    """
    音效管理器 - 天天象棋级别音效系统
    """

    def __init__(self):
        self.sounds: Dict[str, dict] = {}
        self.enabled: bool = True
        self.volume: float = 0.7
        self.current_music: Optional[str] = None

    def load_sound(self, sound_path: str) -> dict:
        """
        加载音效文件（Gradio Audio支持）

        Args:
            sound_path: 音效文件路径

        Returns:
            音效信息字典
        """
        if not os.path.exists(sound_path):
            return None

        return {
            'path': sound_path,
            'name': os.path.basename(sound_path),
            'type': 'sfx'
        }

    def load_sounds(self):
        """
        加载所有音效文件

        音效文件：
        - assets/sounds/move_车.mp3
        - assets/sounds/move_马.mp3
        - assets/sounds/move_炮.mp3
        - assets/sounds/move_卒.mp3
        - assets/sounds/move_相象.mp3
        - assets/sounds/move_士.mp3
        - assets/sounds/move_帅.mp3
        - assets/sounds/move_将.mp3
        - assets/sounds/capture.mp3
        - assets/sounds/check.mp3
        - assets/sounds/win.mp3
        - assets/sounds/lose.mp3
        - assets/sounds/click.mp3
        - assets/sounds/notification.mp3
        """
        # 走棋音效（不同棋子不同声音）
        self.sounds['move'] = [
            {'name': '车', 'path': 'assets/sounds/move_车.mp3', 'type': 'move'},
            {'name': '马', 'path': 'assets/sounds/move_马.mp3', 'type': 'move'},
            {'name': '炮', 'path': 'assets/sounds/move_炮.mp3', 'type': 'move'},
            {'name': '卒', 'path': 'assets/sounds/move_卒.mp3', 'type': 'move'},
            {'name': '相象', 'path': 'assets/sounds/move_相象.mp3', 'type': 'move'},
            {'name': '士', 'path': 'assets/sounds/move_士.mp3', 'type': 'move'},
            {'name': '帅', 'path': 'assets/sounds/move_帅.mp3', 'type': 'move'},
            {'name': '将', 'path': 'assets/sounds/move_将.mp3', 'type': 'move'},
        ]

        # 特殊音效
        self.sounds['special'] = {
            'check': self.load_sound('assets/sounds/check.mp3'),
            'capture': self.load_sound('assets/sounds/capture.mp3'),
            'win': self.load_sound('assets/sounds/win.mp3'),
            'lose': self.load_sound('assets/sounds/lose.mp3'),
        }

        # UI音效
        self.sounds['ui'] = {
            'click': self.load_sound('assets/sounds/click.mp3'),
            'notification': self.load_sound('assets/sounds/notification.mp3'),
        }

    def play_move_sound(self, piece_type: str):
        """
        播放走棋音效

        Args:
            piece_type: 棋子类型（R, N, B, A, K, C, P）
        """
        if not self.enabled:
            return

        # 转换为中文棋子名
        piece_map = {
            'R': '车', 'r': '車',
            'N': '马', 'n': '馬',
            'B': '相', 'b': '象',
            'A': '仕', 'a': '士',
            'K': '帅', 'k': '将',
            'C': '炮', 'c': '砲',
            'P': '兵', 'p': '卒',
        }

        piece_name = piece_map.get(piece_type, '车')

        # 查找对应音效
        for sound in self.sounds['move']:
            if sound['name'] in piece_name:
                print(f"播放走棋音效: {sound['name']}")
                # 在Gradio中实际使用时，会播放音频文件
                return sound['path']

    def play_check_sound(self):
        """
        播放将军音效
        """
        if not self.enabled:
            return

        check_sound = self.sounds['special']['check']
        if check_sound:
            print(f"播放将军音效")
            return check_sound['path']

    def play_capture_sound(self):
        """
        播放吃子音效
        """
        if not self.enabled:
            return

        capture_sound = self.sounds['special']['capture']
        if capture_sound:
            print(f"播放吃子音效")
            return capture_sound['path']

    def play_win_sound(self):
        """
        播放胜利音效
        """
        if not self.enabled:
            return

        win_sound = self.sounds['special']['win']
        if win_sound:
            print(f"播放胜利音效")
            return win_sound['path']

    def play_lose_sound(self):
        """
        播放失败音效
        """
        if not self.enabled:
            return

        lose_sound = self.sounds['special']['lose']
        if lose_sound:
            print(f"播放失败音效")
            return lose_sound['path']

    def play_ui_sound(self, sound_type: str = 'click'):
        """
        播放UI音效

        Args:
            sound_type: 音效类型
        """
        if not self.enabled:
            return

        if sound_type in self.sounds['ui']:
            sound = self.sounds['ui'][sound_type]
            if sound:
                print(f"播放UI音效: {sound_type}")
                return sound['path']

    def set_volume(self, volume: float):
        """
        设置音量（0.0-1.0）

        Args:
            volume: 音量值
        """
        self.volume = max(0.0, min(1.0, volume))

    def toggle_sound(self):
        """
        切换音效开关

        Returns:
            当前音效状态
        """
        self.enabled = not self.enabled
        print(f"音效已{'开启' if self.enabled else '关闭'}")
        return self.enabled

    def get_volume(self) -> float:
        """
        获取当前音量

        Returns:
            音量值
        """
        return self.volume

    def is_enabled(self) -> bool:
        """
        检查音效是否启用

        Returns:
            音效状态
        """
        return self.enabled


# 全局音效管理器实例
audio_manager = AudioManager()
