# 集中管理環境變數與應用設定。
# 集中管理環境變數與應用設定。
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-secret-in-production")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
    FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")
    FIRESTORE_USERS_COLLECTION = os.getenv("FIRESTORE_USERS_COLLECTION", "users")


settings = Settings()
