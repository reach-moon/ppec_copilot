# Deployment Guide

This guide provides instructions for deploying the PPEC Copilot application in different environments.

## Docker Deployment

### Prerequisites

- Docker Engine 20.10 or higher
- Docker Compose 1.29 or higher

### Quick Start

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd ppec_copilot
   ```

2. Configure environment variables:
   ```bash
   cp .env.docker .env
   # Edit .env file to set your specific configuration
   ```

3. Build and start the services:
   ```bash
   docker-compose -f docker-compose.production.yml up -d
   ```

4. Access the application:
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Configuration

The application requires several environment variables to be set. These are defined in the `.env.docker` file:

- `ONE_API_BASE_URL`: URL for your LLM API service
- `ONE_API_KEY`: API key for your LLM service
- `RAGFLOW_API_URL`: URL for your RAGFlow service
- `RAGFLOW_API_KEY`: API key for your RAGFlow service

### Services Overview

The Docker Compose setup includes:

1. **App Service**: The main PPEC Copilot application
2. **Qdrant Service**: Vector database for memory management

### Updating the Application

To update the application:

1. Pull the latest code:
   ```bash
   git pull
   ```

2. Rebuild and restart services:
   ```bash
   docker-compose -f docker-compose.production.yml down
   docker-compose -f docker-compose.production.yml up --build -d
   ```

## Manual Deployment

### Prerequisites

- Ubuntu 20.04/22.04 or CentOS 8/9
- At least 4GB memory (recommended 8GB)
- At least 20GB available disk space
- Docker 20.10+
- Docker Compose 1.27+

### Installation

```
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

### Quick Start

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd ppec_copilot
   ```

2. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env file to set your specific configuration
   ```

3. Build and start the services:
   ```bash
   docker-compose up -d
   ```

4. Access the application:
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Configuration

The application requires several environment variables to be set. These are defined in the `.env.example` file:

- `MEM_0_VECTOR_STORE_HOST`: Hostname for the vector store (e.g., "qdrant")
- `MEM_0_VECTOR_STORE_PORT`: Port for the vector store (e.g., 6333)
- `ONE_API_BASE_URL`: URL for your LLM API service
- `ONE_API_KEY`: API key for your LLM service
- `RAGFLOW_API_URL`: URL for your RAGFlow service
- `RAGFLOW_API_KEY`: API key for your RAGFlow service

### Services Overview

The Docker Compose setup includes:

1. **App Service**: The main PPEC Copilot application
2. **Qdrant Service**: Vector database for memory management

### Updating the Application

To update the application:

1. Pull the latest code:
   ```bash
   git pull
   ```

2. Rebuild and restart services:
   ```bash
   docker-compose down
   docker-compose up --build -d
   ```

## Local Development and Testing

### Windows Environment Notes

Due to Gunicorn's dependency on Unix-specific system calls, it cannot be run directly on Windows. For local development, use Uvicorn instead:

```
# 使用 Uvicorn 运行应用（开发模式）
uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8000

# 或者使用项目提供的脚本
python run_local.py --reload
```

### Local Testing Script

The project includes a local testing script [run_local.py](file:///D:/WorkSpaces/GitHub/reach-moon/ppec_copilot/run_local.py), which can be used to run the application locally:

```
# 给脚本添加执行权限（Unix/Linux/macOS）
chmod +x run_local.py

# 运行应用
python run_local.py

# 运行应用（开发模式，带自动重载）
python run_local.py --reload

# 指定主机和端口
python run_local.py --host 0.0.0.0 --port 8001
```

## Troubleshooting

### Common Issues

1. **Container fails to start**
   ```bash
   # 查看容器日志
   docker-compose logs app
   
   # 检查配置文件
   docker-compose exec app cat .env
   ```

2. **Port conflict**
   - Modify port mappings in `docker-compose.yml`
   - Check if any other services are using the port:
     ```bash
     netstat -tlnp | grep 8000
     ```

3. **Failed to connect to Qdrant**
   ```bash
   # 检查 Qdrant 容器状态
   docker-compose ps qdrant
   
   # 查看 Qdrant 日志
   docker-compose logs qdrant
   ```

4. **Gunicorn Worker fails to start**
   When you see an error like "Worker failed to boot", you can use the following debugging methods:
   ```bash
   # 使用调试模式启动简化版应用
   docker-compose -f docker-compose.debug.yml up
   
   # 或者进入容器手动运行应用
   docker-compose exec app python -m app.api.simple_main
   ```

### Debugging Tools

The project provides several debugging tools to help diagnose issues:

1. **Debugging Script**:
   ```bash
   # 给脚本添加执行权限
   chmod +x debug_docker.sh
   
   # 检查环境
   ./debug_docker.sh check
   
   # 构建镜像
   ./debug_docker.sh build
   
   # 启动调试服务
   ./debug_docker.sh debug
   
   # 查看调试日志
   ./debug_docker.sh dlogs
   ```

2. **Simplified Application**:
   The project includes a simplified entry file [app/api/simple_main.py](file:///D:/WorkSpaces/GitHub/reach-moon/ppec_copilot/app/api/simple_main.py), which can be used to rule out issues caused by complex configurations.

3. **Manual Application Run**:
   ```bash
   # 进入容器
   docker-compose exec app bash
   
   # 直接运行应用
   python -m app.api.simple_main
   ```

### Performance Tuning

1. **Adjust Gunicorn Worker Count**
   - Modify the `GUNICORN_WORKERS` value in the `.env` file
   - Recommended value: (CPU cores * 2) + 1

2. **Adjust Timeout Settings**
   - Modify the `GUNICORN_TIMEOUT` value in the `.env` file
   - For AI applications, recommend setting to 120 seconds or higher

3. **Resource Limits**
   Add resource limits in `docker-compose.yml` for services:
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

### Monitoring and Health Checks

```
# 检查应用健康状态
curl http://localhost:8000/health

# 查看系统资源使用情况
docker stats

# 查看容器详细信息
docker-compose inspect app
```

```
