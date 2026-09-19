"""
AI 核心根因分析引擎

设计理念：
- 规则引擎做快速初筛（缩小范围）
- LLM 做深度推理（真正理解上下文，给出人能看懂的诊断）
- 不是"规则 + 事后AI补一句"，而是 AI 主导整个分析过程
"""
import json
import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime

from app.topology import TopologyGraph
from app.models import NodeType, RootCauseReport
from app.llm_client import get_llm

logger = logging.getLogger(__name__)


class RootCauseAnalyzer:
    """
    AI 核心根因分析器

    分析流程：
    1. 规则引擎：从告警标签定位节点，沿拓扑找候选根因集
    2. 构造上下文：把拓扑 + 告警 + 影响范围 全部整理给 LLM
    3. LLM 深度推理：让模型真正分析根因，给出结构化诊断
    4. 输出报告：根因 + 影响范围 + 修复建议 + 置信度
    """

    SYSTEM_PROMPT = """你是一位资深 SRE / 可观测性专家，专精于云原生和 AI 基础设施的故障诊断。
你的任务是根据提供的资源拓扑、告警信息和影响范围，推理出最可能的根因。

要求：
1. 先列出 2-3 个可能的根因假设，按可能性排序
2. 选出最可能的那个，给出置信度（0-100%）
3. 解释推理过程：为什么是这个根因，排除了哪些其他可能
4. 给出 2-3 条具体、可执行的修复建议，每条建议要包含可直接运行的命令
5. 评估影响范围：哪些业务可能受影响
6. 用中文回答，专业但易懂，控制在 400 字以内

输出格式（JSON）：
{
  "top_cause": "最可能根因",
  "confidence": 85,
  "reasoning": "推理过程简述",
  "alternative_causes": ["备选原因1", "备选原因2"],
  "fix_suggestions": [
    {"action": "操作描述", "command": "可执行命令"},
    {"action": "操作描述", "command": "可执行命令"}
  ],
  "business_impact": "业务影响评估"
}"""

    def __init__(self, graph: TopologyGraph):
        self.graph = graph
        self.recent_alerts: Dict[str, List[Dict]] = {}

    async def analyze(self, alert: Dict) -> RootCauseReport:
        """完整根因分析：规则初筛 + LLM 深度推理"""
        labels = alert.get("labels", {})
        alertname = labels.get("alertname", "unknown")

        # Step 1: 规则引擎初筛 —— 定位告警节点和候选根因
        node_id = self._locate_node(labels)
        if not node_id:
            return self._unknown_root_cause(alert)

        root_node_id = self._find_root_cause(node_id)
        impacted = self.graph.get_children(root_node_id)
        related = self._collect_related_alerts(root_node_id, impacted)

        # Step 2: 构造上下文，喂给 LLM 做深度推理
        context = self._build_context(alert, root_node_id, impacted, related)

        # Step 3: 调用 LLM 做智能推理
        llm_result = await self._llm_root_cause(context)

        # Step 4: 组装最终报告
        root_node = self.graph.nodes.get(root_node_id, {})
        report = RootCauseReport(
            root_node_id=root_node_id,
            root_node_name=root_node.get("name", root_node_id),
            root_node_type=root_node.get("type", NodeType.HOST),
            summary=self._build_summary(alertname, llm_result, len(impacted)),
            impacted_resources=impacted,
            related_alerts=related,
            suggestion=llm_result.get("fix_suggestions", ["请人工排查"])[0],
            generated_at=datetime.now(),
        )

        logger.info(f"Root cause: {report.root_node_name} (confidence: {llm_result.get('confidence', '?')}%)")
        return report

    def _build_context(self, alert: Dict, root_node_id: str, impacted: List[str], related: List[Dict]) -> str:
        """构造给 LLM 的完整上下文"""
        root_node = self.graph.nodes.get(root_node_id, {})

        # 拓扑上下文
        topology_lines = []
        for nid, node in self.graph.nodes.items():
            marker = "◄ 根因候选" if nid == root_node_id else ""
            topology_lines.append(f"  - [{node['type']}] {node['name']} {marker}")

        # 告警详情
        alert_detail = (
            f"告警名称: {alert.get('labels', {}).get('alertname', '?')}\n"
            f"告警级别: {alert.get('labels', {}).get('severity', '?')}\n"
            f"告警描述: {alert.get('annotations', {}).get('summary', '无')}"
        )

        # 相关告警
        related_lines = []
        for a in related[:5]:
            related_lines.append(f"  - {a.get('labels', {}).get('alertname', '?')}")

        return f"""## 资源拓扑结构
{chr(10).join(topology_lines)}

## 当前告警
{alert_detail}

## 影响范围
根因节点: {root_node.get('name', root_node_id)} ({root_node.get('type', '?')})
受影响子资源数: {len(impacted)}

## 近期相关告警
{chr(10).join(related_lines) if related_lines else '无'}

请分析根因并给出诊断:"""

    async def _llm_root_cause(self, context: str) -> Dict:
        """调用 LLM 做深度根因推理"""
        llm = get_llm()

        try:
            loop = asyncio.get_event_loop()
            result_text = await loop.run_in_executor(
                None,
                lambda: llm.chat(self.SYSTEM_PROMPT, context, temperature=0.2)
            )

            # 尝试解析 JSON
            try:
                json_start = result_text.find("{")
                json_end = result_text.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    return json.loads(result_text[json_start:json_end])
            except json.JSONDecodeError:
                pass

            return {
                "top_cause": "见分析",
                "confidence": 70,
                "reasoning": result_text[:200],
                "fix_suggestions": ["查看详细分析"],
                "business_impact": "需进一步评估",
            }

        except Exception as e:
            logger.warning(f"LLM analysis failed, falling back to rules: {e}")
            return {
                "top_cause": "规则引擎推断",
                "confidence": 50,
                "reasoning": "LLM 分析失败，使用规则引擎结果",
                "fix_suggestions": ["请人工排查"],
                "business_impact": "未知",
            }

    def _build_summary(self, alertname: str, llm_result: Dict, impact_count: int) -> str:
        """组装最终摘要"""
        confidence = llm_result.get("confidence", 50)
        top_cause = llm_result.get("top_cause", "未知")
        reasoning = llm_result.get("reasoning", "")
        suggestions = llm_result.get("fix_suggestions", [])

        summary = f"🔍 AI 根因分析 ({confidence}% 置信度)\n"
        summary += f"▸ 最可能根因: {top_cause}\n"
        if reasoning:
            summary += f"▸ 推理: {reasoning[:100]}\n"
        if suggestions:
            summary += f"▸ 建议: {suggestions[0]}\n"
        summary += f"▸ 影响: {impact_count} 个子资源"
        return summary

    def _locate_node(self, labels: Dict) -> Optional[str]:
        """从告警标签中定位拓扑节点"""
        candidates = [
            labels.get("agent_id"),
            labels.get("service_id"),
            labels.get("container_id"),
            labels.get("vm_id"),
            labels.get("gpu_id"),
            labels.get("instance"),
        ]
        for candidate in candidates:
            if candidate and candidate in self.graph.nodes:
                return candidate
            if candidate:
                found = self.graph.find_node_by_label("instance", candidate)
                if found:
                    return found
        return None

    def _find_root_cause(self, start_node_id: str) -> str:
        """沿父链向上追溯候选根因节点"""
        ancestors = self.graph.get_ancestors(start_node_id)
        if not ancestors:
            return start_node_id
        return ancestors[-1]

    def _collect_related_alerts(self, root_node_id: str, impacted: List[str]) -> List[Dict]:
        related = []
        for node_id in [root_node_id] + impacted:
            if node_id in self.recent_alerts:
                related.extend(self.recent_alerts[node_id])
        return related[:10]

    def _unknown_root_cause(self, alert: Dict) -> RootCauseReport:
        return RootCauseReport(
            root_node_id="unknown",
            root_node_name="未知节点",
            root_node_type=NodeType.HOST,
            summary=f"无法定位告警所属资源: {alert.get('labels', {}).get('alertname', 'unknown')}",
            related_alerts=[alert],
            suggestion="请检查告警标签配置是否正确",
            generated_at=datetime.now(),
        )

    def record_alert(self, alert: Dict):
        """记录告警到历史缓存"""
        node_id = self._locate_node(alert.get("labels", {}))
        if node_id:
            self.recent_alerts.setdefault(node_id, []).append(alert)
            self.recent_alerts[node_id] = self.recent_alerts[node_id][-20:]
