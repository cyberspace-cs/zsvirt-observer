"""资源拓扑图引擎 —— 维护 Host → VM → Container → Service → Agent 的依赖关系"""
import logging
from typing import Dict, List, Optional, Set

from app.models import NodeType

logger = logging.getLogger(__name__)


class TopologyGraph:
    """
    资源依赖有向图
    边的方向: child -> parent（子资源指向父资源）
    例如: container -> vm -> host
    """

    def __init__(self):
        self.nodes: Dict[str, Dict] = {}  # node_id -> {id, name, type, attrs}
        self.edges: Dict[str, str] = {}   # child_id -> parent_id
        self.children_map: Dict[str, List[str]] = {}  # parent_id -> [child_ids]

    def add_node(self, node_id: str, name: str, node_type: NodeType, attrs: Dict = None):
        self.nodes[node_id] = {
            "id": node_id,
            "name": name,
            "type": node_type,
            "attrs": attrs or {},
        }

    def add_edge(self, child_id: str, parent_id: str):
        """建立父子依赖: child 运行在 parent 之上"""
        if child_id not in self.nodes or parent_id not in self.nodes:
            logger.debug(f"Skipping edge {child_id} -> {parent_id}, node missing")
            return
        self.edges[child_id] = parent_id
        self.children_map.setdefault(parent_id, []).append(child_id)

    def get_parent(self, node_id: str) -> Optional[str]:
        return self.edges.get(node_id)

    def get_children(self, node_id: str) -> List[str]:
        """获取所有直接+间接子节点"""
        result = []
        stack = [node_id]
        visited = set()
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            for child in self.children_map.get(current, []):
                result.append(child)
                stack.append(child)
        return result

    def get_root_ancestor(self, node_id: str) -> str:
        """沿父链向上追溯，找到最顶层的根节点"""
        current = node_id
        while current in self.edges:
            current = self.edges[current]
        return current

    def get_ancestors(self, node_id: str) -> List[str]:
        """获取所有祖先节点（从近到远）"""
        result = []
        current = node_id
        while current in self.edges:
            current = self.edges[current]
            result.append(current)
        return result

    def find_node_by_label(self, label_key: str, label_value: str) -> Optional[str]:
        """根据标签值查找节点ID，例如 instance=10.0.0.5:9100"""
        for node_id, node in self.nodes.items():
            if node["attrs"].get(label_key) == label_value:
                return node_id
            if node_id == label_value or node["name"] == label_value:
                return node_id
        return None

    def build_from_zsvirt_data(self, hosts: List[Dict], vms: List[Dict], gpus: List[Dict] = None):
        """从 ZSvirt API 返回的数据构建拓扑"""
        self.nodes.clear()
        self.edges.clear()
        self.children_map.clear()

        # 1. 添加宿主机
        for host in hosts:
            host_id = host.get("uuid") or host.get("id") or host.get("name")
            self.add_node(
                node_id=host_id,
                name=host.get("name", host_id),
                node_type=NodeType.HOST,
                attrs=host,
            )

        # 2. 添加 GPU（挂在宿主机下）
        for gpu in (gpus or []):
            gpu_id = gpu.get("uuid") or gpu.get("id") or gpu.get("name")
            host_id = gpu.get("host_uuid") or gpu.get("host_id")
            self.add_node(
                node_id=gpu_id,
                name=gpu.get("name", gpu_id),
                node_type=NodeType.GPU,
                attrs=gpu,
            )
            if host_id:
                self.add_edge(gpu_id, host_id)

        # 3. 添加虚拟机（挂在宿主机下）
        for vm in vms:
            vm_id = vm.get("uuid") or vm.get("id") or vm.get("name")
            host_id = vm.get("host_uuid") or vm.get("host_id")
            self.add_node(
                node_id=vm_id,
                name=vm.get("name", vm_id),
                node_type=NodeType.VM,
                attrs=vm,
            )
            if host_id:
                self.add_edge(vm_id, host_id)

        logger.info(f"Topology built: {len(self.nodes)} nodes, {len(self.edges)} edges")

    def add_container(self, container_id: str, container_name: str, vm_id: str):
        """添加容器节点（运行在VM上）"""
        self.add_node(container_id, container_name, NodeType.CONTAINER)
        self.add_edge(container_id, vm_id)

    def add_service(self, service_id: str, service_name: str, container_id: str):
        """添加推理服务节点（运行在容器内）"""
        self.add_node(service_id, service_name, NodeType.SERVICE)
        self.add_edge(service_id, container_id)

    def add_agent(self, agent_id: str, agent_name: str, service_id: str):
        """添加 Agent 任务节点"""
        self.add_node(agent_id, agent_name, NodeType.AGENT)
        self.add_edge(agent_id, service_id)

    def stats(self) -> Dict:
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "by_type": self._count_by_type(),
        }

    def _count_by_type(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for node in self.nodes.values():
            t = node["type"]
            counts[t] = counts.get(t, 0) + 1
        return counts
