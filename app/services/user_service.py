from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.stats import UserProfile
from app.models.user import UserAccount
from app.schemas.user_schema import TokenResponse, UserInfo, UserLoginRequest, UserRegisterRequest


class UserServiceError(Exception):
    """用户服务错误。"""


class UsernameExistsError(UserServiceError):
    """用户名已存在。"""


class InvalidCredentialsError(UserServiceError):
    """账号或密码错误。"""


class UserNotFoundError(UserServiceError):
    """用户不存在。"""


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def register(self, payload: UserRegisterRequest) -> UserInfo:
        existing = (
            self.db.query(UserAccount)
            .filter(UserAccount.username == payload.username)
            .first()
        )
        if existing:
            raise UsernameExistsError("用户名已存在")

        profile = UserProfile(
            gender=payload.gender,
            age=payload.age,
            city=payload.city,
            signup_ts=datetime.now(),
        )
        self.db.add(profile)
        self.db.flush()

        account = UserAccount(
            id=profile.id,
            username=payload.username,
            password_hash=hash_password(payload.password),
            role="user",
            is_active=True,
        )
        self.db.add(account)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise UsernameExistsError("用户名已存在") from exc

        return UserInfo(
            user_id=account.id,
            username=account.username,
            gender=profile.gender,
            age=profile.age,
            city=profile.city,
            signup_ts=profile.signup_ts,
            role=account.role,
        )

    def login(self, payload: UserLoginRequest) -> TokenResponse:
        account = (
            self.db.query(UserAccount)
            .filter(UserAccount.username == payload.username)
            .first()
        )
        if not account or not account.is_active:
            raise InvalidCredentialsError("账号或密码错误")
        if not verify_password(payload.password, account.password_hash):
            raise InvalidCredentialsError("账号或密码错误")

        profile = self.db.query(UserProfile).filter(UserProfile.id == account.id).first()
        if not profile:
            raise UserNotFoundError("用户基础信息不存在")

        expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        token = create_access_token(subject=str(account.id), expires_delta=expires)

        user = UserInfo(
            user_id=account.id,
            username=account.username,
            gender=profile.gender,
            age=profile.age,
            city=profile.city,
            signup_ts=profile.signup_ts,
            role=account.role,
        )
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=int(expires.total_seconds()),
            user=user,
        )

    def get_user_info(self, user_id: int) -> UserInfo:
        account = self.db.query(UserAccount).filter(UserAccount.id == user_id).first()
        if not account or not account.is_active:
            raise UserNotFoundError("用户不存在")
        profile = self.db.query(UserProfile).filter(UserProfile.id == user_id).first()
        if not profile:
            raise UserNotFoundError("用户基础信息不存在")
        return UserInfo(
            user_id=account.id,
            username=account.username,
            gender=profile.gender,
            age=profile.age,
            city=profile.city,
            signup_ts=profile.signup_ts,
            role=account.role,
        )
