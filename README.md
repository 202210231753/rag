### 数据库
用户画像库：存在mysql中，包含两张表

user_profile：id, gender, age, city, signup_ts

rag_user_traits：id，static_tags，dynamic_interests，negative_tags


内容库，查询库：存在milvus中

milvus：ID，内容片段，标签（根据标签区分query和comment）
