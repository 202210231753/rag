# 【部署】后端镜像构建文件
# 使用 Python 3.10 轻量版
FROM python:3.10-slim

# 设置环境变量 (优化 Python 在 Docker 中的表现)
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# 安装系统级依赖 (编译 mysqlclient 和其他库可能需要)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制并安装依赖
COPY requirements.txt .
# 使用清华源加速安装
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目代码
COPY . .

# 启动命令 (开发环境推荐 reload 模式，生产环境去掉 --reload)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]