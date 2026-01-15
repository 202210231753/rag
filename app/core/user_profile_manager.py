from typing import List, BinaryIO
import csv
import io
from app.data.models import UserProfile
from app.data.user_profile_store import UserProfileStore
from app.infra.ai_client import AIModelClient
from app.infra.vector_db import VectorDBClient

class UserProfileManager:
    def __init__(self, store: UserProfileStore, ai_client: AIModelClient, vector_db: VectorDBClient):
        self.store = store
        self.ai_client = ai_client
        self.vector_db = vector_db

    def update_user_interests(self, user_id: str, history: str) -> None:
        """
        利用 LLM 提取动态兴趣。
        TODO: 生产环境中应为异步（Celery/RabbitMQ）
        """
        profile = self.store.load(user_id)
        # 模拟使用简单逻辑或 ai_client 进行 LLM 提取
        # 在现实世界中: intent = self.ai_client.analyze_user_intent(history)
        # 模拟提取：
        extracted_interests = [word for word in history.split() if len(word) > 4]
        
        # 映射到标准标签
        standard_tags = [self.map_to_standard_tag(i) for i in extracted_interests]
        
        # 更新动态兴趣（保持唯一，限制大小）
        current_set = set(profile.dynamic_interests)
        for tag in standard_tags:
            current_set.add(tag)
        profile.dynamic_interests = list(current_set)[:20]
        
        self.store.save(profile)

    def map_to_standard_tag(self, raw_interest: str) -> str:
        """
        将非标兴趣映射为标准标签。
        """
        # 在真实系统中，这里使用 VectorDB search_standard_tags
        # vector = self.ai_client.get_embedding(raw_interest)
        # return self.vector_db.search_standard_tags(vector)
        return raw_interest.lower() # 目前简化处理

    def import_user_dataset(self, source_data: str) -> int:
        """
        解析 CSV 字符串，批量初始化或更新 UserProfileStore。
        格式: user_id,static_tags_comma_separated,location
        """
        count = 0
        profiles_to_save = []
        
        # 简单的 CSV 解析
        lines = source_data.strip().split('\n')
        for line in lines:
            if not line or line.startswith('user_id'): # 跳过表头
                continue
                
            parts = line.split(',')
            if len(parts) >= 1:
                uid = parts[0].strip()
                tags = parts[1].split(';') if len(parts) > 1 else []
                loc = parts[2].strip() if len(parts) > 2 else ""
                
                p = self.store.load(uid)
                p.static_tags = [t.strip() for t in tags if t.strip()]
                p.location = loc
                profiles_to_save.append(p)
                count += 1
        
        self.store.batch_save(profiles_to_save)
        return count

    def manual_override_profile(self, user_id: str, tags: List[str]) -> None:
        """
        允许运营在后台强行修改某个用户的兴趣标签，优先级高于算法提取。
        我们将 static_tags 视为此需求的人工/强制覆盖存储。
        """
        profile = self.store.load(user_id)
        profile.static_tags = tags
        self.store.save(profile)
