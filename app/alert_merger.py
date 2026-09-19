"""
智能告警降噪引擎

功能：
1. 时间窗口聚合：同类告警自动合并
2. 父子抑制：父节点故障时，子节点告警自动抑制
3. 智能关联：用 LLM 判断哪些告警是同一根因
"""
import time
import logging
from collections import defaultdict
from typing import Dict, List, Optional

from app.config import settings
from app.topology import TopologyGraph

logger = logging.getLogger(__name__)


class AlertGroup:
    """一组关联的告警"""

    def __init__(self, root_cause: str):
        self.root_cause = root_cause
        self.alerts: List[Dict] = []
        self.first_seen = time.time()
        self.last_seen = time.time()
        self.suppressed = 0  # 被抑制的告警数

    def add(self, alert: Dict):
        self.alerts.append(alert)
        self.last_seen = time.time()

    @property
    def count(self) -> int:
        return len(self.alerts)

    def summary(self) -> str:
        alert_names = set(a.get("labels", {}).get("alertname", "?") for a in self.alerts)
        return f"{len(self.alerts)} 条告警 ({', '.join(list(alert_names)[:3])})"


class SmartAlertMerger:
    """
    智能告警降噪器

    降噪策略：
    1. 拓扑父子抑制：父节点故障 → 子节点告警自动抑制
    2. 时间窗口聚合：5分钟内同类告警合并
    3. 语义关联：LLM 判断是否同一根因
    """

    def __init__(self, graph: TopologyGraph, window_seconds: int = None):
        self.graph = graph
        self.window = window_seconds or settings.alert_window_seconds
        self.groups: Dict[str, AlertGroup] = {}  # root_cause -> AlertGroup
        self.all_alerts: List[Dict] = []

    def process(self, alert: Dict) -> Dict:
        """
        处理一条新告警
        返回: {
          "action": "added" | "suppressed" | "merged",
          "group_size": int,
          "message": str
        }
        """
        labels = alert.get("labels", {})
        node_id = self._locate_node(labels)

        # 1. 检查是否被父节点故障抑制
        if node_id and self._is_suppressed(node_id):
            root = self._find_root_node(node_id)
            if root in self.groups:
                self.groups[root].suppressed += 1
                logger.debug(f"Alert suppressed by parent: {node_id} -> {root}")
                return {
                    "action": "suppressed",
                    "group_size": self.groups[root].count,
                    "message": f"被父节点 {root} 故障抑制",
                }

        # 2. 找或创建告警组
        root_cause = node_id or "unknown"
        if root_cause not in self.groups:
            self.groups[root_cause] = AlertGroup(root_cause)

        self.groups[root_cause].add(alert)
        self.all_alerts.append(alert)

        # 3. 清理过期组
        self._expire_old()

        group = self.groups[root_cause]
        return {
            "action": "added",
            "group_size": group.count,
            "suppressed": group.suppressed,
            "message": group.summary(),
        }

    def _locate_node(self, labels: Dict) -> Optional[str]:
        """从告警标签定位拓扑节点"""
        candidates = [
            labels.get("container_id"),
            labels.get("vm_id"),
            labels.get("instance"),
        ]
        for c in candidates:
            if c and c in self.graph.nodes:
                return c
        return None

    def _is_suppressed(self, node_id: str) -> bool:
        """检查该节点是否被父节点故障抑制"""
        ancestors = self.graph.get_ancestors(node_id)
        for ancestor in ancestors:
            if ancestor in self.groups and self.groups[ancestor].count > 0:
                return True
        return False

    def _find_root_node(self, node_id: str) -> str:
        """找到该节点的根因节点"""
        ancestors = self.graph.get_ancestors(node_id)
        if not ancestors:
            return node_id
        return ancestors[-1]

    def _expire_old(self):
        """清理过期的告警组"""
        now = time.time()
        expired = [
            k for k, g in self.groups.items()
            if now - g.last_seen > self.window
        ]
        for k in expired:
            del self.groups[k]

    def get_stats(self) -> Dict:
        """获取降噪统计"""
        total = len(self.all_alerts)
        active_groups = len(self.groups)
        suppressed = sum(g.suppressed for g in self.groups.values())
        return {
            "total_alerts": total,
            "active_groups": active_groups,
            "suppressed": suppressed,
            "reduction_ratio": f"{(suppressed / total * 100):.1f}%" if total > 0 else "0%",
        }
