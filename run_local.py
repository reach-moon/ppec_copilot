#!/usr/bin/env python3
"""
在本地运行 PPEC Copilot 应用进行测试
支持 Windows 和 Unix 系统
"""

import os
import sys
import argparse

def run_with_uvicorn(host="127.0.0.1", port=8000, reload=False):
    """使用 Uvicorn 运行应用"""
    try:
        import uvicorn
    except ImportError:
        print("错误: 未安装 uvicorn")
        print("请运行: pip install uvicorn")
        return False
    
    print(f"使用 Uvicorn 启动应用...")
    print(f"地址: http://{host}:{port}")
    print("按 Ctrl+C 停止应用")
    
    try:
        # 添加项目根目录到 Python 路径
        project_root = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, project_root)
        
        # 确保日志目录存在
        log_dir = os.path.join(project_root, "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 导入并运行应用
        from app.api.main import app
        
        uvicorn.run(
            "app.api.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
        return True
    except KeyboardInterrupt:
        print("\n应用已停止")
        return True
    except Exception as e:
        print(f"运行应用时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_dependencies():
    """检查必要的依赖"""
    dependencies = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "pydantic_settings"
    ]
    
    missing = []
    for dep in dependencies:
        try:
            __import__(dep)
        except ImportError:
            missing.append(dep)
    
    if missing:
        print("缺少以下依赖:")
        for dep in missing:
            print(f"  - {dep}")
        print("\n请运行: pip install " + " ".join(missing))
        return False
    return True

def test_imports():
    """测试关键模块导入"""
    print("测试关键模块导入...")
    
    try:
        # 添加项目根目录到 Python 路径
        project_root = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, project_root)
        
        # 测试配置导入
        from config.settings import settings
        print("✓ 配置模块导入成功")
        print(f"  项目名称: {settings.PROJECT_NAME}")
        
        # 测试主应用导入
        from app.api.main import app
        print("✓ 主应用模块导入成功")
        print(f"  应用标题: {app.title}")
        
        return True
    except Exception as e:
        print(f"✗ 模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description="在本地运行 PPEC Copilot 应用")
    parser.add_argument("--host", default="127.0.0.1", help="绑定的主机地址 (默认: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="绑定的端口 (默认: 8000)")
    parser.add_argument("--reload", action="store_true", help="启用自动重载 (开发模式)")
    parser.add_argument("--test", action="store_true", help="仅测试模块导入")
    
    args = parser.parse_args()
    
    print("PPEC Copilot 本地运行脚本")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        return 1
    
    # 如果是测试模式，仅测试导入
    if args.test:
        success = test_imports()
        return 0 if success else 1
    
    # 运行应用
    success = run_with_uvicorn(args.host, args.port, args.reload)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())