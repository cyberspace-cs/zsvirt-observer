"""数据模型定义"""
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel


class NodeType(str, Enum):
    HOST = "host"
    VM = "vm"
    GPU = "gpu"
    CONTAINER = "container"
    SERVICE = "service"
    AGENT = "agent"


class TopologyNode(BaseModel):
    id: str
    name: str
    type: NodeType
    attrs: Dict = {}
    parent_id: Optional[str] = None


class Alert(BaseModel):
    alertname: str
    severity: str = "warning"
    status: str = "firing"
    description: str = ""
    instance: str = ""
    container_id: Optional[str] = None
    vm_id: Optional[str] = None
    starts_at: Optional[datetime] = None
    labels: Dict = {}


class RootCauseReport(BaseModel):
    root_node_id: str
    root_node_name: str
    root_node_type: NodeType
    summary: str
    impacted_resources: List[str] = []
    related_alerts: List[Dict] = []
    suggestion: str = ""
    generated_at: datetime = None

    model_config = {"arbitrary_types_allowed": True}
