# 處理登入、註冊與使用者資料操作的商業邏輯。
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from firebase_admin import auth, firestore

from app.core.security import create_access_token, hash_password, verify_password
from app.repository.user_repository import UserRepository


# AuthService 負責處理使用者註冊、登入、資料更新與刪除等相關邏輯
class AuthService:
    def __init__(self):
        self.user_repo = UserRepository()

    @staticmethod
    # 將時間值轉成 ISO 格式字串
    def _to_iso(value) -> str | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc).isoformat()
        return str(value)

    @staticmethod
    # 清理後回傳給前端的使用者資料
    def _sanitize_user(user: dict) -> dict:
        return {
            "id": user["id"],
            "account": user.get("account", ""),
            "provider": user.get("provider", "local"),
            "name": user.get("name", ""),
            "description": user.get("description", ""),
            "imageUrl": user.get("imageUrl", ""),
            "createdAt": AuthService._to_iso(user.get("createdAt")),
        }

    # 建立本地帳號並回傳登入 token
    def register_local(self, account: str, password: str, name: str = "") -> dict:
        existed = self.user_repo.get_by_account(account)
        if existed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Account already exists",
            )

        user_id = uuid.uuid4().hex
        payload = {
            "account": account,
            "provider": "local",
            "passwordHash": hash_password(password),
            "name": name,
            "description": "",
            "imageUrl": "",
            "createdAt": firestore.SERVER_TIMESTAMP,
        }
        self.user_repo.create(user_id, payload)

        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Create user failed",
            )

        token, expires_in = create_access_token(
            user_id=user["id"], provider=user["provider"]
        )
        return {
            "accessToken": token,
            "expiresIn": expires_in,
            "user": self._sanitize_user(user),
        }

    # 驗證本地帳號與密碼並回傳登入 token
    def login_local(self, account: str, password: str) -> dict:
        user = self.user_repo.get_by_account(account)
        if not user or user.get("provider") != "local":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        if not verify_password(password, user.get("passwordHash", "")):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        token, expires_in = create_access_token(
            user_id=user["id"], provider=user["provider"]
        )
        return {
            "accessToken": token,
            "expiresIn": expires_in,
            "user": self._sanitize_user(user),
        }

    # 驗證 Google idToken 並建立或登入使用者
    def login_google(self, id_token: str) -> dict:
        try:
            # 這裡用firebase的auth邏輯
            claims = auth.verify_id_token(id_token)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token",
            ) from exc

        google_sub = claims.get("uid") or claims.get("sub")
        if not google_sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google token missing subject",
            )

        user = self.user_repo.get_by_google_sub(google_sub)
        if not user:
            user_id = uuid.uuid4().hex
            account = claims.get("email") or f"google:{google_sub}"
            payload = {
                "account": account,
                "provider": "google",
                "passwordHash": "",
                "googleSub": google_sub,
                "name": claims.get("name", ""),
                "description": "",
                "imageUrl": claims.get("picture", ""),
                "createdAt": firestore.SERVER_TIMESTAMP,
            }
            self.user_repo.create(user_id, payload)
            user = self.user_repo.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google login failed",
            )

        token, expires_in = create_access_token(
            user_id=user["id"], provider=user["provider"]
        )
        return {
            "accessToken": token,
            "expiresIn": expires_in,
            "user": self._sanitize_user(user),
        }

    # 依使用者 id 取得目前登入者資料
    def get_me(self, user_id: str) -> dict:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return self._sanitize_user(user)

    # 更新目前登入者的個人資料
    def update_user(
        self,
        user_id: str,
        account: str | None = None,
        name: str | None = None,
        description: str | None = None,
        image_url: str | None = None,
    ) -> dict:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        payload: dict[str, str] = {}

        if account is not None and account != user.get("account", ""):
            existed = self.user_repo.get_by_account(account)
            if existed and existed.get("id") != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Account already exists",
                )
            payload["account"] = account

        if name is not None:
            payload["name"] = name

        if description is not None:
            payload["description"] = description

        if image_url is not None:
            payload["imageUrl"] = image_url

        if payload:
            self.user_repo.update(user_id, payload)

        updated_user = self.user_repo.get_by_id(user_id)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Update user failed",
            )
        return self._sanitize_user(updated_user)

    # 刪除目前登入者資料
    def delete_user(self, user_id: str) -> None:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        self.user_repo.delete(user_id)
