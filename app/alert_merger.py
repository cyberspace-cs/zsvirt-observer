"""告警聚合降噪引擎"""
import time
import logging
from collections import defaultdict
from typing import Dict, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class MergedAlert:
    """合并后的告警组"""

    def __init__(self, group_key: str):
        self.group_key = group_key
        self.alerts: List[Dict] = []
        self.first_seen: float = time.time()
        self.last_seen: float = time.time()

    def add(self, alert: Dict):
        self.alerts.append(alert)
        self.last_seen = time.time()

    @property
    def count(self) -> int:
        return len(self.alerts)

    @property
    def age_seconds(self) -> float:
        return self.last_seen - self.first_seen

    def to_dict(self) -> Dict:
        return {
            "group_key": self.group_key,
            "count": self.count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "alerts": self.alerts,
        }


class AlertMerger:
    """
    告警聚合器
    - 按 (告警名 + 来源节点) 分组
    - 时间窗口内的同类告警合并
    - 超过阈值则输出合并后的告警
    """

    def __init__(self, window_seconds: int = None, group_threshold: int = None):
        self.window = window_seconds or settings.alert_window_seconds
        self.threshold = group_threshold or settings.alert_group_threshold
        self.buffers: Dict[str, MergedAlert] = {}

    def _group_key(self, alert: Dict) -> str:
        """生成告警分组键"""
        labels = alert.get("labels", {})
        alertname = labels.get("alertname", "unknown")
        instance = labels.get("instance", "")
        return f"{alertname}@{instance}"

    def add(self, alert: Dict) -> Optional[Dict]:
        """
        添加一条告警
        返回: 如果触发了合并输出，返回合并后的告警；否则返回 None
        """
        key = self._group_key(alert)
        now = time.time()

        # 清理过期缓冲
        self._expire_old(now)

        if key not in self.buffers:
            self.buffers[key] = MergedAlert(key)

        self.buffers[key].add(alert)

        # 达到阈值，输出合并告警
        if self.buffers[key].count >= self.threshold:
            merged = self.buffers[key].to_dict()
            del self.buffers[key]
            logger.info(f"Merged alert: {merged['count']}x {key}")
            return merged

        return None

    def _expire_old(self, now: float):
        """清理超过时间窗口的缓冲"""
        expired = [
            key for key, buf in self.buffers.items()
            if now - buf.first_seen > self.window
        ]
        for key in expired:
            del self.buffers[key]

    def suppress_child_alerts(self, alerts: List[Dict], impacted_nodes: List[str]) -> List[Dict]:
        """
        父子抑制：如果某个父节点故障，它下面所有子节点的告警都被抑制
        """
        filtered = []
        suppressed = []
        impacted_set = set(impacted_nodes)

        for alert in alerts:
            labels = alert.get("labels", {})
            # 尝试从标签中提取节点ID
            node_ref = (
                labels.get("container_id")
                or labels.get("vm_id")
                or labels.get("instance")
            )
            if node_ref and node_ref in impacted_set:
                suppressed.append(alert)
            else:
                filtered.append(alert)

        if suppressed:
            logger.info(f"Suppressed {len(suppressed)} child alerts due to parent failure")

        return filtered
