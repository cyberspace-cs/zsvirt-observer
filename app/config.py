"""应用配置"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "ZSvirt Observer"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # ZSvirt
    zsvirt_base_url: str = "http://localhost:5050"
    zsvirt_api_key: str = ""

    # Prometheus
    prometheus_url: str = "http://prometheus:9090"

    # Alert
    alert_window_seconds: int = 300
    alert_group_threshold: int = 3

    # Topology sync interval (seconds)
    topology_sync_interval: int = 30

    class Config:
        env_file = ".env"


settings = Settings()
