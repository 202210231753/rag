from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api import deps
from app.core.security import TokenError, decode_access_token
from app.schemas.stats_schema import ApiResponse
from app.schemas.user_schema import TokenResponse, UserInfo, UserLoginRequest, UserRegisterRequest
from app.services.user_service import (
    InvalidCredentialsError,
    UserNotFoundError,
    UserService,
    UsernameExistsError,
)

router = APIRouter()
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(deps.get_db),
) -> UserInfo:
    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    subject = payload.get("sub")
    if subject is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌")
    try:
        user_id = int(subject)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌") from exc
    service = UserService(db)
    try:
        return service.get_user_info(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/register", response_model=ApiResponse[UserInfo])
def register_user(
    payload: UserRegisterRequest,
    db: Session = Depends(deps.get_db),
) -> ApiResponse[UserInfo]:
    service = UserService(db)
    try:
        user = service.register(payload)
    except UsernameExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ApiResponse(data=user, msg="注册成功")


@router.post("/login", response_model=ApiResponse[TokenResponse])
def login_user(
    payload: UserLoginRequest,
    db: Session = Depends(deps.get_db),
) -> ApiResponse[TokenResponse]:
    service = UserService(db)
    try:
        token = service.login(payload)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ApiResponse(data=token, msg="登录成功")


@router.get("/me", response_model=ApiResponse[UserInfo])
def get_me(current_user: UserInfo = Depends(get_current_user)) -> ApiResponse[UserInfo]:
    return ApiResponse(data=current_user)
