# ---- Stage 1: Builder ----
FROM python:3.11-slim as builder

WORKDIR /app

ENV PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# 复制依赖文件并安装
# 因为 gunicorn 已经在 requirements.txt 中，它会被自动安装
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# ---- Stage 2: Runner ----
FROM python:3.12-slim

# 创建非 root 用户
RUN useradd --create-home appuser
USER appuser
WORKDIR /home/appuser/app

# 从 builder 阶段复制已安装的依赖
# gunicorn 和 uvicorn 会被一起复制过来
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/gunicorn /usr/local/bin/gunicorn
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn

# 复制应用代码和新的 Gunicorn 配置文件
COPY ./app ./app
COPY ./config ./config
COPY gunicorn_conf.py .  # <--- 复制 Gunicorn 配置文件

# 暴露端口
EXPOSE 8000

# 【核心变化】使用 Gunicorn 和我们的配置文件作为启动命令
# -c: 指定配置文件的路径
# app.api.main:app: 指向 FastAPI 应用实例的路径
CMD ["gunicorn", "-c", "gunicorn_conf.py", "app.api.main:app"]