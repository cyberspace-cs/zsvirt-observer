"""ZSvirt Observer - FastAPI 主入口"""
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.topology import TopologyGraph
from app.zsvirt_client import ZSVirtClient
from app.correlator import RootCauseAnalyzer

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

# 全局实例
graph = TopologyGraph()
zsvirt = ZSVirtClient()
analyzer = RootCauseAnalyzer(graph)
sync_task: asyncio.Task = None

WEB_DIR = Path(__file__).parent.parent / "web"


async def sync_topology():
    """定时从 ZSvirt 同步拓扑信息"""
    while True:
        try:
            data = await zsvirt.get_full_topology()
            hosts = data.get("hosts", [])
            vms = data.get("vms", [])
            # 只有拿到真实数据时才更新，避免空数据清掉 demo 拓扑
            if hosts or vms:
                graph.build_from_zsvirt_data(
                    hosts=hosts,
                    vms=vms,
                    gpus=data.get("gpus", []),
                )
                logger.info(f"Topology synced: {graph.stats()}")
            else:
                logger.debug("ZSvirt returned empty data, keeping demo topology")
        except Exception as e:
            logger.warning(f"Topology sync failed: {e}")
        await asyncio.sleep(settings.topology_sync_interval)


def seed_demo_topology():
    """填充演示用的模拟拓扑数据（无真实 ZSvirt 环境时使用）"""
    # Hosts
    graph.add_node("host-01", "物理服务器-01", "host", {"ip": "10.0.0.1"})
    graph.add_node("host-02", "物理服务器-02", "host", {"ip": "10.0.0.2"})

    # VMs (挂在 Host 下)
    graph.add_node("vm-01", "AI推理VM-01", "vm", {"cpu": "16", "mem": "64G"})
    graph.add_node("vm-02", "AI推理VM-02", "vm", {"cpu": "32", "mem": "128G"})
    graph.add_node("vm-03", "应用VM-01", "vm", {"cpu": "8", "mem": "16G"})
    graph.add_edge("vm-01", "host-01")
    graph.add_edge("vm-02", "host-01")
    graph.add_edge("vm-03", "host-02")

    # Containers (挂在 VM 下)
    graph.add_container("container-01", "llm-inference-v1", "vm-01")
    graph.add_container("container-02", "rag-service-v1", "vm-01")
    graph.add_container("container-03", "llm-inference-v2", "vm-02")
    graph.add_container("container-04", "web-app-v1", "vm-03")

    # Services (挂在 Container 下)
    graph.add_service("service-01", "Qwen-Inference", "container-01")
    graph.add_service("service-02", "RAG-Retriever", "container-02")
    graph.add_service("service-03", "Llama-Inference", "container-03")
    graph.add_service("service-04", "Web-Backend", "container-04")

    # Agents (挂在 Service 下)
    graph.add_agent("agent-01", "客服Agent", "service-01")
    graph.add_agent("agent-02", "代码助手Agent", "service-01")
    graph.add_agent("agent-03", "知识库问答Agent", "service-02")

    logger.info(f"Demo topology seeded: {graph.stats()}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global sync_task
    logger.info("Starting ZSVirt Observer...")

    # 先填充演示数据，保证即使没连上 ZSvirt 也有东西看
    seed_demo_topology()

    # 启动定时同步
    sync_task = asyncio.create_task(sync_topology())
    yield

    if sync_task:
        sync_task.cancel()
    await zsvirt.close()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.app_name,
    description="全栈可观测平台 - 根因分析引擎",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== 页面路由 ==========

@app.get("/")
async def index():
    """前端页面"""
    index_file = WEB_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"name": settings.app_name, "version": "0.2.0", "status": "running"}


# ========== API 路由 ==========

@app.get("/api/topology")
async def get_topology():
    """返回完整资源拓扑"""
    return {
        "nodes": list(graph.nodes.values()),
        "edges": [{"child": c, "parent": p} for c, p in graph.edges.items()],
        "stats": graph.stats(),
    }


@app.get("/api/topology/stats")
async def get_topology_stats():
    return graph.stats()


@app.post("/webhook/alerts")
async def receive_alert(request: Request):
    """
    Prometheus AlertManager Webhook 接收端点
    接收告警后自动执行根因分析
    """
    payload = await request.json()
    alerts = payload.get("alerts", [])
    results = []

    for alert in alerts:
        analyzer.record_alert(alert)
        report = await analyzer.analyze(alert)
        results.append({
            "alertname": alert.get("labels", {}).get("alertname"),
            "root_cause": report.root_node_name,
            "root_type": report.root_node_type.value,
            "summary": report.summary,
            "impacted": len(report.impacted_resources),
            "suggestion": report.suggestion,
        })

    return {"analyzed": len(alerts), "results": results}


@app.get("/health")
async def health():
    return {"status": "healthy", "topology_nodes": len(graph.nodes)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )
