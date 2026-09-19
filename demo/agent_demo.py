#!/usr/bin/env python3
"""
AI Agent 可观测性 Demo

使用 OpenLIT 自动将 LLM 调用 Trace 发送到 OTel Collector
支持多家模型提供商: DeepSeek / Qwen / OpenRouter / 火山方舟

用法:
    pip install openlit openai python-dotenv
    cp .env.example .env  # 填入你的 API key
    python demo/agent_demo.py
"""
import os
import sys
import time
import logging

# 加载 .env
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ========== OpenLIT 初始化（自动埋点） ==========
import openlit

openlit.init(
    otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318"),
    application_name="zsvirt-observer-demo-agent",
    environment="demo",
)
# ================================================


def get_llm_client():
    """根据环境变量选择 LLM 提供商"""
    provider = os.getenv("LLM_PROVIDER", "deepseek")

    if provider == "deepseek":
        from openai import OpenAI
        return OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/v1",
        ), os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    elif provider == "qwen":
        from openai import OpenAI
        return OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url=os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        ), os.getenv("QWEN_MODEL", "qwen-plus")

    elif provider == "openrouter":
        from openai import OpenAI
        return OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://github.com/cyberspace-cs/zsvirt-observer",
                "X-Title": "ZSvirt Observer",
            }
        ), os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def run_chat_agent(user_query: str, client, model: str):
    """对话 Agent - 自动被 OpenLIT 埋点"""
    logger.info(f"收到用户查询: {user_query}")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个运维助手，帮用户排查云原生环境的系统故障。回答要简洁专业。"},
                {"role": "user", "content": user_query},
            ],
            max_tokens=300,
            temperature=0.3,
        )

        answer = response.choices[0].message.content
        logger.info(f"Agent 回复: {answer[:100]}...")
        return answer

    except Exception as e:
        logger.error(f"Agent 调用失败: {e}")
        return f"[错误] Agent 调用失败: {e}"


def run_rag_agent(query: str, client, model: str):
    """RAG Agent - 模拟工具调用 + LLM 总结"""
    logger.info(f"RAG Agent 处理: {query}")

    # 模拟工具调用 1: 搜索知识库
    time.sleep(0.5)
    logger.info("🔧 调用工具: search_knowledge_base")
    kb_result = "知识库: 容器OOM通常由内存泄漏或资源配额不足导致"

    # 模拟工具调用 2: 获取监控指标
    time.sleep(0.3)
    logger.info("🔧 调用工具: get_system_metrics")
    metrics = "当前内存使用率: 98%, 容器重启次数: 12"

    # 用 LLM 综合分析
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是运维诊断专家，根据知识库和监控数据给出诊断结论。"},
                {"role": "user", "content": f"""问题: {query}

知识库信息: {kb_result}
监控数据: {metrics}

请给出诊断结论和建议:"""},
            ],
            max_tokens=200,
        )
        answer = response.choices[0].message.content
        logger.info(f"RAG 诊断: {answer[:100]}...")
        return answer
    except Exception as e:
        logger.error(f"RAG 调用失败: {e}")
        return f"[错误] RAG 调用失败: {e}"


def main():
    print("=" * 50)
    print("  ZSVirt Observer - AI Agent 可观测性 Demo")
    print("=" * 50)
    print()

    provider = os.getenv("LLM_PROVIDER", "deepseek")
    print(f"📡 LLM Provider: {provider}")
    print(f"📊 Trace Endpoint: {os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://localhost:4318')}")
    print()

    # 初始化 LLM 客户端
    try:
        client, model = get_llm_client()
        print(f"✅ 模型: {model}")
    except Exception as e:
        print(f"❌ LLM 初始化失败: {e}")
        print("请检查 .env 文件中的 API 配置")
        sys.exit(1)

    print()
    print("--- 场景1: 对话 Agent ---")
    run_chat_agent("我的AI推理服务响应很慢，帮我看看怎么回事", client, model)
    print()

    print("--- 场景2: RAG Agent (工具调用) ---")
    run_rag_agent("容器 OOM 了怎么办", client, model)
    print()

    print("--- 场景3: 连续多轮调用 ---")
    for i in range(3):
        run_chat_agent(f"第{i+1}次查询: GPU显存使用率85%正常吗", client, model)
        time.sleep(1)

    print()
    print("=" * 50)
    print("  ✅ Demo 完成！")
    print("  📊 查看 Trace: Grafana → Explore → OTel-Metrics")
    print("=" * 50)


if __name__ == "__main__":
    main()
