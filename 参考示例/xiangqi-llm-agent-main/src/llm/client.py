"""
LLM客户端封装
负责与大语言模型API通信
"""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import time
import logging
from abc import ABC, abstractmethod
import os

from src.utils.config_loader import load_config, get_config_value

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """
    LLM配置
    
    配置加载优先级（从高到低）:
    1. 显式传入的参数
    2. 环境变量
    3. configs/llm.yaml 配置文件
    4. 默认值
    """
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout: Optional[int] = None
    max_retries: Optional[int] = None
    retry_delay: Optional[float] = None
    provider: Optional[str] = None
    
    def __post_init__(self):
        """从配置文件和环境变量加载配置"""
        # 加载配置文件
        config = {}
        try:
            config = load_config('llm')
        except Exception as e:
            logger.warning(f"加载LLM配置文件失败，使用默认值: {e}")
        
        # 默认值
        defaults = {
            'provider': 'anthropic',
            'model_name': 'claude-sonnet-4-20250514',
            'temperature': 0.7,
            'top_p': 0.9,
            'max_tokens': 2000,
            'timeout': 60,
            'max_retries': 3,
            'retry_delay': 1.0,
        }
        
        # 从配置文件获取值（如果未显式设置）
        # 使用 or 运算符处理字符串类型（None 或空字符串都视为未设置）
        self.provider = self.provider or config.get('provider') or defaults['provider']
        self.model_name = self.model_name or config.get('model_name') or defaults['model_name']
        self.api_key = self.api_key or config.get('api_key')
        self.base_url = self.base_url or config.get('base_url')
        
        # 对于数值类型，需要明确检查 None
        if self.temperature is None:
            self.temperature = config.get('temperature', defaults['temperature'])
        if self.top_p is None:
            self.top_p = config.get('top_p', defaults['top_p'])
        if self.max_tokens is None:
            self.max_tokens = config.get('max_tokens', defaults['max_tokens'])
        if self.timeout is None:
            self.timeout = config.get('timeout', defaults['timeout'])
        if self.max_retries is None:
            self.max_retries = config.get('max_retries', defaults['max_retries'])
        if self.retry_delay is None:
            self.retry_delay = config.get('retry_delay', defaults['retry_delay'])
        
        # 环境变量优先级最高（可以覆盖配置文件）
        if os.getenv("LLM_PROVIDER"):
            self.provider = os.getenv("LLM_PROVIDER")
        
        if os.getenv("LLM_API_KEY"):
            self.api_key = os.getenv("LLM_API_KEY")
        elif self.api_key is None:
            # 如果配置文件中也没有，尝试从环境变量读取
            self.api_key = os.getenv("LLM_API_KEY", "")
        
        if os.getenv("LLM_MODEL"):
            self.model_name = os.getenv("LLM_MODEL")
        
        if os.getenv("LLM_TEMPERATURE"):
            self.temperature = float(os.getenv("LLM_TEMPERATURE"))
        
        if os.getenv("LLM_TOP_P"):
            self.top_p = float(os.getenv("LLM_TOP_P"))
        
        if os.getenv("LLM_MAX_TOKENS"):
            self.max_tokens = int(os.getenv("LLM_MAX_TOKENS"))
        
        if os.getenv("LLM_TIMEOUT"):
            self.timeout = int(os.getenv("LLM_TIMEOUT"))
        
        if os.getenv("LLM_MAX_RETRIES"):
            self.max_retries = int(os.getenv("LLM_MAX_RETRIES"))
        
        if os.getenv("LLM_RETRY_DELAY"):
            self.retry_delay = float(os.getenv("LLM_RETRY_DELAY"))


@dataclass
class LLMResponse:
    """LLM响应"""
    content: str  # 返回的文本内容
    model: str  # 使用的模型
    usage: Dict[str, int]  # token使用情况
    raw_response: Optional[Dict] = None  # 原始响应
    
    @property
    def text(self) -> str:
        """便捷属性:获取文本内容"""
        return self.content


class BaseLLMClient(ABC):
    """LLM客户端抽象基类"""
    
    def __init__(self, config: LLMConfig):
        """
        初始化客户端
        
        Args:
            config: LLM配置
        """
        self.config = config
        self._validate_config()
    
    @abstractmethod
    def _call_api(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        调用API(子类实现)
        
        Args:
            messages: 消息列表
            
        Returns:
            API原始响应
        """
        pass
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """
        生成文本
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示(可选)
            temperature: 温度参数(覆盖配置)
            top_p: top_p参数(覆盖配置)
            max_tokens: 最大token数(覆盖配置)
            
        Returns:
            LLM响应对象
        """
        # 构造消息
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # 覆盖参数
        self._temp_override = {
            "temperature": temperature if temperature is not None else self.config.temperature,
            "top_p": top_p if top_p is not None else self.config.top_p,
            "max_tokens": max_tokens if max_tokens is not None else self.config.max_tokens
        }
        
        # 调用API(带重试)
        response = self._call_with_retry(messages)
        
        return response
    
    def _call_with_retry(self, messages: List[Dict[str, str]]) -> LLMResponse:
        """
        带重试机制的API调用
        
        Args:
            messages: 消息列表
            
        Returns:
            LLM响应
            
        Raises:
            Exception: 重试耗尽后抛出
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"LLM API调用尝试 {attempt + 1}/{self.config.max_retries}")
                
                raw_response = self._call_api(messages)
                response = self._parse_response(raw_response)
                
                logger.info(f"LLM调用成功, 返回{len(response.content)}字符")
                return response
                
            except Exception as e:
                last_exception = e
                logger.warning(f"LLM调用失败 (尝试 {attempt + 1}/{self.config.max_retries}): {e}")
                
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay * (2 ** attempt)  # 指数退避
                    logger.info(f"等待 {delay}s 后重试...")
                    time.sleep(delay)
        
        # 重试耗尽
        logger.error(f"LLM调用失败,已耗尽 {self.config.max_retries} 次重试")
        raise Exception(f"LLM API调用失败: {last_exception}")
    
    @abstractmethod
    def _parse_response(self, raw_response: Dict[str, Any]) -> LLMResponse:
        """
        解析API响应(子类实现)
        
        Args:
            raw_response: 原始响应
            
        Returns:
            LLMResponse对象
        """
        pass
    
    def _validate_config(self):
        """验证配置有效性"""
        if not self.config.api_key:
            logger.warning("API密钥未设置,请设置环境变量 LLM_API_KEY")
        
        if self.config.temperature < 0 or self.config.temperature > 2:
            raise ValueError(f"temperature必须在[0, 2]范围内: {self.config.temperature}")
        
        if self.config.top_p < 0 or self.config.top_p > 1:
            raise ValueError(f"top_p必须在[0, 1]范围内: {self.config.top_p}")


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude客户端"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        try:
            import anthropic
            self.anthropic = anthropic
            self.client = anthropic.Anthropic(api_key=config.api_key)
        except ImportError:
            raise ImportError("请安装anthropic库: pip install anthropic")
    
    def _call_api(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """调用Anthropic API"""
        # 分离system消息
        system_msg = None
        user_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                user_messages.append(msg)
        
        # 调用API
        kwargs = {
            "model": self.config.model_name,
            "messages": user_messages,
            "temperature": self._temp_override["temperature"],
            "top_p": self._temp_override["top_p"],
            "max_tokens": self._temp_override["max_tokens"]
        }
        
        if system_msg:
            kwargs["system"] = system_msg
        
        response = self.client.messages.create(**kwargs)
        
        return response.model_dump()
    
    def _parse_response(self, raw_response: Dict[str, Any]) -> LLMResponse:
        """解析Anthropic响应"""
        content = ""
        
        # 提取文本内容
        for block in raw_response.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")
        
        # 提取usage
        usage = raw_response.get("usage", {})
        
        return LLMResponse(
            content=content,
            model=raw_response.get("model", self.config.model_name),
            usage={
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
            },
            raw_response=raw_response
        )


class OpenAIClient(BaseLLMClient):
    """OpenAI客户端"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        try:
            import openai
            self.openai = openai
            
            # 支持自定义base_url(如使用代理或兼容API)
            if config.base_url:
                self.client = openai.OpenAI(
                    api_key=config.api_key,
                    base_url=config.base_url,
                    timeout=config.timeout
                )
            else:
                self.client = openai.OpenAI(
                    api_key=config.api_key,
                    timeout=config.timeout
                )
        except ImportError:
            raise ImportError("请安装openai库: pip install openai")
    
    def _call_api(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """调用OpenAI API"""
        response = self.client.chat.completions.create(
            model=self.config.model_name,
            messages=messages,
            temperature=self._temp_override["temperature"],
            top_p=self._temp_override["top_p"],
            max_tokens=self._temp_override["max_tokens"]
        )
        
        return response.model_dump()
    
    def _parse_response(self, raw_response: Dict[str, Any]) -> LLMResponse:
        """解析OpenAI响应"""
        choices = raw_response.get("choices", [])
        if not choices:
            raise ValueError("API返回空响应")
        
        content = choices[0].get("message", {}).get("content", "")
        usage = raw_response.get("usage", {})
        
        return LLMResponse(
            content=content,
            model=raw_response.get("model", self.config.model_name),
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0)
            },
            raw_response=raw_response
        )


class MockLLMClient(BaseLLMClient):
    """
    Mock LLM客户端(用于测试)
    返回随机合法走法
    """
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        import random
        self.random = random
    
    def _call_api(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """模拟API调用"""
        time.sleep(0.1)  # 模拟网络延迟
        
        # 从prompt中提取走法选项(简化实现)
        user_msg = messages[-1]["content"]
        
        # 模拟返回
        return {
            "content": "1",  # 返回第一个选项
            "model": "mock-model",
            "usage": {"input_tokens": 100, "output_tokens": 10}
        }
    
    def _parse_response(self, raw_response: Dict[str, Any]) -> LLMResponse:
        """解析Mock响应"""
        return LLMResponse(
            content=raw_response["content"],
            model=raw_response["model"],
            usage={
                "prompt_tokens": raw_response["usage"]["input_tokens"],
                "completion_tokens": raw_response["usage"]["output_tokens"],
                "total_tokens": raw_response["usage"]["input_tokens"] + raw_response["usage"]["output_tokens"]
            },
            raw_response=raw_response
        )


# ============ 工厂函数 ============

def create_llm_client(
    provider: Optional[str] = None,
    config: Optional[LLMConfig] = None
) -> BaseLLMClient:
    """
    工厂函数: 创建LLM客户端
    
    Args:
        provider: 提供商("anthropic", "openai", "mock")，如果为None则从配置读取
        config: LLM配置(可选)，如果为None则从配置文件创建
        
    Returns:
        LLM客户端实例
        
    Raises:
        ValueError: 不支持的provider
    """
    if config is None:
        config = LLMConfig()
    
    # 如果未指定provider，从配置中获取
    if provider is None:
        provider = config.provider or "anthropic"
    
    providers = {
        "anthropic": AnthropicClient,
        "openai": OpenAIClient,
        "mock": MockLLMClient
    }
    
    client_class = providers.get(provider.lower())
    if client_class is None:
        raise ValueError(f"不支持的provider: {provider}, 可选: {list(providers.keys())}")
    
    return client_class(config)


def create_default_client() -> BaseLLMClient:
    """
    创建默认客户端(从配置文件和环境变量读取配置)
    
    Returns:
        LLM客户端实例
    """
    # 创建配置对象，会自动从配置文件和环境变量加载
    config = LLMConfig()
    
    # 使用配置中的provider
    return create_llm_client(config.provider, config)