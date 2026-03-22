"""
配置加载工具
统一加载和管理配置文件
"""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)


class ConfigLoader:
    """配置加载器"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        初始化配置加载器
        
        Args:
            config_dir: 配置目录路径（默认使用项目configs目录）
        """
        if config_dir is None:
            config_dir = Path(__file__).parent.parent.parent / "configs"
        
        self.config_dir = Path(config_dir)
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def load(self, config_name: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            config_name: 配置文件名（不含.yaml）
            use_cache: 是否使用缓存
            
        Returns:
            配置字典
        """
        if use_cache and config_name in self._cache:
            return self._cache[config_name]
        
        config_path = self.config_dir / f"{config_name}.yaml"
        
        if not config_path.exists():
            logger.warning(f"配置文件不存在: {config_path}, 返回空配置")
            config = {}
        else:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            logger.debug(f"加载配置文件: {config_path}")
        
        if use_cache:
            self._cache[config_name] = config
        
        return config
    
    def reload(self, config_name: Optional[str] = None):
        """
        重新加载配置
        
        Args:
            config_name: 配置文件名（None表示全部）
        """
        if config_name:
            if config_name in self._cache:
                del self._cache[config_name]
            self.load(config_name)
        else:
            self._cache.clear()
            logger.info("已清除所有配置缓存")
    
    def get(self, config_name: str, key: str, default: Any = None) -> Any:
        """
        获取配置值（支持点号分隔的嵌套键）
        
        Args:
            config_name: 配置文件名
            key: 配置键（支持 "section.key" 格式）
            default: 默认值
            
        Returns:
            配置值
        """
        config = self.load(config_name)
        
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value if value is not None else default
    
    def merge_with_env(self, config_name: str) -> Dict[str, Any]:
        """
        合并环境变量到配置
        
        环境变量格式: {CONFIG_NAME}_{KEY}，例如 LLM_API_KEY
        
        Args:
            config_name: 配置文件名
            
        Returns:
            合并后的配置
        """
        config = self.load(config_name).copy()
        prefix = config_name.upper().replace('-', '_') + '_'
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # 移除前缀并转换为小写
                config_key = key[len(prefix):].lower()
                
                # 尝试转换类型
                if isinstance(value, str):
                    if value.lower() in ('true', 'false'):
                        value = value.lower() == 'true'
                    elif value.isdigit():
                        value = int(value)
                    elif value.replace('.', '', 1).isdigit():
                        value = float(value)
                
                # 支持嵌套键（用下划线分隔）
                keys = config_key.split('_')
                target = config
                for k in keys[:-1]:
                    if k not in target:
                        target[k] = {}
                    target = target[k]
                target[keys[-1]] = value
        
        return config


# 全局配置加载器实例
_global_loader: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """获取全局配置加载器"""
    global _global_loader
    if _global_loader is None:
        _global_loader = ConfigLoader()
    return _global_loader


def load_config(config_name: str) -> Dict[str, Any]:
    """
    便捷函数：加载配置
    
    Args:
        config_name: 配置文件名
        
    Returns:
        配置字典
    """
    return get_config_loader().load(config_name)


def get_config_value(config_name: str, key: str, default: Any = None) -> Any:
    """
    便捷函数：获取配置值
    
    Args:
        config_name: 配置文件名
        key: 配置键
        default: 默认值
        
    Returns:
        配置值
    """
    return get_config_loader().get(config_name, key, default)

