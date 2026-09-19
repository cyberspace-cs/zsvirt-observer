# ZSVirt Observer

> 面向 ZSvirt 虚拟化底座的全栈可观测平台 —— 打通 宿主机→GPU→虚拟机→容器→AI服务→Agent 全链路

## 🏗️ 项目背景

本项目为 **2026 上海开源软件应用创新大赛 · 智算云赛道** 参赛作品。

针对 ZSvirt 虚拟化环境下，从基础设施到 AI Agent 的全栈可观测性缺失问题，构建一套轻量级、可落地的全链路可观测方案，实现：

- **资源全链路关联**：宿主机 → GPU → 虚拟机 → 容器 → AI 推理服务 → Agent 任务
- **多信号统一采集**：指标、日志、Trace 三类信号统一接入
- **智能根因定位**：告警自动关联，沿依赖链向下钻取定位根因
- **告警降噪**：聚合、静默、父子抑制，告别告警轰炸

## 🚀 快速开始

### 前置要求

- Docker & Docker Compose
- 一台 ZSvirt 管理节点（或本地测试环境）

### 一键启动

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 ZSvirt API 地址和密钥

# 2. 启动全部服务
docker-compose up -d

# 3. 访问
# Grafana: http://localhost:3000
# Observer API: http://localhost:8000
# Prometheus: http://localhost:9090
```

## 📁 项目结构

```
zsvirt-observer/
├── app/                    # 核心 Python 服务
│   ├── main.py            # FastAPI 入口
│   ├── config.py          # 配置管理
│   ├── models.py          # 数据模型
│   ├── zsvirt_client.py   # ZSvirt API 客户端
│   ├── topology.py        # 资源拓扑图引擎
│   ├── correlator.py      # 根因分析引擎
│   ├── alert_merger.py    # 告警聚合降噪
│   └── report.py          # 根因报告生成
├── collector/              # 采集配置
│   ├── prometheus.yml
│   ├── otel-collector.yaml
│   └── grafana/           # Grafana 自动配置
├── dashboards/             # Grafana 面板 JSON
├── demo/                   # 故障注入演示
│   └── inject_fault.py
├── docker-compose.yml      # 一键启动
└── requirements.txt        # Python 依赖
```

## 🧠 核心设计

### 资源拓扑模型

维护一棵 **有向无环图**，表达资源依赖关系：

```
Host (宿主机)
  └── VM (虚拟机)
       └── Container (容器)
            └── Service (推理服务)
                 └── Agent (智能体任务)
```

当告警发生时，沿依赖链向上追溯，找到最顶层的异常节点即为根因。

### 告警关联策略

1. **父子抑制**：父节点告警时，子节点告警自动抑制
2. **时间聚合**：5分钟窗口内同类告警合并为一条
3. **根因下钻**：从告警节点沿拓扑图向上，找到第一个"独立异常"的节点

## 📊 技术栈

| 层 | 技术 |
|---|---|
| 采集 | node_exporter, cAdvisor, DCGM Exporter, OTel Collector |
| 存储 | Prometheus, SQLite |
| 关联引擎 | Python (FastAPI) |
| 展示 | Grafana + 自研根因面板 |

## 📅 开发路线

- [x] Day 1-2: 环境搭建 + 基础指标采集
- [ ] Day 3-7: 资源拓扑引擎 + ZSvirt 对接
- [ ] Day 8-10: AI Agent Trace 接入
- [ ] Day 11-14: 根因分析 + 告警降噪
- [ ] Day 15-18: Demo 打磨 + 故障注入
- [ ] Day 19-22: 路演准备 + 提交

## 📄 License

MIT
