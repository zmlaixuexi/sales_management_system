# 阶段 1：安装依赖
FROM python:3.13-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir --prefix=/install .

# 阶段 2：运行时
FROM python:3.13-slim

WORKDIR /app

# 仅安装运行时系统库
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制 Python 包
COPY --from=builder /install /usr/local

# 复制应用代码
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

# 创建非 root 用户和上传目录
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser \
    && mkdir -p /app/uploads/products \
    && chown -R appuser:appuser /app/uploads

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
