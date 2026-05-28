# FastAPI 主入口，負責建立應用程式並註冊路由。
from fastapi import FastAPI
from app.api.authapi import router as auth_router
from app.api.userapi import router as user_router

app = FastAPI()
app.include_router(auth_router)
app.include_router(user_router)


@app.get("/")
def root():
    return {"message": "RideVoyage API is running"}
