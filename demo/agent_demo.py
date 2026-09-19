#!/usr/bin/env python3
"""
AI Agent 可观测性 Demo

使用 OpenLIT 自动将 LLM 调用 Trace 发送到 OTel Collector
无需修改业务代码，两行初始化即可接入全链路追踪

用法:
    pip install openlit openai
    export OPENAI_API_KEY=sk-xxx
    python demo/agent_demo.py
"""
import os
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ========== OpenLIT 初始化（两行搞定） ==========
import openlit

openlit.init(
    otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318"),
    application_name="zsvirt-observer-demo-agent",
    environment="demo",
)
# ================================================


def run_chat_agent(user_query: str):
    """模拟一个简单的对话 Agent"""
    logger.info(f"收到用户查询: {user_query}")

    try:
        from openai import OpenAI
        client = OpenAI()

        # 这一步会自动被 OpenLIT 捕获 Trace
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是一个运维助手，帮用户排查系统故障。"},
                {"role": "user", "content": user_query},
            ],
            max_tokens=200,
        )

        answer = response.choices[0].message.content
        logger.info(f"Agent 回复: {answer[:100]}...")
        return answer

    except ImportError:
        logger.warning("openai 未安装，使用模拟模式")
        return f"[模拟回复] 针对问题 '{user_query}'，建议检查 GPU 使用率和容器状态。"
    except Exception as e:
        logger.error(f"Agent 调用失败: {e}")
        return f"[错误] Agent 调用失败: {e}"


def run_rag_agent(query: str):
    """模拟 RAG Agent（带工具调用）"""
    logger.info(f"RAG Agent 处理: {query}")

    # 模拟工具调用
    time.sleep(0.5)
    logger.info("调用工具: search_knowledge_base")

    time.sleep(0.3)
    logger.info("调用工具: get_system_metrics")

    return f"[RAG结果] 基于知识库检索，问题可能由 GPU 显存不足引起。"


def main():
    print("=" * 50)
    print("  ZSVirt Observer - AI Agent 可观测性 Demo")
    print("=" * 50)
    print()
    print("Trace 将发送到 OTel Collector: http://localhost:4318")
    print("请确保 otel-collector 服务已启动")
    print()

    # 场景1: 简单对话
    print("--- 场景1: 对话 Agent ---")
    run_chat_agent("我的服务响应很慢，帮我看看怎么回事")
    print()

    # 场景2: RAG Agent
    print("--- 场景2: RAG Agent ---")
    run_rag_agent("容器 OOM 了怎么办")
    print()

    # 场景3: 连续调用
    print("--- 场景3: 连续多轮调用 ---")
    for i in range(3):
        run_chat_agent(f"第{i+1}次查询: 检查 GPU {i} 状态")
        time.sleep(1)

    print()
    print("=" * 50)
    print("  Demo 完成！")
    print("  查看 Trace: Grafana → Explore → OTel-Metrics")
    print("=" * 50)


if __name__ == "__main__":
    main()
