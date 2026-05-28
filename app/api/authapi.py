# 提供註冊、登入與取得目前使用者身分的 API。
# 提供註冊、登入與取得目前使用者身分的 API。
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token
from app.schemas.auth import (
    AuthResponse,
    GoogleLoginRequest,
    LoginRequest,
    RegisterRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)
auth_service = AuthService()


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing access token",
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token payload",
        )
    return user_id


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest):
    result = auth_service.register_local(
        account=payload.account,
        password=payload.password,
        name=payload.name,
    )
    return {
        "accessToken": result["accessToken"],
        "expiresIn": result["expiresIn"],
        "user": result["user"],
    }


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    result = auth_service.login_local(
        account=payload.account,
        password=payload.password,
    )
    return {
        "accessToken": result["accessToken"],
        "expiresIn": result["expiresIn"],
        "user": result["user"],
    }


@router.post("/googlelogin", response_model=AuthResponse)
def google_login(payload: GoogleLoginRequest):
    result = auth_service.login_google(payload.idToken)
    return {
        "accessToken": result["accessToken"],
        "expiresIn": result["expiresIn"],
        "user": result["user"],
    }
