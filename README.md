# ZSvirt Observer

> **AI 驱动的全栈根因诊断平台** —— 从告警到根因，从 45 分钟到 30 秒

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)

---

## 🎯 解决什么问题

在 AI 基础设施环境中，一次故障从**宿主机 → GPU → 虚拟机 → 容器 → 推理服务 → Agent**，跨越 5 层技术栈。传统监控工具只能看到单点告警，SRE 需要花 **45 分钟以上** 才能定位根因。

**ZSvirt Observer** 用 AI 把这个过程压缩到 **30 秒**：

- ✅ **全链路打通**：宿主机 → GPU → 虚拟机 → 容器 → AI 服务 → Agent
- ✅ **AI 根因推理**：LLM 深度分析，不是简单规则匹配
- ✅ **智能告警降噪**：父子抑制 + 语义关联，告别告警轰炸
- ✅ **自动修复建议**：不仅告诉你问题在哪，还告诉你怎么修

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                      被观测对象层                          │
│  宿主机 → GPU → 虚拟机 → 容器 → 推理服务 → Agent        │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                        采集层                            │
│  node_exporter · cAdvisor · DCGM Exporter · OTel       │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                     AI 核心分析层                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ 拓扑关联引擎  │  │ 智能降噪引擎 │  │ LLM 根因推理    │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                        展示层                            │
│  Grafana 仪表盘 · Web 根因报告 · 告警时间线              │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 前置要求

- Python 3.11+
- Docker & Docker Compose（可选，用于完整监控栈）

### 1. 克隆并安装

```bash
git clone https://github.com/cyberspace-cs/zsvirt-observer.git
cd zsvirt-observer

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 LLM API Key（支持 DeepSeek / Qwen / OpenRouter）
```

### 3. 启动服务

```bash
uvicorn app.main:app --reload
```

打开 http://localhost:8000 即可看到演示界面。

### 4. 一键体验

点击页面上的 **「一键制造故障」** 按钮，30 秒内看到 AI 自动完成根因诊断。

---

## 📁 项目结构

```
zsvirt-observer/
├── app/                        # 核心 Python 服务
│   ├── main.py                # FastAPI 入口
│   ├── correlator.py          # AI 根因分析引擎
│   ├── topology.py            # 资源拓扑图引擎
│   ├── alert_merger.py       # 智能告警降噪
│   ├── llm_client.py         # 多模型 LLM 客户端
│   ├── zsvirt_client.py       # ZSvirt API 对接
│   └── config.py             # 配置管理
├── web/                        # 前端演示页面
├── collector/                  # Prometheus / OTel / Grafana 配置
├── dashboards/                 # Grafana 面板 JSON
├── demo/                       # 演示脚本
│   ├── agent_demo.py          # AI Agent 可观测性 Demo
│   └── inject_fault.py        # 故障注入工具
├── docker-compose.yml          # 一键启动完整监控栈
└── requirements.txt
```

---

## 🧠 核心技术亮点

### 1. AI 核心根因推理

不是简单的"向上找父节点"规则引擎，而是把完整拓扑 + 告警上下文喂给 LLM，让模型真正理解故障因果链，输出：
- 最可能根因 + 置信度
- 推理过程（排除了哪些其他可能）
- 可执行的修复命令

### 2. 全栈资源关联

自动维护 **宿主机 → GPU → 虚拟机 → 容器 → 服务 → Agent** 的依赖图，告警发生时自动沿链路下钻。

### 3. 智能告警降噪

- **父子抑制**：父节点故障时，子节点告警自动抑制
- **时间聚合**：5 分钟窗口内同类告警合并
- **语义关联**：LLM 判断哪些告警是同一根因

### 4. 多模型支持

一套接口，支持多家 LLM 提供商：
- DeepSeek（推荐，性价比高）
- 阿里云百炼 Qwen
- 火山方舟 Doubao
- OpenRouter

---

## 📊 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python · FastAPI · Pydantic |
| AI | DeepSeek / Qwen / OpenRouter · OpenTelemetry |
| 采集 | node_exporter · cAdvisor · DCGM · OTel Collector |
| 存储 | Prometheus · SQLite |
| 展示 | Grafana · 原生 HTML/JS |

---

## 🗺️ 开发路线

- [x] 核心框架搭建
- [x] AI 根因分析引擎
- [x] 智能告警降噪
- [x] 演示前端页面
- [x] AI Agent 可观测性接入
- [ ] ZSvirt 真实环境对接
- [ ] eBPF 深度采集
- [ ] 自动修复执行
- [ ] 企业级部署方案

---

## 🤝 贡献

欢迎各种形式的贡献！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

---

## 📄 License

[MIT](LICENSE) © cyberspace-cs
