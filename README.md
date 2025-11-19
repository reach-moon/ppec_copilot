# PPEC Copilot

PPEC Copilot 是一个基于 AI 的智能助手，专为 PPEC 平台设计，提供智能问答、任务规划和执行等功能。

## 目录结构

```
ppec_copilot/
├── app/                          # 应用核心代码
│   ├── api/                      # API 接口层 (FastAPI)
│   │   ├── endpoints/            # API 路由定义
│   │   │   └── v1/               # API v1 版本
│   │   │       ├── chat.py       # 聊天接口
│   │   │       ├── models.py     # 数据模型
│   │   │       └── revert.py     # 回滚接口
│   │   ├── exception_handlers.py # 全局异常处理
│   │   └── main.py               # FastAPI 应用实例和主入口
│   ├── core/                     # 核心业务逻辑
│   │   ├── agents/               # 各类 Agent 实现
│   │   │   ├── hierarchical_planner.py  # 分层规划器
│   │   │   ├── rag_expert.py     # RAG 专家 Agent
│   │   │   └── code_expert.py    # 代码专家 Agent
│   │   ├── graphs/               # LangGraph 工作流
│   │   │   └── main_graph.py     # 主工作流图
│   │   ├── mem0_client.py        # Mem0 客户端
│   │   ├── http_client.py        # HTTP 客户端
│   │   ├── logging_config.py     # 日志配置
│   │   ├── exceptions.py         # 自定义异常
│   │   └── __init__.py
│   ├── schemas/                  # 数据模型定义
│   │   └── graph_state.py        # 图状态定义
│   ├── services/                 # 外部服务封装
│   │   ├── tools/                # 工具实现
│   │   │   ├── mem0_service.py   # Mem0 服务
│   │   │   └── ragflow_tools.py  # RAGFlow 工具
│   │   └── llm_service.py        # LLM 服务
│   └── static/                   # 静态文件
│       └── chat.html             # 聊天界面
├── config/                       # 配置文件
│   └── settings.py               # 应用配置
├── logs/                         # 日志文件目录
├── tests/                        # 测试文件
│   ├── unit/                     # 单元测试
│   ├── component/                # 组件测试
│   ├── integration/              # 集成测试
│   └── e2e/                      # 端到端测试
├── .env.example                  # 环境变量示例
├── .gitignore                    # Git 忽略文件
├── ARCHITECTURE_ANALYSIS.md      # 架构分析文档
├── docker-compose.yml            # Docker Compose 配置
├── Dockerfile                    # Docker 镜像构建文件
├── gunicorn_conf.py              # Gunicorn 配置
├── nginx.conf                    # Nginx 配置
├── pytest.ini                    # Pytest 配置
├── requirements.txt              # Python 依赖
└── TESTING_FRAMEWORK.md          # 测试框架文档
```

## 功能特性

- **智能问答**: 基于 RAG 技术的知识问答系统
- **任务规划**: 使用 LangGraph 实现复杂任务的分层规划与执行
- **记忆管理**: 集成 Mem0 实现对话历史管理和会话回滚
- **流式响应**: 支持服务端推送事件 (SSE) 的实时响应
- **可扩展架构**: 模块化设计，易于添加新功能和工具

## 技术栈

- **后端框架**: FastAPI
- **AI 框架**: LangChain / LangGraph
- **向量数据库**: Qdrant (通过 Mem0)
- **前端技术**: HTML/CSS/JavaScript (原生实现)
- **容器化**: Docker
- **部署**: Gunicorn + Nginx

## 快速开始

### 环境要求

- Python 3.12+
- Docker (可选，用于依赖服务)

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

复制 [.env.example](file:///D:/WorkSpaces/GitHub/reach-moon/ppec_copilot/.env.example) 文件并重命名为 `.env`，然后根据实际情况修改配置：

```bash
cp .env.example .env
# 编辑 .env 文件
```

### 启动服务

开发模式：

```bash
uvicorn app.api.main:app --reload
```

生产模式：

```bash
gunicorn -c gunicorn_conf.py app.api.main:app
```

### Docker 部署

```bash
docker-compose up -d
```

## API 接口

- `POST /api/v1/chat` - 聊天接口
- `POST /api/v1/revert` - 回滚接口
- `GET /health` - 健康检查

## 架构说明

系统采用分层架构设计：

1. **API 层**: 提供 RESTful API 接口
2. **核心业务层**: 实现 LangGraph 工作流和各类 Agent
3. **服务层**: 封装外部服务调用
4. **配置层**: 统一配置管理

## 测试

运行所有测试：

```bash
pytest
```

运行特定类型测试：

```bash
# 单元测试
pytest tests/unit/

# 组件测试
pytest tests/component/

# 集成测试
pytest tests/integration/

# 端到端测试
pytest tests/e2e/
```

## 文档

- [架构分析](file:///D:/WorkSpaces/GitHub/reach-moon/ppec_copilot/ARCHITECTURE_ANALYSIS.md) - 系统架构详细说明
- [测试框架](file:///D:/WorkSpaces/GitHub/reach-moon/ppec_copilot/TESTING_FRAMEWORK.md) - 测试策略和框架说明
- [部署指南](file:///D:/WorkSpaces/GitHub/reach-moon/ppec_copilot/DEPLOYMENT.md) - 详细部署说明和操作指南

## 许可证

[MIT License](file:///D:/WorkSpaces/GitHub/reach-moon/ppec_copilot/LICENSE)