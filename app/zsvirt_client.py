"""
ZSvirt / ZStack API 客户端

ZSvirt 基于 ZStack 虚拟化引擎，API 风格遵循 ZStack 规范：
- Base Path: /zstack/v1/
- 认证: POST /zstack/v1/accounts/login 获取 sessionUuid
- 之后所有请求带 header: Authorization: OAuth {sessionUuid}
- 异步任务: 大部分操作返回 jobUuid，需要轮询查询结果
"""
import logging
from typing import List, Dict, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class ZSVirtClient:
    """ZSvirt (ZStack) API 客户端"""

    def __init__(self, base_url: str = None, username: str = None, password: str = None):
        self.base_url = (base_url or settings.zsvirt_base_url).rstrip("/")
        self.username = username or settings.zsvirt_username
        self.password = password or settings.zsvirt_password
        self._session_uuid: Optional[str] = None
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=15.0,
        )

    async def close(self):
        await self._client.aclose()

    # ---------- 认证 ----------

    async def login(self) -> str:
        """登录获取 sessionUuid"""
        try:
            resp = await self._client.post(
                "/zstack/v1/accounts/login",
                json={
                    "username": self.username,
                    "password": self.password,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            self._session_uuid = data.get("inventory", {}).get("uuid")
            if not self._session_uuid:
                logger.error("Login failed: no sessionUuid in response")
            else:
                logger.info("ZSvirt login success")
            return self._session_uuid or ""
        except Exception as e:
            logger.error(f"ZSvirt login failed: {e}")
            return ""

    async def _ensure_auth(self):
        """确保已登录，没有则自动登录"""
        if not self._session_uuid:
            await self.login()

    async def _get(self, path: str, params: Dict = None) -> List[Dict]:
        """带认证的 GET 请求"""
        await self._ensure_auth()
        try:
            resp = await self._client.get(
                path,
                params=params or {},
                headers={"Authorization": f"OAuth {self._session_uuid}"},
            )
            resp.raise_for_status()
            data = resp.json()
            # ZStack API 通常返回 { "inventories": [...] } 或 { "results": [...] }
            if isinstance(data, list):
                return data
            for key in ("inventories", "results", "list", "hosts", "vms"):
                if key in data and isinstance(data[key], list):
                    return data[key]
            return [data] if isinstance(data, dict) else []
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                # token 过期，重新登录重试
                logger.info("Session expired, re-login...")
                self._session_uuid = None
                await self.login()
                return await self._get(path, params)
            logger.warning(f"API GET {path} failed: {e}")
            return []
        except Exception as e:
            logger.warning(f"API GET {path} error: {e}")
            return []

    # ---------- 宿主机 ----------

    async def list_hosts(self) -> List[Dict]:
        """获取所有宿主机"""
        return await self._get("/zstack/v1/hosts")

    # ---------- 虚拟机 ----------

    async def list_vms(self) -> List[Dict]:
        """获取所有虚拟机实例"""
        return await self._get("/zstack/v1/vm-instances")

    # ---------- 集群 ----------

    async def list_clusters(self) -> List[Dict]:
        """获取集群列表"""
        return await self._get("/zstack/v1/clusters")

    # ---------- 完整拓扑 ----------

    async def get_full_topology(self) -> Dict:
        """一次性获取完整拓扑数据"""
        hosts = await self.list_hosts()
        vms = await self.list_vms()
        clusters = await self.list_clusters()
        return {
            "hosts": hosts,
            "vms": vms,
            "clusters": clusters,
        }
