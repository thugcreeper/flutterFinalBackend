# 初始化 Firebase 與提供 Firestore 連線。
# 初始化 Firebase 與提供 Firestore 連線。
import firebase_admin
from firebase_admin import credentials, firestore

from app.core.config import settings

_app = None


def get_firebase_app():
    global _app
    if _app is not None:
        return _app

    if settings.FIREBASE_CREDENTIALS_PATH:
        credentials_path = (
            settings.FIREBASE_CREDENTIALS_PATH.strip().strip('"').strip("'")
        )
        cred = credentials.Certificate(credentials_path)
        _app = firebase_admin.initialize_app(cred)
    else:
        _app = firebase_admin.initialize_app()

    return _app


def get_firestore_client():
    app = get_firebase_app()
    return firestore.client(app=app)
