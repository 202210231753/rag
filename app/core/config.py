# 读取 .env 配置
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Database
    DB_SERVER: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "rag_user"
    DB_PASSWORD: str = "rag_password"
    DB_NAME: str = "rag_data"

    # Milvus
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: str = "19530"

    # Models
    EMBEDDING_MODEL_PATH: str
    LLM_MODEL_API: str = "http://localhost:8000/v1"

    # OpenAI (Optional fallback)
    OPENAI_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore" # 忽略多余的环境变量
    )

settings = Settings()
