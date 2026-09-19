"""ZSvirt Observer - FastAPI 主入口"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.topology import TopologyGraph
from app.zsvirt_client import ZSVirtClient
from app.correlator import RootCauseAnalyzer
from app.report import format_report_markdown, format_report_text

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

# 全局实例
graph = TopologyGraph()
zsvirt = ZSVirtClient()
analyzer = RootCauseAnalyzer(graph)
sync_task: asyncio.Task = None


async def sync_topology():
    """定时从 ZSvirt 同步拓扑信息"""
    while True:
        try:
            data = await zsvirt.get_full_topology()
            graph.build_from_zsvirt_data(
                hosts=data.get("hosts", []),
                vms=data.get("vms", []),
                gpus=data.get("gpus", []),
            )
            logger.info(f"Topology synced: {graph.stats()}")
        except Exception as e:
            logger.warning(f"Topology sync failed: {e}")
        await asyncio.sleep(settings.topology_sync_interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global sync_task
    logger.info("Starting ZSVirt Observer...")
    sync_task = asyncio.create_task(sync_topology())
    yield
    if sync_task:
        sync_task.cancel()
    await zsvirt.close()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.app_name,
    description="全栈可观测平台 - 根因分析引擎",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== API 路由 ==========

@app.get("/")
async def root():
    return {"name": settings.app_name, "version": "0.1.0", "status": "running"}


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
        # 记录告警历史
        analyzer.record_alert(alert)
        # 执行根因分析
        report = analyzer.analyze(alert)
        results.append({
            "alertname": alert.get("labels", {}).get("alertname"),
            "root_cause": report.root_node_name,
            "root_type": report.root_node_type.value,
            "summary": report.summary,
            "impacted": len(report.impacted_resources),
            "suggestion": report.suggestion,
        })

    return {"analyzed": len(alerts), "results": results}


@app.get("/api/report/{alert_name}")
async def get_report(alert_name: str, format: str = "text"):
    """获取根因报告（文本/Markdown）"""
    # 这里简化：返回最近一次分析结果
    return {"alertname": alert_name, "message": "Report endpoint - use webhook for live analysis"}


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
