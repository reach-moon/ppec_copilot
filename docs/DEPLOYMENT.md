# PPEC Copilot 远程服务器部署指南

本文档详细说明了如何在远程服务器上构建和部署 PPEC Copilot 应用的 Docker 镜像服务。

## 目录

- [部署架构](#部署架构)
- [服务器准备](#服务器准备)
- [代码传输](#代码传输)
- [构建 Docker 镜像](#构建-docker-镜像)
- [运行服务](#运行服务)
- [服务管理](#服务管理)
- [日志查看](#日志查看)
- [故障排除](#故障排除)

## 部署架构

在远程服务器上，PPEC Copilot 应用将通过 Docker 运行以下服务：

1. **主应用容器** - 运行 PPEC Copilot 应用
2. **Qdrant 容器** - 向量数据库服务
3. **可选：Nginx 容器** - 反向代理（当前未启用）

所有服务通过 Docker 网络进行通信。

## 服务器准备

### 系统要求
- Ubuntu 20.04/22.04 或 CentOS 8/9
- 至少 4GB 内存（推荐 8GB）
- 至少 20GB 可用磁盘空间
- Docker 20.10+
- Docker Compose 1.27+

### 安装 Docker 和 Docker Compose

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io docker-compose -y

# 或者使用官方安装脚本
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 启动 Docker 服务
sudo systemctl start docker
sudo systemctl enable docker

# 将当前用户添加到 docker 组
sudo usermod -aG docker $USER
# 注销并重新登录以使组更改生效
```

## 代码传输

有几种方式可以将代码传输到远程服务器：

### 方法一：使用 Git 克隆（推荐）

```bash
# 在远程服务器上执行
git clone <your-repository-url>
cd ppec_copilot
```

### 方法二：使用 SCP 传输

```bash
# 在本地执行
scp -r /path/to/ppec_copilot user@remote_server:/path/to/destination
```

### 方法三：使用 rsync 同步

```bash
# 在本地执行
rsync -avz --progress /path/to/ppec_copilot user@remote_server:/path/to/destination
```

## 构建 Docker 镜像

连接到远程服务器并导航到项目目录：

```bash
cd /path/to/ppec_copilot
```

### 配置环境变量

1. 复制示例配置文件：
   ```bash
   cp .env.example .env
   ```

2. 编辑 .env 文件，根据服务器环境修改配置：
   ```bash
   nano .env
   ```

   关键配置项：
   - `MEM_0_VECTOR_STORE_HOST` - 应设置为 "qdrant"（Docker 服务名）
   - `MEM_0_VECTOR_STORE_PORT` - 保持为 6333
   - `ONE_API_BASE_URL` - LLM API 地址
   - `ONE_API_KEY` - LLM API 密钥
   - `RAGFLOW_API_URL` - RAGFlow API 地址
   - `RAGFLOW_API_KEY` - RAGFlow API 密钥

### 构建镜像

```bash
# 构建应用 Docker 镜像
docker-compose --build -d
```

## 运行服务

### 启动服务

```bash
# 在后台启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps
```

### 验证服务运行

```bash
# 检查应用容器日志
docker-compose logs app

# 检查 Qdrant 容器日志
docker-compose logs qdrant

# 检查端口是否监听
netstat -tlnp | grep 8000
netstat -tlnp | grep 6333
```

### 访问应用

服务启动后，可以通过以下方式访问：

1. 直接访问应用：http://your-server-ip:8000
2. Qdrant 控制台：http://your-server-ip:6333/dashboard

## 服务管理

### 常用命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看服务状态
docker-compose ps

# 查看实时日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f app
docker-compose logs -f qdrant
```

### 更新部署

当有代码更新时：

```bash
# 拉取最新代码
git pull

# 重新构建镜像
docker-compose build

# 重启服务
docker-compose down
docker-compose up -d
```

### 备份和恢复

```bash
# 备份 Qdrant 数据
docker-compose exec qdrant tar -czf /qdrant_backup.tar.gz /qdrant/storage

# 将备份文件复制到本地
docker cp ppec_copilot_qdrant_1:/qdrant_backup.tar.gz ./qdrant_backup.tar.gz
```

## 日志查看

### 实时日志查看

```bash
# 查看所有服务的实时日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f app
docker-compose logs -f qdrant
```

### 日志文件位置

在容器内部，日志文件位于：
- 应用日志: `/home/appuser/app/logs/app.log`
- Gunicorn 访问日志: 根据配置文件位置
- Gunicorn 错误日志: 根据配置文件位置

可以通过以下方式访问容器内的日志文件：

```bash
# 进入应用容器
docker-compose exec app bash

# 查看日志文件
cat logs/app.log
```

## 故障排除

### 常见问题

1. **容器无法启动**
   ```bash
   # 查看容器日志
   docker-compose logs app
   
   # 检查配置文件
   docker-compose exec app cat .env
   ```

2. **端口冲突**
   - 修改 docker-compose.yml 中的端口映射
   - 检查服务器上是否已有服务占用端口：
     ```bash
     netstat -tlnp | grep 8000
     ```

3. **连接 Qdrant 失败**
   ```bash
   # 检查 Qdrant 容器状态
   docker-compose ps qdrant
   
   # 查看 Qdrant 日志
   docker-compose logs qdrant
   ```

4. **内存不足**
   - 检查服务器内存使用情况：
     ```bash
     free -h
     ```
   - 调整 docker-compose.yml 中的服务资源限制

5. **权限问题**
   - 确保当前用户在 docker 组中
   - 检查文件权限：
     ```bash
     ls -la .env
     ```

### 性能调优

1. **调整 Gunicorn 工作进程数**
   - 在 .env 文件中修改 `GUNICORN_WORKERS` 值
   - 建议值为 (CPU 核心数 * 2) + 1

2. **调整超时设置**
   - 在 .env 文件中修改 `GUNICORN_TIMEOUT` 值
   - 对于 AI 应用，建议设置为 120 秒或更高

3. **资源限制**
   在 docker-compose.yml 中为服务添加资源限制：
   ```yaml
   app:
     # ... 其他配置 ...
     deploy:
       resources:
         limits:
           memory: 2G
         reservations:
           memory: 1G
   ```

### 监控和健康检查

```bash
# 检查应用健康状态
curl http://localhost:8000/health

# 查看系统资源使用情况
docker stats

# 查看容器详细信息
docker-compose inspect app
```

通过以上步骤，您可以在远程服务器上成功部署和运行 PPEC Copilot 应用。