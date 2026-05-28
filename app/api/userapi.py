# 提供目前登入使用者的查詢、更新與刪除 API。
# 提供目前登入使用者的查詢、更新與刪除 API。
from fastapi import APIRouter, Depends, status

from app.api.authapi import get_current_user_id
from app.schemas.auth import UserResponse
from app.schemas.user import UserUpdateRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix="/users", tags=["users"])
auth_service = AuthService()


@router.get("/me", response_model=UserResponse)
def get_me(user_id: str = Depends(get_current_user_id)):
    return auth_service.get_me(user_id)


# 這裡用 PATCH，因為使用者通常只會改部分欄位，不需要整筆資料覆蓋
# PUT 代表整筆取代，POST 則比較適合建立新資源
@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: UserUpdateRequest,
    user_id: str = Depends(get_current_user_id),
):
    return auth_service.update_user(
        user_id=user_id,
        account=payload.account,
        name=payload.name,
        description=payload.description,
        image_url=payload.imageUrl,
    )


# 這個狀態碼 204 代表成功但不回傳內容，常用在刪除成功後
@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(user_id: str = Depends(get_current_user_id)):
    auth_service.delete_user(user_id)
    return None
