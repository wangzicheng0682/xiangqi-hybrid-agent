"""
音效系统 - 商业级专业音效

职责: 音效加载、播放、音量控制

文档依据: JOINT_REFACTOR_ARCHITECTURE.md 音效系统

Phase 2完整实现:
- 走棋音效（不同棋子不同声音）
- 吃子音效
- 将军音效
- 胜利/失败音效
- UI音效（点击、通知）
- 音量控制
- 音效开关
"""

import os
from typing import Dict, Optional, List
from dataclasses import dataclass


@dataclass
class SoundEffect:
    """
    音效数据类

    字段:
        name: 音效名称
        path: 音效文件路径
        type: 音效类型（move/special/ui）
    """
    name: str
    path: str
    type: str


class AudioSystem:
    """
    音效系统

    管理所有音效的加载和播放
    """

    # 棋子类型与中文映射
    PIECE_NAMES = {
        'R': '车', 'r': '車',
        'N': '马', 'n': '馬',
        'B': '相', 'b': '象',
        'A': '仕', 'a': '士',
        'K': '帅', 'k': '将',
        'C': '炮', 'c': '砲',
        'P': '兵', 'p': '卒',
    }

    def __init__(self, sounds_dir: str = "assets/sounds"):
        """
        初始化音效系统

        Args:
            sounds_dir: 音效文件目录
        """
        self.sounds_dir = sounds_dir
        self.sounds: Dict[str, SoundEffect] = {}
        self.enabled: bool = True
        self.volume: float = 0.7
        self.current_music: Optional[str] = None

        # 加载音效
        self.load_sounds()

    def load_sounds(self) -> None:
        """
        加载所有音效文件

        音效文件结构:
        assets/sounds/
        ├── move_车.mp3
        ├── move_马.mp3
        ├── move_炮.mp3
        ├── move_卒.mp3
        ├── move_相象.mp3
        ├── move_士.mp3
        ├── move_帅.mp3
        ├── move_将.mp3
        ├── capture.mp3
        ├── check.mp3
        ├── win.mp3
        ├── lose.mp3
        ├── click.mp3
        └── notification.mp3
        """
        # 走棋音效（不同棋子不同声音）
        move_sounds = [
            '车', '马', '炮', '卒', '相象', '士', '帅', '将'
        ]

        for piece_name in move_sounds:
            sound_path = os.path.join(self.sounds_dir, f"move_{piece_name}.mp3")
            if os.path.exists(sound_path):
                self.sounds[f"move_{piece_name}"] = SoundEffect(
                    name=piece_name,
                    path=sound_path,
                    type="move"
                )
            else:
                # 如果找不到特定棋子音效，使用通用走棋音效
                generic_path = os.path.join(self.sounds_dir, "move_generic.mp3")
                if os.path.exists(generic_path):
                    self.sounds[f"move_{piece_name}"] = SoundEffect(
                        name=piece_name,
                        path=generic_path,
                        type="move"
                    )

        # 特殊音效
        special_sounds = {
            'capture': '吃子',
            'check': '将军',
            'win': '胜利',
            'lose': '失败',
        }

        for sound_key, sound_name in special_sounds.items():
            sound_path = os.path.join(self.sounds_dir, f"{sound_key}.mp3")
            if os.path.exists(sound_path):
                self.sounds[sound_key] = SoundEffect(
                    name=sound_name,
                    path=sound_path,
                    type="special"
                )

        # UI音效
        ui_sounds = {
            'click': '点击',
            'notification': '通知',
        }

        for sound_key, sound_name in ui_sounds.items():
            sound_path = os.path.join(self.sounds_dir, f"{sound_key}.mp3")
            if os.path.exists(sound_path):
                self.sounds[sound_key] = SoundEffect(
                    name=sound_name,
                    path=sound_path,
                    type="ui"
                )

    def play_move_sound(self, piece_type: str) -> Optional[str]:
        """
        播放走棋音效

        Args:
            piece_type: 棋子类型（R, N, B, A, K, C, P）

        Returns:
            音效文件路径，如果未找到返回None
        """
        if not self.enabled:
            return None

        # 转换为中文棋子名
        piece_name = self.PIECE_NAMES.get(piece_type, '')

        # 查找对应音效
        sound_key = f"move_{piece_name}"
        sound = self.sounds.get(sound_key)

        if sound and os.path.exists(sound.path):
            print(f"🔊 播放走棋音效: {sound.name}")
            # 在实际应用中，这里会使用Audio HTML元素播放
            # 返回路径供前端使用
            return self._apply_volume(sound.path)

        return None

    def play_capture_sound(self) -> Optional[str]:
        """
        播放吃子音效

        Returns:
            音效文件路径，如果未找到返回None
        """
        if not self.enabled:
            return None

        sound = self.sounds.get('capture')
        if sound and os.path.exists(sound.path):
            print(f"🔊 播放吃子音效")
            return self._apply_volume(sound.path)

        return None

    def play_check_sound(self) -> Optional[str]:
        """
        播放将军音效

        Returns:
            音效文件路径，如果未找到返回None
        """
        if not self.enabled:
            return None

        sound = self.sounds.get('check')
        if sound and os.path.exists(sound.path):
            print(f"🔊 播放将军音效")
            return self._apply_volume(sound.path)

        return None

    def play_win_sound(self) -> Optional[str]:
        """
        播放胜利音效

        Returns:
            音效文件路径，如果未找到返回None
        """
        if not self.enabled:
            return None

        sound = self.sounds.get('win')
        if sound and os.path.exists(sound.path):
            print(f"🔊 播放胜利音效")
            return self._apply_volume(sound.path)

        return None

    def play_lose_sound(self) -> Optional[str]:
        """
        播放失败音效

        Returns:
            音效文件路径，如果未找到返回None
        """
        if not self.enabled:
            return None

        sound = self.sounds.get('lose')
        if sound and os.path.exists(sound.path):
            print(f"🔊 播放失败音效")
            return self._apply_volume(sound.path)

        return None

    def play_ui_sound(self, sound_type: str = 'click') -> Optional[str]:
        """
        播放UI音效

        Args:
            sound_type: 音效类型（click/notification）

        Returns:
            音效文件路径，如果未找到返回None
        """
        if not self.enabled:
            return None

        sound = self.sounds.get(sound_type)
        if sound and os.path.exists(sound.path):
            print(f"🔊 播放UI音效: {sound.name}")
            return self._apply_volume(sound.path)

        return None

    def set_volume(self, volume: float) -> None:
        """
        设置音量

        Args:
            volume: 音量值（0.0-1.0）
        """
        self.volume = max(0.0, min(1.0, volume))
        print(f"🔊 音量设置为: {self.volume:.1f}")

    def toggle_sound(self) -> bool:
        """
        切换音效开关

        Returns:
            当前音效状态
        """
        self.enabled = not self.enabled
        print(f"🔊 音效已{'开启' if self.enabled else '关闭'}")
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

    def _apply_volume(self, sound_path: str) -> str:
        """
        应用音量到音效路径

        Args:
            sound_path: 原始音效路径

        Returns:
            带音量参数的路径（用于Audio元素）
        """
        # 返回格式化的路径，包含音量参数
        # 例如: "path/to/sound.mp3?volume=0.7"
        # 注意：实际应用中可能需要使用Web Audio API来控制音量
        return f"{sound_path}?volume={self.volume}"

    def get_available_sounds(self) -> Dict[str, List[str]]:
        """
        获取可用音效列表

        Returns:
            音效分类字典
        """
        sounds_by_type = {
            'move': [],
            'special': [],
            'ui': []
        }

        for sound_key, sound in self.sounds.items():
            sounds_by_type[sound.type].append(sound.name)

        return sounds_by_type

    def preload_sounds(self) -> List[str]:
        """
        预加载所有音效（返回HTML代码）

        Returns:
            Audio元素HTML列表
        """
        audio_elements = []

        for sound_key, sound in self.sounds.items():
            if os.path.exists(sound.path):
                audio_elements.append(f"""
                <audio id="sound-{sound_key}" preload="auto" src="{self._apply_volume(sound.path)}"></audio>
                """)

        return audio_elements


# 全局音效系统实例
audio_system = AudioSystem()


def play_move_audio(piece_type: str) -> Optional[str]:
    """
    播放走棋音效（便捷函数）

    Args:
        piece_type: 棋子类型

    Returns:
        音效文件路径
    """
    return audio_system.play_move_sound(piece_type)


def play_capture_audio() -> Optional[str]:
    """
    播放吃子音效（便捷函数）

    Returns:
        音效文件路径
    """
    return audio_system.play_capture_sound()


def play_check_audio() -> Optional[str]:
    """
    播放将军音效（便捷函数）

    Returns:
        音效文件路径
    """
    return audio_system.play_check_audio()


def play_win_audio() -> Optional[str]:
    """
    播放胜利音效（便捷函数）

    Returns:
        音效文件路径
    """
    return audio_system.play_win_sound()


def toggle_audio() -> bool:
    """
    切换音效开关（便捷函数）

    Returns:
        当前音效状态
    """
    return audio_system.toggle_sound()


def set_audio_volume(volume: float) -> None:
    """
    设置音量（便捷函数）

    Args:
        volume: 音量值
    """
    audio_system.set_volume(volume)


def get_preloaded_audio_html() -> List[str]:
    """
    获取预加载音效HTML（便捷函数）

    Returns:
        Audio元素HTML列表
    """
    return audio_system.preload_sounds()
