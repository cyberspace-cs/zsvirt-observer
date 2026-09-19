"""
统一 LLM 客户端 - 支持多家模型提供商

配置优先级: 环境变量 > 默认值
支持: DeepSeek / 阿里云百炼(Qwen) / 火山方舟(Ark) / OpenRouter
"""
import os
import logging
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    """统一 LLM 调用客户端，自动选择可用的模型"""

    def __init__(self, provider: str = None):
        self.provider = provider or os.getenv("LLM_PROVIDER", "deepseek")
        self.client = None
        self.model = ""
        self._init_client()

    def _init_client(self):
        """根据配置初始化对应提供商的客户端"""
        if self.provider == "deepseek":
            api_key = os.getenv("DEEPSEEK_API_KEY", "")
            base_url = "https://api.deepseek.com/v1"
            self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
            if api_key:
                self.client = OpenAI(api_key=api_key, base_url=base_url)

        elif self.provider == "qwen":
            api_key = os.getenv("DASHSCOPE_API_KEY", "")
            base_url = os.getenv(
                "DASHSCOPE_BASE_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            self.model = os.getenv("QWEN_MODEL", "qwen-plus")
            if api_key:
                self.client = OpenAI(api_key=api_key, base_url=base_url)

        elif self.provider == "ark":
            api_key = os.getenv("ARK_API_KEY", "")
            base_url = "https://ark.cn-beijing.volces.com/api/v3"
            self.model = os.getenv("ARK_MODEL", "doubao-pro-4k")
            if api_key:
                self.client = OpenAI(api_key=api_key, base_url=base_url)

        elif self.provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY", "")
            base_url = "https://openrouter.ai/api/v1"
            self.model = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
            if api_key:
                self.client = OpenAI(
                    api_key=api_key,
                    base_url=base_url,
                    default_headers={
                        "HTTP-Referer": "https://github.com/cyberspace-cs/zsvirt-observer",
                        "X-Title": "ZSvirt Observer",
                    }
                )

        if self.client:
            logger.info(f"LLM client initialized: {self.provider}/{self.model}")
        else:
            logger.warning(f"LLM provider '{self.provider}' not configured, using mock mode")

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
        """
        调用 LLM 对话
        返回: 模型回复文本
        """
        if not self.client:
            return f"[Mock LLM] 基于规则分析，建议检查相关资源状态。"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=500,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return f"[LLM Error] 调用失败: {str(e)[:100]}"

    def analyze_alert(self, alert_summary: str, topology_context: str, history_alerts: str) -> str:
        """
        用 LLM 分析告警，生成智能根因解读
        """
        system_prompt = """你是一位资深 SRE 专家，擅长云原生环境故障诊断。
请根据以下信息，用简洁专业的中文分析告警的可能根因。
要求:
1. 直接给出结论，不要客套
2. 指出最可能的根因层级
3. 给出 2-3 条具体排查建议
4. 控制在 200 字以内"""

        user_prompt = f"""## 告警信息
{alert_summary}

## 资源拓扑上下文
{topology_context}

## 近期相关告警
{history_alerts}

请分析根因并给出建议:"""

        return self.chat(system_prompt, user_prompt)


# 全局单例
_llm_client: Optional[LLMClient] = None


def get_llm() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
