# 初始化 Firebase 與提供 Firestore 連線。
import firebase_admin,json
from firebase_admin import credentials, firestore

from app.core.config import settings

_app = None


def get_firebase_app():
    global _app
    if _app is not None:
        return _app
    if settings.FIREBASE_CREDENTIALS_JSON:
        try:
            # 解析 JSON 字串
            cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
            cred = credentials.Certificate(cred_dict)
            _app = firebase_admin.initialize_app(cred)
            return _app
        except Exception as e:
            print(f"解析 FIREBASE_CREDENTIALS_JSON 失敗: {e}")

    _app = firebase_admin.initialize_app()
    return _app


def get_firestore_client():
    app = get_firebase_app()
    return firestore.client(app=app)
