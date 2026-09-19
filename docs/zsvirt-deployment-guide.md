# ZSvirt 部署指南

本指南教你如何在本地或云上部署 ZSvirt，然后对接 ZSvirt Observer。

---

## 方案一：官方在线 Demo（最快，0成本）

**推荐先试这个！** 不用装任何东西，直接体验。

- 地址：https://demo.zsvirt.io
- 免注册、免安装，打开就能用
- 有完整的管理界面，可以创建虚拟机、管理集群

体验完之后，如果你要对接我们的可观测平台，再看下面的方案二/三。

---

## 方案二：本地 VirtualBox / VMware 跑（推荐）

如果你有一台笔记本电脑（Windows/Mac），用 VirtualBox 就能跑 ZSvirt 镜像。

### 硬件要求
- CPU：4核以上（支持 VT-x / AMD-V）
- 内存：8GB 以上
- 磁盘：50GB 以上空闲

### 步骤

1. **下载镜像**
   - 去 https://github.com/ZSvirt/zsvirt/releases 下载最新的 OVA 或 QCOW2 镜像
   - OVA 格式适合 VirtualBox / VMware
   - QCOW2 格式适合 KVM / QEMU

2. **导入 VirtualBox**
   ```bash
   # VirtualBox → 管理 → 导入虚拟电脑 → 选择 OVA 文件
   # CPU 分配 4 核，内存分配 8GB
   # 网卡设为「桥接模式」
   ```

3. **启动虚拟机**
   - 启动后等待 2-3 分钟，让服务全部起来
   - 控制台会显示管理界面的 IP 地址

4. **登录管理界面**
   - 浏览器打开控制台显示的 IP
   - 默认账号：admin / password（以官方文档为准）

5. **对接 ZSvirt Observer**
   ```bash
   # 编辑 .env 文件
   ZSVIRT_BASE_URL=http://<zsvirt-ip>:8080
   ZSVIRT_USERNAME=admin
   ZSVIRT_PASSWORD=你的密码
   ```

---

## 方案三：云服务器部署（生产级）

如果你要在云上跑真实环境，推荐用阿里云/腾讯云的 ECS。

### 云服务器要求

| 配置 | 最低 | 推荐 |
|---|---|---|
| CPU | 4核 | 8核 |
| 内存 | 8GB | 16GB |
| 磁盘 | 100GB | 200GB SSD |
| 网络 | 1Mbps | 5Mbps |
| 虚拟化 | 必须开启嵌套虚拟化 | 同左 |

**注意**：买 ECS 时一定要选「支持嵌套虚拟化」的实例规格，比如：
- 阿里云：g7 / c7 系列（开启嵌套虚拟化）
- 腾讯云：标准型 S5 / SA5

### 部署步骤

1. **买一台 ECS**
   - 操作系统选 CentOS 7.9 或 Ubuntu 22.04
   - 安全组开放 8080（ZSvirt）、8000（我们的平台）端口

2. **下载 ZSvirt ISO**
   ```bash
   # SSH 登录到 ECS
   wget https://github.com/ZSvirt/zsvirt/releases/download/v1.0/zsvirt.iso
   ```

3. **挂载 ISO 安装**
   - 把 ISO 挂载为光驱，重启服务器
   - 按安装向导走，大概 20 分钟装完
   - 装完后会显示管理界面地址

4. **初始化 ZSvirt**
   - 浏览器打开管理界面
   - 创建数据中心 → 集群 → 添加主机 → 添加存储
   - 创建几台测试虚拟机

5. **部署 ZSvirt Observer**
   ```bash
   # 在同一台 ECS 上部署我们的平台
   git clone https://github.com/cyberspace-cs/zsvirt-observer.git
   cd zsvirt-observer
   pip install -r requirements.txt

   # 配置 ZSvirt 地址
   cp .env.example .env
   # 编辑 .env，填入 ZSVIRT_BASE_URL=http://localhost:8080

   # 启动
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

---

## 验证对接成功

启动后，打开 http://<服务器IP>:8000/api/topology，应该能看到从 ZSvirt 拉取的真实拓扑数据，而不是 demo 数据。

---

## 常见问题

### Q: 为什么我的 ECS 跑不了 ZSvirt？
A: 99% 是因为没开嵌套虚拟化。买 ECS 时要选支持嵌套虚拟化的实例规格，或者联系云厂商客服开启。

### Q: 能不能用 Docker 跑 ZSvirt？
A: 不行。ZSvirt 是虚拟化平台，必须跑在 KVM 之上，不能用 Docker 容器跑。

### Q: 最小化能跑起来吗？
A: 可以，单节点 All-In-One 模式，4核8G 就够了，管理节点和计算节点在同一台机器上。

---

## 参考链接

- 官方网站：https://zsvirt.io
- GitHub：https://github.com/ZSvirt/zsvirt
- 在线 Demo：https://demo.zsvirt.io
- 官方文档：https://zstack.org/help/zstack_zsphere/
