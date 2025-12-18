


大家就按照这个架构来开发，milvus和mysql我都通过docker搭建了。

环境部署：

```
# 1. 创建名为 rag_env 的环境，指定 Python 3.10
conda create -n rag_env python=3.10

# 2. 激活环境
conda activate rag_env

# 3. 确保你在项目根目录下，安装依赖
pip install -r requirements.txt
```





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





