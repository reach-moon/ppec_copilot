# PPEC Copilot 系统性测试方案与框架

## 概述

本文档描述了 PPEC Copilot 项目的系统性测试方案和框架。该测试体系采用四层测试架构，从单元测试到端到端测试，确保项目的质量、稳定性和可靠性。

## 测试架构层次

### 层次一：单元测试 (Unit Tests)
**目标**: 隔离测试项目中最小的可测试单元（单个函数、类或模块），确保其内部逻辑正确。

**位置**: `tests/unit/`

**关键测试对象与用例**:
- **配置与工具模块** (`config/`, `services/tools/`):
  - 测试 Settings 模型能否从 .env 文件和环境变量中正确加载配置
  - 测试 ragflow_tool 能否正确构建 RAGFlow API 的请求体
  - 测试 ragflow_tool 能否正确解析成功响应和处理错误响应
  - 测试记忆服务能否正确添加、获取和回滚记忆

- **数据模型** (`schemas/`):
  - 测试 Plan 和 PlanStep 模型能否用有效数据成功创建实例
  - 测试模型能否正确地序列化为 JSON 和反序列化
  - 测试包含默认值的字段的默认行为

### 层次二：组件测试 (Component Tests)
**目标**: 测试由多个单元构成的、具有独立业务功能的"组件"，重点是测试 LangChain/LangGraph 链 (Runnable) 的行为。

**位置**: `tests/component/`

**关键测试对象与用例**:
- **Planner 模块**:
  - 测试给定简单 RAG 任务时，生成的 Plan 是否包含调用 ragflow_knowledge_search 的步骤
  - 测试给定复杂 RAG + Code 任务时，生成的 Plan 是否包含两个有序步骤
  - 测试给定模糊任务时，Plan 的合理性

- **Executor 模块**:
  - 测试给定明确知识查询指令时，executor_llm 是否正确选择 ragflow_knowledge_search 工具
  - 测试当指令与任何工具都不匹配时，Executor 的回退行为

- **Summarizer 模块**:
  - 测试给定用户目标和步骤执行结果时，summarizer_chain 能否生成通顺、合理的最终总结

### 层次三：集成测试 (Integration Tests)
**目标**: 测试完整的 LangGraph 工作流，确保所有节点能正确地协同工作，驱动 GraphState 按预期流转。

**位置**: `tests/integration/`

**关键测试对象与用例**:
- **完整的 main_graph 工作流**:
  - **Happy Path (成功路径) - 简单任务**:
    - 模拟简单 RAG 查询，验证最终状态中的 plan 包含 complete 步骤且 final_summary 不为空
    - 验证工作流路径为 retrieve -> plan -> execute -> summarize -> update

  - **Happy Path (成功路径) - 多步任务**:
    - 模拟 RAG+Code 查询，验证最终状态中的 plan 包含两个 complete 步骤
    - 验证 update_memory 节点被调用时传入的 Plan 对象是完整的

  - **自愈路径 (Re-plan Path)**:
    - 模拟 ragflow_tool 在第一次被调用时抛出异常
    - 验证工作流路径包含 ... -> execute -> replan -> execute -> ...
    - 验证 replan_step 节点被成功触发

### 层次四：端到端测试 (End-to-End / E2E Tests)
**目标**: 从外部 API 的角度测试整个应用。模拟真实的用户请求，验证 HTTP 响应是否符合预期。

**位置**: `tests/e2e/`

**关键测试对象与用例**:
- **/chat API 端点**:
  - **测试正常对话**: 发送 POST 请求，验证 SSE 流式响应是否包含预期的 plan_update 和 final_response 事件
  - **测试会话连续性**: 连续调用两次 /chat 接口（使用相同的 session_id），验证第二次调用时 planner_runnable 接收到包含第一次交互结果的上下文

- **/revert API 端点**:
  - **测试回滚功能**:
    1. 调用 /chat 两次，创建两条记忆
    2. 调用 /revert，传入第一次交互的 message_id，验证返回 204 状态码
    3. 再次调用 /chat，验证 mem0_service.get_memory_history 只返回第一条记忆

## 测试框架和工具

### 核心测试框架
- **测试框架**: pytest
- **异步测试**: pytest-asyncio
- **Mocking**: pytest-mock (内置) 或 unittest.mock，用于模拟外部依赖（LLMs, APIs, 数据库）
- **API 测试客户端**: httpx.AsyncClient 或 FastAPI TestClient，与 FastAPI 完美集成
- **代码覆盖率**: pytest-cov，用于衡量测试的覆盖程度，目标是核心业务逻辑覆盖率 > 85%

### 测试策略
1. **隔离性**: 使用 mocking 隔离外部依赖，确保测试的稳定性和速度
2. **自动化**: 所有测试均可自动化运行，无需人工干预
3. **可重复性**: 测试结果应一致且可重现
4. **全面性**: 覆盖正常路径、边界条件和异常情况

## 测试执行

### 运行所有测试
```bash
python -m pytest tests/ -v
```

### 运行特定层级测试
```bash
# 运行单元测试
python -m pytest tests/unit/ -v

# 运行组件测试
python -m pytest tests/component/ -v

# 运行集成测试
python -m pytest tests/integration/ -v

# 运行端到端测试
python -m pytest tests/e2e/ -v
```

### 生成覆盖率报告
```bash
python -m pytest tests/ --cov=app --cov-report=html
```

## 测试维护

### 新增测试
1. 根据变更内容确定测试层级
2. 在对应目录下创建测试文件
3. 遵循现有测试模式和命名约定
4. 确保新测试通过并提供足够的覆盖率

### 测试更新
1. 当功能变更时，相应更新测试用例
2. 定期审查测试覆盖率并补充缺失的测试
3. 重构测试代码以提高可维护性

## 最佳实践

1. **测试命名**: 使用清晰、描述性的测试函数名
2. **测试组织**: 按功能模块组织测试类和方法
3. **断言明确**: 使用明确的断言验证预期结果
4. **数据隔离**: 确保测试间无数据依赖
5. **Mock 合理**: 只 mock 必要的外部依赖
6. **文档完善**: 为复杂测试添加注释说明

## 总结

这套四层测试体系确保了 PPEC Copilot 项目的质量保障：
- **单元测试**保证了基础组件的正确性
- **组件测试**验证了 LangChain 组件的集成
- **集成测试**确保了工作流的正确执行
- **端到端测试**验证了完整的用户场景

通过这套系统性的测试方案，我们可以有效地发现和修复问题，确保项目稳定可靠地运行。