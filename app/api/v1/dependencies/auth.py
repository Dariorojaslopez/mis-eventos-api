from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserRead
from app.services.user_service import UserService

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_user_service(session: DbSession) -> UserService:
    return UserService(session)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> UUID:
    if credentials is None:
        raise UnauthorizedError("Not authenticated")

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError) as exc:
        raise UnauthorizedError("Invalid authentication credentials") from exc

    return user_id


CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]


async def get_current_user(
    user_id: CurrentUserId,
    session: DbSession,
) -> UserRead:
    service = UserService(session)
    return await service.get_current_user(user_id)


CurrentUser = Annotated[UserRead, Depends(get_current_user)]


def require_roles(*allowed_roles: UserRole):
    """Factory de dependencia para RBAC — uso: Depends(require_roles(UserRole.ADMIN))."""

    async def _role_checker(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
        session: DbSession,
    ) -> User:
        if credentials is None:
            raise UnauthorizedError("Not authenticated")

        try:
            payload = decode_access_token(credentials.credentials)
            user_id = UUID(payload["sub"])
            token_role = payload.get("role")
        except (ValueError, KeyError) as exc:
            raise UnauthorizedError("Invalid authentication credentials") from exc

        repository = UserRepository(session)
        user = await repository.get_active_by_id(user_id)
        if user is None:
            raise UnauthorizedError("User not found or inactive")

        if user.role.value != token_role:
            raise UnauthorizedError("Token role mismatch")

        if user.role not in allowed_roles:
            raise ForbiddenError(f"Role '{user.role.value}' is not authorized for this operation")

        return user

    return _role_checker
