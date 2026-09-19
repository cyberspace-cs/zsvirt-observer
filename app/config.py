"""应用配置"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "ZSvirt Observer"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # ZSvirt
    zsvirt_base_url: str = "http://localhost:5050"
    zsvirt_username: str = "admin"
    zsvirt_password: str = "password"

    # Prometheus
    prometheus_url: str = "http://prometheus:9090"

    # Alert
    alert_window_seconds: int = 300
    alert_group_threshold: int = 3

    # Topology sync interval (seconds)
    topology_sync_interval: int = 30

    # LLM
    llm_provider: str = "deepseek"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen-plus"
    ark_api_key: str = ""
    ark_model: str = "doubao-pro-4k"
    openrouter_api_key: str = ""
    openrouter_model: str = "deepseek/deepseek-chat"

    # OpenTelemetry
    otel_exporter_otlp_endpoint: str = "http://localhost:4318"
    otel_service_name: str = "zsvirt-observer"

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
