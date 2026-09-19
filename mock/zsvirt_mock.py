#!/usr/bin/env python3
"""
ZSvirt Mock Server

模拟 ZSvirt (ZStack) 的真实 API 返回数据，用于本地开发和演示。
真实环境部署时，只需修改 .env 中的 ZSVIRT_BASE_URL 指向真实节点即可。

启动: python mock/zsvirt_mock.py
端口: 5050
"""
import json
import time
import uuid
import logging
from datetime import datetime

from fastapi import FastAPI, HTTPException, Header
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="ZSvirt Mock API", version="1.0.0")

# ========== 模拟数据 ==========

CLUSTERS = [
    {
        "uuid": "cluster-001",
        "name": "GPU集群-A",
        "description": "AI推理专用集群",
        "state": "Enabled",
        "hypervisorType": "KVM",
    },
    {
        "uuid": "cluster-002",
        "name": "通用集群-B",
        "description": "通用业务集群",
        "state": "Enabled",
        "hypervisorType": "KVM",
    },
]

HOSTS = [
    {
        "uuid": "host-001",
        "name": "GPU-Node-01",
        "description": "GPU 计算节点 1",
        "managementIp": "10.0.1.11",
        "clusterUuid": "cluster-001",
        "state": "Connected",
        "hypervisorType": "KVM",
        "totalCpuCapacity": 64,
        "availableCpuCapacity": 32,
        "totalMemoryCapacity": 274877906944,
        "availableMemoryCapacity": 137438953472,
        "cpuSockets": 2,
        "cpuSpeed": 3000,
    },
    {
        "uuid": "host-002",
        "name": "GPU-Node-02",
        "description": "GPU 计算节点 2",
        "managementIp": "10.0.1.12",
        "clusterUuid": "cluster-001",
        "state": "Connected",
        "hypervisorType": "KVM",
        "totalCpuCapacity": 64,
        "availableCpuCapacity": 48,
        "totalMemoryCapacity": 274877906944,
        "availableMemoryCapacity": 206158430208,
        "cpuSockets": 2,
        "cpuSpeed": 3000,
    },
    {
        "uuid": "host-003",
        "name": "Web-Node-01",
        "description": "Web 业务节点",
        "managementIp": "10.0.2.11",
        "clusterUuid": "cluster-002",
        "state": "Connected",
        "hypervisorType": "KVM",
        "totalCpuCapacity": 32,
        "availableCpuCapacity": 24,
        "totalMemoryCapacity": 137438953472,
        "availableMemoryCapacity": 103079215104,
        "cpuSockets": 1,
        "cpuSpeed": 2500,
    },
]

VMS = [
    {
        "uuid": "vm-001",
        "name": "llm-inference-v1",
        "description": "LLM 推理服务实例",
        "hostUuid": "host-001",
        "clusterUuid": "cluster-001",
        "state": "Running",
        "instanceOfferingUuid": "offering-gpu-32c",
        "cpuNum": 32,
        "memorySize": 68719476736,
        "vmNics": [
            {"uuid": "nic-001", "ip": "172.16.1.10", "mac": "00:0c:29:1a:2b:01"}
        ],
        "gpuNum": 2,
    },
    {
        "uuid": "vm-002",
        "name": "rag-service-v1",
        "description": "RAG 检索服务",
        "hostUuid": "host-001",
        "clusterUuid": "cluster-001",
        "state": "Running",
        "instanceOfferingUuid": "offering-gpu-16c",
        "cpuNum": 16,
        "memorySize": 34359738368,
        "vmNics": [
            {"uuid": "nic-002", "ip": "172.16.1.11", "mac": "00:0c:29:1a:2b:02"}
        ],
        "gpuNum": 1,
    },
    {
        "uuid": "vm-003",
        "name": "llm-inference-v2",
        "description": "备用 LLM 推理节点",
        "hostUuid": "host-002",
        "clusterUuid": "cluster-001",
        "state": "Running",
        "instanceOfferingUuid": "offering-gpu-32c",
        "cpuNum": 32,
        "memorySize": 68719476736,
        "vmNics": [
            {"uuid": "nic-003", "ip": "172.16.2.10", "mac": "00:0c:29:1a:2b:03"}
        ],
        "gpuNum": 2,
    },
    {
        "uuid": "vm-004",
        "name": "web-backend-v1",
        "description": "Web 后端服务",
        "hostUuid": "host-003",
        "clusterUuid": "cluster-002",
        "state": "Running",
        "instanceOfferingUuid": "offering-8c16g",
        "cpuNum": 8,
        "memorySize": 17179869184,
        "vmNics": [
            {"uuid": "nic-004", "ip": "172.16.3.10", "mac": "00:0c:29:1a:2b:04"}
        ],
        "gpuNum": 0,
    },
]

# ========== 认证 ==========

SESSION_TOKEN = "mock-session-uuid-12345"


@app.post("/zstack/v1/accounts/login")
async def login(body: dict):
    """模拟登录接口"""
    username = body.get("username", "")
    password = body.get("password", "")
    logger.info(f"Login attempt: {username}")
    return {
        "inventory": {
            "uuid": SESSION_TOKEN,
            "accountName": username,
            "realName": "Admin",
            "type": "UserAccount",
        }
    }


def verify_auth(authorization: str = Header(None)):
    """验证 OAuth token (ZStack 格式: OAuth {sessionUuid})"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return authorization


# ========== API 接口 ==========

@app.get("/zstack/v1/hosts")
async def list_hosts(auth: str = Depends(verify_auth)):
    """获取宿主机列表"""
    logger.info(f"GET /hosts → {len(HOSTS)} hosts")
    return {"inventories": HOSTS}


@app.get("/zstack/v1/vm-instances")
async def list_vms(auth: str = Depends(verify_auth)):
    """获取虚拟机列表"""
    logger.info(f"GET /vm-instances → {len(VMS)} VMs")
    return {"inventories": VMS}


@app.get("/zstack/v1/clusters")
async def list_clusters(auth: str = Depends(verify_auth)):
    """获取集群列表"""
    return {"inventories": CLUSTERS}


@app.get("/zstack/v1/instance-offerings")
async def list_offerings(auth: str = Depends(verify_auth)):
    """获取计算规格"""
    return {
        "inventories": [
            {"uuid": "offering-gpu-32c", "name": "GPU 32核64G", "cpuNum": 32, "memorySize": 68719476736},
            {"uuid": "offering-gpu-16c", "name": "GPU 16核32G", "cpuNum": 16, "memorySize": 34359738368},
            {"uuid": "offering-8c16g", "name": "通用 8核16G", "cpuNum": 8, "memorySize": 17179869184},
        ]
    }


@app.get("/zstack/v1/gpus")
async def list_gpus(auth: str = Depends(verify_auth)):
    """获取 GPU 列表"""
    return {
        "inventories": [
            {"uuid": "gpu-001", "name": "NVIDIA-A100-01", "hostUuid": "host-001", "vendor": "NVIDIA"},
            {"uuid": "gpu-002", "name": "NVIDIA-A100-02", "hostUuid": "host-001", "vendor": "NVIDIA"},
            {"uuid": "gpu-003", "name": "NVIDIA-A100-03", "hostUuid": "host-002", "vendor": "NVIDIA"},
            {"uuid": "gpu-004", "name": "NVIDIA-A100-04", "hostUuid": "host-002", "vendor": "NVIDIA"},
        ]
    }


# ========== 启动 ==========

if __name__ == "__main__":
    print("=" * 50)
    print("  ZSvirt Mock Server")
    print("=" * 50)
    print(f"  Port: 5050")
    print(f"  Hosts: {len(HOSTS)}")
    print(f"  VMs: {len(VMS)}")
    print(f"  Clusters: {len(CLUSTERS)}")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=5050)
