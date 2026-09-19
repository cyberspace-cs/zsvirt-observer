# 贡献指南

感谢你对 ZSvirt Observer 的关注！我们欢迎各种形式的贡献。

## 如何贡献

### 报告 Bug

如果你发现了 bug，请提交 Issue，并包含：
- 复现步骤
- 预期行为
- 实际行为
- 环境信息（OS、Python 版本等）

### 提交 PR

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交你的改动 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启一个 Pull Request

### 提交规范

我们使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

- `feat:` 新功能
- `fix:` 修复 bug
- `docs:` 文档更新
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建/工具相关

## 开发环境搭建

```bash
# 克隆仓库
git clone https://github.com/cyberspace-cs/zsvirt-observer.git
cd zsvirt-observer

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的配置

# 启动开发服务器
uvicorn app.main:app --reload
```

## 代码风格

- Python 代码遵循 PEP 8
- 使用 type hints
- 函数和类要有 docstring
- 关键逻辑要有注释

## 社区

- Issue: https://github.com/cyberspace-cs/zsvirt-observer/issues
- Discussions: https://github.com/cyberspace-cs/zsvirt-observer/discussions
