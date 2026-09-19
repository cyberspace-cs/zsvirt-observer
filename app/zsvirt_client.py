"""ZSvirt API 客户端"""
import logging
from typing import List, Dict, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class ZSVirtClient:
    """与 ZSvirt 管理节点交互的客户端"""

    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = (base_url or settings.zsvirt_base_url).rstrip("/")
        self.api_key = api_key or settings.zsvirt_api_key
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=10.0,
        )

    async def close(self):
        await self._client.aclose()

    # ---------- 宿主机 ----------

    async def list_hosts(self) -> List[Dict]:
        """获取所有宿主机"""
        try:
            r = await self._client.get("/v1/hosts")
            r.raise_for_status()
            data = r.json()
            return data.get("hosts", data if isinstance(data, list) else [])
        except Exception as e:
            logger.warning(f"Failed to list hosts: {e}")
            return []

    # ---------- 虚拟机 ----------

    async def list_vms(self) -> List[Dict]:
        """获取所有虚拟机及其所在宿主机"""
        try:
            r = await self._client.get("/v1/vms")
            r.raise_for_status()
            data = r.json()
            return data.get("vms", data if isinstance(data, list) else [])
        except Exception as e:
            logger.warning(f"Failed to list VMs: {e}")
            return []

    # ---------- GPU ----------

    async def list_gpus(self) -> List[Dict]:
        """获取 GPU 设备及其分配情况"""
        try:
            r = await self._client.get("/v1/gpus")
            r.raise_for_status()
            data = r.json()
            return data.get("gpus", data if isinstance(data, list) else [])
        except Exception as e:
            logger.warning(f"Failed to list GPUs: {e}")
            return []

    # ---------- 工具方法 ----------

    async def get_full_topology(self) -> Dict:
        """一次性获取完整拓扑信息"""
        hosts = await self.list_hosts()
        vms = await self.list_vms()
        gpus = await self.list_gpus()
        return {
            "hosts": hosts,
            "vms": vms,
            "gpus": gpus,
        }
