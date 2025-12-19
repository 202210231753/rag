20251218：现在已部署qwen3 4b、es、mysql、milvus、redis（详情如地址见部署指南）
已下载qwen3 embedding0.6b，路径：/home/yl/yl/yl/code-llm/Qwen/Qwen3-Embedding-0.6B
Qwen3-4B-Instruct-2507已部署在服务器上（vllm），端口号8000


大家就按照这个架构来开发
<img width="965" height="940" alt="image" src="https://github.com/user-attachments/assets/8ad7afaa-cbc4-42b7-af37-eae34345240d" />


环境部署：

```
# 1. 创建名为 rag_env 的环境，指定 Python 3.10
conda create -n rag_env python=3.10

# 2. 激活环境
conda activate rag_env

# 3. 确保你在项目根目录下，安装依赖
pip install -r requirements.txt
```


然后要将env.example改为.env



本地启动后端：

```
uvicorn app.main:app --reload
```



mysql+milvus的端口

> ```
> NAME                IMAGE                                      COMMAND                   SERVICE             CREATED          STATUS                   PORTS
> milvus-etcd         quay.io/coreos/etcd:v3.5.5                 "etcd -advertise-cli…"   etcd                6 minutes ago    Up 6 minutes             2379-2380/tcp
> milvus-minio        minio/minio:RELEASE.2023-03-20T20-16-18Z   "/usr/bin/docker-ent…"   minio               6 minutes ago    Up 6 minutes (healthy)   9000/tcp
> milvus-standalone   milvusdb/milvus:v2.3.13                    "/tini -- milvus run…"   milvus-standalone   6 minutes ago    Up 6 minutes             0.0.0.0:9091->9091/tcp, [::]:9091->9091/tcp, 0.0.0.0:19530->19530/tcp, [::]:19530->19530/tcp
> rag_mysql           mysql:8.0                                  "docker-entrypoint.s…"   mysql_db            15 minutes ago   Up 6 minutes             0.0.0.0:3306->3306/tcp, [::]:3306->3306/tcp, 33060/tcp
> ```
>
> 


Qwen3-4B路径：:/home/yl/yl/yl/code-llm/Qwen/Qwen3-4B-Instruct-2507
Qwen3-embedding::/home/yl/yl/yl/code-llm/Qwen/Qwen3-Embedding-0.6B


Qwen3-4B运行命令：（不用你们运行）
CUDA_VISIBLE_DEVICES=0 \
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
python -m vllm.entrypoints.openai.api_server \
  --model /home/yl/yl/yl/code-llm/Qwen/Qwen3-4B-Instruct-2507 \
  --served-model-name Qwen3-4B-Instruct-2507 \
  --host 0.0.0.0 --port 8000 \
  --dtype float16 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.70 \
  --max-num-seqs 32
