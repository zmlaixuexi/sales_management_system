FROM python:3.13-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# 复制应用代码
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

# 创建上传目录
RUN mkdir -p /app/uploads/products

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
