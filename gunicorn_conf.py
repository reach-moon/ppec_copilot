# gunicorn_conf.py
import os

# 确保日志目录存在
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# --- Server Socket ---
# 绑定 IP 和端口
bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")

# --- Worker Processes ---
# 工作进程数量。
# 推荐值为 (2 * CPU核心数) + 1。
# multiprocessing.cpu_count() 会自动获取核心数。
workers = int(os.environ.get("GUNICORN_WORKERS", "1"))  # 调试时使用1个worker

# 工作进程类型。
# 必须使用 uvicorn.workers.UvicornWorker 来运行 ASGI 应用（如 FastAPI）。
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "uvicorn.workers.UvicornWorker")

# Worker timeout
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))

# Worker restart after requests (prevent memory leaks)
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", "100"))

# --- Security ---
# 如果在 Nginx 等反向代理后面运行，限制 Gunicorn 接受的请求来源。
# forwarded_allow_ips = '127.0.0.1'

# --- Logging ---
# 日志级别
loglevel = os.environ.get("GUNICORN_LOGLEVEL", "debug")
# 访问日志文件的路径。'-' 表示输出到 stdout。
accesslog = os.environ.get("GUNICORN_ACCESS_LOG", os.path.join(log_dir, "access.log"))
# 错误日志文件的路径。'-' 表示输出到 stderr。
errorlog = os.environ.get("GUNICORN_ERROR_LOG", os.path.join(log_dir, "error.log"))
# 访问日志格式
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Capture output
capture_output = True

# --- Process Naming ---
# 设置 Gunicorn 进程的名称，方便在 htop 等工具中识别
proc_name = "ppec_copilot"

# --- Prefork ---
# Preload application code before forking worker processes
preload_app = True