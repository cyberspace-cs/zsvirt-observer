"""根因分析引擎 —— 沿拓扑图自动下钻定位故障根因 + AI 智能解读"""
import logging
from typing import Dict, List, Optional
from datetime import datetime

from app.topology import TopologyGraph
from app.models import NodeType, RootCauseReport
from app.alert_merger import AlertMerger
from app.llm_client import get_llm

logger = logging.getLogger(__name__)


class RootCauseAnalyzer:
    """
    根因分析器
    输入: 一条告警
    输出: 根因报告（沿拓扑图向上追溯，找到最顶层的异常节点）
    """

    # 不同节点类型的修复建议
    SUGGESTIONS = {
        NodeType.HOST: "检查宿主机硬件状态、电源、网络连接，查看 dmesg 系统日志",
        NodeType.VM: "检查虚拟机运行状态、资源配额，查看虚拟机内部系统日志",
        NodeType.GPU: "检查 GPU 驱动状态、显存占用、温度，排查 CUDA 错误",
        NodeType.CONTAINER: "检查容器状态、日志，排查 OOM 或应用崩溃",
        NodeType.SERVICE: "检查推理服务进程、端口、日志，排查模型加载失败",
        NodeType.AGENT: "检查 Agent 任务状态、LLM API 调用、工具链是否正常",
    }

    def __init__(self, graph: TopologyGraph):
        self.graph = graph
        self.merger = AlertMerger()
        self.recent_alerts: Dict[str, List[Dict]] = {}

    async def analyze(self, alert: Dict) -> RootCauseReport:
        """
        对一条告警执行根因分析（规则引擎 + AI 智能解读）
        """
        labels = alert.get("labels", {})
        alertname = labels.get("alertname", "unknown")

        # 1. 从告警标签中定位拓扑节点
        node_id = self._locate_node(labels)
        if not node_id:
            return self._unknown_root_cause(alert)

        # 2. 沿父链向上追溯，找到根因节点
        root_node_id = self._find_root_cause(node_id)

        # 3. 收集受影响的所有子资源
        impacted = self.graph.get_children(root_node_id)

        # 4. 收集相关告警
        related = self._collect_related_alerts(root_node_id, impacted)

        # 5. 规则引擎生成基础报告
        root_node = self.graph.nodes.get(root_node_id, {})
        report = RootCauseReport(
            root_node_id=root_node_id,
            root_node_name=root_node.get("name", root_node_id),
            root_node_type=root_node.get("type", NodeType.HOST),
            summary=self._build_summary(root_node_id, alertname, len(impacted)),
            impacted_resources=impacted,
            related_alerts=related,
            suggestion=self.SUGGESTIONS.get(root_node.get("type", NodeType.HOST), "请人工排查"),
            generated_at=datetime.now(),
        )

        # 6. AI 智能解读（可选，失败不影响主流程）
        try:
            ai_analysis = await self._ai_analyze(alert, report)
            if ai_analysis:
                report.summary = f"{report.summary}\n\n🤖 AI 解读: {ai_analysis}"
        except Exception as e:
            logger.warning(f"AI analysis skipped: {e}")

        logger.info(f"Root cause: {report.root_node_name} ({report.root_node_type})")
        return report

    async def _ai_analyze(self, alert: Dict, report: RootCauseReport) -> str:
        """调用 LLM 做智能根因解读"""
        llm = get_llm()

        alert_summary = (
            f"告警名: {alert.get('labels', {}).get('alertname', 'unknown')}\n"
            f"级别: {alert.get('labels', {}).get('severity', 'unknown')}\n"
            f"描述: {alert.get('annotations', {}).get('summary', '无')}"
        )

        topology_context = (
            f"根因节点: {report.root_node_name} ({report.root_node_type.value})\n"
            f"影响资源数: {len(report.impacted_resources)}"
        )

        history_alerts = "\n".join([
            f"- {a.get('labels', {}).get('alertname', '?')}"
            for a in report.related_alerts[:5]
        ]) or "无"

        # LLM 调用目前是同步的，用 run_in_executor 避免阻塞
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: llm.analyze_alert(alert_summary, topology_context, history_alerts)
        )
        return result

    def _locate_node(self, labels: Dict) -> Optional[str]:
        """从告警标签中定位拓扑节点"""
        # 按优先级尝试不同的标签
        candidates = [
            labels.get("agent_id"),
            labels.get("service_id"),
            labels.get("container_id"),
            labels.get("vm_id"),
            labels.get("gpu_id"),
            labels.get("instance"),  # Prometheus 的 instance 标签
        ]
        for candidate in candidates:
            if candidate and candidate in self.graph.nodes:
                return candidate
            # 模糊匹配：用 instance 找 host
            if candidate:
                found = self.graph.find_node_by_label("instance", candidate)
                if found:
                    return found
        return None

    def _find_root_cause(self, start_node_id: str) -> str:
        """
        沿父链向上追溯根因
        简化策略：直接找到最顶层祖先
        （更复杂的实现可以结合历史告警判断哪个父节点也异常）
        """
        ancestors = self.graph.get_ancestors(start_node_id)
        if not ancestors:
            return start_node_id

        # 目前直接返回最顶层祖先
        # TODO: 结合历史告警判断哪个层级最先异常
        return ancestors[-1]

    def _collect_related_alerts(self, root_node_id: str, impacted: List[str]) -> List[Dict]:
        """收集根因节点及其影响范围内的所有相关告警"""
        related = []
        for node_id in [root_node_id] + impacted:
            if node_id in self.recent_alerts:
                related.extend(self.recent_alerts[node_id])
        return related[:10]  # 最多返回10条

    def _build_summary(self, root_node_id: str, alertname: str, impact_count: int) -> str:
        node = self.graph.nodes.get(root_node_id, {})
        node_name = node.get("name", root_node_id)
        node_type = node.get("type", "unknown")
        return (
            f"根因定位: {node_type} '{node_name}' 触发 {alertname} 告警，"
            f"影响其下 {impact_count} 个子资源"
        )

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
        """记录一条告警到历史缓存"""
        node_id = self._locate_node(alert.get("labels", {}))
        if node_id:
            self.recent_alerts.setdefault(node_id, []).append(alert)
            # 只保留最近20条
            self.recent_alerts[node_id] = self.recent_alerts[node_id][-20:]
