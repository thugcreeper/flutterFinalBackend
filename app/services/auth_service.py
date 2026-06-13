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
        # 統一 provider 的識別名稱
        # 因為 Firebase 傳過來的 provider 有可能是 "google" 或 "google.com"
        raw_provider = claims.get("firebase", {}).get("sign_in_provider", "google")
        provider = "google" if "google" in raw_provider else raw_provider
        # 如果 email 欄位是空的，就直接用 google:sub 當作帳號
        if email_val.strip():
            account = email_val.strip()
        else:
            account = f"google:{google_sub}"
        user = self.user_repo.get_by_google_sub(google_sub)
        if not user:
            # google_sub是 Google 使用者的唯一識別碼
            user_id = google_sub
            # 確保有拿到 email，拿不到才用備用字串
            email_val = claims.get("email")
            account = email_val if email_val else f"google:{google_sub}"
            payload = {
                "account": account,
                "provider": "google",
                "passwordHash": "",
                "googleSub": google_sub,
                "email": (
                    email_val if email_val else "No email!"
                ),  # 補上空字串補底，防止 422
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

    # 驗證 Facebook 登入傳過來的 Firebase idToken 並建立或登入使用者
    def login_facebook(self, id_token: str) -> dict:
        try:
            claims = auth.verify_id_token(id_token)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Facebook Firebase token",
            ) from exc

        fb_sub = claims.get("uid") or claims.get("sub")
        if not fb_sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Facebook token missing subject",
            )

        # 1. 透過你寫好的 get_by_facebook_sub 精準查詢是否有舊用戶
        user = self.user_repo.get_by_facebook_sub(fb_sub)

        if not user:
            # 2. 【關鍵修正】不要用 uuid.uuid4().hex！
            # 直接強制將資料庫的 Document ID 設為 Firebase 的唯一 UID (fb_sub)
            user_id = fb_sub

            email_val = claims.get("email")
            account = email_val if email_val else f"facebook:{fb_sub}"

            # 處理可能結構複雜的 picture 欄位，防止 Pydantic 驗證噴 422
            raw_picture = claims.get("picture", "")
            img_url = ""
            if isinstance(raw_picture, str):
                img_url = raw_picture
            elif isinstance(raw_picture, dict):
                img_url = raw_picture.get("data", {}).get("url", "")

            payload = {
                "account": account,
                "provider": "facebook",
                "passwordHash": "",
                "facebookSub": fb_sub,
                "name": claims.get("name", "FB使用者"),
                "email": email_val if email_val else "",  # 補上空字串補底，防止 422
                "description": "",
                "imageUrl": img_url,
                "createdAt": firestore.SERVER_TIMESTAMP,
            }
            # 3. 建立 Document ID 與 Firebase UID 完全一致的使用者
            self.user_repo.create(user_id, payload)
            user = self.user_repo.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Facebook login failed",
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

        provider = user.get("provider", "local")

        # 如果是第三方登入（Google/Facebook），或者是使用與 Firebase 連動的 local 帳號
        # 由於我們前面把 Firestore ID 設定為 Firebase UID 了，直接用 user_id 去刪除 Firebase Auth 帳號
        if provider in ["google", "facebook"]:
            firebase_uid = user.get("googleSub") or user.get("facebookSub") or user_id
            try:
                auth.delete_user(firebase_uid)
            except auth.UserNotFoundError:
                pass  # 避免 Firebase 那邊如果已經手動刪過會噴 404 錯誤
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete user from Firebase Auth",
                ) from exc

        # 最後刪除 Firestore 的記錄
        self.user_repo.delete(user_id)
