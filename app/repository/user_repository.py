# 封裝 Firestore 的使用者資料存取操作。
# 封裝 Firestore 的使用者資料存取操作。
from typing import Any

from app.core.config import settings
from app.core.firebase import get_firestore_client


class UserRepository:
    def __init__(self):
        self.db = get_firestore_client()
        self.collection = self.db.collection(settings.FIRESTORE_USERS_COLLECTION)

    def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        doc = self.collection.document(user_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        data["id"] = doc.id
        return data

    def get_by_account(self, account: str) -> dict[str, Any] | None:
        query = self.collection.where("account", "==", account).limit(1)
        docs = list(query.stream())
        if not docs:
            return None
        doc = docs[0]
        data = doc.to_dict()
        data["id"] = doc.id
        return data

    def get_by_google_sub(self, google_sub: str) -> dict[str, Any] | None:
        query = (
            self.collection.where("provider", "==", "google")
            .where("googleSub", "==", google_sub)
            .limit(1)
        )
        docs = list(query.stream())
        if not docs:
            return None
        doc = docs[0]
        data = doc.to_dict()
        data["id"] = doc.id
        return data

    def create(self, user_id: str, payload: dict[str, Any]) -> None:
        self.collection.document(user_id).set(payload)

    def update(self, user_id: str, payload: dict[str, Any]) -> None:
        self.collection.document(user_id).update(payload)

    def delete(self, user_id: str) -> None:
        self.collection.document(user_id).delete()
