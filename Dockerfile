# ---- Stage 1: Builder ----
FROM python:3.12-slim as builder

# 定义构建参数
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple/
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

# 设置环境变量
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
ENV PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST}

WORKDIR /app

# 配置 pip 使用镜像源
RUN echo "[global]\nindex-url = ${PIP_INDEX_URL}\ntrusted-host = ${PIP_TRUSTED_HOST}\ntimeout = 120\nretries = 5" > /etc/pip.conf

# 升级 pip
RUN pip install --no-cache-dir --upgrade pip

ENV PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=120

# 复制依赖文件并安装
# 使用简化版 requirements 文件以提高构建成功率
COPY requirements-core.txt .
RUN pip install --no-cache-dir --upgrade -r requirements-core.txt

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

# 复制应用代码和配置文件
COPY ./app ./app
COPY ./config ./config
COPY ./gunicorn_conf.py ./gunicorn_conf.py
COPY ./.env ./.env

# 创建日志目录
RUN mkdir -p logs

# 暴露端口
EXPOSE 8000

# 提供一个调试模式的启动命令
# 使用 gunicorn 启动应用
CMD ["gunicorn", "-c", "gunicorn_conf.py", "app.api.main:app"]