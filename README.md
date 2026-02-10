# Ephemeral Key API

临时 Key 管理 API 系统，用于解决外部协作临时接入、降低 Key 泄露风险，并支持自动过期和使用次数限制。

## ⚡ 快速启动指令

```bash
# 1. 启动服务
docker-compose up -d

# 2. 查看日志
docker-compose logs -f api

# 3. 运行测试
docker-compose exec api pytest -v --cov=app

# 4. 访问 API 文档
http://localhost:8000/docs
```

## � 本地开发 (非 Docker)

如果你希望在本地直接运行 (Windows/Mac/Linux):

1. **安装依赖**:
   ```bash
   pip install -r requirements.txt
   ```

2. **启动服务**:
   使用 `python -m` 模块方式启动，避免 path 问题，并确保 `.env` 生效 (已配置使用 FakeRedis 模拟数据库):
   ```bash
   python -m uvicorn app.main:app --reload
   ```

3. **运行测试**:
   ```bash
   python -m pytest -v --cov=app
   ```

## �🛠️ 技术栈

| 类别 | 技术 | 版本要求 |
|------|------|----------|
| 后端框架 | FastAPI | 0.109+ |
| 编程语言 | Python | 3.11+ |
| 数据存储 | Redis | 7.2+ |
| 容器化 | Docker Compose | - |
| 测试框架 | Pytest + HTTPX | - |
